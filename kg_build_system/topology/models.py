"""Graph component property-slot models."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar, dataclass_transform, get_args, get_type_hints

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


def properties_for(cls: type) -> dict[str, "PropertySlot[Any]"]:
    """Resolve property slots for a final component or a reusable component shape."""
    properties: dict[str, PropertySlot[Any]] = {}
    for base in reversed(cls.__mro__):
        properties.update({name: value for name, value in vars(base).items() if isinstance(value, PropertySlot)})
    hints = get_type_hints(cls)
    for attribute, slot in properties.items():
        arguments = get_args(hints.get(attribute, Any))
        object.__setattr__(slot, "type_hint", arguments[0] if arguments else Any)
    return properties

def property[T](*, name: str | None = None, description: str | None = None, nullable: bool = True) -> PropertySlot[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    return PropertySlot(name=name, description=description, nullable=nullable)

@dataclass_transform(field_specifiers=(property,), kw_only_default=True)
class GraphComponent:
    _kind: ClassVar[str] = "component"
    _properties: ClassVar[dict[str, PropertySlot[Any]]] = {}
    _metadata: ClassVar[dict[str, Any]] = {}
    _component_declaration_kind: ClassVar[str | None] = None
