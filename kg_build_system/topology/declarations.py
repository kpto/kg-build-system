"""Graph component declaration decorators."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar, cast, get_type_hints
from .models import GraphComponent, PropertySlot, properties_for, property

T = TypeVar("T")
C = TypeVar("C", bound=GraphComponent)

class ComponentDecorator(Protocol):
    def __call__(self, cls: type[C]) -> type[C]: ...

def _declaration_kind(cls: type) -> str | None:
    return vars(cls).get("_component_declaration_kind")


def is_final_component(cls: type) -> bool:
    return _declaration_kind(cls) in {"node", "edge"}


def _metadata(cls: type, metadata: dict[str, Any]) -> dict[str, Any]:
    inherited: dict[str, Any] = {}
    for base in reversed(cls.__mro__[1:]):
        inherited.update(vars(base).get("_metadata", {}))
    inherited.update(metadata)
    return inherited

def _component(kind: str, **metadata: Any) -> ComponentDecorator:
    def decorate(cls: type[C]) -> type[C]:
        if any(is_final_component(base) for base in cls.__mro__[1:]):
            raise TypeError("a final @node or @edge may not inherit from another final graph component")
        properties = properties_for(cls)
        annotations = dict(vars(cls).get("__annotations__", {}))
        hints = get_type_hints(cls)
        for name in properties:
            annotations.setdefault(name, hints.get(name, Any))
        cls.__annotations__ = annotations
        cls._kind, cls._properties, cls._metadata = kind, properties, _metadata(cls, metadata)
        cls._component_declaration_kind = kind
        return cast(type[C], dataclass(cls, kw_only=True))
    return cast(ComponentDecorator, decorate)


def component_template(**metadata: Any) -> ComponentDecorator:
    def decorate(cls: type[C]) -> type[C]:
        cls._kind, cls._properties, cls._metadata = "component", properties_for(cls), _metadata(cls, metadata)
        cls._component_declaration_kind = "template"
        return cls
    return cast(ComponentDecorator, decorate)

def node(**metadata: Any) -> ComponentDecorator: return _component("node", **metadata)
def edge(*, source: type[GraphComponent], target: type[GraphComponent], **metadata: Any) -> ComponentDecorator: return _component("edge", source=source, target=target, **metadata)
