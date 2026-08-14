"""Typed structured expressions and field-selection tokens."""
from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from ..types import LogicalType, NullableType, Struct, StructType
from .base import operation
from .nullable import NullableValueExpression
from .values import ValueExpression


TStruct = TypeVar("TStruct", bound=Struct)
TExpr = TypeVar("TExpr", bound=ValueExpression)
TNullExpr = TypeVar("TNullExpr", bound=ValueExpression)


@dataclass(frozen=True, slots=True)
class PickedField(Generic[TStruct, TExpr, TNullExpr]):
    """A typed path token returned by a field on a struct declaration."""

    name: str
    logical_type: LogicalType

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("picked fields require a non-empty name")


def _declaration(logical_type: StructType) -> type[Struct]:
    value = importlib.import_module(logical_type.module)
    declaration = value
    for part in logical_type.qualname.split("."):
        declaration = getattr(declaration, part)
    if not isinstance(declaration, type) or not issubclass(declaration, Struct):
        raise TypeError("struct logical type does not resolve to a Struct declaration")
    return declaration


def _selected(parent, selected: PickedField, *, propagate_null: bool):
    from .factory import wrap_expression

    result_type = selected.logical_type
    if propagate_null and not isinstance(result_type, NullableType):
        result_type = NullableType(result_type)
    result = operation(
        "struct_field",
        parent,
        logical_type=result_type,
        parameters={"name": selected.name},
    )
    return wrap_expression(result)


class StructValueExpression(ValueExpression[TStruct], Generic[TStruct]):
    def __init__(self, expression) -> None:
        if not isinstance(expression.logical_type, StructType):
            raise TypeError("StructValueExpression requires a struct logical type")
        super().__init__(expression)

    def pick(self, selector: Callable[[TStruct], PickedField[TStruct, TExpr, TNullExpr]]) -> TExpr:
        logical_type = self.logical_type
        assert isinstance(logical_type, StructType)
        proxy = object.__new__(_declaration(logical_type))
        selected = selector(cast(TStruct, proxy))
        if not isinstance(selected, PickedField):
            raise TypeError("struct selectors must return a declared field")
        return cast(TExpr, _selected(self.expression, selected, propagate_null=False))


class StructNullableValueExpression(
    NullableValueExpression[TStruct, StructValueExpression[TStruct]], Generic[TStruct]
):
    def __init__(self, expression) -> None:
        logical_type = expression.logical_type
        if not (
            isinstance(logical_type, NullableType)
            and isinstance(logical_type.value, StructType)
        ):
            raise TypeError("StructNullableValueExpression requires a nullable struct type")
        super().__init__(expression, StructValueExpression)

    def pick(self, selector: Callable[[TStruct], PickedField[TStruct, TExpr, TNullExpr]]) -> TNullExpr:
        logical_type = self.logical_type
        assert isinstance(logical_type, NullableType)
        assert isinstance(logical_type.value, StructType)
        proxy = object.__new__(_declaration(logical_type.value))
        selected = selector(cast(TStruct, proxy))
        if not isinstance(selected, PickedField):
            raise TypeError("struct selectors must return a declared field")
        return cast(TNullExpr, _selected(self.expression, selected, propagate_null=True))


__all__ = ["PickedField", "StructNullableValueExpression", "StructValueExpression"]
