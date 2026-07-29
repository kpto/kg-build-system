"""Data contract and projection authoring functions."""
from __future__ import annotations

from typing import Any, ClassVar, Protocol, TypeVar, cast, dataclass_transform, get_args, get_type_hints

from ..expressions import Expression, FieldPath
from ..specification import Declaration, Specification
from .models import BoundTable, DataSourceConfig, Field, ProjectedField

T = TypeVar("T")
C = TypeVar("C", bound="TableContract")
P = TypeVar("P", bound=Specification)

class TableDecorator(Protocol):
    def __call__(self, cls: type[C]) -> type[C]: ...

@dataclass_transform(field_specifiers=(Field,))
class TableContract(Specification):
    """A reusable typed table or nested record shape."""
    _fields: ClassVar[dict[str, Field[Any]]] = {}
    _concrete: ClassVar[bool] = False
    _table_name: ClassVar[str] = ""

def field[T](*, name: str) -> Field[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    """Create a declaration; T is inferred from the annotated assignment context."""
    return Field(name)

def _fields(cls: type) -> dict[str, Field[Any]]:
    result: dict[str, Field[Any]] = {}
    for base in reversed(cls.__mro__): result.update({name: value for name, value in vars(base).items() if isinstance(value, Field)})
    return result

def _prepare_contract(cls: type[C], *, concrete: bool, name: str | None = None) -> type[C]:
    fields = _fields(cls); hints = get_type_hints(cls)
    for attribute, declared in fields.items():
        arguments = get_args(hints.get(attribute, Any)); object.__setattr__(declared, "type_hint", arguments[0] if arguments else Any)
    cls._fields, cls._concrete = fields, concrete
    if name is not None: cls._table_name = name
    return cls

def table(*, name: str) -> TableDecorator:
    def decorate(cls: type[C]) -> type[C]: return _prepare_contract(cls, concrete=True, name=name)
    return cast(TableDecorator, decorate)

def struct(cls: type[C]) -> type[C]: return _prepare_contract(cls, concrete=False)

def projected_field[T](value: Expression[T] | FieldPath[T] | Declaration[T]) -> ProjectedField[T]:
    return ProjectedField(cast(Expression[T] | FieldPath[T], value))

def projection(cls: type[P]) -> type[P]:
    cls._projection_fields = {name: value for name, value in vars(cls).items() if isinstance(value, ProjectedField)}
    return cls

def bind_source(*, target: type, config: DataSourceConfig) -> BoundTable:
    if not getattr(target, "_concrete", False): raise TypeError("Sources require a concrete @table")
    return BoundTable(target, config)
