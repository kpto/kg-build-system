"""Built-in module for portable DuckDB workflow steps and artifact roles.

``CoreArtifactRoles`` is the extension-facing vocabulary for artifacts
published by core graph work.  Modules should use it instead of role strings.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal

from ...compile.models import (
    ArtifactRole,
    BindingDefinition,
    BuildBlueprint,
    CollectionInputSlot,
    ModuleDefinition,
    ModuleReference,
    OutputSlot,
    SourceDefinition,
    WorkflowStep,
)
from ...workflow.interfaces import Module, ModuleCompilationResult, ModuleCompiler, ModuleExecutor, WorkflowStepDraft
from ...workflow.models import Artifact, ModuleExecutionContext, StepOutcome, StepStatus
from .lowering import lower_binding_sql


@dataclass(frozen=True)
class GraphRecordArtifact:
    """The component described by a core graph-record role."""

    kind: Literal["node", "edge"]
    component: str


class CoreArtifactRoles:
    """Stable semantic roles produced by the core module.

    ``graph_records`` and ``published`` are the supported extension-facing
    roles.  Temporary DuckDB relation names are executor details, never
    workflow vocabulary.
    """

    NAMESPACE = "core"

    @classmethod
    def graph_records(cls, kind: Literal["node", "edge"], component: str) -> ArtifactRole:
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"graph.records.{kind}.{component}")

    @classmethod
    def published(cls, module_id: str, name: str) -> ArtifactRole:
        """Mark an otherwise module-owned artifact as a workflow result."""
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"publication.{module_id}.{name}")

    @classmethod
    def graph_record_identity(cls, role: ArtifactRole) -> GraphRecordArtifact | None:
        if role.namespace != cls.NAMESPACE:
            return None
        parts = role.name.split(".", 3)
        if len(parts) != 4 or parts[:2] != ["graph", "records"] or parts[2] not in {"node", "edge"} or not parts[3]:
            return None
        return GraphRecordArtifact(kind=parts[2], component=parts[3])

    @classmethod
    def is_graph_records(cls, role: ArtifactRole) -> bool:
        return cls.graph_record_identity(role) is not None

    @classmethod
    def is_publication(cls, role: ArtifactRole) -> bool:
        return role.namespace == cls.NAMESPACE and role.name.startswith("publication.")


@dataclass(frozen=True)
class CoreCompilationContext:
    """Compiled semantic inputs required by the built-in core module.

    Core owns lowering graph bindings into its relation-producing workflow
    steps.  The generic workflow compiler supplies the narrow SQL-lowering
    capability; it no longer creates core workflow steps itself.
    """

    blueprint: BuildBlueprint
    sources: tuple[SourceDefinition, ...]


class CoreCompiler:
    async def compile(self, context: CoreCompilationContext) -> ModuleCompilationResult:
        definition = ModuleDefinition(
            reference=ModuleReference(
                module_id=CoreModule.ID,
                import_module=CoreModule.__module__,
                class_qualname=CoreModule.__qualname__,
                implementation_version=CoreModule.VERSION,
                priority=0,
            ),
        )
        drafts: list[WorkflowStepDraft] = []
        for index, binding in enumerate(context.blueprint.bindings):
            output = OutputSlot(
                slot_id=f"core::binding.{index}.output",
                artifact_role=CoreArtifactRoles.graph_records(binding.kind, binding.component),
            )
            step = WorkflowStep(
                step_id=f"core::binding.{index}",
                module_id=CoreModule.ID,
                outputs=(output,),
                payload={
                    "action": "relation",
                    "relation": f"kg_binding_{index}",
                    "sql": lower_binding_sql(context.blueprint, context.sources, binding),
                    "materialization": "temporary_table",
                },
            )
            drafts.append(WorkflowStepDraft(step, {}))
        publication_input = CollectionInputSlot(slot_id="core::publish.result.publications")
        drafts.append(WorkflowStepDraft(
            WorkflowStep(
                step_id="core::publish.result",
                module_id=CoreModule.ID,
                assembly_preference="deferred",
                inputs=(publication_input,),
                payload={"action": "publish"},
            ),
            {publication_input.slot_id: lambda _input, output: CoreArtifactRoles.is_publication(output.artifact_role)},
        ))
        return ModuleCompilationResult(definition, tuple(drafts))


class CoreModule(Module):
    ID: ClassVar[str] = "core"
    VERSION: ClassVar[str] = "1"

    @classmethod
    async def create_compiler(cls, context: Any) -> ModuleCompiler:
        return CoreCompiler()

    @classmethod
    async def create_executor(cls, context: Any) -> ModuleExecutor:
        return CoreExecutor()


class CoreExecutor:
    async def execute_step(self, context: ModuleExecutionContext, step: WorkflowStep) -> StepOutcome:
        payload = step.payload or {}
        if payload.get("action") == "publish":
            published = tuple(artifact for artifacts in context.inputs.values() for artifact in artifacts)
            return StepOutcome(
                step_id=step.step_id,
                module_id=step.module_id,
                status=StepStatus.SUCCEEDED,
                result={"published_artifacts": published},
            )
        connection = context.services["duckdb"]
        if payload.get("action") != "relation":
            raise ValueError(f"unsupported core action {payload.get('action')!r}")
        materialization = "TABLE" if payload.get("materialization") == "temporary_table" else "VIEW"
        relation = str(payload["relation"]).replace('"', '""')
        connection.execute(f'CREATE TEMP {materialization} "{relation}" AS {payload["sql"]}')
        output = step.outputs[0]
        return StepOutcome(
            step_id=step.step_id,
            module_id=step.module_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(Artifact(output.slot_id, output.artifact_role, relation),),
        )
