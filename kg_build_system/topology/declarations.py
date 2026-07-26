"""Topology authoring functions and class decorators."""
from __future__ import annotations

from typing import Any, Callable, Protocol, TypeVar, cast, get_args, get_type_hints

from .models import GraphComponent, Property

T = TypeVar("T")
C = TypeVar("C", bound=GraphComponent)

class ComponentDecorator(Protocol):
    def __call__(self, cls: type[C]) -> type[C]: ...

def property[T](**kwargs: Any) -> Property[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    """Create a declaration; T is inferred from the annotated assignment context."""
    return Property(**kwargs)

def _properties(cls: type) -> dict[str, Property[Any]]:
    found: dict[str, Property[Any]] = {}
    for base in reversed(cls.__mro__):
        found.update({name: value for name, value in vars(base).items() if isinstance(value, Property)})
    return found

def _component(kind: str, **metadata: Any) -> ComponentDecorator:
    def decorate(cls: type[C]) -> type[C]:
        properties = _properties(cls); hints = get_type_hints(cls)
        for attribute, declared in properties.items():
            arguments = get_args(hints.get(attribute, Any))
            object.__setattr__(declared, "type_hint", arguments[0] if arguments else Any)
        cls._kind, cls._properties, cls._metadata = kind, properties, dict(metadata)
        return cls
    return cast(ComponentDecorator, decorate)

def node(**metadata: Any) -> ComponentDecorator:
    return _component("node", **metadata)

def edge(*, source: type[GraphComponent], target: type[GraphComponent], **metadata: Any) -> ComponentDecorator:
    return _component("edge", source=source, target=target, **metadata)
