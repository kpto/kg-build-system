"""Compilation IR for data declarations and row-source plans.

The IR is the only shape a compiler consumes. A declaration class, its field
descriptors and a row-source value all lower to the values here, so a blueprint
never stores authoring classes or private class attributes.

Row-source plans are engine-neutral. ``row_source_key`` derives a stable logical
key from a plan's canonical encoding, not from the Python object that built it.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias, cast

from ..annotations.ir import AnnotationIR
from ..expressions.ir import ExpressionIR
from ..types.ir import LogicalTypeIR


@dataclass(frozen=True, slots=True)
class FieldIR:
    name: str
    logical_type: LogicalTypeIR
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


@dataclass(frozen=True, slots=True)
class StructIR:
    symbol_id: str
    name: str
    fields: tuple[FieldIR, ...]
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


@dataclass(frozen=True, slots=True)
class TableIR:
    symbol_id: str
    name: str
    fields: tuple[FieldIR, ...]
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectionFieldIR:
    name: str
    expression: ExpressionIR
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


JoinHow = Literal["inner", "left", "right", "full"]


@dataclass(frozen=True, slots=True)
class RowScanIR:
    """Read one named table or projection relation."""

    source: str


@dataclass(frozen=True, slots=True)
class RowFilterIR:
    """Keep the rows of one plan that satisfy a predicate."""

    input: "RowSourcePlanIR"
    predicate: ExpressionIR


@dataclass(frozen=True, slots=True)
class RowUnionIR:
    """Stack two same-shaped plans, optionally deduplicating rows."""

    left: "RowSourcePlanIR"
    right: "RowSourcePlanIR"
    all: bool = True


@dataclass(frozen=True, slots=True)
class RowJoinIR:
    """Equi-join two plans on one expression from each side.

    Null keys never match: the lowerer emits a plain SQL equality, whose
    three-valued result leaves a null key unmatched in every outer-join mode.
    """

    left: "RowSourcePlanIR"
    right: "RowSourcePlanIR"
    left_key: ExpressionIR
    right_key: ExpressionIR
    how: JoinHow = "inner"


@dataclass(frozen=True, slots=True)
class RowGroupByIR:
    """One row per distinct non-null key tuple, with its members collected."""

    input: "RowSourcePlanIR"
    keys: tuple[tuple[str, ExpressionIR], ...]


@dataclass(frozen=True, slots=True)
class RowDistinctIR:
    """Drop duplicate rows while preserving the plan's shape."""

    input: "RowSourcePlanIR"


@dataclass(frozen=True, slots=True)
class RowOrderKeyIR:
    expression: ExpressionIR
    ascending: bool = True


@dataclass(frozen=True, slots=True)
class RowOrderByIR:
    """Order a plan's rows without changing its shape."""

    input: "RowSourcePlanIR"
    keys: tuple[RowOrderKeyIR, ...]


RowSourcePlanIR: TypeAlias = (
    RowScanIR | RowFilterIR | RowUnionIR | RowJoinIR
    | RowGroupByIR | RowDistinctIR | RowOrderByIR
)


@dataclass(frozen=True, slots=True)
class ProjectionIR:
    symbol_id: str
    name: str
    fields: tuple[ProjectionFieldIR, ...]
    description: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()
    row_source: RowSourcePlanIR | None = None


@dataclass(frozen=True, slots=True)
class SourceIR:
    symbol_id: str
    table: str
    location: str
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    version: str | None = None
    annotations: tuple[AnnotationIR, ...] = ()


@dataclass(frozen=True, slots=True)
class DataIR:
    """The frozen ``data`` language part of a build."""

    structs: tuple[StructIR, ...]
    tables: tuple[TableIR, ...]
    projections: tuple[ProjectionIR, ...]
    sources: tuple[SourceIR, ...]


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


def _items(
    value: Mapping[str, Any], key: str, decoder: Any,
) -> tuple[Any, ...]:
    return tuple(
        decoder(_object(item, key)) for item in _array(value.get(key, ()), key)
    )


def _jsonable(value: Any) -> Any:
    """Return a plain JSON-compatible view of an annotation payload."""
    from .._frozen_json import FrozenObject

    if isinstance(value, FrozenObject):
        return {key: _jsonable(item) for key, item in value.items}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Annotation codec


def _encode_annotation(value: AnnotationIR) -> dict[str, Any]:
    return {
        "namespace": value.namespace,
        "annotation_id": value.annotation_id,
        "arguments": _jsonable(value.arguments),
    }


def _decode_annotation(value: Mapping[str, Any]) -> AnnotationIR:
    from .._frozen_json import freeze_json

    return AnnotationIR(
        namespace=_text(value, "namespace"),
        annotation_id=_text(value, "annotation_id"),
        arguments=freeze_json(value.get("arguments")),
    )


# ---------------------------------------------------------------------------
# Row-source plan codec


def encode_row_source_plan(plan: RowSourcePlanIR) -> dict[str, Any]:
    """Encode one row-source plan into its canonical JSON-compatible form."""
    from ..expressions.interfaces import encode_expression_ir

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
    from ..expressions.interfaces import decode_expression_ir

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
            cast(JoinHow, how),
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


# ---------------------------------------------------------------------------
# Data part codec


