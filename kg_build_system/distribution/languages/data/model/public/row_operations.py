"""Project-local relation operations composed as row-source operations.

A relation operation names one operation a project supplies, the shape of the
one row source it reads and the shape of the rows it produces. The project
supplies the SQL emitter; the data language carries the operation through the
plan, the codec and the source renderer.

Example:
    ```python
    from kg_build_system import (
        DerivedRelation, DerivedRelationOptions, Omitted, Selection, Shape,
        SourceRelation, computed_field, field,
    )
    from kg_build_system.distribution.languages.data import (
        RelationOperation, RelationOperationSpec,
    )

    class Row(SourceRelation):
        value = field()

    class CountRow(Shape):
        count: Selection[int]

    count_rows = RelationOperation(RelationOperationSpec(
        name="count_rows", output=CountRow, grain="one_total",
    ))

    rows = count_rows(Row.row_source())

    class RowCount(DerivedRelation(rows)):
        count = computed_field(rows.shape.count)
    ```
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from kg_build_system.kernel import JsonValue
from kg_build_system.kernel.model.public.types import Shape
from .row_sources import DerivedRowSource, RowSource

type Grain = Literal["one_per_input_row", "one_per_group", "one_total"]


@dataclass(frozen=True, slots=True)
class RelationOperationSpec[In: Shape, Out: Shape]:
    """The project's declaration of one relation operation.

    ``In`` names the shape of the one input row source, ``Out`` names the exact
    output shape and ``grain`` states how many output rows one input produces.
    ``output`` is required: the plan carries the declared members, never an
    inferred or open shape.
    """

    name: str
    output: type[Out]
    grain: Grain

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("relation operation names must be non-empty text")
        if not isinstance(self.output, type) or not issubclass(
            self.output, Shape,
        ) or self.output is Shape:
            raise TypeError(
                "relation operation output must be a concrete Shape subclass"
            )
        if self.grain not in {
            "one_per_input_row", "one_per_group", "one_total",
        }:
            raise ValueError(
                "relation operation grain must be one_per_input_row, "
                "one_per_group or one_total"
            )


@dataclass(frozen=True, slots=True)
class RelationOperation[In: Shape, Out: Shape]:
    """One project relation operation, applied to a row source by ``custom_op``."""

    spec: RelationOperationSpec[In, Out]

    def __post_init__(self) -> None:
        if not isinstance(self.spec, RelationOperationSpec):
            raise TypeError(
                "a relation operation requires a RelationOperationSpec"
            )

    def __call__(
        self, rows: RowSource[In], **parameters: JsonValue,
    ) -> DerivedRowSource[Out]:
        """Compose this operation over one input row source.

        Example:
            ```python
            rows = count_rows(Row.row_source())
            ```
        """
        from ...service.public.rows import derive_relation_operation

        return derive_relation_operation(rows, self, **parameters)


__all__ = ["Grain", "RelationOperation", "RelationOperationSpec"]
