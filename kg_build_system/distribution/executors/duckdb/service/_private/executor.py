"""Execute the DuckDB instruction kinds one distribution plan emits."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.kernel import (
    DisruptedExecutionContext,
    ExecutionContext,
    Instruction,
    InstructionKind,
    StepOutcome,
    StepStatus,
)

from ....runtime import (
    execution_services,
    instruction_payload,
    skipped,
    succeeded,
)
from .findings import ConflictingNonNullValueFinding
from .readers import open_source, source_spec

SOURCE_RELATION: InstructionKind = ("source_relation", "duckdb")
SQL: InstructionKind = ("sql", "duckdb")
AGGREGATE: InstructionKind = ("aggregate", "duckdb")
DEDUPLICATION: InstructionKind = ("deduplication", "duckdb")
MERGING: InstructionKind = ("merging", "duckdb")
CONFLICT_FINDINGS: InstructionKind = ("conflict_findings", "duckdb")


def _quote_identifier(value: object) -> str:
    return str(value).replace('"', '""')


def _first_relation(context: ExecutionContext) -> Any | None:
    for contributions in context.inputs.values():
        for item in contributions:
            if item.artifact is not None:
                return item.artifact.value
    return None


class DuckDbExecutor:
    """Run the source, SQL, aggregate, distinct, merge and findings kinds."""

    kinds: tuple[InstructionKind, ...] = (
        SOURCE_RELATION,
        SQL,
        AGGREGATE,
        DEDUPLICATION,
        MERGING,
        CONFLICT_FINDINGS,
    )

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        """Dispatch on the exact instruction kind and finish the engine step.

        Example:
            ```python
            outcome = DuckDbExecutor().execute(context, instruction)
            ```
        """
        services = execution_services(context)
        try:
            if isinstance(context, DisruptedExecutionContext):
                return skipped(context)
            if instruction.kind == SOURCE_RELATION:
                return self._source_relation(context, instruction)
            if instruction.kind == SQL:
                return self._sql(context, instruction)
            if instruction.kind == AGGREGATE:
                return self._aggregate(context, instruction)
            if instruction.kind == DEDUPLICATION:
                return self._deduplication(context, instruction)
            if instruction.kind == MERGING:
                return self._merging(context, instruction)
            if instruction.kind == CONFLICT_FINDINGS:
                return self._conflict_findings(context, instruction)
            raise ValueError(f"unknown instruction kind {instruction.kind!r}")
        finally:
            services.engine.finish_step()

    def _source_relation(
        self,
        context: ExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        services = execution_services(context)
        spec = source_spec(instruction_payload(instruction))
        relation, warned = open_source(spec, services)
        return succeeded(
            context,
            relation,
            status=StepStatus.WARNING if warned else StepStatus.SUCCEEDED,
        )

    def _sql(
        self,
        context: ExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        services = execution_services(context)
        payload = instruction_payload(instruction)
        sql = payload.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError("a sql instruction requires a non-empty 'sql' payload")
        relation_name = payload.get("relation", context.step.name)
        if not isinstance(relation_name, str) or not relation_name:
            raise ValueError(
                "a sql instruction requires a non-empty 'relation' payload"
            )
        relation = services.relations.materialize(relation_name, sql)
        return succeeded(context, relation)

    def _aggregate(
        self,
        context: ExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        services = execution_services(context)
        payload = instruction_payload(instruction)
        relation_name = payload.get("relation")
        if not isinstance(relation_name, str) or not relation_name:
            raise ValueError(
                "an aggregate instruction requires a non-empty 'relation' payload"
            )
        sources = tuple(
            services.relations.reference(item.artifact.value)
            for contributions in context.inputs.values()
            for item in contributions
            if item.artifact is not None
        )
        union_sql = " UNION ALL ".join(
            f"SELECT * FROM {source}" for source in sources
        )
        relation = services.relations.view(relation_name, union_sql)
        return succeeded(context, relation)

    def _deduplication(
        self,
        context: ExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        services = execution_services(context)
        payload = instruction_payload(instruction)
        relation_name = payload.get("relation")
        if not isinstance(relation_name, str) or not relation_name:
            raise ValueError(
                "a deduplication instruction requires a non-empty 'relation' payload"
            )
        input_relation = _first_relation(context)
        if input_relation is None:
            return StepOutcome(context.step_id, StepStatus.SUCCEEDED)
        source = services.relations.reference(input_relation)
        relation = services.relations.materialize(
            relation_name, f"SELECT DISTINCT * FROM {source}",
        )
        return succeeded(context, relation)

    def _merging(
        self,
        context: ExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        services = execution_services(context)
        payload = instruction_payload(instruction)
        relation_name = payload.get("relation")
        select = payload.get("select")
        if not isinstance(relation_name, str) or not relation_name:
            raise ValueError(
                "a merging instruction requires a non-empty 'relation' payload"
            )
        if not isinstance(select, str) or not select.strip():
            raise ValueError(
                "a merging instruction requires a non-empty 'select' payload"
            )
        input_relation = _first_relation(context)
        if input_relation is None:
            return StepOutcome(context.step_id, StepStatus.SUCCEEDED)
        source = services.relations.reference(input_relation)
        relation = services.relations.materialize(
            relation_name,
            f'SELECT {select} FROM {source} GROUP BY "build_key"',
        )
        return succeeded(context, relation)

    def _conflict_findings(
        self,
        context: ExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        services = execution_services(context)
        payload: Mapping[str, Any] = instruction_payload(instruction)
        relation = _first_relation(context)
        if relation is None:
            return StepOutcome(context.step_id, StepStatus.SUCCEEDED)
        field_name = str(payload["field"])
        field = _quote_identifier(field_name)
        source = services.relations.reference(relation)
        sql = (
            f'SELECT "build_key", count(DISTINCT "{field}") '
            f"FROM {source} "
            'GROUP BY "build_key" '
            f'HAVING count(DISTINCT "{field}") '
            f'FILTER (WHERE "{field}" IS NOT NULL) > 1'
        )
        findings = tuple(
            ConflictingNonNullValueFinding(
                component=str(payload["component"]),
                build_key=str(key),
                property_name=field_name,
                distinct_values=count,
            )
            for key, count in services.relations.query(sql).fetchall()
        )
        return succeeded(context, findings)


__all__ = [
    "AGGREGATE",
    "CONFLICT_FINDINGS",
    "DEDUPLICATION",
    "DuckDbExecutor",
    "MERGING",
    "SOURCE_RELATION",
    "SQL",
]
