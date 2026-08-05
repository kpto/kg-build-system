"""Graph component declaration decorators."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar, cast, get_type_hints, overload
from .models import GraphComponent, PropertySlot, properties_for, property
from .._support.naming import declaration_name

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

def _component(kind: str, *, name: str | None = None, **metadata: Any) -> ComponentDecorator:
    def decorate(cls: type[C]) -> type[C]:
        if any(is_final_component(base) for base in cls.__mro__[1:]):
            raise TypeError("a final @node or @edge may not inherit from another final graph component")
        properties = properties_for(cls)
        annotations = dict(vars(cls).get("__annotations__", {}))
        hints = get_type_hints(cls)
        for attribute in properties:
            annotations.setdefault(attribute, hints.get(attribute, Any))
        cls.__annotations__ = annotations
        cls._kind, cls._properties, cls._metadata = kind, properties, _metadata(cls, metadata)
        cls._component_name = name or declaration_name(cls.__name__, suffixes=(("Node",) if kind == "node" else ("Edge",)))
        cls._component_declaration_kind = kind
        return cast(type[C], dataclass(cls, kw_only=True))
    return cast(ComponentDecorator, decorate)


@overload
def component_template(cls: type[C]) -> type[C]: ...
@overload
def component_template(*, name: str | None = None, **metadata: Any) -> ComponentDecorator: ...
def component_template(cls: type[C] | None = None, *, name: str | None = None, **metadata: Any) -> type[C] | ComponentDecorator:
    def decorate(cls: type[C]) -> type[C]:
        cls._kind, cls._properties, cls._metadata = "component", properties_for(cls), _metadata(cls, metadata)
        cls._component_name = name or declaration_name(cls.__name__, suffixes=("ComponentTemplate", "Template"))
        cls._component_declaration_kind = "template"
        return cls
    return decorate if cls is None else decorate(cls)

@overload
def node(cls: type[C]) -> type[C]: ...
@overload
def node(*, name: str | None = None, **metadata: Any) -> ComponentDecorator: ...
def node(cls: type[C] | None = None, *, name: str | None = None, **metadata: Any) -> type[C] | ComponentDecorator:
    decorate = _component("node", name=name, **metadata)
    return decorate if cls is None else decorate(cls)

def edge(*, source: type[GraphComponent], target: type[GraphComponent], name: str | None = None, **metadata: Any) -> ComponentDecorator: return _component("edge", name=name, source=source, target=target, **metadata)
