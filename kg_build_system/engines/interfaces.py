"""Framework-internal interface of the concrete execution engines.

Other subpackages import the engine protocol, the lowering protocols, the DuckDB
lowering, type mapping, macros and Parquet metadata readers here. This
subpackage has no author-facing surface. The engine type IR is
:mod:`kg_build_system.engines.ir`.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, TypeVar, runtime_checkable

from ..expressions.ir import ExpressionIR
from ..relational.interfaces import (
    PlanLowerer, RelationPlanLowerer, RowSourcePlanLowerer,
)
from ..relational.ir import RelationPlanIR
from ..table.ir import RowSourcePlanIR
from .protocols import (
    ExpressionLowerer,
    ExpressionLowering,
    LoweringContext,
    NodeT,
    Operand,
    RowSourceContext,
    RowSourceLowerer,
)
from .duckdb import (
    ARRAY_CANONICAL,
    CANONICAL_SQL_TYPES,
    DIGEST_TABLE,
    EXTENSION_CONDITIONAL_TYPE_NAMES,
    NULL_GUARD_MACRO,
    NULL_GUARD_MACRO_SQL,
    PARQUET_LIST_WRAPPER_PATH,
    PARQUET_LIST_WRAPPERS,
    STRUCT_CANONICAL,
    TYPE_NAME_ALIASES,
    ArraySqlType,
    CanonicalDigest,
    CanonicalTypeName,
    DeclaredOnlyDigest,
    DigestDisposition,
    DuckDBEngine,
    DuckDBLowering,
    DuckDBRelationService,
    DEFAULT_ENGINE,
    DEFAULT_LOWERING,
    NullStatistic,
    NullStatisticReport,
    ParquetSchemaRow,
    RefusedDigest,
    RowReader,
    SqlNode,
    SqlType,
    StructSqlType,
    TypeDigest,
    canonical_sql_type,
    canonical_type_name,
    configure_framework_macros,
    digest_for,
    lower_expression_sql,
    lower_plan,
    lower_relation_sql,
    lower_row_source,
    lower_row_source_sql,
    read_declared_null_statistics,
    read_parquet_schema_rows,
)


@runtime_checkable
class Engine(Protocol[NodeT]):
    """What another subpackage may ask of a concrete execution engine.

    The engine owns lowering from neutral plans to its SQL node type and the
    creation of its relation service. It does not own the workflow, the build
    contract or the graph model.
    """

    name: str

    @property
    def operators(self) -> Mapping[str, ExpressionLowerer[NodeT]]: ...

    def lower_expression(
        self,
        expression: ExpressionIR,
        *,
        aliases: Mapping[str, str] | None = None,
        expansions: Mapping[tuple[str, ...], NodeT] | None = None,
    ) -> NodeT: ...

    def lower_expression_sql(
        self, expression: ExpressionIR, *,
        aliases: Mapping[str, str] | None = None,
    ) -> str: ...

    def lower_plan(self, plan: RelationPlanIR) -> str: ...

    def lower(self, plan: RelationPlanIR) -> str: ...

    def lower_row_source(
        self,
        plan: RowSourcePlanIR,
        relations: Mapping[str, str],
        shapes: Mapping[str, tuple[Any, ...]],
    ) -> str: ...

    def configure(self, connection: Any) -> None: ...

    def relation_service(
        self, connection: Any, *, checkpoint_on_step: bool = False,
    ) -> Any: ...


__all__ = [
    "ARRAY_CANONICAL",
    "ArraySqlType",
    "CANONICAL_SQL_TYPES",
    "CanonicalDigest",
    "CanonicalTypeName",
    "DIGEST_TABLE",
    "DEFAULT_ENGINE",
    "DEFAULT_LOWERING",
    "DuckDBEngine",
    "DeclaredOnlyDigest",
    "DigestDisposition",
    "DuckDBEngine",
    "DuckDBLowering",
    "DuckDBRelationService",
    "EXTENSION_CONDITIONAL_TYPE_NAMES",
    "Engine",
    "ExpressionLowerer",
    "ExpressionLowering",
    "LoweringContext",
    "NULL_GUARD_MACRO",
    "NULL_GUARD_MACRO_SQL",
    "NodeT",
    "NullStatistic",
    "NullStatisticReport",
    "Operand",
    "PARQUET_LIST_WRAPPER_PATH",
    "PARQUET_LIST_WRAPPERS",
    "ParquetSchemaRow",
    "PlanLowerer",
    "RefusedDigest",
    "RelationPlanLowerer",
    "RowReader",
    "RowSourceContext",
    "RowSourceLowerer",
    "RowSourcePlanLowerer",
    "STRUCT_CANONICAL",
    "SqlNode",
    "SqlType",
    "StructSqlType",
    "TYPE_NAME_ALIASES",
    "TypeDigest",
    "canonical_sql_type",
    "canonical_type_name",
    "configure_framework_macros",
    "digest_for",
    "lower_expression_sql",
    "lower_plan",
    "lower_relation_sql",
    "lower_row_source",
    "lower_row_source_sql",
    "read_declared_null_statistics",
    "read_parquet_schema_rows",
]
