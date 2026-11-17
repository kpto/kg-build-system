# pyright: reportUnnecessaryTypeIgnoreComment=error
"""Project-local relation operations keep the declared output shape precise."""
from __future__ import annotations

from typing import assert_type

from kg_build_system import Omitted
from kg_build_system.distribution.languages.data.model.public import (
    DerivedRowSource,
    Field,
    RelationOperation,
    RelationOperationSpec,
    SourceRelation,
)
from kg_build_system.distribution.languages.data.service.public import field
from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.kernel import Shape
from tests.distribution.support import TestEstate


class OperationRow(SourceRelation[TestEstate]):
    value: Field[str] = field(name="value", meaning=Omitted)


class CountRow(Shape):
    count: Selection[int]


COUNT_ROWS: RelationOperationSpec[OperationRow, CountRow] = (
    RelationOperationSpec(
        name="count_rows", output=CountRow, grain="one_total",
    )
)
count_rows: RelationOperation[OperationRow, CountRow] = RelationOperation(
    COUNT_ROWS,
)

rows = count_rows(OperationRow.row_source())
assert_type(rows, DerivedRowSource[CountRow])
assert_type(rows.shape, type[CountRow])
assert_type(rows.shape.count, Selection[int])

method = OperationRow.row_source().custom_op(count_rows)
assert_type(method, DerivedRowSource[CountRow])
assert_type(method.shape.count, Selection[int])
