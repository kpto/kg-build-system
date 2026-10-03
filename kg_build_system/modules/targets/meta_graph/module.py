"""Workflow module that describes the effective topology as JSON and HTML."""
from __future__ import annotations

import datetime
import json
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, ClassVar

from ...._frozen_json import freeze_json
from ....types import canonical_value_text
from ....compile.interfaces import CompilationContext, ModuleCompiler
from ....modules._paths import validate_relative_path
from ....modules.interfaces import Module, ModuleRegistrationConfiguration
from ....workflow.identity import output_name
from ....workflow.interfaces import ModuleExecutor
from ....workflow.models import (
    Artifact,
    ArtifactType,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    Input,
    ModuleDefinition,
    ModuleReference,
    Publication,
    StepOutcome,
    StepStatus,
    WorkflowContribution,
    WorkflowStep,
)
from ...core import CoreArtifactTypes
from .ir import (
    MetaGraphComponentIR,
    MetaGraphDocumentIR,
    decode_meta_graph_instruction,
    encode_meta_graph_instruction,
)
from .render import render
from .topology import component_entries

_MODULE_ID = "meta_graph"

_RECORDS_INPUT = "records"

# The step name doubles as the key its instruction is stored under in variables.
_DOCUMENT_STEP_NAME = "document"

# Count column for the aggregate observation query. Prefixed like core's own
# ``_kg_binding_symbol`` so it cannot collide with an authored property name.
_TOTAL_COLUMN = "_kg_example_count"


def _canonical_example_value(value: Any) -> Any:
    """The canonical text form of one observed value, as the file target writes it.

    The document quotes values straight out of the graph relation, so a ``date``,
    ``time``, ``timestamp`` or ``uuid`` column arrives as the Python object DuckDB
    hands back, and a scalar with a canonical text form takes it from the shared
    mapping. A value outside the canonical vocabulary — a ``bytes`` or ``Decimal``
    the boundary should have refused — has no form here and raises naming its type,
    rather than being quietly stringified into a document that is supposed to be
    reproducible.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time, uuid.UUID)):
        return canonical_value_text(value)
    if isinstance(value, dict):
        return {key: _canonical_example_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_example_value(item) for item in value]
    raise TypeError(
        f"example value of type {type(value).__qualname__} has no canonical form"
        " in the meta-graph document"
    )


def _example_order_key(value: Any) -> tuple[str, str]:
    """Order example values by canonical text form, then by ``repr`` of the value.

    Ordering the values themselves is not available: an inherited list is pooled by
    property name, so a bool can meet an int, and Python refuses to compare a str
    with either. The primary key is therefore the JSON text the value is written
    as — defined for every canonical value, and the text the document shows, so the
    list reads in the order it prints. The secondary key is for the pair the text
    cannot separate, a ``date`` and a string spelling it identically; ``repr`` of
    the original value settles it because the canonicaliser has already rejected
    anything whose repr is not itself stable.
    """
    return (
        json.dumps(_canonical_example_value(value), sort_keys=True), repr(value),
    )


@dataclass(frozen=True, slots=True)
class _Observed:
    """What the emitted graph records say about one component."""

    records: int = 0
    values: dict[str, list[Any]] | None = None


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _observe(
    relation: str,
    properties: tuple[str, ...],
    value_limit: int,
    context: ExecutionContext,
) -> _Observed:
    """Exact row count plus example values for ``properties``, in one pass.

    Both are plain aggregates, so the relation is streamed once with memory that
    does not depend on its size. The obvious alternatives are worse: a second
    ``ORDER BY ... LIMIT`` query traverses everything again, and folding the
    count into a sample with ``COUNT(*) OVER ()`` measured 300x slower and two
    gigabytes of spill at forty million rows, because a window function must
    materialise its input to know the total.

    ``approx_top_k`` is a frequency sketch, so examples are the most common
    values rather than the first in key order. Exact counts and bounded memory
    both depend on staying aggregate-only; a sorted sample would cost a further
    traversal.
    """
    select = [f"COUNT(*) AS {_quote(_TOTAL_COLUMN)}"]
    select += [
        f"approx_top_k({_quote(name)}, {value_limit}) AS {_quote(name)}"
        for name in properties
    ]
    query = context.services.relations.query(
        f"SELECT {', '.join(select)} FROM {relation}"
    )
    columns = tuple(column[0] for column in query.description)
    row = dict(zip(columns, query.fetchone(), strict=True))
    return _Observed(
        records=int(row[_TOTAL_COLUMN]),
        values={
            # Canonicalised and ordered here, so every later stage — pooling,
            # deduplication, the written document — works on the text the
            # document shows; the sketch's own order is not contractual.
            name: [
                _canonical_example_value(item)
                for item in sorted(row.get(name) or [], key=_example_order_key)
            ][:value_limit]
            for name in properties
        },
    )


def _observed_components(
    context: ExecutionContext, instruction: MetaGraphDocumentIR,
) -> dict[tuple[str, str], _Observed]:
    """Measure every graph-record artifact this step was given."""
    declared = {
        (item.kind, item.name): tuple(prop.name for prop in item.properties)
        for item in instruction.components
    }
    limit = instruction.example_limit
    observed: dict[tuple[str, str], _Observed] = {}
    for contribution in context.inputs.get(_RECORDS_INPUT, ()):
        artifact = contribution.artifact
        if artifact is None:
            continue
        identity = CoreArtifactTypes.graph_record_identity(artifact.type)
        if identity is None:
            continue
        key = (identity.kind, identity.component)
        if key in observed:
            # A component must reach this step through exactly one
            # artifact; summing duplicates would silently over-count.
            raise RuntimeError(
                f"multiple graph-record artifacts for {identity.kind} "
                f"component {identity.component!r}"
            )
        relation = context.services.relations.reference(artifact.value)
        if limit > 0:
            observed[key] = _observe(
                relation, declared.get(key, ()), limit, context,
            )
        else:
            observed[key] = _Observed(
                records=context.services.relations.query(
                    f"SELECT COUNT(*) FROM {relation}"
                ).fetchone()[0],
            )
    return observed


def _inclusive_records(
    component: MetaGraphComponentIR,
    index: dict[tuple[str, str], MetaGraphComponentIR],
    observed: dict[tuple[str, str], _Observed],
    active: frozenset[str] = frozenset(),
) -> int:
    """A component's own rows plus every row produced beneath it."""
    if component.name in active:
        raise RuntimeError(
            f"meta-graph component hierarchy cycle includes {component.name!r}"
        )
    total = 0 if component.abstract else observed.get(
        (component.kind, component.name), _Observed(),
    ).records
    active = active | {component.name}
    for child_name in component.children:
        child = index.get((component.kind, child_name))
        if child is not None:
            total += _inclusive_records(child, index, observed, active)
    return total


