"""Table, struct, and projection decorators."""
from __future__ import annotations
from typing import Any, Protocol, TypeVar, cast, get_args, get_type_hints
from ..expressions import Expression, FieldPath
from .models import BoundTable, DataSourceConfig, Field, ProjectedField

T = TypeVar("T")
C = TypeVar("C")

class TableDecorator(Protocol):
    def __call__(self, cls: type[C]) -> type[C]: ...

def field[T](*, name: str | None = None, description: str | None = None) -> Field[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    return Field(name=name, description=description)

def _fields(cls: type) -> dict[str, Field[Any]]:
    result: dict[str, Field[Any]] = {}
    for base in reversed(cls.__mro__): result.update({name: value for name, value in vars(base).items() if isinstance(value, Field)})
    return result

def _prepare(cls: type[C], concrete: bool, name: str | None = None) -> type[C]:
    fields = _fields(cls); hints = get_type_hints(cls)
    for attribute, descriptor in fields.items():
        annotation = hints.get(attribute, Any)
        arguments = get_args(annotation)
        object.__setattr__(descriptor, "type_hint", arguments[0] if arguments else Any)
    setattr(cls, "_fields", fields); setattr(cls, "_concrete", concrete)
    if name is not None: setattr(cls, "_table_name", name)
    return cls

def table(*, name: str) -> TableDecorator:
    def decorate(cls: type[C]) -> type[C]: return _prepare(cls, True, name)
    return cast(TableDecorator, decorate)

def struct(cls: type[C]) -> type[C]: return _prepare(cls, False)

def projected_field[T](value: Expression[T] | FieldPath[T]) -> ProjectedField[T]: return ProjectedField(value)

def projection(cls: type[C]) -> type[C]:
    setattr(cls, "_projection_fields", {name: value for name, value in vars(cls).items() if isinstance(value, ProjectedField)})
    return cls

def bind_source(*, target: type, config: DataSourceConfig) -> BoundTable:
    if not getattr(target, "_concrete", False): raise TypeError("sources require a concrete @table")
    return BoundTable(target, config)
