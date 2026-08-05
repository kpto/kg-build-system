"""Table, struct, and projection decorators."""
from __future__ import annotations
from typing import Any, Callable, Protocol, TypeVar, cast, overload
from ..expressions import Expression, FieldPath
from .models import BoundTable, DataSourceConfig, Field, ProjectedField, fields_for

T = TypeVar("T")
C = TypeVar("C")

class TableDecorator(Protocol):
    def __call__(self, cls: type[C]) -> type[C]: ...

def field[T](*, name: str | None = None, description: str | None = None) -> Field[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    return Field(name=name, description=description)

def _declaration_kind(cls: type) -> str | None:
    return vars(cls).get("_data_declaration_kind")


def is_concrete_table(cls: type) -> bool:
    return _declaration_kind(cls) == "table"


def _prepare(cls: type[C], kind: str, *, name: str | None = None, metadata: dict[str, Any] | None = None) -> type[C]:
    if kind == "table" and any(_declaration_kind(base) == "table" for base in cls.__mro__[1:]):
        raise TypeError("a final @table may not inherit from another final @table")
    inherited_metadata: dict[str, Any] = {}
    for base in reversed(cls.__mro__[1:]):
        inherited_metadata.update(vars(base).get("_data_metadata", {}))
    inherited_metadata.update(metadata or {})
    setattr(cls, "_fields", fields_for(cls))
    setattr(cls, "_data_declaration_kind", kind)
    setattr(cls, "_data_metadata", inherited_metadata)
    if name is not None:
        setattr(cls, "_data_name", name)
    if kind == "table":
        setattr(cls, "_table_name", name)
    return cls

def table(*, name: str) -> TableDecorator:
    def decorate(cls: type[C]) -> type[C]: return _prepare(cls, "table", name=name)
    return cast(TableDecorator, decorate)

def table_template(*, name: str | None = None, description: str | None = None, **metadata: Any) -> TableDecorator:
    if description is not None:
        metadata["description"] = description
    def decorate(cls: type[C]) -> type[C]: return _prepare(cls, "table_template", name=name, metadata=metadata)
    return cast(TableDecorator, decorate)


@overload
def struct(cls: type[C]) -> type[C]: ...
@overload
def struct(*, name: str | None = None, description: str | None = None, **metadata: Any) -> Callable[[type[C]], type[C]]: ...
def struct(cls: type[C] | None = None, *, name: str | None = None, description: str | None = None, **metadata: Any) -> type[C] | Callable[[type[C]], type[C]]:
    if description is not None:
        metadata["description"] = description
    def decorate(shape: type[C]) -> type[C]: return _prepare(shape, "struct", name=name, metadata=metadata)
    return decorate if cls is None else decorate(cls)

def projected_field[T](value: Expression[T] | FieldPath[T]) -> ProjectedField[T]: return ProjectedField(value)

def _validate_projection_value(value: Expression[Any] | FieldPath[Any]) -> None:
    if isinstance(value, FieldPath):
        if not is_concrete_table(value.table):
            raise TypeError("projections may reference only final @table inputs")
        return
    for argument in value.args:
        if isinstance(argument, (Expression, FieldPath)):
            _validate_projection_value(argument)


def projection(cls: type[C]) -> type[C]:
    for value in vars(cls).values():
        if isinstance(value, ProjectedField):
            _validate_projection_value(value.expression)
    setattr(cls, "_projection_fields", {name: value for name, value in vars(cls).items() if isinstance(value, ProjectedField)})
    return cls

def bind_source(*, target: type, config: DataSourceConfig) -> BoundTable:
    if not is_concrete_table(target): raise TypeError("sources require a final @table")
    return BoundTable(target, config)
