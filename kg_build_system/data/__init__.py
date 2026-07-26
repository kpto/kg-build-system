from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Generic, Protocol, TypeVar, cast, dataclass_transform, get_args, get_type_hints
from ..expressions import Expression, FieldPath
from ..specification import Declaration, Specification

T = TypeVar("T")
C = TypeVar("C", bound="TableContract")
P = TypeVar("P", bound=Specification)

class _TableDecorator(Protocol):
    """A decorator that retains the concrete table subclass for type checkers."""
    def __call__(self, cls: type[C]) -> type[C]: ...

@dataclass(frozen=True)
class Field(Declaration[T], Generic[T]):
    name: str
    type_hint: Any = None
    def __set_name__(self, owner: type, attr: str): object.__setattr__(self, "attr", attr)
    def __get__(self, instance: Any, owner: type) -> FieldPath[T] | T | None:
        if instance is None: return FieldPath[T](owner, (self.name,), self.type_hint)
        return instance

def field[T](*, name: str) -> Field[T]: return Field(name)

@dataclass_transform(field_specifiers=(field,))
class TableContract(Specification): pass

def _fields(cls: type) -> dict[str, Field]:
    found = {}
    for base in reversed(cls.__mro__):
        found.update({name: value for name, value in vars(base).items() if isinstance(value, Field)})
    return found

def _declaration_type(annotation: Any) -> Any:
    args = get_args(annotation)
    return args[0] if args else Any

def _prepare_contract(cls: type, *, concrete: bool, name: str | None = None) -> type:
    hints = get_type_hints(cls)
    fields = _fields(cls)
    for attribute, declared in fields.items():
        object.__setattr__(declared, "type_hint", _declaration_type(hints.get(attribute, Any)))
    cls._fields, cls._concrete = fields, concrete
    if name is not None: cls._table_name = name
    return cls

def table(*, name: str) -> _TableDecorator:
    def decorate(cls: type[C]) -> type[C]:
        return cast(type[C], _prepare_contract(cls, concrete=True, name=name))
    return cast(_TableDecorator, decorate)

@dataclass(frozen=True)
class ProjectedField(Declaration[T], Generic[T]):
    expression: Expression[T] | FieldPath[T]
    name: str | None = None
    def __set_name__(self, owner: type, attr: str):
        object.__setattr__(self, "attr", attr)
        if self.name is None: object.__setattr__(self, "name", attr)
    def __get__(self, instance: Any, owner: type) -> Expression[T] | FieldPath[T]:
        if instance is None: return FieldPath[T](owner, (self.name or self.attr,), self.expression.type_hint, self.expression.cardinality)
        return self.expression

def projected_field[T](value: Expression[T] | FieldPath[T] | Declaration[T]) -> ProjectedField[T]:
    # At runtime, class-level declarations resolve through their descriptor to FieldPath.
    return ProjectedField(cast(Expression[T] | FieldPath[T], value))
def projection(cls: type[P]) -> type[P]:
    cls._projection_fields = {n: v for n, v in vars(cls).items() if isinstance(v, ProjectedField)}
    return cls

def struct(cls: type[C]) -> type[C]:
    """Declare a reusable nested record shape, never a source-bindable table."""
    return cast(type[C], _prepare_contract(cls, concrete=False))

class InputFormat(StrEnum): CSV = "csv"; PARQUET = "parquet"
@dataclass(frozen=True)
class DataSourceConfig:
    location: str
    format: InputFormat = InputFormat.CSV
    credentials: str | None = None
    version: str | None = None
@dataclass(frozen=True)
class BoundTable:
    table: type
    config: DataSourceConfig
def bind_source(*, target: type, config: DataSourceConfig) -> BoundTable:
    if not getattr(target, "_concrete", False): raise TypeError("Sources require a concrete @table")
    return BoundTable(target, config)
