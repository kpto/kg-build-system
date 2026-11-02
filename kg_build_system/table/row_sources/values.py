"""The authoring row-source algebra.

A row source is a value: a shape plus a plan. ``where``, ``union``, ``distinct``
and ``order_by`` preserve the shape; ``join`` and ``group_by`` generate a shape
because the row genuinely has new members.

The class-level ``Table.where`` and ``Projection.where`` shorthands live on the
declaration classes; the methods here are the value operations they delegate to.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast

from ...expressions.interfaces import (
    BoolExpression, OperationExpression, ValueExpression, as_expression,
    field_reference, wrap_expression,
)
from ...expressions.ir import ExpressionIR
from ...types.interfaces import ArrayType, LogicalType, NullableType, Shape, StructType
from ..ir import (
    JoinHow, RowDistinctIR, RowGroupByIR, RowJoinIR, RowOrderByIR,
    RowOrderKeyIR, RowScanIR, RowSourcePlanIR, RowUnionIR,
)
from .plans import (
    _evaluate_predicate, _retarget, declaration_source_name, row_source_key,
    row_source_plan_ir,
)
from .shapes import (
    ShapeField, _base, _is_nullable, _traversals, make_row_shape,
    record_shape_type, shape_fields, shape_source_name, union_shape_fields,
)

S = TypeVar("S", bound=Shape)


def shape_context(shape: type[S]) -> S:
    """A symbolic instance of a shape, used as the subject of authoring lambdas."""
    return object.__new__(shape)


def _root_source(value: Any) -> Any:
    if isinstance(value, (DerivedRowSource, RelationRowSource)):
        return value.source
    return value.shape


def _join_pair(
    on: Any, left_shape: type[Shape], right_shape: type[Shape],
) -> tuple[ValueExpression[Any], ValueExpression[Any]]:
    if not callable(on):
        raise TypeError("join on must be a callable returning a key pair")
    pair = on(shape_context(left_shape), shape_context(right_shape))
    if isinstance(pair, BoolExpression):
        model = pair.model
        if (
            not isinstance(model, OperationExpression)
            or model.operator != "equals"
            or len(model.arguments) != 2
        ):
            raise TypeError(
                "join on must return a (left key, right key) pair or one equals expression"
            )
        left = wrap_expression(model.arguments[0])
        right = wrap_expression(model.arguments[1])
    elif isinstance(pair, tuple) and len(pair) == 2:
        left = as_expression(pair[0])
        right = as_expression(pair[1])
    else:
        raise TypeError("join on must return a (left key, right key) pair")
    left_type = _base(left.logical_type)
    right_type = _base(right.logical_type)
    if left_type != right_type:
        raise TypeError("join key expressions must have the same logical type")
    if isinstance(left_type, (ArrayType, StructType)):
        raise TypeError("join keys must be scalar expressions")
    return left, right


class RowSource(Generic[S]):
    """A source of rows whose shape is ``S``; declarations satisfy it by subclassing."""

    shape: type[S]

    def where(self, predicate: Callable[[S], BoolExpression]) -> "DerivedRowSource[S]":
        """Keep rows whose predicate is true.

        The predicate receives a symbolic shape instance and must return a
        ``BoolExpression``.

        Example:
            ```python
            active = SiteTable.row_source().where(
                lambda site: site.name.alter_rows().drop_null()
                .expression.equals("Depot")
            )
            ```
        """
        from .plans import derive_row_source

        result = _evaluate_predicate(self.shape, predicate)
        return cast("DerivedRowSource[S]", derive_row_source(self, result))

    def union(self, other: Any, *, all: bool = True) -> "DerivedRowSource[S]":
        """Stack two same-shaped sources; ``all=False`` removes duplicates.

        Example:
            ```python
            everyone = SiteTable.row_source().union(
                ArchivedSiteTable.row_source()
            )
            ```
        """
        from .plans import as_row_source

        right = as_row_source(other)
        union_shape_fields(self.shape, right.shape)
        plan = RowUnionIR(row_source_plan_ir(self), row_source_plan_ir(right), bool(all))
        return DerivedRowSource(
            shape=self.shape,
            source=_root_source(self),
            plan_ir=plan,
        )

    def join(
        self, other: Any, *, on: Callable[[Any, Any], tuple[Any, Any]],
        how: JoinHow = "inner",
    ) -> "DerivedRowSource[Any]":
        """Equi-join two sources on one expression from each side.

        ``on`` receives one shape instance per side and returns the two key
        selections. A null key never matches in any join mode.

        Example:
            ```python
            site_readings = SiteTable.row_source().join(
                ReadingTable.row_source(),
                on=lambda site, reading: (site.site_id, reading.site_id),
                how="left",
            )
            ```
        """
        from .plans import as_row_source

        if how not in {"inner", "left", "right", "full"}:
            raise ValueError("join how must be 'inner', 'left', 'right', or 'full'")
        right = as_row_source(other)
        left_key, right_key = _join_pair(on, self.shape, right.shape)
        left_plan = row_source_plan_ir(self)
        right_plan = row_source_plan_ir(right)
        plan = RowJoinIR(
            left_plan,
            right_plan,
            _retarget(
                _expression_ir(left_key),
                {shape_source_name(self.shape): row_source_key(left_plan)},
            ),
            _retarget(
                _expression_ir(right_key),
                {shape_source_name(right.shape): row_source_key(right_plan)},
            ),
            how,
        )
        key_type = _base(left_key.logical_type)
        on_type: LogicalType = key_type
        if (
            (how in {"left", "full"} and _is_nullable(left_key.logical_type))
            or (how in {"right", "full"} and _is_nullable(right_key.logical_type))
        ):
            on_type = NullableType(key_type)
        left_record = record_shape_type(shape_fields(self.shape))
        right_record = record_shape_type(shape_fields(right.shape))
        fields = (
            ShapeField("on", "on", on_type),
            ShapeField(
                "left", "left",
                left_record if how in {"inner", "left"} else NullableType(cast(Any, left_record)),
            ),
            ShapeField(
                "right", "right",
                right_record if how in {"inner", "right"} else NullableType(cast(Any, right_record)),
            ),
        )
        return DerivedRowSource(
            shape=make_row_shape(row_source_key(plan), fields),
            source=_root_source(self),
            plan_ir=plan,
        )

    def group_by(self, *, by: Callable[[S], Any]) -> "DerivedRowSource[Any]":
        """Group rows by named key expressions; null keys are dropped.

        Example:
            ```python
            by_region = SiteTable.row_source().group_by(
                by=lambda site: {"region": site.region},
            )
            ```
        """
        if not callable(by):
            raise TypeError("group_by by must be a callable")
        selected = by(shape_context(self.shape))
        if isinstance(selected, Mapping):
            items = list(selected.items())
        elif (
            isinstance(selected, Sequence)
            and not isinstance(selected, (str, bytes, bytearray))
            and all(
                isinstance(item, tuple) and len(item) == 2
                for item in selected
            )
        ):
            items = list(selected)
        else:
            items = [("key", selected)]
        if not items:
            raise ValueError("group_by requires at least one key")
        keys: list[tuple[str, ExpressionIR]] = []
        fields: list[ShapeField] = []
        seen: set[str] = set()
        input_plan = row_source_plan_ir(self)
        source_key = row_source_key(input_plan)
        for name, value in items:
            if not isinstance(name, str) or not name.isidentifier() or name.startswith("_"):
                raise ValueError("group_by key names must be Python identifiers")
            if name in seen:
                raise ValueError("group_by key names must be unique")
            seen.add(name)
            expression = as_expression(cast(Any, value))
            logical_type = _base(expression.logical_type)
            if isinstance(logical_type, (ArrayType, StructType)):
                raise TypeError("group_by keys must be scalar expressions")
            keys.append((name, _retarget(
                _expression_ir(expression),
                {shape_source_name(self.shape): source_key},
            )))
            fields.append(ShapeField(name, name, logical_type))
        plan = RowGroupByIR(input_plan, tuple(keys))
        result_fields = (
            ShapeField("by", "by", record_shape_type(fields)),
            ShapeField(
                "members", "members",
                ArrayType(cast(Any, record_shape_type(shape_fields(self.shape)))),
            ),
        )
        return DerivedRowSource(
            shape=make_row_shape(row_source_key(plan), result_fields),
            source=_root_source(self),
            plan_ir=plan,
        )

    def distinct(self) -> "DerivedRowSource[S]":
        """Drop duplicate rows without changing the shape.

        Example:
            ```python
            unique_sites = SiteTable.row_source().distinct()
            ```
        """
        plan = RowDistinctIR(row_source_plan_ir(self))
        return DerivedRowSource(
            shape=self.shape, source=_root_source(self), plan_ir=plan,
        )

    def order_by(self, *keys: Any, ascending: bool = True) -> "DerivedRowSource[S]":
        """Order rows by expressions, selections, or column names.

        Example:
            ```python
            ordered = SiteTable.row_source().order_by("region", "name")
            ```
        """
        if not keys:
            raise ValueError("order_by requires at least one key")
        input_plan = row_source_plan_ir(self)
        source_key = row_source_key(input_plan)
        fields = shape_fields(self.shape)
        names = {field.name: field for field in fields}
        authored: list[RowOrderKeyIR] = []
        for key in keys:
            if isinstance(key, str):
                field = names.get(key)
                if field is None:
                    raise ValueError(
                        f"order_by column {key!r} is not a member of the row source"
                    )
                expression = wrap_expression(field_reference(
                    source=source_key,
                    path=(field.name,),
                    logical_type=field.logical_type,
                    traversals=_traversals(field.name, field.logical_type),
                ))
            elif callable(key):
                expression = as_expression(
                    cast(Callable[[Any], Any], key)(shape_context(self.shape))
                )
            else:
                expression = as_expression(key)
            if not isinstance(expression, ValueExpression):
                raise TypeError("order_by keys must be expressions or column names")
            authored.append(RowOrderKeyIR(
                _retarget(
                    _expression_ir(expression),
                    {shape_source_name(self.shape): source_key},
                ),
                bool(ascending),
            ))
        plan = RowOrderByIR(input_plan, tuple(authored))
        return DerivedRowSource(
            shape=self.shape, source=_root_source(self), plan_ir=plan,
        )


def _expression_ir(expression: ValueExpression[Any]) -> ExpressionIR:
    from ...expressions.interfaces import expression_to_ir

    return expression_to_ir(expression.model)


@dataclass(frozen=True, slots=True)
class RelationRowSource(RowSource[S], Generic[S]):
    """A row source over one named table or projection relation."""

    source: type[Any]
    shape: type[S]
    filters: tuple[BoolExpression, ...] = ()

    @property
    def plan_ir(self) -> RowScanIR:
        """The scan plan this relation reads."""
        return RowScanIR(declaration_source_name(self.source))

    def projection_base(self) -> type:
        """Return a projection base over this relation.

        Example:
            ```python
            from kg_build_system import computed_field

            base = SiteTable.row_source().projection_base()

            class SiteLabels(base):
                label = computed_field(SiteTable.name)
            ```
        """
        from ..models import projection_base

        return projection_base(self)


@dataclass(frozen=True, slots=True)
class DerivedRowSource(RowSource[S], Generic[S]):
    """A row source derived by filtering or by the relational algebra."""

    shape: type[S]
    source: type[Any]
    filters: tuple[BoolExpression, ...] = ()
    plan_ir: RowSourcePlanIR | None = None

    def projection_base(self) -> type:
        """Return a projection base over this derived row source.

        Example:
            ```python
            from kg_build_system import computed_field

            active = SiteTable.row_source().where(
                lambda site: site.name.alter_rows().drop_null()
                .expression.equals("Depot")
            )
            base = active.projection_base()

            class ActiveSiteLabels(base):
                label = computed_field(SiteTable.name)
            ```
        """
        from ..models import projection_base

        return projection_base(self)


__all__ = [
    "DerivedRowSource", "RelationRowSource", "RowSource", "shape_context",
]