def _encode_field(value: FieldIR) -> dict[str, Any]:
    from ..types.interfaces import encode_type_ir

    result: dict[str, Any] = {
        "name": value.name,
        "logical_type": encode_type_ir(value.logical_type),
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    return result


def _encode_declaration(value: StructIR | TableIR) -> dict[str, Any]:
    result: dict[str, Any] = {
        "symbol_id": value.symbol_id,
        "name": value.name,
        "fields": [_encode_field(field) for field in value.fields],
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    return result


def _encode_projection_field(value: ProjectionFieldIR) -> dict[str, Any]:
    from ..expressions.interfaces import encode_expression_ir

    result: dict[str, Any] = {
        "name": value.name,
        "expression": encode_expression_ir(value.expression),
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    return result


def _encode_projection(value: ProjectionIR) -> dict[str, Any]:
    result: dict[str, Any] = {
        "symbol_id": value.symbol_id,
        "name": value.name,
        "fields": [_encode_projection_field(field) for field in value.fields],
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.description is not None:
        result["description"] = value.description
    if value.row_source is None:
        raise ValueError("projections require a row source")
    result["row_source"] = encode_row_source_plan(value.row_source)
    return result


def _encode_source(value: SourceIR) -> dict[str, Any]:
    result: dict[str, Any] = {
        "symbol_id": value.symbol_id,
        "table": value.table,
        "location": value.location,
        "format": value.format,
        "annotations": [_encode_annotation(item) for item in value.annotations],
    }
    if value.credential_reference is not None:
        result["credential_reference"] = value.credential_reference
    if value.version is not None:
        result["version"] = value.version
    return result


def encode_data_part(data: DataIR) -> dict[str, Any]:
    """Encode the data part into its canonical JSON-compatible form.

    The argument is usually a :class:`DataIR`; the blueprint aggregate carries
    the same four attributes, so it is accepted as well.
    """
    return {
        "structs": [_encode_declaration(item) for item in data.structs],
        "tables": [_encode_declaration(item) for item in data.tables],
        "projections": [_encode_projection(item) for item in data.projections],
        "sources": [_encode_source(item) for item in data.sources],
    }


def _decode_field(value: Mapping[str, Any]) -> FieldIR:
    from ..types.interfaces import decode_type_ir

    return FieldIR(
        name=_text(value, "name"),
        logical_type=decode_type_ir(_object(value.get("logical_type"), "logical_type")),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_struct(value: Mapping[str, Any]) -> StructIR:
    return StructIR(
        symbol_id=_text(value, "symbol_id"),
        name=_text(value, "name"),
        fields=_items(value, "fields", _decode_field),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_table(value: Mapping[str, Any]) -> TableIR:
    return TableIR(
        symbol_id=_text(value, "symbol_id"),
        name=_text(value, "name"),
        fields=_items(value, "fields", _decode_field),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_projection_field(value: Mapping[str, Any]) -> ProjectionFieldIR:
    from ..expressions.interfaces import decode_expression_ir

    return ProjectionFieldIR(
        name=_text(value, "name"),
        expression=decode_expression_ir(_object(value.get("expression"), "expression")),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def _decode_projection(value: Mapping[str, Any]) -> ProjectionIR:
    row_source = value.get("row_source")
    if row_source is None:
        raise ValueError("projections require a row source")
    return ProjectionIR(
        symbol_id=_text(value, "symbol_id"),
        name=_text(value, "name"),
        fields=_items(value, "fields", _decode_projection_field),
        description=_optional_text(value, "description"),
        annotations=_items(value, "annotations", _decode_annotation),
        row_source=decode_row_source_plan(_object(row_source, "row_source")),
    )


def _decode_source(value: Mapping[str, Any]) -> SourceIR:
    source_format = value.get("format")
    if source_format not in {"csv", "json", "parquet"}:
        raise ValueError(f"unknown source format {source_format!r}")
    return SourceIR(
        symbol_id=_text(value, "symbol_id"),
        table=_text(value, "table"),
        location=_text(value, "location"),
        format=cast(Literal["csv", "json", "parquet"], source_format),
        credential_reference=_optional_text(value, "credential_reference"),
        version=_optional_text(value, "version"),
        annotations=_items(value, "annotations", _decode_annotation),
    )


def decode_data_part(value: Mapping[str, Any]) -> DataIR:
    """Decode the data part from its canonical JSON-compatible form."""
    if not isinstance(value, Mapping):
        raise ValueError("the data part must be an object")
    return DataIR(
        structs=_items(value, "structs", _decode_struct),
        tables=_items(value, "tables", _decode_table),
        projections=_items(value, "projections", _decode_projection),
        sources=_items(value, "sources", _decode_source),
    )


__all__ = [
    "DataIR", "FieldIR", "JoinHow", "ProjectionFieldIR", "ProjectionIR",
    "RowDistinctIR", "RowFilterIR", "RowGroupByIR", "RowJoinIR",
    "RowOrderByIR", "RowOrderKeyIR", "RowScanIR", "RowSourcePlanIR",
    "RowUnionIR", "SourceIR", "StructIR", "TableIR", "decode_data_part",
    "decode_row_source_plan", "encode_data_part", "encode_row_source_plan",
]