def _inclusive_values(
    component: MetaGraphComponentIR,
    index: dict[tuple[str, str], MetaGraphComponentIR],
    observed: dict[tuple[str, str], _Observed],
    limit: int,
    active: frozenset[str] = frozenset(),
) -> dict[str, list[Any]]:
    """Example values for a component, inherited from descendants by name.

    A category never emits rows, so its own properties have no values of their
    own. Pooling the values observed on the components beneath it is the only
    way a category entry can carry evidence about the properties it declares.
    """
    if component.name in active:
        raise RuntimeError(
            f"meta-graph component hierarchy cycle includes {component.name!r}"
        )
    active = active | {component.name}
    pooled: dict[str, list[Any]] = dict(
        observed.get((component.kind, component.name), _Observed()).values or {}
    )
    for child_name in component.children:
        child = index.get((component.kind, child_name))
        if child is None:
            continue
        for name, values in _inclusive_values(
            child, index, observed, limit, active,
        ).items():
            pooled.setdefault(name, []).extend(values)
    return {
        # Ordered and deduplicated so an inherited list is stable regardless of
        # which descendants contributed, then trimmed back to the limit.
        name: sorted(dict.fromkeys(values), key=_example_order_key)[:limit]
        for name, values in pooled.items()
    }


def _document(
    instruction: MetaGraphDocumentIR,
    observed: dict[tuple[str, str], _Observed],
    location: str,
) -> dict[str, Any]:
    index = {
        (item.kind, item.name): item for item in instruction.components
    }
    examples_enabled = instruction.example_limit > 0
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    totals = {"node": 0, "edge": 0}
    for component in sorted(
        instruction.components, key=lambda item: (item.kind, item.symbol_id),
    ):
        entry = component.model_dump(mode="json")
        records = 0 if component.abstract else observed.get(
            (component.kind, component.name), _Observed(),
        ).records
        if not component.abstract:
            totals[component.kind] += records
        entry["counts"] = {
            "records": records,
            "inclusive_records": _inclusive_records(component, index, observed),
            "bindings": len(component.bindings),
            "declared_children": len(component.children),
        }
        if examples_enabled:
            values = _inclusive_values(
                component, index, observed, instruction.example_limit,
            )
            for prop in entry["properties"]:
                prop["examples"] = values.get(prop["name"], [])
        (nodes if component.kind == "node" else edges).append(entry)
    return {
        "schema_version": instruction.schema_version,
        "generated_by": {
            "module_id": _MODULE_ID,
            "module_version": MetaGraphModule.VERSION,
        },
        "examples": {
            "method": "approx_top_k",
            "limit": instruction.example_limit,
        },
        "summary": {
            "node_components": len(nodes),
            "edge_components": len(edges),
            "abstract_components": sum(
                1 for item in instruction.components if item.abstract
            ),
            "total_nodes": totals["node"],
            "total_edges": totals["edge"],
            "location": location,
        },
        "nodes": nodes,
        "edges": edges,
    }


