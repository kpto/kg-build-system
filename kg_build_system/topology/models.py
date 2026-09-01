"""Typed graph-component declarations and property metadata."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar, cast, dataclass_transform, get_args, get_origin, get_type_hints

from .._support.naming import declaration_name, member_name
from ..annotations import Annotation, EdgeLabel, NodeLabel, annotation_tuple
from ..expressions import NullableAuthoringInput, ValueInput
from ..types import CustomDataType, LogicalType, normalize_type, require_scalar

type GraphValue = bool | int | float | str | CustomDataType | None
type NonNullableGraphValue = bool | int | float | str | CustomDataType
T = TypeVar("T", bound=GraphValue)

# The public slot type describes accepted values. Declaration metadata remains
# separate so expressions do not inherit from graph-schema objects.
type PropertySlot[T: GraphValue] = ValueInput[T] | NullableAuthoringInput[T]


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
class NodeOptionsTemplate:
    """Annotations-only options for a node-side template tier."""

    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True)
class EdgeOptionsTemplate:
    """Annotations-only options for an edge-side template tier."""

    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass_transform(field_specifiers=(property,), kw_only_default=True)
class _TopologyDeclarationBase:
    """Internal root of every topology declaration.

    The ``dataclass_transform`` scope follows the chain root, so every MRO
    class between a declaration and ``object`` must descend from this base.
    """

    _framework_root: ClassVar[bool] = True
    _kind: ClassVar[str] = "component"
    _properties: ClassVar[dict[str, _PropertyDeclaration[Any]]] = {}
    _metadata: ClassVar[dict[str, Any]] = {}
    _component_declaration_kind: ClassVar[str | None] = None
    _component_abstract: ClassVar[bool] = False
    _component_parent_class: ClassVar[type[Any] | None] = None
    _component_name: ClassVar[str] = "component"
    _component_annotations: ClassVar[tuple[Annotation, ...]] = ()
    _template_annotations: ClassVar[tuple[Annotation, ...]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _prepare_topology_declaration(cls)


def _is_framework_root(cls: type[Any]) -> bool:
    return vars(cls).get("_framework_root", False) is True


def _record_template_annotations(cls: type[Any], kind: str, options: Any) -> None:
    """Record the template class's own annotation contribution."""
    template_options = NodeOptionsTemplate if kind == "node" else EdgeOptionsTemplate
    opposite = EdgeOptionsTemplate if kind == "node" else NodeOptionsTemplate
    if options is None:
        cls._template_annotations = ()
        return
    if isinstance(options, template_options):
        cls._template_annotations = tuple(options.annotations)
        return
    if isinstance(options, opposite):
        raise TypeError(
            f"{cls.__name__} is a {kind} template: its options must be "
            f"{template_options.__name__}, not {opposite.__name__} — use "
            f"`options = {template_options.__name__}(annotations=(...))`"
        )
    if isinstance(options, (NodeOptions, EdgeOptions)):
        raise TypeError(
            f"{cls.__name__} is a {kind} template: its options must be "
            f"{template_options.__name__}, which carries no identity fields — wrap it: "
            f"`options = {template_options.__name__}(annotations=(...))`"
        )
    raise TypeError(
        f"{cls.__name__} is a {kind} template: wrap the value: "
        f"`options = {template_options.__name__}(annotations=(...))`"
    )


def _require_visible_options(cls: type[Any], kind: str, options: Any) -> Any:
    """IR-visible declarations own real, kind-matched options."""
    if options is None:
        return None
    own_options = NodeOptions if kind == "node" else EdgeOptions
    if isinstance(options, (NodeOptionsTemplate, EdgeOptionsTemplate)):
        raise TypeError(
            f"{cls.__name__} is a graph component declaration: declare "
            f"{own_options.__name__}, not template options"
        )
    if not isinstance(options, own_options):
        raise TypeError(
            f"{cls.__name__} is a {kind} component declaration: its options "
            f"must be a {own_options.__name__} value"
        )
    return options


def _require_label_uniqueness(cls: type[Any], kind: str, annotations: tuple[Annotation, ...]) -> None:
    """At most one label of the matching kind across the effective set."""
    label = NodeLabel if kind == "node" else EdgeLabel
    matches = tuple(
        item for item in annotations
        if item.namespace == label.namespace and item.annotation_id == label.annotation_id
    )
    if len(matches) > 1:
        raise TypeError(
            f"{cls.__name__} has {len(matches)} {kind} labels in its effective "
            "annotations; a graph component carries at most one"
        )


def _endpoint_category_error(cls: type[Any], category: Any) -> str:
    if not isinstance(category, type):
        return (
            f"{cls.__name__} endpoint category {category!r} is not a node "
            "declaration — endpoints must be node components"
        )
    if not issubclass(category, _NodeSideBase):
        return (
            f"{cls.__name__} endpoint category {category.__name__} is not "
            "node-side — endpoints must be node components"
        )
    if vars(category).get("_component_declaration_kind") != "node":
        return (
            f"{cls.__name__} endpoint category {category.__name__} is not a "
            "node declaration — endpoints must be node components"
        )
    return ""


