from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Generic, Protocol, TypeVar, cast, dataclass_transform, get_args, get_type_hints
from ..expressions import FieldPath
from ..specification import Declaration, Specification

T = TypeVar("T")
C = TypeVar("C", bound="GraphComponent")

class _ComponentDecorator(Protocol):
    """A decorator that retains the concrete component subclass for type checkers."""
    def __call__(self, cls: type[C]) -> type[C]: ...

@dataclass(frozen=True)
class Property(Declaration[T], Generic[T]):
    name: str | None = None
    nullable: bool = True
    description: str | None = None
    def __set_name__(self, owner: type, attr: str):
        object.__setattr__(self, "attr", attr)
    def __get__(self, instance: Any, owner: type) -> FieldPath[T] | T | None:
        if instance is None: return FieldPath[T](owner, (self.name or self.attr,))
        return instance._values.get(self.attr)

def property[T](*, name: str | None = None, nullable: bool = True, description: str | None = None) -> Property[T]:
    return Property(name, nullable, description)

@dataclass_transform(field_specifiers=(property,))
class GraphComponent(Specification):
    _kind = "component"
    def __init__(self, **values: Any):
        declared = self.__class__._properties
        unknown = set(values) - set(declared)
        if unknown: raise TypeError(f"Unknown properties for {type(self).__name__}: {sorted(unknown)}")
        self._values = values

def _properties(cls: type) -> dict[str, Property]:
    result: dict[str, Property] = {}
    for base in reversed(cls.__mro__):
        for name, value in vars(base).items():
            if isinstance(value, Property): result[name] = value
    return result

def _component(kind: str, **meta: Any) -> _ComponentDecorator:
    def decorate(cls: type[C]) -> type[C]:
        properties = _properties(cls); hints = get_type_hints(cls)
        for attribute, declared in properties.items():
            args = get_args(hints.get(attribute, Any))
            object.__setattr__(declared, "type_hint", args[0] if args else Any)
        cls._kind, cls._properties, cls._metadata = kind, properties, dict(meta)
        return cls
    return cast(_ComponentDecorator, decorate)

def node(**meta: Any) -> _ComponentDecorator: return _component("node", **meta)
def edge(*, source: type[GraphComponent], target: type[GraphComponent], **meta: Any) -> _ComponentDecorator: return _component("edge", source=source, target=target, **meta)
