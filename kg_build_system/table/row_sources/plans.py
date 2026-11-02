"""Plan construction and inspection for row-source values.

A plan is canonical frozen IR. This module turns a row-source value into its
plan, names the plan by content, reads plan children, derives the shape of a
plan from the IR alone and rewrites field references from one logical key to
another.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import replace
from hashlib import sha256
from typing import Any, cast

from ...expressions.interfaces import BoolExpression, expression_to_ir
from ...expressions.ir import (
    ExpressionIR, FieldReferenceExpressionIR, OperationExpressionIR,
)
from ...types.ir import ArrayTypeIR
from ..ir import (
    RowDistinctIR, RowFilterIR, RowGroupByIR, RowJoinIR, RowOrderByIR,
    RowOrderKeyIR, RowScanIR, RowSourcePlanIR, RowUnionIR,
    encode_row_source_plan,
)
from .shapes import (
    ShapeField, record_shape_type, shape_source_name,
    _base, _is_nullable, _nullable_ir,
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
    from .values import DerivedRowSource, RelationRowSource

    if isinstance(value, (DerivedRowSource, RelationRowSource)):
        return value.source
    return value.shape


def as_row_source(value: Any) -> Any:
    """Require a value row source; declarations provide one via ``row_source()``."""
    from .values import RowSource

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
    from .values import shape_context

    if not callable(predicate):
        raise TypeError("where requires a callable predicate")
    result = predicate(shape_context(shape))
    if not isinstance(result, BoolExpression):
        raise TypeError("where predicates must return a BoolExpression")
    return result


def derive_row_source(
    parent: Any, predicate: BoolExpression, *, shape: Any | None = None,
) -> Any:
    """Add one filter over a row source, preserving its shape by default."""
    from .values import DerivedRowSource

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


def row_source_plan_ir(value: Any) -> RowSourcePlanIR:
    """The plan IR a value row source authors."""
    from .values import DerivedRowSource, RelationRowSource

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
    "as_row_source", "declaration_source_name", "derive_row_source",
    "plan_expressions", "plan_fields", "plan_inputs", "plan_scan_sources",
    "plan_shape_source_name", "retarget_expression_ir", "row_source_key",
    "row_source_plan_ir",
]