@dataclass(frozen=True)
class MetaGraphModuleConfiguration(ModuleRegistrationConfiguration):
    """Where the document lands, and how much of the data it may quote."""

    relative_path: str = "meta_graph.json"
    example_limit: int = 3
    include_html: bool = True
    html_relative_path: str = "meta_graph.html"

    def __post_init__(self) -> None:
        validate_relative_path(
            self.relative_path, context="meta-graph document path",
        )
        validate_relative_path(
            self.html_relative_path, context="meta-graph HTML path",
        )
        if self.example_limit < 0:
            raise ValueError("meta-graph example limit may not be negative")


@dataclass(frozen=True)
class MetaGraphModule(Module):
    configuration: MetaGraphModuleConfiguration

    ID: ClassVar[str] = _MODULE_ID
    VERSION: ClassVar[str] = "2"
    CONFIGURATION_TYPE: ClassVar[
        type[MetaGraphModuleConfiguration]
    ] = MetaGraphModuleConfiguration

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return cls(context.configuration)

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return MetaGraphExecutor()

    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        entries = component_entries(context.blueprint)
        definition = ModuleDefinition(
            reference=ModuleReference(
                module_id=self.ID,
                import_module=type(self).__module__,
                class_qualname=type(self).__qualname__,
                implementation_version=self.VERSION,
                configuration=freeze_json({
                    "relative_path": self.configuration.relative_path,
                }),
            ),
        )
        step = WorkflowStep(
            inputs=(Input(ArtifactType("core", "graph.*"), name=_RECORDS_INPUT),),
            outputs=(
                Publication(
                    ArtifactType(self.ID, "meta_graph_document"), name="result",
                ),
            ),
            name=_DOCUMENT_STEP_NAME,
            assembly_preference="deferred",
        )
        instruction = encode_meta_graph_instruction(MetaGraphDocumentIR(
            relative_path=self.configuration.relative_path,
            example_limit=self.configuration.example_limit,
            include_html=self.configuration.include_html,
            html_relative_path=self.configuration.html_relative_path,
            components=entries,
        ))
        return WorkflowContribution(
            definition,
            (step,),
            freeze_json({"instructions": {_DOCUMENT_STEP_NAME: instruction}}),
        )


class MetaGraphExecutor(ModuleExecutor):
    def handle(self, context: ExecutionContext) -> StepOutcome:
        instruction = decode_meta_graph_instruction(
            context.variables["instructions"][context.step.name],
        )
        # The path came from a serialized contract, so re-check it cannot escape.
        validate_relative_path(
            instruction.relative_path, context="meta-graph document path",
        )
        output_path = context.services.output_storage.child(
            PurePosixPath(instruction.relative_path),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        document = _document(
            instruction, _observed_components(context, instruction), str(output_path),
        )

        html_path = None
        if instruction.include_html:
            validate_relative_path(
                instruction.html_relative_path, context="meta-graph HTML path",
            )
            html_path = context.services.output_storage.child(
                PurePosixPath(instruction.html_relative_path),
            )
            # Recorded before either file is written, so the JSON on disk and
            # the copy embedded in the page name the same pair.
            document["summary"]["html_location"] = str(html_path)

        output_path.write_text(
            # Examples are canonicalised as they are observed, so nothing here
            # should need the hook. It stays as the fail-closed last line: a value
            # that reached the document without a canonical form is a bug, and
            # ``default=str`` would have hidden it behind a spelling the file
            # target never writes.
            json.dumps(
                document, sort_keys=True, indent=2, default=_canonical_example_value,
            ) + "\n",
            encoding="utf-8",
        )

        if html_path is not None:
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(render(document), encoding="utf-8")

        output = context.step.outputs[0]
        artifact = Artifact(
            output_name(output), output.type, dict(document["summary"]),
        )
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(artifact,),
        )

    def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return super().handle_disrupted(context)


__all__ = [
    "MetaGraphModule",
    "MetaGraphModuleConfiguration",
]
