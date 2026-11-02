"""Framework-internal interface of the concrete execution engines.

Other subpackages import the engine protocol, the lowering protocols, the DuckDB
lowering, type mapping, macros and Parquet metadata readers here. This
subpackage has no author-facing surface. The engine type IR is
:mod:`kg_build_system.engines.ir`.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypeVar, runtime_checkable

from ..expressions.ir import ExpressionIR
from ..relational.interfaces import (
    PlanLowerer, RelationPlanLowerer, RowSourcePlanLowerer,
)
from ..relational.ir import RelationPlanIR
from ..table.interfaces import ShapeField
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
    canonical_sql_type as _canonical_sql_type,
    canonical_type_name as _canonical_type_name,
    configure_framework_macros as _configure_framework_macros,
    digest_for as _digest_for,
    lower_expression as _lower_expression,
    lower_expression_sql as _lower_expression_sql,
    lower_plan as _lower_plan,
    lower_relation_sql as _lower_relation_sql,
    lower_row_source as _lower_row_source,
    lower_row_source_sql as _lower_row_source_sql,
    read_declared_null_statistics as _read_declared_null_statistics,
    read_parquet_schema_rows as _read_parquet_schema_rows,
)


def lower_expression(
    expression: ExpressionIR,
    *,
    aliases: Mapping[str, str] | None = None,
    expansions: Mapping[tuple[str, ...], SqlNode] | None = None,
    lowering: DuckDBLowering = DEFAULT_LOWERING,
) -> SqlNode:
    """Lower one expression to a DuckDB SQL node without a relation plan.

    ``aliases`` maps a logical source to the relation alias its fields are read
    through. ``expansions`` maps an expansion scope to the SQL node that supplies
    its item, which is how a structured expression refers to an expanded row.

    Example:
    ```python
    from kg_build_system import value_expression
    from kg_build_system.expressions.interfaces import expression_to_ir
    from kg_build_system.engines.interfaces import lower_expression

    expression = value_expression(1).add(value_expression(2))
    node = lower_expression(expression_to_ir(expression.model))
    print(node.sql(dialect="duckdb"))
    # 1 + 2
    ```
    """
    return _lower_expression(
        expression,
        aliases=aliases,
        expansions=expansions,
        lowering=lowering,
    )


def lower_expression_sql(
    expression: ExpressionIR,
    *,
    aliases: Mapping[str, str] | None = None,
    lowering: DuckDBLowering = DEFAULT_LOWERING,
) -> str:
    """Render one expression directly as DuckDB SQL text.

    This is :func:`lower_expression` followed by DuckDB rendering. It accepts no
    expansions because a standalone expression has no surrounding row context.

    Example:
    ```python
    from kg_build_system import value_expression
    from kg_build_system.expressions.interfaces import expression_to_ir
    from kg_build_system.engines.interfaces import lower_expression_sql

    expression = value_expression(1).add(value_expression(2))
    print(lower_expression_sql(expression_to_ir(expression.model)))
    # 1 + 2
    ```
    """
    return _lower_expression_sql(
        expression, aliases=aliases, lowering=lowering,
    )


def lower_plan(
    plan: RelationPlanIR, *, lowering: DuckDBLowering = DEFAULT_LOWERING,
) -> str:
    """Render a self-contained relational product as DuckDB SQL.

    The plan owns its scans, expansions, filters and outputs. Scans are crossed
    and expanded items are unnested, and a plan with no scans reads a one-row
    constant input.

    Example:
    ```python
    from kg_build_system import value_expression
    from kg_build_system.engines.interfaces import lower_plan
    from kg_build_system.expressions.interfaces import expression_to_ir
    from kg_build_system.relational.interfaces import lower_product

    expression = expression_to_ir(value_expression(1).add(value_expression(2)).model)
    plan = lower_product({"total": expression}, {})
    print(lower_plan(plan))
    # SELECT 1 + 2 AS "total" FROM (SELECT 1) AS constant_input
    ```
    """
    return _lower_plan(plan, lowering=lowering)


def lower_relation_sql(
    plan: RelationPlanIR, *, lowering: DuckDBLowering = DEFAULT_LOWERING,
) -> str:
    """Render a self-contained relational product as DuckDB SQL.

    This is the compatibility spelling for :func:`lower_plan`; new code may call
    either name and receives the same SQL.

    Example:
    ```python
    from kg_build_system import value_expression
    from kg_build_system.engines.interfaces import lower_relation_sql
    from kg_build_system.expressions.interfaces import expression_to_ir
    from kg_build_system.relational.interfaces import lower_product

    expression = expression_to_ir(value_expression(1).add(value_expression(2)).model)
    plan = lower_product({"total": expression}, {})
    print(lower_relation_sql(plan))
    # SELECT 1 + 2 AS "total" FROM (SELECT 1) AS constant_input
    ```
    """
    return _lower_relation_sql(plan, lowering=lowering)


def lower_row_source(
    plan: RowSourcePlanIR,
    relations: Mapping[str, str],
    shapes: Mapping[str, tuple[ShapeField, ...]],
    *,
    lowering: DuckDBLowering = DEFAULT_LOWERING,
) -> str:
    """Render one row-source plan over relations the caller already named.

    ``relations`` maps a logical row-source key to the SQL identifier that holds
    its rows. ``shapes`` maps a key to its row fields for the lowerers that need
    to read members; a plan whose lowerer needs no shape accepts an empty map.

    Example:
    ```python
    from kg_build_system import Field, Table, TableOptions, field
    from kg_build_system.engines.interfaces import lower_row_source

    class Row(Table):
        options = TableOptions(name="row")
        id: Field[int] = field(name="id")

    plan = Row.row_source().union(Row.row_source()).plan_ir
    print(lower_row_source(plan, {"row": "raw_row"}, {}))
    # SELECT * FROM "raw_row" UNION ALL SELECT * FROM "raw_row"
    ```
    """
    return _lower_row_source(
        plan, relations, shapes, lowering=lowering,
    )


def lower_row_source_sql(
    plan: RowSourcePlanIR,
    relations: Mapping[str, str],
    shapes: Mapping[str, tuple[ShapeField, ...]],
    *,
    lowering: DuckDBLowering = DEFAULT_LOWERING,
) -> str:
    """Render one row-source plan as DuckDB SQL text.

    This is the compatibility spelling for :func:`lower_row_source`; both names
    render the same SQL over the relations and shapes the caller supplies.

    Example:
    ```python
    from kg_build_system import Field, Table, TableOptions, field
    from kg_build_system.engines.interfaces import lower_row_source_sql

    class Row(Table):
        options = TableOptions(name="row")
        id: Field[int] = field(name="id")

    plan = Row.row_source().union(Row.row_source()).plan_ir
    print(lower_row_source_sql(plan, {"row": "raw_row"}, {}))
    # SELECT * FROM "raw_row" UNION ALL SELECT * FROM "raw_row"
    ```
    """
    return _lower_row_source_sql(
        plan, relations, shapes, lowering=lowering,
    )


def canonical_sql_type(canonical: SqlType) -> str:
    """The SQL text a canonical type is written as, composed from its parts.

    A canonical unit type has one SQL type of its own; a container composes its
    SQL from its item or member types. A bare container name has no parts to
    compose from and is refused.

    Example:
    ```python
    from kg_build_system.engines.interfaces import ArraySqlType, canonical_sql_type

    print(canonical_sql_type(ArraySqlType("int")))
    # BIGINT[]
    ```
    """
    return _canonical_sql_type(canonical)


def canonical_type_name(value: str) -> str:
    """Reduce one DuckDB type name to the key this engine's digest table uses.

    The parameter list is removed and the remaining family name is upper-cased,
    so ``DECIMAL(18,2)`` and ``decimal`` both become ``DECIMAL``.

    Example:
    ```python
    from kg_build_system.engines.interfaces import canonical_type_name

    print(canonical_type_name("DECIMAL(18,2)"))
    # DECIMAL
    ```
    """
    return _canonical_type_name(value)


def digest_for(value: str) -> TypeDigest | None:
    """The digest gate's decision for one DuckDB type name, or ``None``.

    ``None`` means the name is not a DuckDB type the gate knows, which is a
    different answer from a refusal: a refusal states why no canonical type
    exists, while an unknown name states that the gate has no opinion.

    Example:
    ```python
    from kg_build_system.engines.interfaces import digest_for

    print(digest_for("INTEGER").disposition)
    # canonical
    print(digest_for("BLOB").disposition)
    # refused
    ```
    """
    return _digest_for(value)


def configure_framework_macros(connection: Any) -> None:
    """Create the engine's framework macros on one build connection.

    Creation is idempotent and runs during connection setup, before any view is
    created, because a lowered guard resolves its macro at view-creation time.

    Example:
    ```python
    import duckdb

    from kg_build_system.engines.interfaces import configure_framework_macros

    connection = duckdb.connect()
    configure_framework_macros(connection)
    print(connection.execute("SELECT _kg_nn(1)").fetchone())
    # (1,)
    ```
    """
    _configure_framework_macros(connection)


def read_declared_null_statistics(
    read: RowReader, sources: Sequence[str], schema_paths: Sequence[str],
) -> NullStatisticReport:
    """Read ``stats_null_count`` for the given paths from Parquet footers only.

    A path the writer never reported statistics for is returned as unknown; an
    absent statistic tests nothing and is never read as a zero count.

    Example:
    ```python
    import duckdb

    from kg_build_system.engines.interfaces import read_declared_null_statistics

    connection = duckdb.connect()

    def read(sql, parameters):
        return connection.execute(sql, parameters).fetchall()

    report = read_declared_null_statistics(read, ["rows.parquet"], ["id"])
    print(report.unknown_paths)
    # ()
    ```
    """
    return _read_declared_null_statistics(read, sources, schema_paths)


def read_parquet_schema_rows(
    read: RowReader, sources: Sequence[str],
) -> tuple[ParquetSchemaRow, ...]:
    """Return every Parquet schema node of every source file.

    One row set per file, in pre-order depth-first order keyed on ``column_id``:
    ``file_name``, ``name``, ``repetition_type``, ``type``, ``num_children``,
    ``duckdb_type``, ``column_id``.

    Example:
    ```python
    import duckdb

    from kg_build_system.engines.interfaces import read_parquet_schema_rows

    connection = duckdb.connect()

    def read(sql, parameters):
        return connection.execute(sql, parameters).fetchall()

    rows = read_parquet_schema_rows(read, ["rows.parquet"])
    print(rows[0][1])
    # id
    ```
    """
    return _read_parquet_schema_rows(read, sources)


@runtime_checkable
class Engine(Protocol[NodeT]):
    """What another subpackage may ask of a concrete execution engine.

    The engine owns lowering from neutral plans to its SQL node type and the
    creation of its relation service. It does not own the workflow, the build
    contract or the graph model.
    """

    name: str

    @property
    def operators(self) -> Mapping[str, ExpressionLowerer[NodeT]]:
        """The expression operators this engine can lower, keyed by name."""
        ...

    def lower_expression(
        self,
        expression: ExpressionIR,
        *,
        aliases: Mapping[str, str] | None = None,
        expansions: Mapping[tuple[str, ...], NodeT] | None = None,
    ) -> NodeT:
        """Lower one expression to this engine's node type."""
        ...

    def lower_expression_sql(
        self, expression: ExpressionIR, *,
        aliases: Mapping[str, str] | None = None,
    ) -> str:
        """Render one expression as this engine's SQL text."""
        ...

    def lower_plan(self, plan: RelationPlanIR) -> str:
        """Render a self-contained relation plan as SQL text."""
        ...

    def lower(self, plan: RelationPlanIR) -> str:
        """Alias for :meth:`lower_plan`."""
        ...

    def lower_row_source(
        self,
        plan: RowSourcePlanIR,
        relations: Mapping[str, str],
        shapes: Mapping[str, tuple[Any, ...]],
    ) -> str:
        """Render a row-source plan over relations the caller already named."""
        ...

    def configure(self, connection: Any) -> None:
        """Prepare one connection with the macros this engine requires."""
        ...

    def relation_service(
        self, connection: Any, *, checkpoint_on_step: bool = False,
    ) -> Any:
        """Wrap one connection in this engine's relation service."""
        ...


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
    "lower_expression",
    "lower_expression_sql",
    "lower_plan",
    "lower_relation_sql",
    "lower_row_source",
    "lower_row_source_sql",
    "read_declared_null_statistics",
    "read_parquet_schema_rows",
]
