"""Plan construction and inspection for row-source values."""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from hashlib import sha256
from typing import Any, cast

from ...expressions.internal import (
    BoolExpression, OperationExpression, ValueExpression, as_expression,
    expression_to_ir, field_reference, wrap_expression,
)
from ...expressions.internal.ir import (
    ExpressionIR, FieldReferenceExpressionIR, OperationExpressionIR,
)
from ...types.internal import ArrayType, LogicalType, NullableType, StructType
from ...types.internal.ir import ArrayTypeIR
from ..internal.ir import (
    JoinHow, RowDistinctIR, RowFilterIR, RowGroupByIR, RowJoinIR, RowOrderByIR,
    RowOrderKeyIR, RowScanIR, RowSourcePlanIR, RowUnionIR,
    encode_row_source_plan,
)
from .shapes import (
    ShapeField, make_row_shape, record_shape_type, shape_fields,
    shape_source_name, union_shape_fields, _base, _is_nullable, _nullable_ir,
    _traversals,
)


def declaration_source_name(source: Any) -> str:
    """The logical name a table or projection writes its relation under."""
    spec = vars(source).get("_kg_declaration_spec")
    if spec is not None and spec.name and spec.kind in {"table", "projection"}:
        return spec.name
    name = getattr(source, "_table_name", None) or getattr(source, "_projection_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("row sources must be a Table or Projection")
    return name


def _root_source(value: Any) -> Any:
    from ..public.row_sources import DerivedRowSource, RelationRowSource

    if isinstance(value, (DerivedRowSource, RelationRowSource)):
        return value.source
    return value.shape


def as_row_source(value: Any) -> Any:
    """Require a value row source; declarations provide one via ``row_source()``."""
    from ..public.row_sources import RowSource

    if isinstance(value, RowSource) and not isinstance(value, type):
        return cast(Any, value)
    raise TypeError(
        "rows must be a row source value; use Table.row_source() or Projection.row_source()"
    )


def row_source_key(plan: RowSourcePlanIR) -> str:
    """The logical source key one plan's rows are read through."""
    if isinstance(plan, RowScanIR):
        return plan.source
    encoded = json.dumps(
        encode_row_source_plan(plan), sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return "derived:" + sha256(encoded).hexdigest()[:24]


def plan_shape_source_name(plan: RowSourcePlanIR) -> str:
    """The source the authoring shape's own fields refer to."""
    if isinstance(plan, (RowFilterIR, RowDistinctIR, RowOrderByIR)):
        return plan_shape_source_name(plan.input)
    if isinstance(plan, RowUnionIR):
        return plan_shape_source_name(plan.left)
    return row_source_key(plan)


def plan_inputs(plan: RowSourcePlanIR) -> tuple[RowSourcePlanIR, ...]:
    """The direct child plans a plan reads."""
    if isinstance(plan, (RowFilterIR, RowDistinctIR, RowOrderByIR, RowGroupByIR)):
        return (plan.input,)
    if isinstance(plan, (RowUnionIR, RowJoinIR)):
        return (plan.left, plan.right)
    return ()


def plan_scan_sources(plan: RowSourcePlanIR) -> tuple[str, ...]:
    """Every named table or projection a plan reads, in traversal order."""
    if isinstance(plan, RowScanIR):
        return (plan.source,)
    return tuple(
        source
        for child in plan_inputs(plan)
        for source in plan_scan_sources(child)
    )


def plan_expressions(plan: RowSourcePlanIR) -> tuple[ExpressionIR, ...]:
    """Every expression a plan itself evaluates."""
    if isinstance(plan, RowFilterIR):
        return (plan.predicate,)
    if isinstance(plan, RowJoinIR):
        return (plan.left_key, plan.right_key)
    if isinstance(plan, RowGroupByIR):
        return tuple(expression for _, expression in plan.keys)
    if isinstance(plan, RowOrderByIR):
        return tuple(key.expression for key in plan.keys)
    return ()


def plan_fields(
    plan: RowSourcePlanIR,
    declarations: Mapping[str, Any],
) -> tuple[ShapeField, ...]:
    """The row shape one plan produces, derived only from its IR and inputs."""
    if isinstance(plan, RowScanIR):
        try:
            return tuple(declarations[plan.source])
        except KeyError as error:
            raise ValueError(
                f"row-source plan reads unknown logical source {plan.source!r}"
            ) from error
    if isinstance(plan, (RowFilterIR, RowDistinctIR, RowOrderByIR)):
        return plan_fields(plan.input, declarations)
    if isinstance(plan, RowUnionIR):
        left = plan_fields(plan.left, declarations)
        right = plan_fields(plan.right, declarations)
        if tuple((item.name, item.logical_type) for item in left) != tuple(
            (item.name, item.logical_type) for item in right
        ):
            raise ValueError("union row sources must have the same shape")
        return left
    if isinstance(plan, RowJoinIR):
        left = plan_fields(plan.left, declarations)
        right = plan_fields(plan.right, declarations)
        left_key = _base(plan.left_key.logical_type)
        right_key = _base(plan.right_key.logical_type)
        if left_key != right_key:
            raise ValueError("join key expressions must have the same logical type")
        on_type: Any = left_key
        if (
            plan.how in {"left", "full"}
            and _is_nullable(plan.left_key.logical_type)
        ) or (
            plan.how in {"right", "full"}
            and _is_nullable(plan.right_key.logical_type)
        ):
            on_type = _nullable_ir(left_key)
        left_record = record_shape_type(left)
        right_record = record_shape_type(right)
        return (
            ShapeField("on", "on", on_type),
            ShapeField(
                "left", "left",
                left_record if plan.how in {"inner", "left"} else _nullable_ir(left_record),
            ),
            ShapeField(
                "right", "right",
                right_record if plan.how in {"inner", "right"} else _nullable_ir(right_record),
            ),
        )
    if isinstance(plan, RowGroupByIR):
        source = plan_fields(plan.input, declarations)
        keys = tuple(
            ShapeField(name, name, _base(key.logical_type))
            for name, key in plan.keys
        )
        if not keys:
            raise ValueError("group_by requires at least one key")
        return (
            ShapeField("by", "by", record_shape_type(keys)),
            ShapeField(
                "members", "members",
                ArrayTypeIR(cast(Any, record_shape_type(source))),
            ),
        )
    raise TypeError(f"unsupported row-source plan {plan!r}")


def retarget_expression_ir(
    expression: ExpressionIR, mapping: Mapping[str, str],
) -> ExpressionIR:
    """Rewrite field references from one logical source key to another."""
    if not mapping:
        return expression
    if isinstance(expression, FieldReferenceExpressionIR):
        target = mapping.get(expression.source)
        return expression if target is None else replace(expression, source=target)
    if isinstance(expression, OperationExpressionIR):
        return replace(
            expression,
            arguments=tuple(
                retarget_expression_ir(item, mapping)
                for item in expression.arguments
            ),
        )
    return expression


def _retarget(
    expression: ExpressionIR, mapping: Mapping[str, str],
) -> ExpressionIR:
    return retarget_expression_ir(expression, mapping)


def _evaluate_predicate(
    shape: Any, predicate: Callable[[Any], BoolExpression],
) -> BoolExpression:
    from .shapes import make_shape_context

    if not callable(predicate):
        raise TypeError("where requires a callable predicate")
    result = predicate(make_shape_context(shape))
    if not isinstance(result, BoolExpression):
        raise TypeError("where predicates must return a BoolExpression")
    return result


def derive_row_source(
    parent: Any, predicate: BoolExpression, *, shape: Any | None = None,
) -> Any:
    """Add one filter over a row source, preserving its shape by default."""
    from ..public.row_sources import DerivedRowSource

    base = as_row_source(parent)
    base_plan = row_source_plan_ir(base)
    predicate_ir = _retarget(
        expression_to_ir(predicate.model),
        {shape_source_name(base.shape): row_source_key(base_plan)},
    )
    result_shape = base.shape if shape is None else shape
    return DerivedRowSource(
        shape=result_shape,
        source=_root_source(base),
        filters=(*getattr(base, "filters", ()), predicate),
        plan_ir=RowFilterIR(base_plan, predicate_ir),
    )


def derive_where(
    source: Any, predicate: Callable[[Any], BoolExpression],
) -> Any:
    """Add one validated filter over a value row source."""
    return derive_row_source(source, _evaluate_predicate(source.shape, predicate))


def _join_pair(
    on: Any, left_shape: Any, right_shape: Any,
) -> tuple[ValueExpression[Any], ValueExpression[Any]]:
    """Resolve a join ``on`` callable into one key expression per side."""
    from .shapes import make_shape_context

    if not callable(on):
        raise TypeError("join on must be a callable returning a key pair")
    pair = on(make_shape_context(left_shape), make_shape_context(right_shape))
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


def derive_union(source: Any, other: Any, *, all: bool = True) -> Any:
    """Stack two same-shaped sources; ``all=False`` removes duplicates."""
    from ..public.row_sources import DerivedRowSource

    right = as_row_source(other)
    union_shape_fields(source.shape, right.shape)
    plan = RowUnionIR(
        row_source_plan_ir(source), row_source_plan_ir(right), bool(all),
    )
    return DerivedRowSource(
        shape=source.shape,
        source=_root_source(source),
        plan_ir=plan,
    )


def derive_join(
    source: Any,
    other: Any,
    *,
    on: Callable[[Any, Any], tuple[Any, Any]],
    how: JoinHow = "inner",
) -> Any:
    """Equi-join two value row sources on one key expression from each side."""
    from ..public.row_sources import DerivedRowSource

    if how not in {"inner", "left", "right", "full"}:
        raise ValueError("join how must be 'inner', 'left', 'right', or 'full'")
    right = as_row_source(other)
    left_key, right_key = _join_pair(on, source.shape, right.shape)
    left_plan = row_source_plan_ir(source)
    right_plan = row_source_plan_ir(right)
    plan = RowJoinIR(
        left_plan,
        right_plan,
        _retarget(
            expression_to_ir(left_key.model),
            {shape_source_name(source.shape): row_source_key(left_plan)},
        ),
        _retarget(
            expression_to_ir(right_key.model),
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
    left_record = record_shape_type(shape_fields(source.shape))
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
        source=_root_source(source),
        plan_ir=plan,
    )


def derive_group_by(source: Any, *, by: Callable[[Any], Any]) -> Any:
    """Group rows by named key expressions; null keys are dropped."""
    from ..public.row_sources import DerivedRowSource
    from .shapes import make_shape_context

    if not callable(by):
        raise TypeError("group_by by must be a callable")
    selected = by(make_shape_context(source.shape))
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
    input_plan = row_source_plan_ir(source)
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
            expression_to_ir(expression.model),
            {shape_source_name(source.shape): source_key},
        )))
        fields.append(ShapeField(name, name, logical_type))
    plan = RowGroupByIR(input_plan, tuple(keys))
    result_fields = (
        ShapeField("by", "by", record_shape_type(fields)),
        ShapeField(
            "members", "members",
            ArrayType(cast(Any, record_shape_type(shape_fields(source.shape)))),
        ),
    )
    return DerivedRowSource(
        shape=make_row_shape(row_source_key(plan), result_fields),
        source=_root_source(source),
        plan_ir=plan,
    )


