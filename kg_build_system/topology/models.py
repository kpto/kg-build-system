"""Typed graph-component declarations and property metadata."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar, cast, dataclass_transform, get_args, get_type_hints

from .._support.naming import declaration_name, member_name
from ..annotations import Annotation, annotation_tuple
from ..expressions import AuthoringValueExpression
from ..types import CustomDataType, LogicalType, normalize_type, require_scalar

type GraphValue = bool | int | float | str | CustomDataType | None
type NonNullableGraphValue = bool | int | float | str | CustomDataType
T = TypeVar("T", bound=GraphValue)
S = TypeVar("S", bound="Node")
D = TypeVar("D", bound="Node")

# The public slot type describes accepted values. Declaration metadata remains
# separate so expressions do not inherit from graph-schema objects.
type PropertySlot[T: GraphValue] = AuthoringValueExpression[T]


@dataclass(frozen=True, slots=True)
class _PropertyDeclaration(Generic[T]):
    name: str | None = None
    description: str | None = None
    authoring_type: Any = None
    logical_type: LogicalType | None = None
    attr: str = ""
    annotations: tuple[Annotation, ...] = ()

    def __set_name__(self, owner: type[Any], attr: str) -> None:
        object.__setattr__(self, "attr", attr)
        if self.name is None:
            object.__setattr__(self, "name", member_name(attr))


def properties_for(cls: type[Any]) -> dict[str, _PropertyDeclaration[Any]]:
    """Resolve inherited properties with normal Python shadowing semantics."""
    properties: dict[str, _PropertyDeclaration[Any]] = {}
    for base in reversed(cls.__mro__):
        for attribute, value in vars(base).items():
            if isinstance(value, _PropertyDeclaration):
                properties[attribute] = value
            elif attribute in properties:
                del properties[attribute]

    hints = get_type_hints(cls)
    external: dict[str, str] = {}
    for attribute, declaration in properties.items():
        arguments = get_args(hints.get(attribute, Any))
        if len(arguments) != 1:
            raise TypeError(f"{cls.__name__}.{attribute} must be annotated as PropertySlot[T]")
        authoring_type = arguments[0]
        logical_type = require_scalar(
            normalize_type(authoring_type), context=f"{cls.__name__}.{attribute}"
        )
        object.__setattr__(declaration, "authoring_type", authoring_type)
        object.__setattr__(declaration, "logical_type", logical_type)
        name = declaration.name
        assert name is not None
        if name in external:
            raise TypeError(
                f"{cls.__name__} properties {external[name]!r} and {attribute!r} "
                f"share external name {name!r}"
            )
        external[name] = attribute
    return properties


def property[T: GraphValue](  # pyright: ignore[reportInvalidTypeVarUse]
    *, name: str | None = None, description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> PropertySlot[T]:
    """Declare a graph property accepting an expression of authoring type ``T``."""
    if name is not None and not name:
        raise ValueError("property names must be non-empty")
    declaration = _PropertyDeclaration[T](
        name=name, description=description,
        annotations=annotation_tuple(list(annotations)),
    )
    return cast(PropertySlot[T], declaration)


@dataclass_transform(field_specifiers=(property,), kw_only_default=True)
class GraphComponent:
    _kind: ClassVar[str] = "component"
    _properties: ClassVar[dict[str, _PropertyDeclaration[Any]]] = {}
    _metadata: ClassVar[dict[str, Any]] = {}
    _component_declaration_kind: ClassVar[str | None] = None
    _component_name: ClassVar[str] = "component"
    _component_annotations: ClassVar[tuple[Annotation, ...]] = ()


@dataclass(frozen=True)
class NodeOptions:
    name: str | None = None
    description: str | None = None
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True)
class EdgeOptions:
    name: str | None = None
    description: str | None = None
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True)
class GraphComponentOptions:
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


def _prepare_component(
    cls: type[GraphComponent], kind: str, options: NodeOptions | EdgeOptions
) -> None:
    if any(vars(base).get("_component_declaration_kind") in {"node", "edge"} for base in cls.__mro__[1:]):
        raise TypeError("a final Node or Edge may not inherit from another final graph component")
    component_annotations = (
        tuple(a for base in reversed(cls.__mro__[1:]) for a in vars(base).get("_component_annotations", ()))
        + tuple(
            a for base in reversed(cls.__mro__[1:])
            for a in getattr(vars(base).get("options", None), "annotations", ())
            if isinstance(vars(base).get("options", None), GraphComponentOptions)
        )
        + tuple(options.annotations)
    )
    description = options.description if options.description is not None else (vars(cls).get("__doc__") or None)
    cls._kind = kind
    cls._properties = properties_for(cls)
    annotations = dict(vars(cls).get("__annotations__", {}))
    hints = get_type_hints(cls)
    for attribute in cls._properties:
        annotations.setdefault(attribute, hints[attribute])
    cls.__annotations__ = annotations
    cls._metadata = {"description": description} if description is not None else {}
    cls._component_annotations = component_annotations
    cls._component_name = options.name or declaration_name(
        cls.__name__, suffixes=("Node",) if kind == "node" else ("Edge",)
    )
    cls._component_declaration_kind = kind
    dataclass(cls, kw_only=True)


class Node(GraphComponent):
    options: ClassVar[NodeOptions] = NodeOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options", NodeOptions())
        if not isinstance(options, NodeOptions):
            raise TypeError("Node.options must be a NodeOptions value")
        _prepare_component(cls, "node", options)


class Edge(GraphComponent, Generic[S, D]):
    options: ClassVar[EdgeOptions] = EdgeOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options", EdgeOptions())
        if not isinstance(options, EdgeOptions):
            raise TypeError("Edge.options must be an EdgeOptions value")
        endpoints = next((base for base in getattr(cls, "__orig_bases__", ()) if getattr(base, "__origin__", None) is Edge), None)
        endpoint_types = get_args(endpoints)
        if len(endpoint_types) != 2 or not all(
            isinstance(item, type) and vars(item).get("_component_declaration_kind") == "node"
            for item in endpoint_types
        ):
            raise TypeError("Edge must declare final Node endpoints as Edge[SourceNode, TargetNode]")
        _prepare_component(cls, "edge", options)
        cls._metadata = cls._metadata | {"source": endpoint_types[0], "target": endpoint_types[1]}


__all__ = [
    "Edge", "EdgeOptions", "GraphComponent", "GraphComponentOptions", "GraphValue",
    "Node", "NodeOptions", "NonNullableGraphValue", "PropertySlot", "properties_for", "property",
]
