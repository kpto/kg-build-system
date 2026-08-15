"""Core workflow compilation, execution, and artifact roles."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, cast

from ...compile.blueprint import BuildBlueprint
from ...table.ir import ProjectionIR as ProjectionDefinition
from ...workflow.models import (
    ArtifactRole, CollectionInputSlot, ModuleDefinition, ModuleReference,
    OutputSlot, WorkflowStep,
)
from ...workflow.interfaces import (
    CompilationContext,
    Module,
    ModuleCompilationResult,
    ModuleCompiler,
    ModuleExecutor,
    ModuleRegistration,
    ModuleRegistrationConfiguration,
    WorkflowStepDraft,
)
from ...workflow.models import (
    Artifact,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    StepOutcome,
    StepStatus,
)
from .lowering import (
    binding_sources,
    lower_binding_sql,
    lower_projection_sql,
    projection_sources,
)
from .ir import (
    AggregateInstructionIR, RelationInstructionIR,
    SourceRelationInstructionIR, decode_core_instruction,
    encode_core_instruction,
)
from .credentials import configure_source_credentials


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


def _ordered_projections(
    blueprint: BuildBlueprint,
) -> tuple[ProjectionDefinition, ...]:
    pending = {projection.name: projection for projection in blueprint.projections}
    ordered: list[ProjectionDefinition] = []
    while pending:
        ready = sorted(
            (
                projection
                for projection in pending.values()
                if not (projection_sources(projection) & pending.keys())
            ),
            key=lambda projection: projection.symbol_id,
        )
        if not ready:
            raise ValueError("projection dependency graph contains a cycle")
        for projection in ready:
            ordered.append(projection)
            del pending[projection.name]
    return tuple(ordered)


@dataclass(frozen=True)
class GraphRecordArtifact:
    kind: Literal["node", "edge"]
    component: str


class CoreArtifactRoles:
    """Stable semantic roles produced and consumed by graph workflow modules."""

    NAMESPACE = "core"

    @classmethod
    def graph_records(
        cls, kind: Literal["node", "edge"], component: str,
    ) -> ArtifactRole:
        return ArtifactRole(
            namespace=cls.NAMESPACE,
            name=f"graph.{kind}.{component}",
        )

    @classmethod
    def binding(cls, symbol_id: str) -> ArtifactRole:
        return ArtifactRole(
            namespace=cls.NAMESPACE,
            name=f"binding.{symbol_id}",
        )

    @classmethod
    def table(cls, name: str) -> ArtifactRole:
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"data.table.{name}")

    @classmethod
    def projection(cls, name: str) -> ArtifactRole:
        return ArtifactRole(
            namespace=cls.NAMESPACE,
            name=f"data.projection.{name}",
        )

    @classmethod
    def graph_record_identity(
        cls, role: ArtifactRole,
    ) -> GraphRecordArtifact | None:
        if role.namespace != cls.NAMESPACE:
            return None
        parts = role.name.split(".", 2)
        if (
            len(parts) != 3
            or parts[0] != "graph"
            or parts[1] not in {"node", "edge"}
            or not parts[2]
        ):
            return None
        return GraphRecordArtifact(
            kind=cast(Literal["node", "edge"], parts[1]),
            component=parts[2],
        )

    @classmethod
    def is_graph_records(cls, role: ArtifactRole) -> bool:
        return cls.graph_record_identity(role) is not None


@dataclass(frozen=True)
class _CoreConfiguration(ModuleRegistrationConfiguration):
    """The mandatory core module has no author-configurable behavior."""


class CoreCompiler:
    async def compile(
        self, context: CompilationContext[Any],
    ) -> ModuleCompilationResult:
        definition = ModuleDefinition(
            reference=ModuleReference(
                module_id=CoreModule.ID,
                import_module=CoreModule.__module__,
                class_qualname=CoreModule.__qualname__,
                implementation_version=CoreModule.VERSION,
                configuration={},
            )
        )
        sources = self._sources(context)
        projections = _ordered_projections(context.blueprint)
        table_relations = {
            source.table: f"kg_table_{index}"
            for index, source in enumerate(sources)
        }
        projection_relations = {
            projection.name: f"kg_projection_{index}"
            for index, projection in enumerate(projections)
        }
        relations = table_relations | projection_relations

        drafts = [
            self._source_step(source, table_relations[source.table])
            for source in sources
        ]
        drafts.extend(
            self._projection_step(
                context.blueprint,
                projection,
                projection_relations[projection.name],
                relations,
                projection_relations,
            )
            for projection in projections
        )
        drafts.extend(
            self._binding_step(
                context.blueprint,
                binding,
                index,
                relations,
                projection_relations,
            )
            for index, binding in enumerate(context.blueprint.bindings)
        )
        drafts.extend(self._aggregation_steps(context.blueprint))
        return ModuleCompilationResult(definition, tuple(drafts))

    @staticmethod
    def _sources(context: CompilationContext[Any]):
        sources = {source.table: source for source in context.blueprint.sources}
        sources.update(
            {
                override.table: override.override
                for override in context.overrides.sources
            }
        )
        return tuple(sources[name] for name in sorted(sources))

    @staticmethod
    def _source_step(source, relation: str) -> WorkflowStepDraft:
        output = OutputSlot(
            slot_id=f"core::table.{source.table}.output",
            artifact_role=CoreArtifactRoles.table(source.table),
        )
        step = WorkflowStep(
            step_id=f"core::table.{source.table}",
            module_id=CoreModule.ID,
            outputs=(output,),
            payload=encode_core_instruction(SourceRelationInstructionIR(
                relation=relation,
                location=source.location,
                format=source.format,
                credential_reference=source.credential_reference,
            )),
        )
        return WorkflowStepDraft(step, {})

    @staticmethod
    def _projection_step(
        blueprint: BuildBlueprint,
        projection: ProjectionDefinition,
        relation: str,
        relations: dict[str, str],
        projection_relations: dict[str, str],
    ) -> WorkflowStepDraft:
        required_sources = projection_sources(projection)
        required_roles = tuple(
            CoreArtifactRoles.projection(name)
            if name in projection_relations
            else CoreArtifactRoles.table(name)
            for name in required_sources
        )
        input_slot = CollectionInputSlot(
            slot_id=f"core::projection.{projection.name}.inputs"
        )
        output = OutputSlot(
            slot_id=f"core::projection.{projection.name}.output",
            artifact_role=CoreArtifactRoles.projection(projection.name),
        )
        step = WorkflowStep(
            step_id=f"core::projection.{projection.name}",
            module_id=CoreModule.ID,
            inputs=(input_slot,),
            outputs=(output,),
            payload=encode_core_instruction(RelationInstructionIR(
                relation=relation,
                sql=lower_projection_sql(
                    blueprint, relations, projection
                ),
            )),
        )
        candidates = {
            input_slot.slot_id: lambda _input, candidate, roles=required_roles: (
                candidate.artifact_role in roles
            )
        }
        return WorkflowStepDraft(step, candidates)

    @staticmethod
    def _binding_step(
        blueprint: BuildBlueprint,
        binding,
        index: int,
        relations: dict[str, str],
        projection_relations: dict[str, str],
    ) -> WorkflowStepDraft:
        required_roles = tuple(
            CoreArtifactRoles.projection(name)
            if name in projection_relations
            else CoreArtifactRoles.table(name)
            for name in binding_sources(binding)
        )
        inputs = ()
        candidates = {}
        if required_roles:
            input_slot = CollectionInputSlot(
                slot_id=f"core::binding.{index}.inputs"
            )
            inputs = (input_slot,)
            candidates = {
                input_slot.slot_id: (
                    lambda _input, candidate, roles=required_roles: (
                        candidate.artifact_role in roles
                    )
                )
            }

        output = OutputSlot(
            slot_id=f"core::binding.{index}.output",
            artifact_role=CoreArtifactRoles.binding(binding.symbol_id),
        )
        binding_sql = lower_binding_sql(
            blueprint, relations, binding
        )
        step = WorkflowStep(
            step_id=f"core::binding.{index}",
            module_id=CoreModule.ID,
            inputs=inputs,
            outputs=(output,),
            payload=encode_core_instruction(RelationInstructionIR(
                relation=f"kg_binding_{index}",
                sql=(
                    f"SELECT *, '{binding.symbol_id}' AS _kg_binding_symbol "
                    f"FROM ({binding_sql})"
                ),
            )),
        )
        return WorkflowStepDraft(step, candidates)

    @staticmethod
    def _aggregation_steps(
        blueprint: BuildBlueprint,
    ) -> tuple[WorkflowStepDraft, ...]:
        drafts: list[WorkflowStepDraft] = []
        for component in blueprint.components:
            binding_roles = tuple(
                CoreArtifactRoles.binding(binding.symbol_id)
                for binding in blueprint.bindings
                if binding.component == component.name
            )
            if not binding_roles:
                continue
            input_slot = CollectionInputSlot(
                slot_id=f"core::aggregate.{component.name}.bindings"
            )
            output = OutputSlot(
                slot_id=f"core::aggregate.{component.name}.output",
                artifact_role=CoreArtifactRoles.graph_records(
                    component.kind, component.name
                ),
            )
            step = WorkflowStep(
                step_id=f"core::aggregate.{component.name}",
                module_id=CoreModule.ID,
                assembly_preference="deferred",
                inputs=(input_slot,),
                outputs=(output,),
                payload=encode_core_instruction(AggregateInstructionIR(
                    relation=f"kg_graph_{component.name.lower()}",
                )),
            )
            candidates = {
                input_slot.slot_id: (
                    lambda _input, candidate, roles=binding_roles: (
                        candidate.artifact_role in roles
                    )
                )
            }
            drafts.append(WorkflowStepDraft(step, candidates))
        return tuple(drafts)


@dataclass(frozen=True)
class CoreModule(Module, ModuleRegistration[_CoreConfiguration]):
    configuration: _CoreConfiguration = field(default_factory=_CoreConfiguration)

    ID: ClassVar[str] = "core"
    VERSION: ClassVar[str] = "1"

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return CoreCompiler()

    @classmethod
    async def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return CoreExecutor()


class CoreExecutor(ModuleExecutor):
    async def handle(self, context: ExecutionContext) -> StepOutcome:
        instruction = decode_core_instruction(context.step.payload)
        if isinstance(instruction, AggregateInstructionIR):
            return self._aggregate(context, instruction)
        if isinstance(instruction, SourceRelationInstructionIR):
            return self._materialize_source(context, instruction)
        return self._materialize_relation(context, instruction)

    @staticmethod
    def _aggregate(
        context: ExecutionContext, instruction: AggregateInstructionIR,
    ) -> StepOutcome:
        relation = _quote_identifier(instruction.relation)
        source_relations = tuple(
            item.artifact.value
            for contributions in context.inputs.values()
            for item in contributions
            if item.artifact is not None
        )
        union_sql = " UNION ALL ".join(
            f'SELECT * FROM "{_quote_identifier(source)}"'
            for source in source_relations
        )
        context.services.duckdb.execute(
            f'CREATE TEMP TABLE "{relation}" AS {union_sql}'
        )
        return CoreExecutor._success(context, relation)

    @staticmethod
    def _materialize_relation(
        context: ExecutionContext, instruction: RelationInstructionIR,
    ) -> StepOutcome:
        relation = _quote_identifier(instruction.relation)
        context.services.duckdb.execute(
            f'CREATE TEMP TABLE "{relation}" AS {instruction.sql}'
        )
        return CoreExecutor._success(context, relation)

    @staticmethod
    def _materialize_source(
        context: ExecutionContext, instruction: SourceRelationInstructionIR,
    ) -> StepOutcome:
        if instruction.credential_reference is not None:
            configure_source_credentials(
                context.services,
                location=instruction.location,
                credential_reference=instruction.credential_reference,
            )

        scan_function = {
            "csv": "read_csv_auto",
            "json": "read_json_auto",
            "parquet": "read_parquet",
        }[instruction.format]
        location = instruction.location.replace("'", "''")
        sql = f"SELECT * FROM {scan_function}('{location}')"
        return CoreExecutor._materialize_relation(
            context,
            RelationInstructionIR(
                relation=instruction.relation,
                sql=sql,
            ),
        )

    @staticmethod
    def _success(context: ExecutionContext, relation: str) -> StepOutcome:
        output = context.step.outputs[0]
        artifact = Artifact(output.slot_id, output.artifact_role, relation)
        return StepOutcome(
            step_id=context.step.step_id,
            module_id=context.step.module_id,
            status=StepStatus.SUCCEEDED,
            artifacts=(artifact,),
        )

    async def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return await super().handle_disrupted(context)
