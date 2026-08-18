"""Workflow target that writes a Neo4j administrative-import bundle."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, ClassVar, Literal, cast

from ...._frozen_json import freeze_json, thaw_json
from ....annotations import EdgeLabel, NodeLabel
from ....compile.interfaces import CompilationContext, ModuleCompiler
from ....modules.interfaces import Module, ModuleRegistrationConfiguration
from ....topology.ir import ComponentIR
from ....workflow.interfaces import ModuleExecutor
from ....workflow.models import (
    Artifact,
    ArtifactRole,
    CollectionInputSlot,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    ModuleDefinition,
    ModuleReference,
    OutputSlot,
    RuntimeFieldDefinition,
    SingleInputSlot,
    StepOutcome,
    StepStatus,
    WorkflowArtifactRoles,
    WorkflowContribution,
    WorkflowStep,
    WorkflowStepDraft,
)
from ....workflow.services import RelationRef
from ...core import CoreArtifactRoles
from .ir import (
    Neo4jComponentImportIR,
    Neo4jEdgeImportIR,
    Neo4jExportInstructionIR,
    Neo4jNodeImportIR,
    Neo4jScriptInstructionIR,
    decode_neo4j_instruction,
    encode_neo4j_instruction,
)
from .script import render_import_script


_HEADER_CONTROL = frozenset(":{}\r\n")
_MODULE_ID = "neo4j"
_RESERVED_PROPERTIES = frozenset({
    "build_key", "source_build_key", "target_build_key", "_kg_binding_symbol",
})


def _validate_relative_path(value: str, *, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{context} must be relative to the build output directory")


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


def _sql_string(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _component_stem(component: ComponentIR) -> str:
    readable = re.sub(r"[^A-Za-z0-9._-]+", "_", component.name).strip("._-")
    readable = readable or component.kind
    digest = sha256(component.symbol_id.encode("utf-8")).hexdigest()[:8]
    return f"{readable}-{digest}"


def _id_space(component: ComponentIR) -> str:
    digest = sha256(component.symbol_id.encode("utf-8")).hexdigest()[:16]
    return f"kg_{digest}"


def _component_export_role(
    specification: Neo4jComponentImportIR,
) -> ArtifactRole:
    return ArtifactRole(
        namespace=_MODULE_ID,
        name=f"component.{specification.kind}.{specification.symbol_id}",
    )


def _component_step_key(specification: Neo4jComponentImportIR) -> str:
    stem = PurePosixPath(specification.relative_path).stem
    return f"{specification.kind}.{stem}"


def _annotation_label(component: ComponentIR) -> str:
    expected = NodeLabel if component.kind == "node" else EdgeLabel
    opposite = EdgeLabel if component.kind == "node" else NodeLabel
    wrong = [
        item for item in component.annotations
        if item.namespace == opposite.namespace
        and item.annotation_id == opposite.annotation_id
    ]
    if wrong:
        raise ValueError(
            f"{component.kind} component {component.name!r} has an incompatible "
            f"{opposite.__name__} annotation"
        )
    matches = [
        item for item in component.annotations
        if item.namespace == expected.namespace
        and item.annotation_id == expected.annotation_id
    ]
    if len(matches) > 1:
        raise ValueError(
            f"{component.kind} component {component.name!r} accepts at most one "
            f"{expected.__name__} annotation"
        )
    if not matches:
        label = component.name
    else:
        arguments = thaw_json(matches[0].arguments)
        if not isinstance(arguments, dict) or set(arguments) != {"label"}:
            raise ValueError(f"{expected.__name__} has invalid serialized arguments")
        label = arguments["label"]
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"{expected.__name__} label must be a non-empty string")
    if component.kind == "node" and ";" in label:
        raise ValueError(
            f"node component {component.name!r} must have a single Neo4j label"
        )
    return label


def _validate_properties(component: ComponentIR) -> tuple[str, ...]:
    names = tuple(item.name for item in component.properties)
    for name in names:
        if name in _RESERVED_PROPERTIES:
            raise ValueError(
                f"component {component.name!r} property {name!r} conflicts with "
                "a graph-record import field"
            )
        if any(character in name for character in _HEADER_CONTROL):
            raise ValueError(
                f"component {component.name!r} property {name!r} cannot be encoded "
                "as an inline Neo4j import header"
            )
    return names


@dataclass(frozen=True)
class Neo4jModuleConfiguration(ModuleRegistrationConfiguration):
    relative_directory: str = "neo4j-import"
    script_name: str = "import_neo4j.py"
    default_database: str = "neo4j"

    def __post_init__(self) -> None:
        _validate_relative_path(
            self.relative_directory, context="Neo4j output directory"
        )
        _validate_relative_path(self.script_name, context="Neo4j script name")
        if len(Path(self.script_name).parts) != 1 or not self.script_name.endswith(".py"):
            raise ValueError("Neo4j script name must be a Python filename")
        if not isinstance(self.default_database, str) or not self.default_database.strip():
            raise ValueError("Neo4j default database must be non-empty")


@dataclass(frozen=True, slots=True)
class Neo4jComponentExport:
    kind: Literal["node", "edge"]
    component: str
    relative_path: str
    rows: int


@dataclass(frozen=True)
class Neo4jModule(Module):
    configuration: Neo4jModuleConfiguration

    ID: ClassVar[str] = _MODULE_ID
    VERSION: ClassVar[str] = "2"
    CONFIGURATION_TYPE: ClassVar[type[Neo4jModuleConfiguration]] = (
        Neo4jModuleConfiguration
    )

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return cls(context.configuration)

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return Neo4jExecutor(dict(context.runtime_configuration))

    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        components = self._component_imports(context)
        definition = ModuleDefinition(
            reference=ModuleReference(
                module_id=self.ID,
                import_module=type(self).__module__,
                class_qualname=type(self).__qualname__,
                implementation_version=self.VERSION,
                configuration=freeze_json({
                    "default_database": self.configuration.default_database,
                    "relative_directory": self.configuration.relative_directory,
                    "script_name": self.configuration.script_name,
                }),
            ),
            runtime_fields=(RuntimeFieldDefinition(
                key="relative_directory",
                description=(
                    "Optional runtime replacement for the Neo4j import-bundle directory."
                ),
                required=False,
            ),),
        )
        exports = tuple(
            self._component_export_step(component) for component in components
        )
        return WorkflowContribution(
            definition,
            (*exports, self._script_step(components)),
        )

    @classmethod
    def _component_export_step(
        cls, component: Neo4jComponentImportIR,
    ) -> WorkflowStepDraft:
        key = _component_step_key(component)
        records = SingleInputSlot(slot_id=f"neo4j::export.{key}.records")
        output = OutputSlot(
            slot_id=f"neo4j::export.{key}.result",
            artifact_role=_component_export_role(component),
        )
        step = WorkflowStep(
            step_id=f"neo4j::export.{key}",
            module_id=cls.ID,
            inputs=(records,),
            outputs=(output,),
            payload=encode_neo4j_instruction(Neo4jExportInstructionIR(
                component=component,
            )),
        )
        expected_role = CoreArtifactRoles.graph_records(
            component.kind, component.component,
        )
        return WorkflowStepDraft(
            definition=step,
            assembly_preference="deferred",
            candidates={
                records.slot_id: lambda _input, candidate, role=expected_role: (
                    candidate.artifact_role == role
                )
            },
        )

    def _script_step(
        self, components: tuple[Neo4jComponentImportIR, ...],
    ) -> WorkflowStepDraft:
        inputs = CollectionInputSlot(slot_id="neo4j::script.components")
        output = OutputSlot(
            slot_id="neo4j::script.result",
            artifact_role=WorkflowArtifactRoles.published(self.ID, "import_bundle"),
        )
        step = WorkflowStep(
            step_id="neo4j::script",
            module_id=self.ID,
            inputs=(inputs,),
            outputs=(output,),
            payload=encode_neo4j_instruction(Neo4jScriptInstructionIR(
                components=components,
                script_name=self.configuration.script_name,
                default_database=self.configuration.default_database,
            )),
        )
        roles = frozenset(_component_export_role(item) for item in components)
        return WorkflowStepDraft(
            definition=step,
            assembly_preference="deferred",
            candidates={
                inputs.slot_id: lambda _input, candidate, expected=roles: (
                    candidate.artifact_role in expected
                )
            },
        )

    @staticmethod
    def _component_imports(
        context: CompilationContext[Any],
    ) -> tuple[Neo4jComponentImportIR, ...]:
        bound_components = {
            binding.component for binding in context.blueprint.bindings
        }
        ordered = tuple(sorted(
            (
                component for component in context.blueprint.components
                if component.name in bound_components
            ),
            key=lambda item: (item.kind, item.symbol_id),
        ))
        node_spaces = {
            component.name: _id_space(component)
            for component in ordered
            if component.kind == "node"
        }
        imports: list[Neo4jComponentImportIR] = []
        for component in ordered:
            label = _annotation_label(component)
            properties = _validate_properties(component)
            stem = _component_stem(component)
            if component.kind == "node":
                imports.append(Neo4jNodeImportIR(
                    component=component.name,
                    symbol_id=component.symbol_id,
                    label=label,
                    relative_path=f"nodes/{stem}.parquet",
                    properties=properties,
                    id_space=node_spaces[component.name],
                ))
                continue
            if component.source not in node_spaces or component.target not in node_spaces:
                raise ValueError(
                    f"edge component {component.name!r} requires bound source and "
                    "target node components"
                )
            imports.append(Neo4jEdgeImportIR(
                component=component.name,
                symbol_id=component.symbol_id,
                label=label,
                relative_path=f"relationships/{stem}.parquet",
                properties=properties,
                source_id_space=node_spaces[cast(str, component.source)],
                target_id_space=node_spaces[cast(str, component.target)],
            ))
        return tuple(imports)


class Neo4jExecutor(ModuleExecutor):
    def __init__(self, runtime_configuration: dict[str, Any]) -> None:
        self._runtime_configuration = runtime_configuration

    def _relative_directory(self, context: ExecutionContext) -> str:
        compiled = thaw_json(context.module.reference.configuration)  # type: ignore[arg-type]
        if not isinstance(compiled, dict):
            raise RuntimeError("Neo4j module requires an object configuration")
        value = self._runtime_configuration.get(
            "relative_directory", compiled.get("relative_directory")
        )
        if not isinstance(value, str):
            raise TypeError("runtime Neo4j output directory must be a string")
        _validate_relative_path(value, context="Neo4j output directory")
        return value

    def handle(self, context: ExecutionContext) -> StepOutcome:
        instruction = decode_neo4j_instruction(context.step.payload)
        bundle_path = context.services.output_storage.child(PurePosixPath(
            self._relative_directory(context)
        ))
        bundle_path.mkdir(parents=True, exist_ok=True)
        if isinstance(instruction, Neo4jExportInstructionIR):
            return self._export_component(context, bundle_path, instruction)
        return self._write_script(context, bundle_path, instruction)

    @staticmethod
    def _export_component(
        context: ExecutionContext,
        bundle_path: Path,
        instruction: Neo4jExportInstructionIR,
    ) -> StepOutcome:
        specification = instruction.component
        artifacts = tuple(
            contribution.artifact
            for contributions in context.inputs.values()
            for contribution in contributions
            if contribution.artifact is not None
        )
        if len(artifacts) != 1:
            raise RuntimeError(
                f"Neo4j component export {specification.component!r} requires "
                "exactly one graph-record artifact"
            )
        artifact = artifacts[0]
        identity = CoreArtifactRoles.graph_record_identity(artifact.role)
        if (
            identity is None
            or identity.kind != specification.kind
            or identity.component != specification.component
        ):
            raise RuntimeError(
                f"unexpected graph-record artifact for {specification.component!r}"
            )
        if not isinstance(artifact.value, RelationRef):
            raise TypeError("graph-record artifacts must contain RelationRef values")

        relation_sql = context.services.relations.reference(artifact.value)
        output_path = bundle_path.joinpath(
            *PurePosixPath(specification.relative_path).parts
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        context.services.relations.export_parquet(
            Neo4jExecutor._select_sql(specification, relation_sql), output_path,
        )
        count = context.services.relations.query(
            "SELECT count(*) FROM read_parquet(?)", [str(output_path)]
        ).fetchone()[0]
        result = Neo4jComponentExport(
            kind=specification.kind,
            component=specification.component,
            relative_path=specification.relative_path,
            rows=int(count),
        )
        output = context.step.outputs[0]
        return StepOutcome(
            context.step.step_id,
            context.step.module_id,
            StepStatus.SUCCEEDED,
            (Artifact(output.slot_id, output.artifact_role, result),),
        )

    @staticmethod
    def _write_script(
        context: ExecutionContext,
        bundle_path: Path,
        instruction: Neo4jScriptInstructionIR,
    ) -> StepOutcome:
        expected = {
            (item.kind, item.component): item for item in instruction.components
        }
        exports: dict[tuple[str, str], Neo4jComponentExport] = {}
        for contributions in context.inputs.values():
            for contribution in contributions:
                artifact = contribution.artifact
                if artifact is None:
                    continue
                if not isinstance(artifact.value, Neo4jComponentExport):
                    raise TypeError(
                        "Neo4j script inputs must contain component export results"
                    )
                result = artifact.value
                key = (result.kind, result.component)
                if key not in expected or result.relative_path != expected[key].relative_path:
                    raise RuntimeError(f"unexpected Neo4j component export {key}")
                if key in exports:
                    raise RuntimeError(f"duplicate Neo4j component export {key}")
                exports[key] = result

        missing = set(expected) - set(exports)
        if missing:
            names = ", ".join(f"{kind}:{name}" for kind, name in sorted(missing))
            raise RuntimeError(f"missing Neo4j component exports for {names}")

        node_paths = tuple(
            item.relative_path for item in instruction.components if item.kind == "node"
        )
        relationship_paths = tuple(
            item.relative_path for item in instruction.components if item.kind == "edge"
        )
        script_path = bundle_path / instruction.script_name
        script_path.write_text(render_import_script(
            node_paths=node_paths,
            relationship_paths=relationship_paths,
            default_database=instruction.default_database,
        ), encoding="utf-8", newline="\n")
        if os.name != "nt":
            script_path.chmod(script_path.stat().st_mode | 0o111)

        counts: dict[Literal["node", "edge"], int] = {"node": 0, "edge": 0}
        for result in exports.values():
            counts[result.kind] += result.rows
        summary = {
            "directory": str(bundle_path),
            "script": str(script_path),
            "nodes": counts["node"],
            "edges": counts["edge"],
            "node_files": list(node_paths),
            "relationship_files": list(relationship_paths),
        }
        output = context.step.outputs[0]
        return StepOutcome(
            context.step.step_id,
            context.step.module_id,
            StepStatus.SUCCEEDED,
            (Artifact(output.slot_id, output.artifact_role, summary),),
        )

    @staticmethod
    def _select_sql(
        specification: Neo4jComponentImportIR, relation_sql: str,
    ) -> str:
        columns: list[str]
        if isinstance(specification, Neo4jNodeImportIR):
            columns = [
                'CAST("build_key" AS VARCHAR) AS '
                f'"build_key:ID({specification.id_space})"'
            ]
        else:
            columns = [
                'CAST("build_key" AS VARCHAR) AS "build_key"',
                'CAST("source_build_key" AS VARCHAR) AS '
                f'":START_ID({specification.source_id_space})"',
                'CAST("target_build_key" AS VARCHAR) AS '
                f'":END_ID({specification.target_id_space})"',
            ]
        columns.extend(
            f'"{_quote_identifier(name)}"' for name in specification.properties
        )
        special = ":LABEL" if specification.kind == "node" else ":TYPE"
        columns.append(f'{_sql_string(specification.label)} AS "{special}"')
        return (
            "SELECT " + ", ".join(columns)
            + f" FROM {relation_sql}"
        )

    def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return super().handle_disrupted(context)


__all__ = ["Neo4jModule", "Neo4jModuleConfiguration"]
