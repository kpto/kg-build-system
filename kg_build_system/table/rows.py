"""Authoring row sources and the relational algebra over their plans.

A row source's shape is the type of one row, not its schema: reading a field
returns a typed selection. The operations here stay shape-preserving where the
shape can be — ``where``, ``union``, ``distinct`` and ``order_by`` — and generate
a shape only where the row genuinely has new members: ``join`` and ``group_by``.

Join result shape
-----------------
``join(other, on=..., how=...)`` produces ``{on, left, right}``:

* ``on`` is the join key, typed from the key expressions (which must agree).
  It is non-null for an inner join; for an outer join it is nullable when the
  key on the side whose rows survive unmatched is nullable. A null key never
  matches, because the lowerer emits plain SQL equality.
* ``left`` and ``right`` are the records of the two input rows. Each side is
  nullable according to ``how``: the right side for ``left`` and ``full``, the
  left side for ``right`` and ``full``, neither for ``inner``.

Group result shape
------------------
``group_by(by=...)`` produces ``{by, members}``:

* ``by`` is a record holding the named key expressions.
* ``members`` is an array of generated record shapes mirroring the input row,
  one row per distinct key. Its item order is unspecified. Rows whose key tuple
  contains a null are dropped before grouping, so a key never groups a null.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any, Generic, TypeVar, cast

from ..expressions import (
    BoolExpression,
    OperationExpression,
    Traversal,
    ValueExpression,
    as_expression,
    field_reference,
    select_member,
    wrap_expression,
)
from ..expressions.ir import (
    ExpressionIR,
    FieldReferenceExpressionIR,
    OperationExpressionIR,
)
from ..expressions.mapping import expression_to_ir
from ..types import (
    ArrayType,
    LogicalType,
    NullableType,
    Shape,
    Struct,
    StructType,
    register_shape,
)
from ..types.ir import (
    ArrayTypeIR,
    CustomTypeIR,
    LogicalTypeIR,
    NullableTypeIR,
    StructTypeIR as StructTypeIRModel,
    UnitTypeIR,
)
from ..types.ir_codec import decode_type_ir, encode_type_ir
from ..types.mapping import type_to_ir
from .ir import (
    JoinHow,
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
from .ir_codec import encode_row_source_plan
from .fields import Field, FieldMetadata

S = TypeVar("S", bound=Shape)


def shape_context(shape: type[S]) -> S:
    """A symbolic instance of a shape, used as the subject of authoring lambdas."""
    return object.__new__(shape)


@dataclass(frozen=True, slots=True)
class ShapeField:
    """One member of a row shape, in both attribute and external form."""

    attribute: str
    name: str
    logical_type: Any


_TYPE_MODULE = "kg_build_system.table.rows"


def _base(logical_type: Any) -> Any:
    if isinstance(logical_type, (NullableType, NullableTypeIR)):
        return logical_type.value
    return logical_type


def _is_nullable(logical_type: Any) -> bool:
    return isinstance(logical_type, (NullableType, NullableTypeIR))


def _encode_logical_type(logical_type: Any) -> Any:
    if isinstance(logical_type, (
        UnitTypeIR, CustomTypeIR, StructTypeIRModel, ArrayTypeIR, NullableTypeIR,
    )):
        return encode_type_ir(logical_type)
    return encode_type_ir(type_to_ir(cast(LogicalType, logical_type)))


def _nullable_ir(logical_type: Any) -> Any:
    if isinstance(logical_type, (NullableType, NullableTypeIR)):
        return logical_type
    if isinstance(logical_type, (
        UnitTypeIR, CustomTypeIR, StructTypeIRModel, ArrayTypeIR,
    )):
        return NullableTypeIR(cast(Any, logical_type))
    return NullableType(cast(Any, logical_type))


def _traversals(name: str, logical_type: Any) -> tuple[Traversal, ...]:
    base = _base(logical_type)
    if isinstance(base, StructType):
        return (Traversal("struct", (name,)),)
    if isinstance(base, ArrayType):
        return (Traversal("array", (name,)),)
    return ()


def _identifier(name: str) -> str:
    if not name.isidentifier() or name.startswith("_"):
        raise ValueError(
            f"generated shape member {name!r} must be a public Python identifier"
        )
    return name


def _shape_signature(fields: Sequence[ShapeField]) -> tuple[tuple[str, Any], ...]:
    return tuple((field.name, field.logical_type) for field in fields)


def _field_digest(fields: Sequence[ShapeField]) -> str:
    return sha256(json.dumps(
        [
            {
                "attribute": field.attribute,
                "name": field.name,
                "logical_type": _encode_logical_type(field.logical_type),
            }
            for field in fields
        ],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


_RECORD_SHAPES: dict[StructType, type[Struct]] = {}


class _RecordField:
    """One structural member of a generated record shape."""

    __slots__ = ("name", "logical_type")

    def __init__(self, name: str, logical_type: Any) -> None:
        self.name = name
        self.logical_type = logical_type

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any:
        if owner is None:
            if instance is None:
                raise TypeError("record fields require a declaration owner")
            owner = type(instance)
        declaration = StructType(owner.__module__, owner.__qualname__)
        return select_member(self.name, self.logical_type, declaration)


def record_shape(fields: Sequence[ShapeField]) -> type[Struct]:
    """A ``Struct`` mirror of a row shape, resolved from its logical type."""
    logical = StructType(
        _TYPE_MODULE, f"RowSourceRecord_{_field_digest(fields)[:24]}",
    )
    registered = _RECORD_SHAPES.get(logical)
    if registered is not None:
        return registered
    namespace: dict[str, Any] = {
        "__module__": logical.module,
        "__qualname__": logical.qualname,
    }
    for field in fields:
        logical_type = (
            decode_type_ir(encode_type_ir(field.logical_type))
            if _is_ir_type(field.logical_type)
            else field.logical_type
        )
        namespace[_identifier(field.attribute)] = _RecordField(
            field.name, logical_type,
        )
    shape = type(logical.qualname, (Struct,), namespace)
    register_shape(shape)
    _RECORD_SHAPES[logical] = shape
    return shape


def _is_ir_type(logical_type: Any) -> bool:
    return isinstance(logical_type, (
        UnitTypeIR, CustomTypeIR, StructTypeIRModel, ArrayTypeIR, NullableTypeIR,
    ))


def record_shape_type(fields: Sequence[ShapeField]):
    """The struct type identity of a row shape used as a nested record.

    The name is a pure function of the members, so authoring and a decoded
    blueprint compute the same identity without sharing a Python class. The
    class is generated and registered here too: a struct type only ever
    reaches a selector, which needs the declaration behind its identity.
    """
    shape = record_shape(fields)
    if fields and _is_ir_type(fields[0].logical_type):
        return StructTypeIRModel(shape.__module__, shape.__qualname__)
    return StructType(shape.__module__, shape.__qualname__)


def make_row_shape(
    source_name: str, fields: Sequence[ShapeField], *, allow_empty: bool = False,
) -> type[Shape]:
    """A generated row shape whose fields read one physical row-source key."""
    if not fields and not allow_empty:
        raise ValueError("row-source shapes require at least one field")
    used: set[str] = set()
    attrs: dict[str, Any] = {
        "_kg_row_source_name": source_name,
        "_projection_name": source_name,
        "_kg_shape_view": True,
        "_kg_row_source_fields": tuple(fields),
    }
    for field in fields:
        attribute = _identifier(field.attribute)
        if attribute in used:
            raise ValueError(f"duplicate generated shape attribute {attribute!r}")
        used.add(attribute)
        attrs[attribute] = Field(
            wrap_expression(field_reference(
                source=source_name,
                path=(field.name,),
                logical_type=field.logical_type,
                traversals=_traversals(field.name, field.logical_type),
            )),
            FieldMetadata(name=field.name, attribute=attribute),
        )
    name = "RowSourceShape_" + sha256(
        (source_name + _field_digest(fields)).encode("utf-8")
    ).hexdigest()[:24]
    return type(name, (Shape,), attrs)


def projection_attrs(shape: type[Shape]) -> dict[str, Any]:
    """Projection-field descriptors for every member of a shape."""
    source_name = shape_source_name(shape)
    return {
        field.attribute: Field(
            wrap_expression(field_reference(
                source=source_name,
                path=(field.name,),
                logical_type=field.logical_type,
                traversals=_traversals(field.name, field.logical_type),
            )),
            FieldMetadata(name=field.name, attribute=field.attribute),
        )
        for field in shape_fields(shape)
    }


def shape_fields(shape: type[Shape]) -> tuple[ShapeField, ...]:
    """The members of a shape, whether declared or generated."""
    recorded = vars(shape).get("_kg_row_source_fields")
    if recorded is not None:
        return cast(tuple[ShapeField, ...], tuple(recorded))
    fields = vars(shape).get("_fields")
    if fields is not None:
        return tuple(
            ShapeField(
                attribute=attribute,
                name=field.metadata.name or attribute,
                logical_type=field.access_type(shape),
            )
            for attribute, field in fields.items()
        )
    raise TypeError(f"{shape.__name__} is not a row shape with readable fields")


def shape_source_name(shape: type[Shape]) -> str:
    """The expression source the shape's own fields read."""
    recorded = vars(shape).get("_kg_row_source_name")
    if isinstance(recorded, str) and recorded:
        return recorded
    table_name = getattr(shape, "_table_name", None)
    if isinstance(table_name, str) and table_name:
        return table_name
    projection_name = getattr(shape, "_projection_name", None)
    if isinstance(projection_name, str) and projection_name:
        return projection_name
    raise TypeError(f"{shape.__name__} is not a row shape with a logical source")


