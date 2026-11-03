"""Descriptor that exposes a selection's bindable expression family."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

if TYPE_CHECKING:
    from kg_build_system.kernel.model.public.types import Array, CustomDataType, Nullable, Struct
    from ...model.public.arrays import ArrayExpression
    from ...model.public.boolean import BoolExpression
    from ...model.public.custom import CustomDataTypeExpression
    from ...model.public.nullable import NullableExpression
    from ...model.public.numeric import FloatExpression, IntExpression
    from ...model.public.selections.types import NullableDataType
    from ...model.public.selections.value import ValueSelection
    from ...model.public.structs import StructExpression
    from ...model.public.text import StrExpression
    from ...model.public.values import ValueExpression


class ExpressionDescriptor:
    @overload
    def __get__(self, instance: "ValueSelection[bool]", owner: type[Any] | None) -> "BoolExpression": ...
    @overload
    def __get__(self, instance: "ValueSelection[int]", owner: type[Any] | None) -> "IntExpression": ...
    @overload
    def __get__(self, instance: "ValueSelection[float]", owner: type[Any] | None) -> "FloatExpression": ...
    @overload
    def __get__(self, instance: "ValueSelection[str]", owner: type[Any] | None) -> "StrExpression": ...
    @overload
    def __get__[C: CustomDataType](self, instance: "ValueSelection[C]", owner: type[Any] | None) -> "CustomDataTypeExpression[C]": ...
    @overload
    def __get__(self, instance: "ValueSelection[Nullable[bool]]", owner: type[Any] | None) -> "NullableExpression[bool, BoolExpression]": ...
    @overload
    def __get__(self, instance: "ValueSelection[Nullable[int]]", owner: type[Any] | None) -> "NullableExpression[int, IntExpression]": ...
    @overload
    def __get__(self, instance: "ValueSelection[Nullable[float]]", owner: type[Any] | None) -> "NullableExpression[float, FloatExpression]": ...
    @overload
    def __get__(self, instance: "ValueSelection[Nullable[str]]", owner: type[Any] | None) -> "NullableExpression[str, StrExpression]": ...
    @overload
    def __get__[C: CustomDataType](self, instance: "ValueSelection[Nullable[C]]", owner: type[Any] | None) -> "NullableExpression[C, CustomDataTypeExpression[C]]": ...
    @overload
    def __get__[I: NullableDataType](self, instance: "ValueSelection[Array[I]]", owner: type[Any] | None) -> "ArrayExpression[I]": ...
    @overload
    def __get__[I: NullableDataType](self, instance: "ValueSelection[Nullable[Array[I]]]", owner: type[Any] | None) -> "NullableExpression[Array[I], ArrayExpression[I]]": ...
    @overload
    def __get__[S: Struct](self, instance: "ValueSelection[S]", owner: type[Any] | None) -> "StructExpression[S]": ...
    @overload
    def __get__[S: Struct](self, instance: "ValueSelection[Nullable[S]]", owner: type[Any] | None) -> "NullableExpression[S, StructExpression[S]]": ...
    @overload
    def __get__[T](self, instance: "ValueSelection[T]", owner: type[Any] | None) -> "ValueExpression[T]": ...  # pyright: ignore[reportOverlappingOverload]

    def __get__(self, instance: Any, owner: Any) -> Any:
        if instance is None:
            return self
        from .selections import require_expression

        return require_expression(instance)


__all__ = ["ExpressionDescriptor"]
