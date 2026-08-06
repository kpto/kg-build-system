"""Graph component property-slot models."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar, dataclass_transform, get_args, get_type_hints
from ..annotations import Annotation, annotation_tuple
from .._support.naming import declaration_name, member_name

T = TypeVar("T")
S = TypeVar("S", bound="Node")
D = TypeVar("D", bound="Node")

@dataclass(frozen=True)
class PropertySlot(Generic[T]):
    name: str | None = None
    description: str | None = None
    type_hint: Any = None
    attr: str = ""
    annotations: tuple[Annotation, ...] = ()
    def __set_name__(self, owner: type, attr: str) -> None:
        object.__setattr__(self, "attr", attr)
        if self.name is None: object.__setattr__(self, "name", member_name(attr))


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

def property[T](*, name: str | None = None, description: str | None = None, annotations: tuple[Annotation, ...] | list[Annotation] = ()) -> PropertySlot[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    return PropertySlot(name=name, description=description, annotations=annotation_tuple(annotations))

@dataclass_transform(field_specifiers=(property,), kw_only_default=True)
class GraphComponent:
    _kind: ClassVar[str] = "component"
    _properties: ClassVar[dict[str, PropertySlot[Any]]] = {}
    _metadata: ClassVar[dict[str, Any]] = {}
    _component_declaration_kind: ClassVar[str | None] = None
    _component_name: ClassVar[str] = "component"


@dataclass(frozen=True)
class NodeOptions:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None: object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True)
class EdgeOptions:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None: object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True)
class GraphComponentOptions:
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None: object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


def _prepare_component(cls: type[GraphComponent], kind: str, options: NodeOptions | EdgeOptions) -> None:
    if any(vars(base).get("_component_declaration_kind") in {"node", "edge"} for base in cls.__mro__[1:]):
        raise TypeError("a final Node or Edge may not inherit from another final graph component")
    component_annotations = (
        tuple(annotation for base in reversed(cls.__mro__[1:] ) for annotation in vars(base).get("_component_annotations", ()))
        + tuple(annotation for base in reversed(cls.__mro__[1:]) for annotation in getattr(vars(base).get("options", None), "annotations", ()) if isinstance(vars(base).get("options", None), GraphComponentOptions))
        + tuple(options.annotations)
    )
    description = options.description if options.description is not None else (vars(cls).get("__doc__") or None)
    cls._kind = kind
    cls._properties = properties_for(cls)
    # Plain Python mixins deliberately need no framework base class.  Copy
    # their property annotations onto the final class before dataclass creates
    # its keyword-only constructor.
    annotations = dict(vars(cls).get("__annotations__", {}))
    hints = get_type_hints(cls)
    for attribute in cls._properties:
        annotations.setdefault(attribute, hints.get(attribute, Any))
    cls.__annotations__ = annotations
    cls._metadata = {"description": description} if description is not None else {}
    cls._component_annotations = component_annotations
    cls._component_name = options.name or declaration_name(cls.__name__, suffixes=("Node",) if kind == "node" else ("Edge",))
    cls._component_declaration_kind = kind
    dataclass(cls, kw_only=True)


class Node(GraphComponent):
    """Final graph-node declaration."""
    options: ClassVar[NodeOptions] = NodeOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options", NodeOptions())
        if not isinstance(options, NodeOptions):
            raise TypeError("Node.options must be a NodeOptions value")
        _prepare_component(cls, "node", options)


class Edge(GraphComponent, Generic[S, D]):
    """Final directed graph-edge declaration, parameterised by its endpoints."""
    options: ClassVar[EdgeOptions] = EdgeOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options", EdgeOptions())
        if not isinstance(options, EdgeOptions):
            raise TypeError("Edge.options must be an EdgeOptions value")
        endpoints = next((base for base in getattr(cls, "__orig_bases__", ()) if getattr(base, "__origin__", None) is Edge), None)
        endpoint_types = get_args(endpoints)
        if len(endpoint_types) != 2 or not all(isinstance(item, type) and vars(item).get("_component_declaration_kind") == "node" for item in endpoint_types):
            raise TypeError("Edge must declare final Node endpoints as Edge[SourceNode, TargetNode]")
        _prepare_component(cls, "edge", options)
        cls._metadata = cls._metadata | {"source": endpoint_types[0], "target": endpoint_types[1]}
