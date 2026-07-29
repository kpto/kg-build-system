"""Topology declaration data models."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar

from ..expressions import FieldPath
from ..specification import Declaration, Specification

T = TypeVar("T")

@dataclass(frozen=True)
class Property(Declaration[T], Generic[T]):
    name: str | None = None
    nullable: bool = True
    description: str | None = None
    type_hint: Any = None
    attr: str = ""

    def __set_name__(self, owner: type, attr: str) -> None:
        object.__setattr__(self, "attr", attr)

    def __get__(self, instance: Any, owner: type) -> FieldPath[T] | T | None:
        if instance is None:
            return FieldPath[T](owner, (self.name or self.attr,), self.type_hint)
        return instance._values.get(self.attr)

class GraphComponent(Specification):
    _kind: str = "component"
    _properties: ClassVar[dict[str, Property[Any]]] = {}
    _metadata: ClassVar[dict[str, Any]] = {}

    def __init__(self, **values: Declaration[Any]) -> None:
        unknown = set(values) - set(self.__class__._properties)
        if unknown: raise TypeError(f"Unknown properties for {type(self).__name__}: {sorted(unknown)}")
        self._values = values
