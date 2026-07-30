"""Graph component declaration decorators."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar, cast, dataclass_transform, get_args, get_type_hints
from .models import GraphComponent, PropertySlot, property

T = TypeVar("T")
C = TypeVar("C", bound=GraphComponent)

class ComponentDecorator(Protocol):
    def __call__(self, cls: type[C]) -> type[C]: ...

def _properties(cls: type) -> dict[str, PropertySlot[Any]]:
    found: dict[str, PropertySlot[Any]] = {}
    for base in reversed(cls.__mro__): found.update({name: value for name, value in vars(base).items() if isinstance(value, PropertySlot)})
    return found

def _component(kind: str, **metadata: Any) -> ComponentDecorator:
    def decorate(cls: type[C]) -> type[C]:
        properties = _properties(cls); hints = get_type_hints(cls)
        for attribute, slot in properties.items():
            arguments = get_args(hints.get(attribute, Any)); object.__setattr__(slot, "type_hint", arguments[0] if arguments else Any)
        cls._kind, cls._properties, cls._metadata = kind, properties, dict(metadata)
        return cast(type[C], dataclass(cls, kw_only=True))
    return cast(ComponentDecorator, decorate)

def node(**metadata: Any) -> ComponentDecorator: return _component("node", **metadata)
def edge(*, source: type[GraphComponent], target: type[GraphComponent], **metadata: Any) -> ComponentDecorator: return _component("edge", source=source, target=target, **metadata)
