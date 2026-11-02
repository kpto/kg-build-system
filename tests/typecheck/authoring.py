"""Authoring surface type fixture: names and inferred types an author sees."""
from __future__ import annotations

from typing import assert_type

from kg_build_system import (
    Field, Node, NodeBinding, NodeOptions, NodeValues, PropertySlot, Table, TableOptions,
    field, node_binding, property, value_expression,
)
from kg_build_system.expressions import (
    IntExpression, NullableSelection, StrExpression, ValueSelection,
)


class Row(Table):
    options = TableOptions(name="row")
    id: Field[str] = field(name="id")
    count: Field[int] = field(name="count")


class OptionalRow(Table):
    value: Field[str | None] = field(name="value")  # pyright: ignore[reportUnknownVariableType]


class RowNode(Node):
    options = NodeOptions(name="row_node")
    label: PropertySlot[str] = property()


assert_type(Row.id, ValueSelection[str])
assert_type(Row.id.expression, StrExpression)
assert_type(Row.count.expression, IntExpression)
assert_type(OptionalRow.value, NullableSelection[str])
assert_type(value_expression("x"), StrExpression)


def bind(row: Row) -> NodeValues[RowNode, str]:
    return NodeValues(
        build_key=row.id,
        properties=RowNode(label=row.id),
    )


binding = node_binding(target=RowNode, rows=Row, bind=bind)
assert_type(binding, NodeBinding[RowNode])
