"""DuckDB SQL node helpers shared by lowering implementations."""
from __future__ import annotations

from typing import Any

from sqlglot import exp

from .nodes import SqlNode

from ....table.interfaces import ShapeField


def identifier(value: str, *, quoted: bool = True) -> exp.Identifier:
    return exp.Identifier(this=value, quoted=quoted)


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
    "identifier",
    "nullable_struct",
    "present_filter",
    "relation_table",
    "struct_pack",
]