def declaration_source_name(source: Any) -> str:
    """The logical name a table or projection writes its relation under."""
    name = getattr(source, "_table_name", None) or getattr(source, "_projection_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("row sources must be a Table or Projection")
    return name


def _shape_view(shape: type[Shape]) -> type[Shape]:
    """A row shape carrying the fields of a declaration under its own name."""
    return make_row_shape(
        shape_source_name(shape), shape_fields(shape), allow_empty=True,
    )


def _retarget(
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
            arguments=tuple(_retarget(item, mapping) for item in expression.arguments),
        )
    return expression


def retarget_expression_ir(
    expression: ExpressionIR, mapping: Mapping[str, str],
) -> ExpressionIR:
    """Public view of :func:`_retarget` for the lowerers."""
    return _retarget(expression, mapping)


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
    declarations: Mapping[str, Sequence[ShapeField]],
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
        if _shape_signature(left) != _shape_signature(right):
            raise ValueError("union row sources must have the same shape")
        return left
    if isinstance(plan, RowJoinIR):
        left = plan_fields(plan.left, declarations)
        right = plan_fields(plan.right, declarations)
        left_key = _base(plan.left_key.logical_type)
        right_key = _base(plan.right_key.logical_type)
        if left_key != right_key:
            raise ValueError("join key expressions must have the same logical type")
        on_type: LogicalType = left_key
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


def _evaluate_predicate(
    shape: type[Shape], predicate: Callable[[Any], BoolExpression],
) -> BoolExpression:
    if not callable(predicate):
        raise TypeError("where requires a callable predicate")
    result = predicate(shape_context(shape))
    if not isinstance(result, BoolExpression):
        raise TypeError("where predicates must return a BoolExpression")
    return result


def derive_row_source(
    parent: Any, predicate: BoolExpression, *, shape: type[Shape] | None = None,
) -> "DerivedRowSource[Any]":
    """Add one filter over a row source, preserving its shape by default."""
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


def as_row_source(value: Any) -> "RowSource[Any]":
    """Normalize a class object or value row source to a value row source."""
    if isinstance(value, type) and issubclass(value, RowSource):
        method = getattr(value, "row_source", None)
        if not callable(method):
            raise TypeError("row-source classes must provide row_source()")
        return cast("RowSource[Any]", method())
    if isinstance(value, RowSource) and not isinstance(value, type):
        return cast("RowSource[Any]", value)
    raise TypeError(
        "row sources must be a Table, a Projection, or a derived row source"
    )


def _root_source(value: Any) -> Any:
    if isinstance(value, (DerivedRowSource, RelationRowSource)):
        return value.source
    return value.shape


def row_source_plan_ir(value: Any) -> RowSourcePlanIR:
    """The plan IR a class object or value row source authors."""
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


def union_shape_fields(left: type[Shape], right: type[Shape]) -> tuple[ShapeField, ...]:
    """Validate two union operands and return their shared shape."""
    left_fields = shape_fields(left)
    right_fields = shape_fields(right)
    if _shape_signature(left_fields) != _shape_signature(right_fields):
        raise TypeError("union row sources must have the same shape")
    return left_fields


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
    """A source of rows whose shape is ``S``; class objects satisfy this by subclassing."""

    shape: type[S]

    def where(self, predicate: Callable[[S], BoolExpression]) -> "DerivedRowSource[S]":
        result = _evaluate_predicate(self.shape, predicate)
        return cast("DerivedRowSource[S]", derive_row_source(self, result))

    def union(
        self, other: Any, *, all: bool = True,
    ) -> "DerivedRowSource[S]":
        """Stack two same-shaped sources; ``all=False`` removes duplicates."""
        right = as_row_source(other)
        fields = union_shape_fields(self.shape, right.shape)
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
        """
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
                expression_to_ir(left_key.model),
                {shape_source_name(self.shape): row_source_key(left_plan)},
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

    def group_by(
        self, *, by: Callable[[S], Any],
    ) -> "DerivedRowSource[Any]":
        """Group rows by named key expressions; null keys are dropped.

        ``by`` returns either one value input (named ``key``), a mapping of
        names to value inputs, or a sequence of ``(name, value input)`` pairs.
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
            if not isinstance(name, str) or not name.isidentifier():
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
        """Drop duplicate rows without changing the shape."""
        plan = RowDistinctIR(row_source_plan_ir(self))
        return DerivedRowSource(
            shape=self.shape, source=_root_source(self), plan_ir=plan,
        )

    def order_by(
        self, *keys: Any, ascending: bool = True,
    ) -> "DerivedRowSource[S]":
        """Order rows by expressions, selections, or column names."""
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
                    expression_to_ir(expression.model),
                    {shape_source_name(self.shape): source_key},
                ),
                bool(ascending),
            ))
        plan = RowOrderByIR(input_plan, tuple(authored))
        return DerivedRowSource(
            shape=self.shape, source=_root_source(self), plan_ir=plan,
        )


