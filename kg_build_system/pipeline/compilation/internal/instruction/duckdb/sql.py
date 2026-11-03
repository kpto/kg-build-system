"""The DuckDB SQL node type and the helpers shared by its emitters.

Only this package imports :mod:`sqlglot`. The emitter protocols are generic over
their node type, so the relational planner and the engine interface never depend
on the SQL AST.
"""
from __future__ import annotations

from typing import Any

from sqlglot import exp

from ......declaration.languages.table.public import ShapeField


#: sqlglot publishes no public base-class alias that type checkers accept, so the
#: engine names the node type once here. Every DuckDB emitter returns this type.
SqlNode = Any


def identifier(value: str, *, quoted: bool = True) -> exp.Identifier:
    return exp.Identifier(this=value, quoted=quoted)


def quote_identifier(value: str) -> str:
    """One identifier as SQL text, quoted unconditionally."""
    return '"' + value.replace('"', '""') + '"'


def quote_string(value: str) -> str:
    """One string as a SQL literal."""
    return "'" + value.replace("'", "''") + "'"


def relation_table(relation: str, alias: str) -> exp.Table:
    return exp.Table(
        this=identifier(relation),
        alias=exp.TableAlias(this=identifier(alias, quoted=False)),
    )


def struct_pack(fields: tuple[ShapeField, ...], alias: str) -> SqlNode:
    """A row record read through one relation alias, with its declared names."""
    return exp.Anonymous(
        this="struct_pack",
        expressions=[
            exp.PropertyEQ(
                this=identifier(field.name),
                expression=exp.column(field.name, table=alias, quoted=True),
            )
            for field in fields
        ],
    )


def nullable_struct(
    fields: tuple[ShapeField, ...], alias: str, *, nullable: bool,
) -> SqlNode:
    value = struct_pack(fields, alias)
    if not nullable:
        return value
    present = exp.column("_kg_present", table=alias, quoted=True)
    return exp.Case(ifs=[exp.If(this=present, true=value)], default=exp.Null())


def present_filter(value: Any) -> SqlNode:
    return exp.Not(this=exp.Is(this=value, expression=exp.Null()))


__all__ = [
    "SqlNode",
    "identifier",
    "nullable_struct",
    "present_filter",
    "quote_identifier",
    "quote_string",
    "relation_table",
    "struct_pack",
]
