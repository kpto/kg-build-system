"""Canonical document codec for the data language blueprint part."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from kg_build_system.distribution.languages.annotations.service.internal import annotation_from_document, annotation_to_document
from kg_build_system.distribution.languages.expressions.service.internal.dto.codec import expression_from_document, expression_to_document
from kg_build_system.distribution.model.public.refs import (
    AssetRef, FieldRef, RelationRef, ref_from_document, ref_to_document,
)
from kg_build_system.kernel.service.internal.types import type_from_document, type_to_document
from ...model.internal.dto.blueprint_dto import (
    ColumnDTO, DataPartDTO, ProjectionDTO, RelationDTO, RowDistinctDTO,
    RowFilterDTO, RowGroupByDTO, RowJoinDTO, RowOrderByDTO, RowScanDTO,
    RowSourcePlanDTO, RowUnionDTO, StructDTO,
)

_JOIN_MODES = {"inner", "left", "right", "full"}


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


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    result = value.get(key)
    if result is not None and (not isinstance(result, str) or not result):
        raise ValueError(f"{key!r} must be null or a non-empty string")
    return result


def _boolean(value: Mapping[str, Any], key: str, default: bool | None = None) -> bool:
    result = value.get(key, default)
    if not isinstance(result, bool):
        raise ValueError(f"{key!r} must be a boolean")
    return result


def _items(value: Mapping[str, Any], key: str, decoder: Any) -> tuple[Any, ...]:
    return tuple(
        decoder(_object(item, key)) for item in _array(value.get(key, ()), key)
    )


# ---------------------------------------------------------------------------
# Row plans


def _encode_plan(plan: RowSourcePlanDTO) -> dict[str, Any]:
    if isinstance(plan, RowScanDTO):
        return {"kind": "scan", "relation": ref_to_document(plan.relation)}
    if isinstance(plan, RowFilterDTO):
        return {
            "kind": "filter",
            "input": _encode_plan(plan.input),
            "predicate": expression_to_document(plan.predicate),
        }
    if isinstance(plan, RowUnionDTO):
        return {
            "kind": "union",
            "left": _encode_plan(plan.left),
            "right": _encode_plan(plan.right),
            "all": plan.all,
        }
    if isinstance(plan, RowJoinDTO):
        return {
            "kind": "join",
            "left": _encode_plan(plan.left),
            "right": _encode_plan(plan.right),
            "left_key": expression_to_document(plan.left_key),
            "right_key": expression_to_document(plan.right_key),
            "how": plan.how,
        }
    if isinstance(plan, RowGroupByDTO):
        return {
            "kind": "group_by",
            "input": _encode_plan(plan.input),
            "keys": [
                {"name": name, "expression": expression_to_document(expression)}
                for name, expression in plan.keys
            ],
        }
    if isinstance(plan, RowDistinctDTO):
        return {"kind": "distinct", "input": _encode_plan(plan.input)}
    if isinstance(plan, RowOrderByDTO):
        return {
            "kind": "order_by",
            "input": _encode_plan(plan.input),
            "keys": [
                {
                    "expression": expression_to_document(expression),
                    "ascending": ascending,
                }
                for expression, ascending in plan.keys
            ],
        }
    raise TypeError(f"unsupported row-source plan {plan!r}")


def _decode_plan(value: Mapping[str, Any]) -> RowSourcePlanDTO:
    kind = value.get("kind")
    if kind == "scan":
        relation = ref_from_document(value.get("relation"))
        if not isinstance(relation, RelationRef):
            raise ValueError("a row plan 'relation' must be a relation reference")
        return RowScanDTO(relation)
    if kind == "filter":
        return RowFilterDTO(
            _decode_plan(_object(value.get("input"), "row-source input")),
            expression_from_document(
                _object(value.get("predicate"), "row-source predicate")
            ),
        )
    if kind == "union":
        return RowUnionDTO(
            _decode_plan(_object(value.get("left"), "row-source left")),
            _decode_plan(_object(value.get("right"), "row-source right")),
            _boolean(value, "all"),
        )
    if kind == "join":
        how = value.get("how")
        if how not in _JOIN_MODES:
            raise ValueError(f"unknown join mode {how!r}")
        return RowJoinDTO(
            _decode_plan(_object(value.get("left"), "row-source left")),
            _decode_plan(_object(value.get("right"), "row-source right")),
            expression_from_document(_object(value.get("left_key"), "join left key")),
            expression_from_document(_object(value.get("right_key"), "join right key")),
            cast(Any, how),
        )
    if kind == "group_by":
        keys = []
        for item in _array(value.get("keys"), "group-by keys"):
            document = _object(item, "group-by key")
            keys.append((
                _text(document, "name"),
                expression_from_document(
                    _object(document.get("expression"), "group-by key expression")
                ),
            ))
        return RowGroupByDTO(
            _decode_plan(_object(value.get("input"), "row-source input")),
            tuple(keys),
        )
    if kind == "distinct":
        return RowDistinctDTO(
            _decode_plan(_object(value.get("input"), "row-source input"))
        )
    if kind == "order_by":
        keys = []
        for item in _array(value.get("keys"), "order-by keys"):
            document = _object(item, "order-by key")
            keys.append((
                expression_from_document(
                    _object(document.get("expression"), "order-by key expression")
                ),
                _boolean(document, "ascending"),
            ))
        return RowOrderByDTO(
            _decode_plan(_object(value.get("input"), "row-source input")),
            tuple(keys),
        )
    raise ValueError(f"unknown row-source plan kind {kind!r}")


# ---------------------------------------------------------------------------
# Declarations


def _encode_column(value: ColumnDTO) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": value.name,
        "logical_type": type_to_document(value.logical_type),
        "ref": ref_to_document(value.ref),
        "annotations": [annotation_to_document(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    if value.expression is not None:
        result["expression"] = expression_to_document(value.expression)
    return result


def _decode_column(value: Mapping[str, Any]) -> ColumnDTO:
    expression = value.get("expression")
    reference = ref_from_document(value.get("ref"))
    if not isinstance(reference, FieldRef):
        raise ValueError("a column 'ref' must be a field reference")
    return ColumnDTO(
        name=_text(value, "name"),
        logical_type=type_from_document(
            _object(value.get("logical_type"), "logical_type")
        ),
        ref=reference,
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", annotation_from_document),
        expression=(
            None if expression is None
            else expression_from_document(_object(expression, "expression"))
        ),
    )


def _encode_declaration(
    value: StructDTO | RelationDTO | ProjectionDTO,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": value.name,
        "columns": [_encode_column(column) for column in value.columns],
        "annotations": [annotation_to_document(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    if isinstance(value, RelationDTO):
        result["asset"] = ref_to_document(value.asset)
    return result


def _decode_struct(value: Mapping[str, Any]) -> StructDTO:
    return StructDTO(
        name=_text(value, "name"),
        columns=_items(value, "columns", _decode_column),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", annotation_from_document),
    )


def _decode_relation(value: Mapping[str, Any]) -> RelationDTO:
    asset = ref_from_document(value.get("asset"))
    if not isinstance(asset, AssetRef):
        raise ValueError("a relation 'asset' must be an asset reference")
    return RelationDTO(
        name=_text(value, "name"),
        columns=_items(value, "columns", _decode_column),
        asset=asset,
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", annotation_from_document),
    )


def _encode_projection(value: ProjectionDTO) -> dict[str, Any]:
    result = _encode_declaration(value)
    result["row_source"] = _encode_plan(value.row_source)
    return result


def _decode_projection(value: Mapping[str, Any]) -> ProjectionDTO:
    return ProjectionDTO(
        name=_text(value, "name"),
        columns=_items(value, "columns", _decode_column),
        row_source=_decode_plan(
            _object(value.get("row_source"), "projection row_source")
        ),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", annotation_from_document),
    )


def data_to_document(data: DataPartDTO) -> dict[str, Any]:
    """Encode the data language part as its canonical document.

    Example:
        ```python
        from kg_build_system.distribution.languages.data.model.internal.dto import (
            DataPartDTO, data_to_document,
        )

        document = data_to_document(DataPartDTO((), (), ()))
        ```
    """
    return {
        "structs": [_encode_declaration(item) for item in data.structs],
        "relations": [_encode_declaration(item) for item in data.relations],
        "projections": [_encode_projection(item) for item in data.projections],
    }


def data_from_document(value: Mapping[str, Any]) -> DataPartDTO:
    """Decode the data language part from its canonical document.

    Example:
        ```python
        from kg_build_system.distribution.languages.data.model.internal.dto import (
            data_from_document,
        )

        data = data_from_document({
            "structs": [], "relations": [], "projections": [],
        })
        ```
    """
    if not isinstance(value, Mapping):
        raise ValueError("the data part must be an object")
    return DataPartDTO(
        structs=_items(value, "structs", _decode_struct),
        relations=_items(value, "relations", _decode_relation),
        projections=_items(value, "projections", _decode_projection),
    )


__all__ = ["data_from_document", "data_to_document"]
