"""Stable JSON codec for row-source plan IR."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from ..expressions.ir_codec import decode_expression_ir, encode_expression_ir
from .ir import (
    RowDistinctIR,
    RowFilterIR,
    RowGroupByIR,
    RowJoinIR,
    RowOrderByIR,
    RowOrderKeyIR,
    RowScanIR,
    RowSourcePlanIR,
    RowUnionIR,
)


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _array(value: Any, context: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{context} must be an array")
    return value


def _text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"{key!r} must be a non-empty string")
    return result


def _boolean(value: Mapping[str, Any], key: str, default: bool | None = None) -> bool:
    result = value.get(key, default)
    if not isinstance(result, bool):
        raise ValueError(f"{key!r} must be a boolean")
    return result


def encode_row_source_plan(plan: RowSourcePlanIR) -> dict[str, Any]:
    """Encode one row-source plan into its canonical JSON-compatible form."""
    if isinstance(plan, RowScanIR):
        return {"kind": "scan", "source": plan.source}
    if isinstance(plan, RowFilterIR):
        return {
            "kind": "filter",
            "input": encode_row_source_plan(plan.input),
            "predicate": encode_expression_ir(plan.predicate),
        }
    if isinstance(plan, RowUnionIR):
        return {
            "kind": "union",
            "left": encode_row_source_plan(plan.left),
            "right": encode_row_source_plan(plan.right),
            "all": plan.all,
        }
    if isinstance(plan, RowJoinIR):
        return {
            "kind": "join",
            "left": encode_row_source_plan(plan.left),
            "right": encode_row_source_plan(plan.right),
            "left_key": encode_expression_ir(plan.left_key),
            "right_key": encode_expression_ir(plan.right_key),
            "how": plan.how,
        }
    if isinstance(plan, RowGroupByIR):
        return {
            "kind": "group_by",
            "input": encode_row_source_plan(plan.input),
            "keys": [
                {"name": name, "expression": encode_expression_ir(expression)}
                for name, expression in plan.keys
            ],
        }
    if isinstance(plan, RowDistinctIR):
        return {"kind": "distinct", "input": encode_row_source_plan(plan.input)}
    if isinstance(plan, RowOrderByIR):
        return {
            "kind": "order_by",
            "input": encode_row_source_plan(plan.input),
            "keys": [
                {
                    "expression": encode_expression_ir(key.expression),
                    "ascending": key.ascending,
                }
                for key in plan.keys
            ],
        }
    raise TypeError(f"unsupported row-source plan {plan!r}")


def decode_row_source_plan(value: Mapping[str, Any]) -> RowSourcePlanIR:
    """Decode one row-source plan from its canonical JSON-compatible form."""
    kind = value.get("kind")
    if kind == "scan":
        return RowScanIR(_text(value, "source"))
    if kind == "filter":
        return RowFilterIR(
            decode_row_source_plan(_object(value.get("input"), "row-source input")),
            decode_expression_ir(_object(value.get("predicate"), "row-source predicate")),
        )
    if kind == "union":
        return RowUnionIR(
            decode_row_source_plan(_object(value.get("left"), "row-source left")),
            decode_row_source_plan(_object(value.get("right"), "row-source right")),
            _boolean(value, "all"),
        )
    if kind == "join":
        how = value.get("how")
        if how not in {"inner", "left", "right", "full"}:
            raise ValueError(f"unknown join mode {how!r}")
        return RowJoinIR(
            decode_row_source_plan(_object(value.get("left"), "row-source left")),
            decode_row_source_plan(_object(value.get("right"), "row-source right")),
            decode_expression_ir(_object(value.get("left_key"), "join left key")),
            decode_expression_ir(_object(value.get("right_key"), "join right key")),
            cast(Any, how),
        )
    if kind == "group_by":
        keys = []
        for item in _array(value.get("keys"), "group-by keys"):
            document = _object(item, "group-by key")
            keys.append((
                _text(document, "name"),
                decode_expression_ir(
                    _object(document.get("expression"), "group-by key expression")
                ),
            ))
        return RowGroupByIR(
            decode_row_source_plan(_object(value.get("input"), "row-source input")),
            tuple(keys),
        )
    if kind == "distinct":
        return RowDistinctIR(
            decode_row_source_plan(_object(value.get("input"), "row-source input"))
        )
    if kind == "order_by":
        keys = []
        for item in _array(value.get("keys"), "order-by keys"):
            document = _object(item, "order-by key")
            keys.append(RowOrderKeyIR(
                decode_expression_ir(
                    _object(document.get("expression"), "order-by key expression")
                ),
                _boolean(document, "ascending"),
            ))
        return RowOrderByIR(
            decode_row_source_plan(_object(value.get("input"), "row-source input")),
            tuple(keys),
        )
    raise ValueError(f"unknown row-source plan kind {kind!r}")


__all__ = ["decode_row_source_plan", "encode_row_source_plan"]