@dataclass(frozen=True, slots=True)
class RelationRowSource(RowSource[S], Generic[S]):
    """A row source over one named table or projection relation."""

    source: type[Any]
    shape: type[S]
    filters: tuple[BoolExpression, ...] = ()

    @property
    def plan_ir(self) -> RowScanIR:
        return RowScanIR(declaration_source_name(self.source))

    def projection_base(self) -> type:
        from .models import projection_base

        return projection_base(self)


@dataclass(frozen=True, slots=True)
class DerivedRowSource(RowSource[S], Generic[S]):
    """A row source derived by filtering or by the relational algebra."""

    shape: type[S]
    source: type[Any]
    filters: tuple[BoolExpression, ...] = ()
    plan_ir: RowSourcePlanIR | None = None

    def projection_base(self) -> type:
        from .models import projection_base

        return projection_base(self)


__all__ = [
    "DerivedRowSource",
    "RelationRowSource",
    "RowSource",
    "ShapeField",
    "as_row_source",
    "declaration_source_name",
    "derive_row_source",
    "make_row_shape",
    "plan_expressions",
    "plan_fields",
    "plan_inputs",
    "plan_scan_sources",
    "plan_shape_source_name",
    "record_shape",
    "record_shape_type",
    "retarget_expression_ir",
    "row_source_key",
    "row_source_plan_ir",
    "shape_fields",
    "shape_source_name",
    "union_shape_fields",
]
