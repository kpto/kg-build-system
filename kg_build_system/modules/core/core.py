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
from ...workflow.interfaces import CompilationContext, Module, ModuleCompilationResult, ModuleCompiler, ModuleExecutor, WorkflowStepDraft
from ...workflow.models import Artifact, DisruptedExecutionContext, ExecutionContext, StepOutcome, StepStatus
from .lowering import binding_relation_names, lower_binding_sql, lower_projection_sql, projection_tables


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
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"graph.{kind}.{component}")

    @classmethod
    def binding(cls, symbol_id: str) -> ArtifactRole:
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"binding.{symbol_id}")

    @classmethod
    def table(cls, name: str) -> ArtifactRole:
        """The relation materialised from one logical source table."""
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"data.table.{name}")

    @classmethod
    def projection(cls, name: str) -> ArtifactRole:
        """The relation materialised for one logical projection."""
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"data.projection.{name}")

    @classmethod
    def published(cls, module_id: str, name: str) -> ArtifactRole:
        """Mark an otherwise module-owned artifact as a workflow result."""
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"publication.{module_id}.{name}")

    @classmethod
    def graph_record_identity(cls, role: ArtifactRole) -> GraphRecordArtifact | None:
        if role.namespace != cls.NAMESPACE:
            return None
        parts = role.name.split(".", 2)
        if len(parts) != 3 or parts[0] != "graph" or parts[1] not in {"node", "edge"} or not parts[2]:
            return None
        return GraphRecordArtifact(kind=parts[1], component=parts[2])

    @classmethod
    def is_graph_records(cls, role: ArtifactRole) -> bool:
        return cls.graph_record_identity(role) is not None

    @classmethod
    def is_publication(cls, role: ArtifactRole) -> bool:
        return role.namespace == cls.NAMESPACE and role.name.startswith("publication.")


