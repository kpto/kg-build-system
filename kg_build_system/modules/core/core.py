"""Core workflow compilation, execution, and artifact roles."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, cast

from ..._frozen_json import freeze_json
from ...compile.models import BuildBlueprint
from ...engines.duckdb import (
    PARQUET_LIST_WRAPPER_PATH,
    ArraySqlType,
    SqlType,
    canonical_sql_type,
    read_declared_null_statistics,
)
from ...expressions.ir import (
    FieldReferenceExpressionIR,
    walk_expression_ir,
)
from ...table.ir import ProjectionIR as ProjectionDefinition
from ...table.ir import StructIR, struct_type_key
from ...types.ir import (
    ArrayTypeIR, LogicalTypeIR, NullableTypeIR, StructTypeIR, UnitTypeIR,
)
from ...topology.ir import ComponentIR as ComponentDefinition
from ...workflow.models import (
    ArtifactRole, CollectionInputSlot, ModuleDefinition, ModuleReference,
    OutputSlot, WorkflowStep,
)
from ...compile.interfaces import CompilationContext, ModuleCompiler
from ...modules.interfaces import Module, ModuleRegistrationConfiguration
from ...workflow.interfaces import ModuleExecutor
from ...workflow.services import RelationRef
from ...workflow.models import (
    Artifact,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    StepOutcome,
    StepStatus,
    WorkflowContribution,
    WorkflowStepDraft,
)
from .lowering import (
    binding_outputs,
    binding_sources,
    lower_binding_sql,
    lower_projection_sql,
    projection_sources,
)
from .ir import (
    AggregateInstructionIR, DeclaredColumnIR, DeclaredPathIR,
    RelationInstructionIR, SourceRelationInstructionIR, decode_core_instruction,
    encode_core_instruction, encode_declared_column,
)
from .credentials import configure_source_credentials


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


def graph_record_components(
    blueprint: BuildBlueprint,
) -> tuple[ComponentDefinition, ...]:
    """Components that actually produce graph records.

    A component produces records only when at least one binding targets it.
    Abstract categories enter the blueprint to carry topology meaning and the
    parent chain, and are never binding targets, so they produce no records,
    no aggregation step, and no downstream artifact for any consumer.
    """
    bound = {binding.component for binding in blueprint.bindings}
    return tuple(item for item in blueprint.components if item.name in bound)


@dataclass(frozen=True)
class _CoreConfiguration(ModuleRegistrationConfiguration):
    """The mandatory core module has no author-configurable behavior."""


def _declared_non_null_paths(
    table, structs: Mapping[tuple[str, str], StructIR],
) -> dict[tuple[str, ...], tuple[str, ...]]:
    """Every path the contract claims is non-null, by logical and schema form.

    The contract's array markers supply Parquet's list wrappers, so the schema
    form matches what ``parquet_metadata()`` reports as ``path_in_schema`` even
    for a member several expansions deep.

    Struct members are resolved by ``(module, qualname)``, not by name: two
    modules may declare same-named structs, and a member's type names one of
    them by its full identity.
    """
    found: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def walk(
        fields, prefix: tuple[str, ...], schema_prefix: tuple[str, ...],
        parents: frozenset[tuple[str, str]],
    ) -> None:
        for declared in fields:
            logical_type = declared.logical_type
            nullable = isinstance(logical_type, NullableTypeIR)
            base = logical_type.value if nullable else logical_type
            is_array = isinstance(base, ArrayTypeIR)
            item = base.item if is_array else base
            logical_path = (*prefix, declared.name)
            schema_path = (
                *schema_prefix, declared.name,
                *(PARQUET_LIST_WRAPPER_PATH if is_array else ()),
            )
            if not nullable:
                found.append((logical_path, schema_path))
            if isinstance(item, StructTypeIR):
                key = (item.module, item.qualname)
                if key not in parents:
                    declaration = structs.get(key)
                    if declaration is not None:
                        walk(
                            declaration.fields, logical_path, schema_path,
                            parents | {key},
                        )

    walk(table.fields, (), (), frozenset())
    return dict(found)


def _declared_read_paths(blueprint: BuildBlueprint) -> dict[str, tuple[DeclaredPathIR, ...]]:
    """The non-null-claiming contract paths this build reads, per table.

    The null-count pre-flight asks only about what is read: a forty-column table
    whose three used columns are clean should not fill a report with the
    thirty-seven nobody reads. A projection output is consumed whole, so the table
    columns feeding a consumed projection count as read too. Claimed paths come
    from the contract, so a nullable path never reaches the pre-flight at all.
    """
    tables = {table.name: table for table in blueprint.tables}
    structs = {
        key: struct
        for struct in blueprint.structs
        if (key := struct_type_key(struct)) is not None
    }
    projections = {projection.name: projection for projection in blueprint.projections}
    claims = {
        name: _declared_non_null_paths(table, structs)
        for name, table in tables.items()
    }
    read: dict[str, set[tuple[str, ...]]] = {name: set() for name in tables}
    pending: list[Any] = [
        expression
        for binding in blueprint.bindings
        for expression in binding_outputs(binding).values()
    ]
    included: set[str] = set()
    while pending:
        for node in walk_expression_ir(pending.pop()):
            if not isinstance(node, FieldReferenceExpressionIR):
                continue
            if node.source in tables:
                read[node.source].add(node.path)
            elif node.source in projections and node.source not in included:
                included.add(node.source)
                pending.extend(
                    field.expression for field in projections[node.source].fields
                )
    def is_read(table_name: str, claimed: tuple[str, ...]) -> bool:
        """Whether the build reaches one claimed path.

        A reference to a nested value arrives as the outermost field plus a
        ``struct_field``/``expand`` operation over it, so a read of a prefix
        reaches everything below that prefix.
        """
        return any(
            claimed[:len(seen)] == seen for seen in read[table_name]
        )

    return {
        table: tuple(
            DeclaredPathIR(
                schema_path=".".join(claims[table][path]),
                logical_path=".".join(path),
            )
            for path in sorted(
                claimed for claimed in claims[table] if is_read(table, claimed)
            )
        )
        for table in tables
        if any(is_read(table, claimed) for claimed in claims[table])
    }


class CoreCompiler:
    async def compile(
        self, context: CompilationContext[Any],
    ) -> WorkflowContribution:
        definition = ModuleDefinition(
            reference=ModuleReference(
                module_id=CoreModule.ID,
                import_module=CoreModule.__module__,
                class_qualname=CoreModule.__qualname__,
                implementation_version=CoreModule.VERSION,
                configuration=freeze_json({}),
            )
        )
        sources = tuple(sorted(
            context.blueprint.sources, key=lambda source: source.table,
        ))
        projections = _ordered_projections(context.blueprint)
        table_relations = {
            source.table: f"kg_table_{index}"
            for index, source in enumerate(sources)
        }
        read_paths = _declared_read_paths(context.blueprint)
        projection_relations = {
            projection.name: f"kg_projection_{index}"
            for index, projection in enumerate(projections)
        }
        relations = table_relations | projection_relations

        drafts = [
            self._source_step(
                source,
                table_relations[source.table],
                context.blueprint,
                read_paths,
            )
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
        return WorkflowContribution(definition, tuple(drafts))

    @staticmethod
    def _source_step(
        source, relation: str, blueprint: BuildBlueprint,
        read_paths: Mapping[str, tuple[DeclaredPathIR, ...]],
    ) -> WorkflowStepDraft:
        output = OutputSlot(
            slot_id=f"core::table.{source.table}.output",
            artifact_role=CoreArtifactRoles.table(source.table),
        )
        table = next(
            (item for item in blueprint.tables if item.name == source.table), None,
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
                declaration=source.table,
                declared_columns=tuple(
                    encode_declared_column(field.name, field.logical_type)
                    for field in table.fields
                ) if table is not None else (),
                declared_paths=tuple(
                    path for path in read_paths.get(source.table, ())
                    if path.schema_path
                ),
            )),
        )
        return WorkflowStepDraft(definition=step)

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
        return WorkflowStepDraft(definition=step, candidates=candidates)

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
        return WorkflowStepDraft(definition=step, candidates=candidates)

    @staticmethod
    def _aggregation_steps(
        blueprint: BuildBlueprint,
    ) -> tuple[WorkflowStepDraft, ...]:
        drafts: list[WorkflowStepDraft] = []
        for component in graph_record_components(blueprint):
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
            drafts.append(WorkflowStepDraft(
                definition=step,
                assembly_preference="deferred",
                candidates=candidates,
            ))
        return tuple(drafts)


class CoreModule(Module):
    ID: ClassVar[str] = "core"
    VERSION: ClassVar[str] = "3"
    CONFIGURATION_TYPE: ClassVar[type[_CoreConfiguration]] = _CoreConfiguration

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext[Any],
    ) -> ModuleCompiler:
        return CoreCompiler()

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor:
        return CoreExecutor()


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _sql_type(declared: LogicalTypeIR) -> SqlType | None:
    """The SQL shape one declared column type composes to, when it composes to one.

    The declared canonical type is what the relation is asked to hold, because the
    ingest boundary only widens. Nullability is dropped: an SQL type states no
    nullity, so ``Array[str | None]`` and ``Array[str]`` are both ``VARCHAR[]``.
    Two declarations have no SQL type to be cast to and are passed through as the
    file has them rather than failing the build — a custom scalar, whose values the
    engine knows nothing of, and a struct, whose members the encoded declaration
    names only by the struct's own identity, which no module can resolve.
    """
    if isinstance(declared, NullableTypeIR):
        return _sql_type(declared.value)
    if isinstance(declared, UnitTypeIR):
        return declared.name
    if isinstance(declared, ArrayTypeIR):
        item = _sql_type(declared.item)
        return None if item is None else ArraySqlType(item)
    return None


def _widened_column(column: DeclaredColumnIR) -> str:
    """One select item of a source view: the declared column, widened in place.

    The alias repeats the column's own name, so widening the type cannot rename
    anything — ``_require_declared_columns`` and every lowered expression still
    reach the column by the name the contract declares.
    """
    name = _quote_identifier(column.name)
    sql_type = _sql_type(column.logical_type_ir)
    if sql_type is None:
        return name
    return f"CAST({name} AS {canonical_sql_type(sql_type)}) AS {name}"


def _require_declared_columns(
    context: ExecutionContext, instruction: SourceRelationInstructionIR, scan: str,
) -> None:
    """Check the contract's declared fields against the relation, before any use.

    A missing column otherwise surfaces much later as a DuckDB binder error naming
    candidate columns from the file, and a source whose declared format does not
    match its bytes fails mid-execution in DuckDB's vocabulary. Both are framework
    facts — a declaration and a location — so both are reported here, in
    framework terms, while nothing has yet read a row.

    The scan is described rather than the view built over it: a declared column the
    file does not have would otherwise fail the widening cast's own binding, where
    DuckDB reads it as a self-reference and blames the alias.
    """
    if not instruction.declared_columns:
        return
    query = f"DESCRIBE SELECT * FROM {scan}"
    try:
        columns = {
            str(row[0])
            for row in context.services.relations.query(query).fetchall()
        }
    except Exception as error:
        raise RuntimeError(
            f"the shape of the source at '{instruction.location}' for "
            f"'{instruction.declaration}' cannot be read as the declared "
            f"'{instruction.format}' format: {error}"
        ) from error
    missing = [
        column.name for column in instruction.declared_columns
        if column.name not in columns
    ]
    if missing:
        raise RuntimeError(
            f"declared field(s) {', '.join(repr(name) for name in missing)} are "
            f"absent from '{instruction.location}' for "
            f"'{instruction.declaration}'; the source exposes "
            f"{', '.join(sorted(map(repr, columns))) or 'no columns'}"
        )


def _report_declared_null_statistics(
    context: ExecutionContext, instruction: SourceRelationInstructionIR,
) -> bool:
    """Count nulls behind a declared non-null claim, from file footers only.

    A statistic tests a claim, it never sets or enforces one, so this reports and
    never fails: enforcement belongs to the guard at the point of use. A path with
    no published statistic is unknown, which is not the same as zero.
    """
    if instruction.format != "parquet" or not instruction.declared_paths:
        return False
    def read(query: str, parameters: Sequence[object]) -> list[tuple[Any, ...]]:
        return list(context.services.relations.query(query, parameters).fetchall())

    try:
        report = read_declared_null_statistics(
            read,
            (instruction.location,),
            [path.schema_path for path in instruction.declared_paths],
        )
    except Exception as error:
        context.services.logger.warning(
            "could not read null statistics from %s: %s",
            instruction.location, error,
        )
        return False
    logical = {
        path.schema_path: path.logical_path for path in instruction.declared_paths
    }
    for statistic in report.violations:
        context.services.logger.warning(
            "%s reports %d null value(s) in %d rows for the declared non-null "
            "column %r; the guard will abort the build unless the contract changes",
            instruction.location, statistic.nulls, statistic.values,
            logical.get(statistic.schema_path, statistic.schema_path),
        )
    for path in report.unknown_paths:
        context.services.logger.debug(
            "no null statistics published for %r; unknown is not zero", path,
        )
    return bool(report.violations)


class CoreExecutor(ModuleExecutor):
    def handle(self, context: ExecutionContext) -> StepOutcome:
        instruction = decode_core_instruction(context.step.payload)
        if isinstance(instruction, AggregateInstructionIR):
            return self._aggregate(context, instruction)
        if isinstance(instruction, SourceRelationInstructionIR):
            return self._define_source(context, instruction)
        return self._define_relation(context, instruction)

    @staticmethod
    def _aggregate(
        context: ExecutionContext, instruction: AggregateInstructionIR,
    ) -> StepOutcome:
        source_relations = tuple(
            context.services.relations.reference(item.artifact.value)
            for contributions in context.inputs.values()
            for item in contributions
            if item.artifact is not None
        )
        union_sql = " UNION ALL ".join(
            f"SELECT * FROM {source}"
            for source in source_relations
        )
        relation = context.services.relations.view(
            instruction.relation, union_sql,
        )
        return CoreExecutor._success(context, relation)

    @staticmethod
    def _define_relation(
        context: ExecutionContext, instruction: RelationInstructionIR,
    ) -> StepOutcome:
        relation = context.services.relations.view(
            instruction.relation, instruction.sql,
        )
        return CoreExecutor._success(context, relation)

    @staticmethod
    def _define_source(
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
        scan = f"{scan_function}('{location}')"
        # ``DESCRIBE`` reads file metadata only, so the contract's shape is checked
        # before a view exists and before any consumer can reach this relation —
        # every other step arrives through the role this step emits.
        _require_declared_columns(context, instruction, scan)
        # A multi-file scan does not widen the partitions it unions: it reports the
        # width of one file, which can be narrower than another partition's. The
        # widening happens here, in the per-source view, so every reader downstream
        # — projection, binding, and the union that aggregates a component — sees
        # one type for one declared column.
        select = ", ".join(
            _widened_column(column) for column in instruction.declared_columns
        ) or "*"
        sql = f"SELECT {select} FROM {scan}"
        try:
            relation = context.services.relations.view(instruction.relation, sql)
        except Exception as error:
            # DuckDB binds a view as it is created, so a source whose declared
            # format does not match its bytes fails here — in framework terms,
            # naming the declaration and the location, rather than mid-build.
            raise RuntimeError(
                f"the source at '{instruction.location}' for "
                f"'{instruction.declaration}' cannot be read as the declared "
                f"'{instruction.format}' format: {error}"
            ) from error
        # ``CREATE VIEW`` reads nothing, so the statistics pre-flight issues its own
        # metadata query.
        found = _report_declared_null_statistics(context, instruction)
        return CoreExecutor._success(
            context, relation,
            status=StepStatus.WARNING if found else StepStatus.SUCCEEDED,
        )

    @staticmethod
    def _success(
        context: ExecutionContext, relation: RelationRef,
        *, status: StepStatus = StepStatus.SUCCEEDED,
    ) -> StepOutcome:
        output = context.step.outputs[0]
        artifact = Artifact(output.slot_id, output.artifact_role, relation)
        return StepOutcome(
            step_id=context.step.step_id,
            module_id=context.step.module_id,
            status=status,
            artifacts=(artifact,),
        )

    def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return super().handle_disrupted(context)
