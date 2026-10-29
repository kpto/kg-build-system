"""Core workflow compilation, execution, and artifact types."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, cast

from ..._frozen_json import FrozenJson, freeze_json
from ...compile.models import BuildBlueprint
from ...engines.duckdb import (
    PARQUET_LIST_WRAPPER_PATH,
    canonical_sql_type,
    lower_row_source_sql,
    read_declared_null_statistics,
)
from ...expressions.ir import (
    FieldReferenceExpressionIR,
    walk_expression_ir,
)
from ...table.ir import ProjectionIR as ProjectionDefinition
from ...table.ir import RowScanIR, RowSourcePlanIR, StructIR, struct_type_key
from ...table.rows import (
    ShapeField, plan_fields, plan_inputs, plan_scan_sources, row_source_key,
)
from ...types.ir import ArrayTypeIR, NullableTypeIR, StructTypeIR
from ...topology.ir import ComponentIR as ComponentDefinition
from ...workflow.models import (
    Artifact,
    ArtifactType,
    DisruptedExecutionContext,
    ExecutionContext,
    ExecutorFactoryContext,
    Input,
    ModuleDefinition,
    ModuleReference,
    Output,
    StepOutcome,
    StepStatus,
    WorkflowContribution,
    WorkflowStep,
)
from ...compile.interfaces import CompilationContext, ModuleCompiler
from ...modules.interfaces import Module, ModuleRegistrationConfiguration
from ...workflow.identity import output_name
from ...workflow.interfaces import ModuleExecutor
from ...workflow.services import RelationRef
from .lowering import (
    binding_outputs,
    binding_sources,
    lower_binding_sql,
    lower_projection_sql,
    projection_sources,
    sql_type_for,
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


def _ordered_row_source_plans(
    blueprint: BuildBlueprint,
) -> tuple[RowSourcePlanIR, ...]:
    """Every derived plan once, children before the plans that read them."""
    roots = [
        item.row_source
        for item in (*blueprint.projections, *blueprint.bindings)
        if item.row_source is not None
    ]
    ordered: list[RowSourcePlanIR] = []
    seen: set[str] = set()

    def visit(plan: RowSourcePlanIR) -> None:
        key = row_source_key(plan)
        if key in seen:
            return
        seen.add(key)
        for child in plan_inputs(plan):
            visit(child)
        if not isinstance(plan, RowScanIR):
            ordered.append(plan)

    for plan in roots:
        visit(plan)
    return tuple(ordered)


@dataclass(frozen=True)
class GraphRecordArtifact:
    kind: Literal["node", "edge"]
    component: str


class CoreArtifactTypes:
    """Stable artifact types produced and consumed by graph workflow modules."""

    NAMESPACE = "core"

    @classmethod
    def graph_records(
        cls, kind: Literal["node", "edge"], component: str,
    ) -> ArtifactType:
        return ArtifactType(
            namespace=cls.NAMESPACE,
            name=f"graph.{kind}.{component}",
        )

    @classmethod
    def binding(cls, symbol_id: str) -> ArtifactType:
        return ArtifactType(
            namespace=cls.NAMESPACE,
            name=f"binding.{symbol_id}",
        )

    @classmethod
    def table(cls, name: str) -> ArtifactType:
        return ArtifactType(namespace=cls.NAMESPACE, name=f"data.table.{name}")

    @classmethod
    def projection(cls, name: str) -> ArtifactType:
        return ArtifactType(
            namespace=cls.NAMESPACE,
            name=f"data.projection.{name}",
        )

    @classmethod
    def row_source(cls, key: str) -> ArtifactType:
        return ArtifactType(
            namespace=cls.NAMESPACE,
            name=f"data.row_source.{key}",
        )

    @classmethod
    def graph_record_identity(
        cls, artifact_type: ArtifactType,
    ) -> GraphRecordArtifact | None:
        if artifact_type.namespace != cls.NAMESPACE:
            return None
        parts = artifact_type.name.split(".", 2)
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
    def is_graph_records(cls, artifact_type: ArtifactType) -> bool:
        return cls.graph_record_identity(artifact_type) is not None


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


@dataclass(frozen=True, slots=True)
class _AuthoredStep:
    """One step core declares, and the instruction its executor runs for it.

    The name is both the step's name among core's steps and the key its instruction is
    filed under in the module's variables, so the two are authored together.
    """

    name: str
    instruction: FrozenJson
    inputs: tuple[Input, ...] = ()
    outputs: tuple[Output, ...] = ()
    assembly_preference: Literal["eager", "deferred"] = "eager"

    def step(self) -> WorkflowStep:
        return WorkflowStep(
            inputs=self.inputs,
            outputs=self.outputs,
            name=self.name,
            assembly_preference=self.assembly_preference,
        )


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
        declaration_fields = {
            item.name: tuple(
                ShapeField(field.name, field.name, field.logical_type)
                for field in item.fields
            )
            for item in context.blueprint.tables
        }
        declaration_fields.update({
            item.name: tuple(
                ShapeField(field.name, field.name, field.expression.logical_type)
                for field in item.fields
            )
            for item in context.blueprint.projections
        })
        row_source_plans = _ordered_row_source_plans(context.blueprint)
        row_source_relations = {
            row_source_key(plan): f"kg_rowsource_{index}"
            for index, plan in enumerate(row_source_plans)
        }
        row_source_fields = {
            row_source_key(plan): plan_fields(plan, declaration_fields)
            for plan in row_source_plans
        }
        for plan in row_source_plans:
            for scan in plan_scan_sources(plan):
                if scan in declaration_fields:
                    row_source_fields.setdefault(scan, declaration_fields[scan])
        relations = table_relations | projection_relations | row_source_relations

        authored = [
            self._source_step(
                source,
                table_relations[source.table],
                context.blueprint,
                read_paths,
            )
            for source in sources
        ]
        authored.extend(
            self._row_source_step(
                plan,
                row_source_relations[row_source_key(plan)],
                relations,
                row_source_fields,
                projection_relations,
                row_source_relations,
            )
            for plan in row_source_plans
        )
        authored.extend(
            self._projection_step(
                context.blueprint,
                projection,
                projection_relations[projection.name],
                relations,
                projection_relations,
                row_source_relations,
            )
            for projection in projections
        )
        authored.extend(
            self._binding_step(
                context.blueprint,
                binding,
                index,
                relations,
                projection_relations,
                row_source_relations,
            )
            for index, binding in enumerate(context.blueprint.bindings)
        )
        authored.extend(self._aggregation_steps(context.blueprint))
        return WorkflowContribution(
            definition,
            tuple(item.step() for item in authored),
            freeze_json({
                "instructions": {item.name: item.instruction for item in authored},
            }),
        )

    @staticmethod
    def _read_input(
        name: str,
        projection_relations: Mapping[str, str],
        row_source_relations: Mapping[str, str] | None = None,
    ) -> Input:
        """One opening a projection or binding takes: a relation its SQL reads.

        The sources a projection or binding reads come out of a set, so the caller
        orders them; that order is the order these openings are declared in.
        """
        if row_source_relations is not None and name in row_source_relations:
            return Input(
                type=CoreArtifactTypes.row_source(name),
                name=f"row_source.{name}",
            )
        projection = name in projection_relations
        return Input(
            type=(
                CoreArtifactTypes.projection(name) if projection
                else CoreArtifactTypes.table(name)
            ),
            name=f"{'projection' if projection else 'table'}.{name}",
        )

    @staticmethod
    def _source_step(
        source, relation: str, blueprint: BuildBlueprint,
        read_paths: Mapping[str, tuple[DeclaredPathIR, ...]],
    ) -> _AuthoredStep:
        table = next(
            (item for item in blueprint.tables if item.name == source.table), None,
        )
        return _AuthoredStep(
            name=f"table.{source.table}",
            outputs=(Output(CoreArtifactTypes.table(source.table)),),
            instruction=encode_core_instruction(SourceRelationInstructionIR(
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

    @staticmethod
    def _row_source_step(
        plan: RowSourcePlanIR,
        relation: str,
        relations: dict[str, str],
        shapes: Mapping[str, tuple[ShapeField, ...]],
        projection_relations: dict[str, str],
        row_source_relations: dict[str, str],
    ) -> _AuthoredStep:
        key = row_source_key(plan)
        return _AuthoredStep(
            name=f"rowsource.{key}",
            inputs=tuple(
                CoreCompiler._read_input(
                    child_key,
                    projection_relations,
                    row_source_relations,
                )
                for child_key in dict.fromkeys(
                    row_source_key(child) for child in plan_inputs(plan)
                )
            ),
            outputs=(Output(CoreArtifactTypes.row_source(key)),),
            instruction=encode_core_instruction(RelationInstructionIR(
                relation=relation,
                sql=lower_row_source_sql(plan, relations, shapes),
            )),
        )

    @staticmethod
    def _projection_step(
        blueprint: BuildBlueprint,
        projection: ProjectionDefinition,
        relation: str,
        relations: dict[str, str],
        projection_relations: dict[str, str],
        row_source_relations: dict[str, str],
    ) -> _AuthoredStep:
        return _AuthoredStep(
            name=f"projection.{projection.name}",
            inputs=tuple(
                CoreCompiler._read_input(
                    name, projection_relations, row_source_relations,
                )
                for name in sorted(projection_sources(projection))
            ),
            outputs=(Output(CoreArtifactTypes.projection(projection.name)),),
            instruction=encode_core_instruction(RelationInstructionIR(
                relation=relation,
                sql=lower_projection_sql(
                    blueprint, relations, projection
                ),
            )),
        )

    @staticmethod
    def _binding_step(
        blueprint: BuildBlueprint,
        binding,
        index: int,
        relations: dict[str, str],
        projection_relations: dict[str, str],
        row_source_relations: dict[str, str],
    ) -> _AuthoredStep:
        binding_sql = lower_binding_sql(
            blueprint, relations, binding
        )
        return _AuthoredStep(
            name=f"binding.{index}",
            inputs=tuple(
                CoreCompiler._read_input(
                    name, projection_relations, row_source_relations,
                )
                for name in sorted(binding_sources(binding))
            ),
            outputs=(Output(CoreArtifactTypes.binding(binding.symbol_id)),),
            instruction=encode_core_instruction(RelationInstructionIR(
                relation=f"kg_binding_{index}",
                sql=(
                    f"SELECT *, '{binding.symbol_id}' AS _kg_binding_symbol "
                    f"FROM ({binding_sql})"
                ),
            )),
        )

    @staticmethod
    def _aggregation_steps(
        blueprint: BuildBlueprint,
    ) -> tuple[_AuthoredStep, ...]:
        steps: list[_AuthoredStep] = []
        for component in graph_record_components(blueprint):
            symbol_ids = tuple(
                binding.symbol_id
                for binding in blueprint.bindings
                if binding.component == component.name
            )
            if not symbol_ids:
                continue
            steps.append(_AuthoredStep(
                name=f"aggregate.{component.name}",
                inputs=tuple(
                    Input(
                        type=CoreArtifactTypes.binding(symbol_id),
                        name=f"binding.{symbol_id}",
                    )
                    for symbol_id in symbol_ids
                ),
                outputs=(Output(CoreArtifactTypes.graph_records(
                    component.kind, component.name,
                )),),
                assembly_preference="deferred",
                instruction=encode_core_instruction(AggregateInstructionIR(
                    relation=f"kg_graph_{component.name.lower()}",
                )),
            ))
        return tuple(steps)


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


def _widened_column(column: DeclaredColumnIR) -> str:
    """One select item of a source view: the declared column, widened in place.

    The alias repeats the column's own name, so widening the type cannot rename
    anything — ``_require_declared_columns`` and every lowered expression still
    reach the column by the name the contract declares.
    """
    name = _quote_identifier(column.name)
    sql_type = sql_type_for(column.logical_type_ir)
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
        instruction = decode_core_instruction(
            context.variables["instructions"][context.step.name],
        )
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
        # every other step arrives through the type this step emits.
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
        artifact = Artifact(output_name(output), output.type, relation)
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=status,
            artifacts=(artifact,),
        )

    def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome:
        return super().handle_disrupted(context)
