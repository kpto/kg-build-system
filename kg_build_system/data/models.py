"""Data-contract descriptors and source models."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Generic, Self, TypeAlias, TypeVar, get_args, get_type_hints, overload
from ..expressions import Expression, FieldPath, item_type
from .._support.naming import snake_case

T = TypeVar("T")

@dataclass(frozen=True)
class Field(Generic[T]):
    name: str | None = None
    description: str | None = None
    type_hint: Any = None
    attr: str = ""
    def __set_name__(self, owner: type, attr: str) -> None:
        object.__setattr__(self, "attr", attr)
        if self.name is None: object.__setattr__(self, "name", snake_case(attr))
    @overload
    def __get__(self, instance: None, owner: type | None = None) -> FieldPath[T]: ...
    @overload
    def __get__(self, instance: object, owner: type | None = None) -> Self: ...
    def __get__(self, instance: object | None, owner: type | None = None) -> FieldPath[T] | Self:
        if instance is not None: return self
        path = (self.name or self.attr,); collections = (path,) if item_type(self.type_hint) is not None else ()
        return FieldPath[T](owner or object, path, self.type_hint, "collection" if collections else "scalar", collections)


def fields_for(cls: type) -> dict[str, "Field[Any]"]:
    """Resolve the declared data shape for final declarations and plain mixins alike."""
    fields: dict[str, Field[Any]] = {}
    for base in reversed(cls.__mro__):
        fields.update({name: value for name, value in vars(base).items() if isinstance(value, Field)})
    hints = get_type_hints(cls)
    for attribute, descriptor in fields.items():
        arguments = get_args(hints.get(attribute, Any))
        object.__setattr__(descriptor, "type_hint", arguments[0] if arguments else Any)
    return fields

@dataclass(frozen=True)
class ProjectedField(Generic[T]):
    expression: Expression[T] | FieldPath[T]
    name: str | None = None
    attr: str = ""
    def __set_name__(self, owner: type, attr: str) -> None:
        object.__setattr__(self, "attr", attr)
        if self.name is None: object.__setattr__(self, "name", snake_case(attr))
    def __get__(self, instance: object | None, owner: type | None = None) -> Expression[T] | FieldPath[T]:
        return self.expression if instance is not None else FieldPath[T](owner or object, (self.name or self.attr,), self.expression.type_hint, self.expression.cardinality)

class InputFormat(StrEnum): CSV = "csv"; JSON = "json"; PARQUET = "parquet"
@dataclass(frozen=True)
class DataSourceConfig: location: str; format: InputFormat = InputFormat.CSV; layout: str | None = None; credentials: str | None = None; version: str | None = None
@dataclass(frozen=True)
class BoundTable:
    table: type
    config: DataSourceConfig


@dataclass(frozen=True)
class BoundTableGroup:
    group: type
    config: DataSourceConfig


BoundSource: TypeAlias = BoundTable | BoundTableGroup