def derive_distinct(source: Any) -> Any:
    """Drop duplicate rows without changing the shape."""
    from ..public.row_sources import DerivedRowSource

    plan = RowDistinctIR(row_source_plan_ir(source))
    return DerivedRowSource(
        shape=source.shape, source=_root_source(source), plan_ir=plan,
    )


def derive_order_by(
    source: Any, *keys: Any, ascending: bool = True,
) -> Any:
    """Order rows by expressions, selections, or column names."""
    from ..public.row_sources import DerivedRowSource
    from .shapes import make_shape_context

    if not keys:
        raise ValueError("order_by requires at least one key")
    input_plan = row_source_plan_ir(source)
    source_key = row_source_key(input_plan)
    fields = shape_fields(source.shape)
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
                cast(Callable[[Any], Any], key)(make_shape_context(source.shape))
            )
        else:
            expression = as_expression(key)
        if not isinstance(expression, ValueExpression):
            raise TypeError("order_by keys must be expressions or column names")
        authored.append(RowOrderKeyIR(
            _retarget(
                expression_to_ir(expression.model),
                {shape_source_name(source.shape): source_key},
            ),
            bool(ascending),
        ))
    plan = RowOrderByIR(input_plan, tuple(authored))
    return DerivedRowSource(
        shape=source.shape, source=_root_source(source), plan_ir=plan,
    )


def row_source_plan_ir(value: Any) -> RowSourcePlanIR:
    """The plan IR a value row source authors."""
    from ..public.row_sources import DerivedRowSource, RelationRowSource

    source = as_row_source(value)
    if isinstance(source, RelationRowSource):
        return RowScanIR(declaration_source_name(source.source))
    if isinstance(source, DerivedRowSource):
        if source.plan_ir is not None:
            return source.plan_ir
        plan: RowSourcePlanIR = RowScanIR(declaration_source_name(source.source))
        for predicate in source.filters:
            plan = RowFilterIR(
                plan,
                _retarget(
                    expression_to_ir(predicate.model),
                    {plan_shape_source_name(plan): row_source_key(plan)},
                ),
            )
        return plan
    raise TypeError(f"unsupported row source {source!r}")


__all__ = [
    "as_row_source", "declaration_source_name", "derive_distinct",
    "derive_group_by", "derive_join", "derive_order_by", "derive_row_source",
    "derive_union", "derive_where", "plan_expressions", "plan_fields",
    "plan_inputs", "plan_scan_sources", "plan_shape_source_name",
    "retarget_expression_ir", "row_source_key", "row_source_plan_ir",
]
