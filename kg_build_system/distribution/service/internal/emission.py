"""The engine boundary for relational planning.

A core planner describes the rows it needs as an engine-neutral
:class:`RelationPlan`: scans, row effects, filters and outputs. The plan carries
expression DTOs, never SQL text and never an engine object. An engine supplies a
:class:`SqlEmitter`; the composition root injects one into the core planners.

The module also states the canonical SQL type shapes and the non-null guard macro
name that a planner and the default engine must agree on. DuckDB renders the
plan and implements the protocol in ``distribution/modules/duckdb``.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Final, Literal, Protocol, runtime_checkable

from kg_build_system.distribution.languages.data.model.internal import (
    RowSourcePlanDTO,
)
from kg_build_system.distribution.languages.data.model.public import ShapeField
from kg_build_system.distribution.languages.expressions.model.internal import (
    ExpressionDTO,
)
from kg_build_system.distribution.model.internal import (
    ARRAY_CANONICAL,
    STRUCT_CANONICAL,
    CanonicalTypeName,
)
from kg_build_system.kernel import Instruction, InstructionKind
from kg_build_system.kernel.model.public.types import (
    UnitTypeName,
    is_canonical_unit_name,
)

#: Aborts with ``msg`` when a value is null. Emitted bindings wrap every non-null
#: output in it, so a violated contract claim stops a build instead of emitting a
#: value the contract forbids.
NULL_GUARD_MACRO: Final = "_kg_nn"

#: The SQL type each canonical unit type is written as. A container composes its
#: SQL type from its item or member types.
CANONICAL_SQL_TYPES: Final[dict[UnitTypeName, str]] = {
    "bool": "BOOLEAN",
    "int": "BIGINT",
    "float": "DOUBLE",
    "str": "VARCHAR",
    "date": "DATE",
    "time": "TIME",
    "timestamp": "TIMESTAMP",
    "uuid": "UUID",
}


@dataclass(frozen=True, slots=True)
class Scan:
    """Read one materialised relation under one plan-local alias."""

    source: str
    relation: str
    alias: str


@dataclass(frozen=True, slots=True)
class Expand:
    """Fan one array expression out into rows under a stable scope."""

    scope: tuple[str, ...]
    expression: ExpressionDTO
    alias: str


@dataclass(frozen=True, slots=True)
class Filter:
    """Keep rows whose expression is present, or whose predicate is true."""

    expression: ExpressionDTO
    mode: Literal["present", "true"] = "present"


@dataclass(frozen=True, slots=True)
class RelationPlan:
    """One projection or binding: its scans, row effects and outputs.

    ``relations`` and ``shapes`` resolve the named relations an inline lookup
    reads without making them scans of this product.
    """

    scans: tuple[Scan, ...]
    expands: tuple[Expand, ...]
    filters: tuple[Filter, ...]
    outputs: tuple[tuple[str, ExpressionDTO], ...]
    relations: Mapping[str, str] = field(default_factory=dict)
    shapes: Mapping[str, tuple[ShapeField, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ArraySqlType:
    """An ordered collection whose SQL type is composed from one item type."""

    item: "SqlType"


@dataclass(frozen=True, slots=True)
class StructSqlType:
    """A nested record whose SQL type is composed from its members, in order.

    SQL types carry no nullability, so a member is a name and a type and nothing
    else; a member name is quoted as it is written unless it needs no quotes.
    """

    members: tuple[tuple[str, "SqlType"], ...]


#: A canonical type as SQL is written from it: a canonical unit name, or one of
#: the two container shapes composed from the types below it.
type SqlType = CanonicalTypeName | ArraySqlType | StructSqlType

SIMPLE_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


def sql_identifier(value: str) -> str:
    """A struct member name as SQL: quoted only where it has to be."""
    if SIMPLE_IDENTIFIER.fullmatch(value):
        return value
    return '"' + value.replace('"', '""') + '"'


def canonical_sql_type(canonical: SqlType) -> str:
    """The SQL a canonical type is written as, composed from its parts.

    A canonical unit type has one SQL type of its own and a container composes
    its SQL from its item or member types, so ``Array[int]`` is ``BIGINT[]`` and
    ``Struct{a: int}`` is ``STRUCT(a BIGINT)``. A bare container name has no
    parts to compose from and is the one thing this function refuses.

    Example:
        ```python
        assert canonical_sql_type(ArraySqlType("int")) == "BIGINT[]"
        ```
    """
    if isinstance(canonical, ArraySqlType):
        return f"{canonical_sql_type(canonical.item)}[]"
    if isinstance(canonical, StructSqlType):
        if not canonical.members:
            raise ValueError("a struct SQL type composes its SQL from its members")
        return "STRUCT({})".format(", ".join(
            f"{sql_identifier(name)} {canonical_sql_type(member)}"
            for name, member in canonical.members
        ))
    if not is_canonical_unit_name(canonical):
        raise ValueError(
            f"canonical {canonical!r} composes its SQL type from its item or "
            "member types; only a canonical unit type has one of its own"
        )
    return CANONICAL_SQL_TYPES[canonical]


@runtime_checkable
class RelationSqlEmitter(Protocol):
    """Render a relation plan or a row-source plan as SQL text."""

    def relation_sql(self, plan: RelationPlan) -> str: ...

    def emit_row_source(
        self,
        plan: RowSourcePlanDTO,
        relations: Mapping[str, str],
        shapes: Mapping[str, tuple[ShapeField, ...]],
    ) -> str: ...


@runtime_checkable
class SqlEmitter(Protocol):
    """An engine's instruction-facing SQL emitter.

    The emitter owns its SQL instruction kind, so a SQL planner never names an
    engine. Its instruction emitter renders the engine-neutral relation and
    row-source plans; ``emit`` wraps one relation plan as the engine's
    instruction.
    """

    @property
    def kind(self) -> InstructionKind: ...

    @property
    def instruction_emitter(self) -> RelationSqlEmitter: ...

    def emit(self, plan: RelationPlan, context: Any = None) -> Instruction: ...


__all__ = [
    "ARRAY_CANONICAL",
    "ArraySqlType",
    "CANONICAL_SQL_TYPES",
    "CanonicalTypeName",
    "Expand",
    "Filter",
    "NULL_GUARD_MACRO",
    "RelationPlan",
    "RelationSqlEmitter",
    "STRUCT_CANONICAL",
    "Scan",
    "SqlEmitter",
    "SqlType",
    "StructSqlType",
    "canonical_sql_type",
    "sql_identifier",
]
