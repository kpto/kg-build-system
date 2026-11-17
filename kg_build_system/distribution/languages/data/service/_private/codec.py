"""Canonical document codec for the data language blueprint part."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from kg_build_system.distribution.languages.annotations.service.internal import annotation_from_document, annotation_to_document
from kg_build_system.distribution.languages.expressions.model.internal.dto import OperationParameterDTO
from kg_build_system.distribution.languages.expressions.service.internal.dto.codec import expression_from_document, expression_to_document
from kg_build_system.distribution.model.public.refs import (
    AssetRef, FieldRef, RelationRef, ref_from_document, ref_to_document,
)
from kg_build_system.distribution.languages.data.model.public.shapes import ShapeField
from kg_build_system.kernel.model.internal.json import FrozenObject, freeze_json
from kg_build_system.kernel.service.internal.types import type_from_dto, type_from_document, type_to_document, type_to_dto
from ...model.internal.dto.blueprint_dto import (
    ColumnDTO, DataPartDTO, DefinitionDTO, DerivedRelationDTO,
    FieldDefinitionDTO, SourceRelationDTO, RowDistinctDTO,
    RowFilterDTO, RowGroupByDTO, RowJoinDTO, RowOperationDTO, RowOrderByDTO,
    RowScanDTO, RowSourcePlanDTO, RowUnionDTO, RowUnnestDTO, StructDTO,
)

_JOIN_MODES = {"inner", "left", "right", "full"}
_GRAINS = {"one_per_input_row", "one_per_group", "one_total"}


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


def _encode_meaning(value: Any) -> dict[str, Any]:
    from kg_build_system.distribution.languages.meaning.service.internal import (
        meaning_to_document,
    )

    return meaning_to_document(value)


def _decode_meaning(value: Any) -> Any:
    from kg_build_system.distribution.languages.meaning.service.internal import (
        meaning_from_document,
    )

    return meaning_from_document(value)


def _optional_meaning(value: Mapping[str, Any]) -> Any:
    document = value.get("meaning")
    return None if document is None else _decode_meaning(document)


def _encode_definition(value: DefinitionDTO) -> dict[str, Any]:
    return {
        "grain": value.grain,
        "identity": list(value.identity),
    }


def _decode_definition(value: Any) -> DefinitionDTO:
    document = _object(value, "definition")
    identity = _array(document.get("identity"), "definition identity")
    names: list[str] = []
    for item in identity:
        if not isinstance(item, str) or not item:
            raise ValueError(
                "definition identity names must be non-empty strings"
            )
        names.append(item)
    return DefinitionDTO(grain=_text(document, "grain"), identity=tuple(names))


def _optional_definition(value: Mapping[str, Any]) -> DefinitionDTO | None:
    document = value.get("definition")
    return None if document is None else _decode_definition(document)


def _encode_field_definition(value: FieldDefinitionDTO) -> dict[str, Any]:
    result: dict[str, Any] = {"value": value.value}
    if value.unit is not None:
        result["unit"] = value.unit
    if value.null_meaning is not None:
        result["null_meaning"] = value.null_meaning
    return result


def _decode_field_definition(value: Any) -> FieldDefinitionDTO:
    document = _object(value, "field definition")
    return FieldDefinitionDTO(
        value=_text(document, "value"),
        unit=_optional_text(document, "unit"),
        null_meaning=_optional_text(document, "null_meaning"),
    )


def _optional_field_definition(
    value: Mapping[str, Any],
) -> FieldDefinitionDTO | None:
    document = value.get("definition")
    return None if document is None else _decode_field_definition(document)


def _thaw_json(value: Any) -> Any:
    if isinstance(value, FrozenObject):
        return {key: _thaw_json(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _encode_shape_field(field: ShapeField) -> dict[str, Any]:
    return {
        "attribute": field.attribute,
        "name": field.name,
        "logical_type": type_to_document(type_to_dto(field.logical_type)),
    }


def _decode_shape_field(value: Any) -> ShapeField:
    document = _object(value, "shape field")
    return ShapeField(
        attribute=_text(document, "attribute"),
        name=_text(document, "name"),
        logical_type=type_from_dto(
            type_from_document(
                _object(document.get("logical_type"), "logical_type")
            )
        ),
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
    if isinstance(plan, RowUnnestDTO):
        return {
            "kind": "unnest",
            "input": _encode_plan(plan.input),
            "field": plan.field,
            "expression": expression_to_document(plan.expression),
        }
    if isinstance(plan, RowOperationDTO):
        return {
            "kind": "operation",
            "operation": plan.operation,
            "input": _encode_plan(plan.input),
            "parameters": [
                {"name": parameter.name, "value": _thaw_json(parameter.value)}
                for parameter in plan.parameters
            ],
            "output": [_encode_shape_field(field) for field in plan.output],
            "grain": plan.grain,
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
    if kind == "unnest":
        return RowUnnestDTO(
            _decode_plan(_object(value.get("input"), "row-source input")),
            _text(value, "field"),
            expression_from_document(
                _object(value.get("expression"), "unnest expression")
            ),
        )
    if kind == "operation":
        grain = value.get("grain")
        if grain not in _GRAINS:
            raise ValueError(f"unknown row operation grain {grain!r}")
        parameters = []
        for item in _array(value.get("parameters", ()), "operation parameters"):
            document = _object(item, "operation parameter")
            parameters.append(OperationParameterDTO(
                _text(document, "name"), freeze_json(document.get("value")),
            ))
        return RowOperationDTO(
            operation=_text(value, "operation"),
            input=_decode_plan(_object(value.get("input"), "row-source input")),
            parameters=tuple(parameters),
            output=_items(value, "output", _decode_shape_field),
            grain=cast(Any, grain),
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
    if value.expression is not None:
        result["expression"] = expression_to_document(value.expression)
    if value.meaning is not None:
        result["meaning"] = _encode_meaning(value.meaning)
    if value.definition is not None:
        result["definition"] = _encode_field_definition(value.definition)
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
        annotations=_items(value, "annotations", annotation_from_document),
        expression=(
            None if expression is None
            else expression_from_document(_object(expression, "expression"))
        ),
        meaning=_optional_meaning(value),
        definition=_optional_field_definition(value),
    )


def _encode_declaration(
    value: StructDTO | SourceRelationDTO | DerivedRelationDTO,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": value.name,
        "columns": [_encode_column(column) for column in value.columns],
        "annotations": [annotation_to_document(item) for item in value.annotations],
    }
    if value.meaning is not None:
        result["meaning"] = _encode_meaning(value.meaning)
    if isinstance(value, SourceRelationDTO):
        result["asset"] = ref_to_document(value.asset)
        if value.definition is not None:
            result["definition"] = _encode_definition(value.definition)
    elif isinstance(value, DerivedRelationDTO):
        result["definition"] = _encode_definition(value.definition)
    return result


def _decode_struct(value: Mapping[str, Any]) -> StructDTO:
    return StructDTO(
        name=_text(value, "name"),
        columns=_items(value, "columns", _decode_column),
        annotations=_items(value, "annotations", annotation_from_document),
        meaning=_optional_meaning(value),
    )


def _decode_relation(value: Mapping[str, Any]) -> SourceRelationDTO:
    asset = ref_from_document(value.get("asset"))
    if not isinstance(asset, AssetRef):
        raise ValueError("a source relation 'asset' must be an asset reference")
    return SourceRelationDTO(
        name=_text(value, "name"),
        columns=_items(value, "columns", _decode_column),
        asset=asset,
        annotations=_items(value, "annotations", annotation_from_document),
        meaning=_optional_meaning(value),
        definition=_optional_definition(value),
    )


def _encode_derived_relation(value: DerivedRelationDTO) -> dict[str, Any]:
    result = _encode_declaration(value)
    result["row_source"] = _encode_plan(value.row_source)
    result["visibility"] = value.visibility
    return result


def _decode_derived_relation(value: Mapping[str, Any]) -> DerivedRelationDTO:
    visibility = value.get("visibility", "public")
    if visibility not in ("public", "internal"):
        raise ValueError("derived relation visibility must be public or internal")
    definition = _optional_definition(value)
    if definition is None:
        raise ValueError(
            "a derived relation requires a Contract with a Definition and a Meaning"
        )
    return DerivedRelationDTO(
        name=_text(value, "name"),
        columns=_items(value, "columns", _decode_column),
        row_source=_decode_plan(
            _object(value.get("row_source"), "derived relation row_source")
        ),
        definition=definition,
        annotations=_items(value, "annotations", annotation_from_document),
        visibility=cast(Any, visibility),
        meaning=_optional_meaning(value),
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
        "source_relations": [_encode_declaration(item) for item in data.source_relations],
        "derived_relations": [
            _encode_derived_relation(item) for item in data.derived_relations
        ],
    }


def data_from_document(value: Mapping[str, Any]) -> DataPartDTO:
    """Decode the data language part from its canonical document.

    Example:
        ```python
        from kg_build_system.distribution.languages.data.model.internal.dto import (
            data_from_document,
        )

        data = data_from_document({
            "structs": [], "source_relations": [], "derived_relations": [],
        })
        ```
    """
    if not isinstance(value, Mapping):
        raise ValueError("the data part must be an object")
    return DataPartDTO(
        structs=_items(value, "structs", _decode_struct),
        source_relations=_items(value, "source_relations", _decode_relation),
        derived_relations=_items(
            value, "derived_relations", _decode_derived_relation,
        ),
    )


__all__ = ["data_from_document", "data_to_document"]