class CoreCompiler:
    async def compile(self, context: CompilationContext[Any]) -> ModuleCompilationResult:
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
        source_map = {source.table: source for source in context.blueprint.sources}
        source_map.update({override.table: override.override for override in context.overrides.sources})
        sources = tuple(source_map[name] for name in sorted(source_map))
        table_relations = {source.table: f"kg_table_{index}" for index, source in enumerate(sources)}
        projection_relations = {projection.name: f"kg_projection_{index}" for index, projection in enumerate(context.blueprint.projections)}
        relations = table_relations | projection_relations
        for source in sources:
            output = OutputSlot(
                slot_id=f"core::table.{source.table}.output",
                artifact_role=CoreArtifactRoles.table(source.table),
            )
            function = {"csv": "read_csv_auto", "json": "read_json_auto", "parquet": "read_parquet"}[source.format]
            relation = table_relations[source.table]
            location = source.location.replace("'", "''")
            sql = f"SELECT * FROM {function}('{location}')"
            drafts.append(WorkflowStepDraft(WorkflowStep(
                step_id=f"core::table.{source.table}", module_id=CoreModule.ID,
                outputs=(output,), payload={"action": "relation", "relation": relation, "sql": sql, "materialization": "temporary_table"},
            ), {}))
        for index, projection in enumerate(context.blueprint.projections):
            required = projection_tables(context.blueprint, projection)
            input_slot = CollectionInputSlot(slot_id=f"core::projection.{projection.name}.tables")
            output = OutputSlot(
                slot_id=f"core::projection.{projection.name}.output",
                artifact_role=CoreArtifactRoles.projection(projection.name),
            )
            drafts.append(WorkflowStepDraft(WorkflowStep(
                step_id=f"core::projection.{projection.name}", module_id=CoreModule.ID,
                inputs=(input_slot,), outputs=(output,), payload={
                    "action": "relation", "relation": f"kg_projection_{index}",
                    "sql": lower_projection_sql(context.blueprint, table_relations, projection),
                    "materialization": "temporary_table",
                },
            ), {input_slot.slot_id: lambda _input, candidate, required=required: candidate.artifact_role in {CoreArtifactRoles.table(table) for table in required}}))
        for index, binding in enumerate(context.blueprint.bindings):
            relation_names = binding_relation_names(binding)
            required_roles = {
                CoreArtifactRoles.projection(name) if name in projection_relations else CoreArtifactRoles.table(name)
                for name in relation_names
            }
            inputs = ()
            candidates = {}
            if required_roles:
                input_slot = CollectionInputSlot(slot_id=f"core::binding.{index}.inputs")
                inputs = (input_slot,)
                candidates = {input_slot.slot_id: lambda _input, candidate, roles=required_roles: candidate.artifact_role in roles}
            output = OutputSlot(
                slot_id=f"core::binding.{index}.output",
                artifact_role=CoreArtifactRoles.binding(binding.symbol_id),
            )
            step = WorkflowStep(
                step_id=f"core::binding.{index}",
                module_id=CoreModule.ID,
                inputs=inputs,
                outputs=(output,),
                payload={
                    "action": "relation",
                    "relation": f"kg_binding_{index}",
                    "sql": f"SELECT *, '{binding.symbol_id}' AS _kg_binding_symbol FROM ({lower_binding_sql(context.blueprint, relations, binding)})",
                    "materialization": "temporary_table",
                },
            )
            drafts.append(WorkflowStepDraft(step, candidates))
        for component in context.blueprint.components:
            binding_roles = {CoreArtifactRoles.binding(binding.symbol_id) for binding in context.blueprint.bindings if binding.component == component.name}
            if not binding_roles:
                continue
            input_slot = CollectionInputSlot(slot_id=f"core::aggregate.{component.name}.bindings")
            output = OutputSlot(slot_id=f"core::aggregate.{component.name}.output", artifact_role=CoreArtifactRoles.graph_records(component.kind, component.name))
            step = WorkflowStep(step_id=f"core::aggregate.{component.name}", module_id=CoreModule.ID, assembly_preference="deferred", inputs=(input_slot,), outputs=(output,), payload={"action": "aggregate", "relation": f"kg_graph_{component.name.lower()}"})
            drafts.append(WorkflowStepDraft(step, {input_slot.slot_id: lambda _input, candidate, roles=binding_roles: candidate.artifact_role in roles}))
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


class CoreExecutor(ModuleExecutor):
    async def _publish(self, context: ExecutionContext | DisruptedExecutionContext) -> StepOutcome:
        published = tuple(
            item.artifact
            for inputs in context.inputs.values()
            for item in inputs
            if item.artifact is not None
        )
        return StepOutcome(
            step_id=context.step.step_id,
            module_id=context.step.module_id,
            status=StepStatus.SUCCEEDED,
            result={"published_artifacts": published},
        )

    async def handle(self, context: ExecutionContext) -> StepOutcome:
        step = context.step
        payload = step.payload or {}
        if payload.get("action") == "publish":
            return await self._publish(context)
        connection = context.services.duckdb
        if payload.get("action") == "aggregate":
            relation = str(payload["relation"]).replace('"', '""')
            values = tuple(item.artifact.value for inputs in context.inputs.values() for item in inputs if item.artifact is not None)
            sql = " UNION ALL ".join(f'SELECT * FROM "{str(value).replace(chr(34), chr(34)*2)}"' for value in values)
            connection.execute(f'CREATE TEMP TABLE "{relation}" AS {sql}')
            output = step.outputs[0]
            return StepOutcome(step.step_id, step.module_id, StepStatus.SUCCEEDED, (Artifact(output.slot_id, output.artifact_role, relation),))
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

    async def handle_disrupted(self, context: DisruptedExecutionContext) -> StepOutcome:
        if (context.step.payload or {}).get("action") == "publish":
            return await self._publish(context)
        return await super().handle_disrupted(context)