def _resolve_edge_endpoints(
    cls: type[Any], parent: type[Any] | None,
) -> tuple[type[Any], type[Any]]:
    """R4: endpoints follow the abstract edge parent; re-declaration may narrow.

    Only the class's own ``__orig_bases__`` reveal a re-declaration — the
    attribute is inherited through the MRO. A re-declared endpoint must equal
    or descend from every abstract edge ancestor's; a class that re-declares
    nothing inherits its parent's endpoints. An edge with neither has no
    endpoints and fails at class creation.
    """

    def concrete(args: tuple[object, ...]) -> bool:
        return args != () and all(isinstance(arg, type) for arg in args)

    own: Any = None
    inherited: list[Any] = []

    def walk(klass: type[Any], depth: int) -> None:
        nonlocal own
        # Only the class's own dict may reveal its declarations —
        # __orig_bases__ is inherited through the MRO. A class with no
        # generic alias among its bases records none, so traversal falls
        # back to that class's real __bases__.
        for base in klass.__dict__.get("__orig_bases__", ()) or klass.__bases__:
            origin = get_origin(base)
            if origin in (AbstractEdge, Edge):
                arguments = get_args(base)
                if concrete(arguments):
                    if depth == 0 and own is None:
                        own = arguments
                    else:
                        inherited.append(arguments)
            elif isinstance(base, type):
                walk(base, depth + 1)

    walk(cls, 0)
    for category in (own or ()) + tuple(item for spec in inherited for item in spec):
        error = _endpoint_category_error(cls, category)
        if error:
            raise TypeError(error)
    if own is not None:
        for spec in inherited:
            if not (issubclass(own[0], spec[0]) and issubclass(own[1], spec[1])):
                raise TypeError(
                    f"{cls.__name__} endpoints ({own[0].__name__}, {own[1].__name__}) "
                    "must equal or descend from its abstract edge lineage "
                    f"({spec[0].__name__}, {spec[1].__name__})"
                )
        return cast(tuple[type[Any], type[Any]], own)
    if parent is not None:
        return parent._metadata["source"], parent._metadata["target"]
    raise TypeError(
        f"{cls.__name__} must declare its edge endpoints, for example "
        "`Edge[SourceNode, TargetNode]`, or inherit them from an abstract edge"
    )


def _prepare_topology_declaration(cls: type[Any]) -> None:
    """One pass at class creation: lineage, tiers, options, endpoints."""
    if _is_framework_root(cls):
        return

    for base in cls.__mro__[1:]:
        if base is object or base is Generic:
            continue
        if not issubclass(base, _TopologyDeclarationBase):
            raise TypeError(
                f"{cls.__name__} inherits non-framework base {base.__name__!r}: "
                "every topology declaration must descend from Node, AbstractNode, "
                "NodeTemplate, Edge, AbstractEdge, or EdgeTemplate"
            )

    node_side = issubclass(cls, _NodeSideBase)
    edge_side = issubclass(cls, AbstractEdge)
    node_template = issubclass(cls, NodeTemplate)
    edge_template = issubclass(cls, EdgeTemplate)
    node_lineage = node_side or node_template
    edge_lineage = edge_side or edge_template
    if node_lineage and edge_lineage:
        raise TypeError(
            f"{cls.__name__} cannot mix node-side and edge-side lineage: a "
            "declaration follows one side and may only mix matching-kind templates"
        )
    if not (node_lineage or edge_lineage):
        raise TypeError(
            f"{cls.__name__} must inherit from Node, AbstractNode, NodeTemplate, "
            "Edge, AbstractEdge, or EdgeTemplate"
        )
    kind = "node" if node_lineage else "edge"

    # Property slots must validate even on inert templates.
    properties_for(cls)

    own_options = vars(cls).get("options")
    if not node_side and not edge_side:
        _record_template_annotations(cls, kind, own_options)
        return

    tier = "concrete" if issubclass(cls, Node if kind == "node" else Edge) else "abstract"
    own_options = _require_visible_options(cls, kind, own_options)

    # R1: one direct category parent; concrete components stay terminal.
    parents = [
        base for base in cls.__bases__
        if vars(base).get("_component_declaration_kind") == kind
        and not _is_framework_root(base)
    ]
    for base in cls.__mro__[1:]:
        if (
            vars(base).get("_component_declaration_kind") == kind
            and not _is_framework_root(base)
            and not vars(base).get("_component_abstract", False)
        ):
            raise TypeError(
                f"{cls.__name__} cannot inherit from concrete graph component "
                f"{base.__name__}"
            )
    if len(parents) > 1:
        names = ", ".join(base.__name__ for base in parents)
        raise TypeError(
            f"{cls.__name__} has more than one abstract category parent: {names}"
        )

    template_annotations = tuple(
        annotation
        for base in reversed(cls.__mro__[1:])
        for annotation in vars(base).get("_template_annotations", ())
    )
    own_annotations = () if own_options is None else tuple(own_options.annotations)
    effective_annotations = template_annotations + own_annotations
    _require_label_uniqueness(cls, kind, effective_annotations)

    description = own_options.description if own_options is not None and own_options.description is not None else (vars(cls).get("__doc__") or None)
    name = (own_options.name if own_options is not None else None) or declaration_name(
        cls.__name__, suffixes=("Node",) if kind == "node" else ("Edge",)
    )

    metadata: dict[str, Any] = {"description": description} if description is not None else {}
    if kind == "edge":
        source, target = _resolve_edge_endpoints(cls, parents[0] if parents else None)
        metadata["source"] = source
        metadata["target"] = target

    cls._kind = kind
    cls._properties = properties_for(cls)
    annotations_map = dict(vars(cls).get("__annotations__", {}))
    hints = get_type_hints(cls)
    for attribute in cls._properties:
        annotations_map.setdefault(attribute, hints[attribute])
    cls.__annotations__ = annotations_map
    cls._metadata = metadata
    cls._component_declaration_kind = kind
    cls._component_abstract = tier == "abstract"
    cls._component_parent_class = parents[0] if parents else None
    cls._component_annotations = effective_annotations
    cls._component_name = name

    if tier == "concrete":
        dataclass(cls, kw_only=True)


