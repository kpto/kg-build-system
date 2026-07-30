"""Graph component property-slot models."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar, dataclass_transform

T = TypeVar("T")

@dataclass(frozen=True)
class PropertySlot(Generic[T]):
    name: str | None = None
    description: str | None = None
    nullable: bool = True
    type_hint: Any = None
    attr: str = ""
    def __set_name__(self, owner: type, attr: str) -> None:
        object.__setattr__(self, "attr", attr)
        if self.name is None: object.__setattr__(self, "name", attr)

def property[T](*, name: str | None = None, description: str | None = None, nullable: bool = True) -> PropertySlot[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    return PropertySlot(name=name, description=description, nullable=nullable)

@dataclass_transform(field_specifiers=(property,), kw_only_default=True)
class GraphComponent:
    _kind: ClassVar[str] = "component"
    _properties: ClassVar[dict[str, PropertySlot[Any]]] = {}
    _metadata: ClassVar[dict[str, Any]] = {}
