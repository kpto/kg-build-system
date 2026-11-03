"""Authoring surface type fixture: names and inferred types an author sees."""
from __future__ import annotations

from typing import assert_type

from kg_build_system.declaration.foundations.expressions.model.public import (
    IntExpression,
    NullableSelection,
    StrExpression,
    ValueSelection,
)
from kg_build_system.declaration.foundations.expressions.service.public import (
    value_expression,
)
from kg_build_system.declaration.languages.binding.model.public import (
    NodeBinding,
    NodeValues,
)
from kg_build_system.declaration.languages.binding.service.public import (
    node_binding,
)
from kg_build_system.declaration.languages.table.model.public import (
    Field,
    Table,
    TableOptions,
)
from kg_build_system.declaration.languages.table.service.public import field
from kg_build_system.declaration.languages.topology.model.public import (
    Node,
    NodeOptions,
    PropertySlot,
)
from kg_build_system.declaration.languages.topology.service.public import property


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