class _NodeSideBase(_TopologyDeclarationBase):
    """Internal node-side root shared by ``AbstractNode`` and ``Node``.

    Every endpoint-category parameter is bound to this root, so an edge-kind
    type argument is statically impossible.
    """

    _framework_root: ClassVar[bool] = True


class NodeTemplate(_TopologyDeclarationBase):
    """Inert node-side mixin sharing property slots and annotation flow."""

    _framework_root: ClassVar[bool] = True
    options: ClassVar[Any] = NodeOptionsTemplate()
    _template_annotations: ClassVar[tuple[Annotation, ...]] = ()


class EdgeTemplate(_TopologyDeclarationBase):
    """Inert edge-side mixin sharing property slots and annotation flow."""

    _framework_root: ClassVar[bool] = True
    options: ClassVar[Any] = EdgeOptionsTemplate()
    _template_annotations: ClassVar[tuple[Annotation, ...]] = ()


# Endpoint categories are node-side. Constrained typevars were measured and
# rejected: they break binding inference and the base-consistency order guard.
N_co = TypeVar("N_co", bound=_NodeSideBase, covariant=True)
S_co = TypeVar("S_co", bound=_NodeSideBase, covariant=True)
D_co = TypeVar("D_co", bound=_NodeSideBase, covariant=True)
S = TypeVar("S", bound=_NodeSideBase)
D = TypeVar("D", bound=_NodeSideBase)


class AbstractNode(_NodeSideBase):
    """Category node: a graph-visible parent for concrete nodes."""

    _framework_root: ClassVar[bool] = True
    options: ClassVar[Any] = NodeOptions()


class Node(_NodeSideBase):
    """Concrete node base: bindable, terminal, and a sibling of AbstractNode."""

    _framework_root: ClassVar[bool] = True
    options: ClassVar[Any] = NodeOptions()


class AbstractEdge(_TopologyDeclarationBase, Generic[S_co, D_co]):
    """Category edge; endpoint parameters are covariant so children may descend."""

    _framework_root: ClassVar[bool] = True
    options: ClassVar[Any] = EdgeOptions()


class Edge(AbstractEdge[S, D], Generic[S, D]):
    """Concrete edge base; endpoint parameters stay invariant, as the
    binding matrix requires, while the covariant ``AbstractEdge`` parent
    makes endpoint descent through the terminal base checkable."""

    _framework_root: ClassVar[bool] = True


@dataclass(frozen=True)
class Endpoint(Generic[N_co]):
    """A graph-identity reference to one concrete node component."""

    target: type[N_co]


def endpoint[N: Node](target: type[N]) -> Endpoint[N]:
    """Name a concrete node component as an edge-binding endpoint."""
    if not isinstance(target, type):
        raise TypeError(f"{target!r} is not a concrete node")
    if (
        vars(target).get("_component_declaration_kind") != "node"
        or vars(target).get("_component_abstract", False)
    ):
        raise TypeError(f"'{target.__name__}' is not a concrete node")
    return Endpoint(target)


__all__ = [
    "AbstractEdge", "AbstractNode", "D", "D_co", "Edge", "EdgeOptions",
    "EdgeOptionsTemplate", "EdgeTemplate", "Endpoint", "GraphValue",
    "N_co", "Node", "NodeOptions", "NodeOptionsTemplate", "NodeTemplate",
    "NonNullableGraphValue", "PropertySlot", "S", "S_co", "endpoint",
    "properties_for", "property",
]
