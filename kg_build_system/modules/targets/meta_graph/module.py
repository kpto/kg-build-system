"""Workflow module that writes the effective topology as a JSON document."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, ClassVar

from ...._frozen_json import freeze_json
from ....compile.interfaces import CompilationContext, ModuleCompiler
from ....modules._paths import validate_relative_path
from ....modules.interfaces import Module, ModuleRegistrationConfiguration
from ....workflow.interfaces import ModuleExecutor
from ....workflow.models import (
    Artifact,
    CandidatePredicate,
    CollectionInputSlot,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    ModuleDefinition,
    ModuleReference,
    OutputSlot,
    StepOutcome,
    StepStatus,
    WorkflowArtifactRoles,
    WorkflowContribution,
    WorkflowStep,
    WorkflowStepDraft,
)
from ...core import CoreArtifactRoles
from .ir import (
    MetaGraphComponentIR,
    MetaGraphDocumentIR,
    decode_meta_graph_instruction,
    encode_meta_graph_instruction,
)
from .topology import component_entries

_MODULE_ID = "meta_graph"


def _own_counts(context: ExecutionContext) -> dict[tuple[str, str], int]:
    """Rows produced per ``(kind, component name)`` graph-record artifact."""
    counts: dict[tuple[str, str], int] = {}
    for contributions in context.inputs.values():
        for contribution in contributions:
            artifact = contribution.artifact
            if artifact is None:
                continue
            identity = CoreArtifactRoles.graph_record_identity(artifact.role)
            if identity is None:
                continue
            key = (identity.kind, identity.component)
            if key in counts:
                # A component must reach this step through exactly one
                # artifact; summing duplicates would silently over-count.
                raise RuntimeError(
                    f"multiple graph-record artifacts for {identity.kind} "
                    f"component {identity.component!r}"
                )
            relation = context.services.relations.reference(artifact.value)
            counts[key] = context.services.relations.query(
                f"SELECT COUNT(*) FROM {relation}"
            ).fetchone()[0]
    return counts


def _inclusive_records(
    component: MetaGraphComponentIR,
    index: dict[tuple[str, str], MetaGraphComponentIR],
    own: dict[tuple[str, str], int],
    active: frozenset[str] = frozenset(),
) -> int:
    """A component's own rows plus every row produced beneath it."""
    if component.name in active:
        raise RuntimeError(
            f"meta-graph component hierarchy cycle includes {component.name!r}"
        )
    total = 0 if component.abstract else own.get(
        (component.kind, component.name), 0,
    )
    active = active | {component.name}
    for child_name in component.children:
        child = index.get((component.kind, child_name))
        if child is not None:
            total += _inclusive_records(child, index, own, active)
    return total


def _document(
    instruction: MetaGraphDocumentIR,
    own: dict[tuple[str, str], int],
    location: str,
) -> dict[str, Any]:
    index = {
        (item.kind, item.name): item for item in instruction.components
    }
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    totals = {"node": 0, "edge": 0}
    for component in sorted(
        instruction.components, key=lambda item: (item.kind, item.symbol_id),
    ):
        entry = component.model_dump(mode="json")
        records = 0 if component.abstract else own.get(
            (component.kind, component.name), 0,
        )
        if not component.abstract:
            totals[component.kind] += records
        entry["counts"] = {
            "records": records,
            "inclusive_records": _inclusive_records(component, index, own),
            "bindings": len(component.bindings),
            "declared_children": len(component.children),
        }
        (nodes if component.kind == "node" else edges).append(entry)
    return {
        "schema_version": instruction.schema_version,
        "generated_by": {
            "module_id": _MODULE_ID,
            "module_version": MetaGraphModule.VERSION,
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
    """Where the document lands beneath the build output directory."""

    relative_path: str = "meta_graph.json"

    def __post_init__(self) -> None:
        validate_relative_path(
            self.relative_path, context="meta-graph document path",
        )


@dataclass(frozen=True)
class MetaGraphModule(Module):
    configuration: MetaGraphModuleConfiguration

    ID: ClassVar[str] = _MODULE_ID
    VERSION: ClassVar[str] = "1"
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
        # Abstract components are never binding targets and so never produce an
        # artifact; only concrete components can be counted.
        counted_roles = frozenset(
            CoreArtifactRoles.graph_records(item.kind, item.name)
            for item in entries if not item.abstract
        )

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
        inputs: tuple[CollectionInputSlot, ...] = ()
        candidates: dict[str, CandidatePredicate] = {}
        if counted_roles:
            records = CollectionInputSlot(slot_id="meta_graph::document.records")
            inputs = (records,)
            candidates = {
                records.slot_id: lambda _input, candidate, expected=counted_roles: (
                    candidate.artifact_role in expected
                ),
            }
        step = WorkflowStep(
            step_id="meta_graph::document",
            module_id=self.ID,
            inputs=inputs,
            outputs=(OutputSlot(
                slot_id="meta_graph::document.result",
                artifact_role=WorkflowArtifactRoles.published(
                    self.ID, "meta_graph_document",
                ),
            ),),
            payload=encode_meta_graph_instruction(MetaGraphDocumentIR(
                relative_path=self.configuration.relative_path,
                components=entries,
            )),
        )
        return WorkflowContribution(definition, (WorkflowStepDraft(
            definition=step,
            assembly_preference="deferred",
            candidates=candidates,
        ),))


class MetaGraphExecutor(ModuleExecutor):
    def handle(self, context: ExecutionContext) -> StepOutcome:
        instruction = decode_meta_graph_instruction(context.step.payload)
        # The path came from a serialized contract, so re-check it cannot escape.
        validate_relative_path(
            instruction.relative_path, context="meta-graph document path",
        )
        output_path = context.services.output_storage.child(
            PurePosixPath(instruction.relative_path),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        document = _document(
            instruction, _own_counts(context), str(output_path),
        )
        output_path.write_text(
            json.dumps(document, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

        output = context.step.outputs[0]
        artifact = Artifact(
            output.slot_id, output.artifact_role, dict(document["summary"]),
        )
        return StepOutcome(
            step_id=context.step.step_id,
            module_id=context.step.module_id,
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
