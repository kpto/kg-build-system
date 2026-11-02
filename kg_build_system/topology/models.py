"""Typed graph-component declarations.

A graph author writes declaration classes here. Class creation resolves the
declaration into frozen metadata once; lowering reads only that metadata. The
authoring class never becomes a component in the IR.
"""
from __future__ import annotations

import ast
import inspect
import re
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from typing import (
    Any, ClassVar, Generic, Literal, TypeVar, cast, dataclass_transform,
    get_args, get_origin, get_type_hints,
)

from ..annotations.interfaces import (
    Annotation, EdgeLabel, NodeLabel, annotation_tuple,
)
from ..expressions.interfaces import NullableAuthoringInput, ValueInput
from ..types.interfaces import (
    Array, CustomDataType, Date, LogicalType, Time, Timestamp, Uuid,
    normalize_type, require_graph_property,
)

type GraphScalar = bool | int | float | str | Date | Time | Timestamp | Uuid | CustomDataType
# A graph property may also be a flat, homogeneous list of non-null scalars.
type GraphArray = Array[GraphScalar]
type GraphValue = GraphScalar | GraphArray | None
type NonNullableGraphValue = GraphScalar
T = TypeVar("T", bound=GraphValue)


# The public slot describes accepted authoring values; declaration metadata is
# a separate object returned by ``property()``.
type PropertySlot[T: GraphValue] = ValueInput[T] | NullableAuthoringInput[T]


@dataclass(frozen=True, slots=True)
class _PropertyDeclaration(Generic[T]):
    """The descriptor an author assigns to a property slot."""

    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()
    attr: str = ""

    def __set_name__(self, owner: type[Any], attr: str) -> None:
        object.__setattr__(self, "attr", attr)
        if self.name is None:
            object.__setattr__(self, "name", member_name(attr))
        if self.description is None:
            object.__setattr__(
                self, "description", attribute_docstring(owner, attr),
            )


@dataclass(frozen=True, slots=True)
class PropertyDeclaration:
    """One property resolved against a declaring class."""

    attribute: str
    name: str
    logical_type: LogicalType
    authoring_type: Any = None
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()

    @property
    def attr(self) -> str:
        return self.attribute


@dataclass(frozen=True, slots=True)
class ComponentMetadata:
    """The declaration facts of one graph-visible component.

    The object is frozen and complete before lowering; no later consumer
    mutates the authoring class to recover metadata.
    """

    kind: Literal["node", "edge"]
    name: str
    properties: tuple[PropertyDeclaration, ...] = ()
    description: str | None = None
    source: type[Any] | None = None
    target: type[Any] | None = None
    annotations: tuple[Annotation, ...] = ()
    abstract: bool = False
    parent: type[Any] | None = None


def properties_for(cls: type[Any]) -> dict[str, PropertyDeclaration]:
    """Resolve inherited properties with normal Python shadowing semantics.

    The resolved map is built once while the class is created. Calling this for
    a class that did not pass through the topology root resolves it locally
    without mutating the class.
    """
    resolved = vars(cls).get("_properties")
    if isinstance(resolved, dict):
        return resolved
    return {
        declaration.attribute: declaration
        for declaration in _resolve_properties(cls)
    }


def property[T: GraphValue](  # pyright: ignore[reportInvalidTypeVarUse]
    *, name: str | None = None, description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> PropertySlot[T]:
    """Declare a graph property accepting an authoring value of type ``T``."""
    if name is not None and not name:
        raise ValueError("property names must be non-empty")
    declaration = _PropertyDeclaration[T](
        name=name,
        description=description,
        annotations=annotation_tuple(list(annotations)),
    )
    return cast(PropertySlot[T], declaration)


@dataclass(frozen=True, slots=True)
class NodeOptions:
    """Identity and annotations for a concrete or abstract node.

    Assign an instance to a declaration's ``options`` class variable. ``name``
    is the logical graph name, ``description`` overrides the class docstring and
    ``annotations`` carries portable metadata such as a node label.

    Example:
        ```python
        from kg_build_system import (
            Node, NodeLabel, NodeOptions, PropertySlot, property,
        )

        class SiteNode(Node):
            options = NodeOptions(
                name="site",
                description="A monitored site.",
                annotations=(NodeLabel("Site"),),
            )
            name: PropertySlot[str] = property()
        ```
    """

    name: str | None = None
    description: str | None = None
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True, slots=True)
class EdgeOptions:
    """Identity and annotations for a concrete or abstract edge.

    Assign an instance to a declaration's ``options`` class variable. ``name``
    is the logical graph name, ``description`` overrides the class docstring and
    ``annotations`` carries portable metadata such as an edge label.

    Example:
        ```python
        from kg_build_system import (
            Edge, EdgeLabel, EdgeOptions, Node,
        )

        class SiteNode(Node):
            ...

        class HasUnitEdge(Edge[SiteNode, SiteNode]):
            options = EdgeOptions(
                name="has_unit",
                annotations=(EdgeLabel("HAS_UNIT"),),
            )
        ```
    """

    name: str | None = None
    description: str | None = None
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True, slots=True)
class NodeOptionsTemplate:
    """Annotations-only options for a node-side template.

    A node template's ``options`` must be this type. It has no name or
    description because a template has no graph identity.

    Example:
        ```python
        from kg_build_system import (
            NodeLabel, NodeOptionsTemplate, NodeTemplate,
        )

        class ProvenancedNodeTemplate(NodeTemplate):
            options = NodeOptionsTemplate(
                annotations=(NodeLabel("Provenanced"),),
            )
        ```
    """

    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True, slots=True)
class EdgeOptionsTemplate:
    """Annotations-only options for an edge-side template.

    An edge template's ``options`` must be this type. It has no name or
    description because a template has no graph identity.

    Example:
        ```python
        from kg_build_system import (
            EdgeLabel, EdgeOptionsTemplate, EdgeTemplate,
        )

        class ProvenancedEdgeTemplate(EdgeTemplate):
            options = EdgeOptionsTemplate(
                annotations=(EdgeLabel("PROVENANCED"),),
            )
        ```
    """

    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass_transform(field_specifiers=(property,), kw_only_default=True)
class TopologyDeclarationBase:
    """Internal root of every topology declaration.

    Every MRO class between a declaration and ``object`` descends from this
    root. The root also gives the synthesized authoring value a minimal
    keyword constructor without decorating the user's class as a dataclass.
    """

    _framework_root: ClassVar[bool] = True
    _kind: ClassVar[str] = "component"
    _properties: ClassVar[dict[str, PropertyDeclaration]] = {}
    _metadata: ClassVar[dict[str, Any]] = {}
    _component_declaration_kind: ClassVar[str | None] = None
    _component_abstract: ClassVar[bool] = False
    _component_parent_class: ClassVar[type[Any] | None] = None
    _component_name: ClassVar[str] = "component"
    _component_annotations: ClassVar[tuple[Annotation, ...]] = ()
    _template_annotations: ClassVar[tuple[Annotation, ...]] = ()
    _declaration: ClassVar[ComponentMetadata | None] = None

    def __init__(self, **values: Any) -> None:
        for name, value in values.items():
            setattr(self, name, value)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _prepare_topology_declaration(cls)


# --- Naming ---------------------------------------------------------------

def snake_case(value: str) -> str:
    """Convert a Python identifier to the portable external-name convention."""
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"([A-Za-z])([0-9])", r"\1_\2", value)
    value = re.sub(r"([0-9])([A-Za-z])", r"\1_\2", value)
    return value.lower()


def member_name(attribute: str) -> str:
    """Infer an external member name, reserving one trailing underscore."""
    return snake_case(attribute[:-1] if attribute.endswith("_") else attribute)


def declaration_name(class_name: str, *, suffixes: tuple[str, ...] = ()) -> str:
    """Infer a declaration name, removing one matching semantic suffix."""
    stem = class_name
    for suffix in suffixes:
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    if not stem:
        raise ValueError(f"{class_name!r} has no name after removing its declaration suffix")
    return snake_case(stem)


# --- Attribute documentation ---------------------------------------------

def _assigned_name(statement: ast.stmt) -> str | None:
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return statement.target.id
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        target = statement.targets[0]
        if isinstance(target, ast.Name):
            return target.id
    return None


def _attribute_documents(body: list[ast.stmt]) -> dict[str, str]:
    documents: dict[str, str] = {}
    for statement, following in zip(body, body[1:]):
        name = _assigned_name(statement)
        if name is None or not isinstance(following, ast.Expr):
            continue
        value = following.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        text = inspect.cleandoc(value.value)
        if text:
            documents[name] = text
    return documents


def attribute_docstring(owner: type[Any], attribute: str) -> str | None:
    """The documentation written directly below ``owner.attribute``, if any."""
    try:
        source = textwrap.dedent(inspect.getsource(owner))
    except (OSError, TypeError, IndentationError):
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    declaration = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef)), None
    )
    if declaration is None:
        return None
    return _attribute_documents(declaration.body).get(attribute)


# --- Class preparation ----------------------------------------------------

def _is_framework_root(cls: type[Any]) -> bool:
    return vars(cls).get("_framework_root", False) is True


def _resolve_properties(cls: type[Any]) -> tuple[PropertyDeclaration, ...]:
    """Resolve property declarations over the MRO, once, in declaration order."""
    declarations: dict[str, tuple[type[Any], _PropertyDeclaration[Any]]] = {}
    for base in reversed(cls.__mro__):
        for attribute, value in vars(base).items():
            if isinstance(value, _PropertyDeclaration):
                declarations[attribute] = (base, value)
            elif attribute in declarations:
                del declarations[attribute]

    hints = get_type_hints(cls)
    external: dict[str, str] = {}
    resolved: list[PropertyDeclaration] = []
    for attribute, (owner, declaration) in declarations.items():
        arguments = get_args(hints.get(attribute, Any))
        if len(arguments) != 1:
            raise TypeError(f"{cls.__name__}.{attribute} must be annotated as PropertySlot[T]")
        authoring_type = arguments[0]
        logical_type = require_graph_property(
            normalize_type(authoring_type), context=f"{cls.__name__}.{attribute}"
        )
        name = declaration.name
        if name is None:
            name = member_name(attribute)
        description = declaration.description
        if description is None:
            description = attribute_docstring(owner, attribute)
        if name in external:
            raise TypeError(
                f"{cls.__name__} properties {external[name]!r} and {attribute!r} "
                f"share external name {name!r}"
            )
        external[name] = attribute
        resolved.append(PropertyDeclaration(
            attribute=attribute,
            name=name,
            logical_type=logical_type,
            authoring_type=authoring_type,
            description=description,
            annotations=tuple(declaration.annotations),
        ))
    return tuple(resolved)


def _record_template_annotations(cls: type[Any], kind: str, options: Any) -> None:
    """Record a template's own annotation contribution."""
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


def _require_label_uniqueness(
    cls: type[Any], kind: str, annotations: tuple[Annotation, ...],
) -> None:
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
    if not issubclass(category, NodeSideBase):
        return (
            f"{cls.__name__} endpoint category {category.__name__} is not "
            "node-side — endpoints must be node components"
        )
    if component_kind(category) != "node":
        return (
            f"{cls.__name__} endpoint category {category.__name__} is not a "
            "node declaration — endpoints must be node components"
        )
    return ""


def _resolve_edge_endpoints(
    cls: type[Any], parent: type[Any] | None,
) -> tuple[type[Any], type[Any]]:
    """Resolve an edge's declared endpoints, inheriting from its category.

    Only the class's own ``__orig_bases__`` reveal a re-declaration — the
    attribute is inherited through the MRO. A re-declared endpoint must equal
    or descend from every abstract edge ancestor's pair; a class that
    re-declares nothing inherits its parent's endpoints. An edge with neither
    has no endpoints and fails at class creation.
    """

    def concrete(args: tuple[object, ...]) -> bool:
        return args != () and all(isinstance(arg, type) for arg in args)

    own: Any = None
    inherited: list[Any] = []

    def walk(klass: type[Any], depth: int) -> None:
        nonlocal own
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
        metadata = _metadata_for(parent)
        assert metadata is not None
        assert metadata.source is not None and metadata.target is not None
        return metadata.source, metadata.target
    raise TypeError(
        f"{cls.__name__} must declare its edge endpoints, for example "
        "`Edge[SourceNode, TargetNode]`, or inherit them from an abstract edge"
    )


def _inferred_component_name(cls: type[Any], kind: str, tier: str) -> str:
    """Infer a logical name from the class name, stripping its tier suffix."""
    kind_suffix = "Node" if kind == "node" else "Edge"
    suffixes: tuple[str, ...]
    if tier == "abstract":
        suffixes = (f"Abstract{kind_suffix}", kind_suffix)
    else:
        suffixes = (kind_suffix,)
    return declaration_name(cls.__name__, suffixes=suffixes)


def _metadata_for(cls: type[Any]) -> ComponentMetadata | None:
    """The frozen declaration metadata owned by ``cls``, if any."""
    value = vars(cls).get("_declaration")
    return value if isinstance(value, ComponentMetadata) else None


def _prepare_topology_declaration(cls: type[Any]) -> None:
    """One pass at class creation: lineage, tier, options, properties, endpoints."""
    if _is_framework_root(cls):
        return

    for base in cls.__mro__[1:]:
        if base is object or base is Generic:
            continue
        if not issubclass(base, TopologyDeclarationBase):
            raise TypeError(
                f"{cls.__name__} inherits non-framework base {base.__name__!r}: "
                "every topology declaration must descend from Node, AbstractNode, "
                "NodeTemplate, Edge, AbstractEdge, or EdgeTemplate"
            )

    node_side = issubclass(cls, NodeSideBase)
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
    kind: Literal["node", "edge"] = "node" if node_lineage else "edge"

    # Property slots must validate even on inert templates.
    resolved_properties = _resolve_properties(cls)
    own_options = vars(cls).get("options")
    if not node_side and not edge_side:
        _record_template_annotations(cls, kind, own_options)
        cls._properties = {item.attribute: item for item in resolved_properties}
        return

    tier = "concrete" if issubclass(cls, Node if kind == "node" else Edge) else "abstract"
    own_options = _require_visible_options(cls, kind, own_options)

    # One direct category parent; concrete components stay terminal.
    parents = [
        base for base in cls.__bases__
        if component_kind(base) == kind and not _is_framework_root(base)
    ]
    for base in cls.__mro__[1:]:
        if component_kind(base) == kind and not _is_framework_root(base):
            if not is_abstract_component(base):
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

    description = (
        own_options.description
        if own_options is not None and own_options.description is not None
        else (vars(cls).get("__doc__") or None)
    )
    name = (
        (own_options.name if own_options is not None else None)
        or _inferred_component_name(cls, kind, tier)
    )

    source: type[Any] | None = None
    target: type[Any] | None = None
    if kind == "edge":
        source, target = _resolve_edge_endpoints(cls, parents[0] if parents else None)

    metadata = ComponentMetadata(
        kind=kind,
        name=name,
        properties=resolved_properties,
        description=description,
        source=source,
        target=target,
        annotations=effective_annotations,
        abstract=tier == "abstract",
        parent=parents[0] if parents else None,
    )

    # Compatibility aliases for consumers written against the declaration
    # surface. The package itself reads only ``_declaration``.
    cls._kind = kind
    cls._properties = {item.attribute: item for item in resolved_properties}
    cls._metadata = {
        key: value
        for key, value in (
            ("description", description),
            ("source", source),
            ("target", target),
        )
        if value is not None
    }
    cls._component_declaration_kind = kind
    cls._component_abstract = metadata.abstract
    cls._component_parent_class = metadata.parent
    cls._component_name = metadata.name
    cls._component_annotations = metadata.annotations
    cls._declaration = metadata


def component_kind(cls: type[Any]) -> str | None:
    """``"node"`` or ``"edge"`` when the class declares a component."""
    metadata = _metadata_for(cls)
    return metadata.kind if metadata is not None else None


def is_abstract_component(cls: type[Any]) -> bool:
    """Whether the class declares an abstract category."""
    metadata = _metadata_for(cls)
    return metadata.abstract if metadata is not None else False


def is_concrete_component(cls: type[Any]) -> bool:
    """Whether the class declares a concrete node or edge."""
    metadata = _metadata_for(cls)
    return metadata is not None and not metadata.abstract


class NodeSideBase(TopologyDeclarationBase):
    """Internal node-side root shared by ``AbstractNode`` and ``Node``.

    Every endpoint-category parameter is bound to this root, so an edge-kind
    type argument is statically impossible.
    """

    _framework_root: ClassVar[bool] = True


class NodeTemplate(TopologyDeclarationBase):
    """Inert node-side mixin sharing property slots and annotation flow.

    A node template contributes properties and annotations to its host but
    never becomes a graph component, receives a name, or becomes a binding
    target. Use ``NodeOptionsTemplate`` for its options.

    Example:
        ```python
        from kg_build_system import (
            Node, NodeTemplate, PropertySlot, property,
        )

        class ProvenancedNodeTemplate(NodeTemplate):
            source_version: PropertySlot[str] = property()

        class SiteNode(ProvenancedNodeTemplate, Node):
            name: PropertySlot[str] = property()
        ```
    """

    _framework_root: ClassVar[bool] = True
    options: ClassVar[Any] = NodeOptionsTemplate()
    _template_annotations: ClassVar[tuple[Annotation, ...]] = ()


class EdgeTemplate(TopologyDeclarationBase):
    """Inert edge-side mixin sharing property slots and annotation flow.

    An edge template contributes properties and annotations to its host but
    never becomes a graph component, receives a name, or becomes a binding
    target. Use ``EdgeOptionsTemplate`` for its options.

    Example:
        ```python
        from kg_build_system import (
            Edge, EdgeTemplate, Node, PropertySlot, property,
        )

        class SiteNode(Node):
            ...

        class ProvenancedEdgeTemplate(EdgeTemplate):
            source_version: PropertySlot[str] = property()

        class LinkedEdge(ProvenancedEdgeTemplate, Edge[SiteNode, SiteNode]):
            ...
        ```
    """

    _framework_root: ClassVar[bool] = True
    options: ClassVar[Any] = EdgeOptionsTemplate()
    _template_annotations: ClassVar[tuple[Annotation, ...]] = ()


# Endpoint categories are node-side. Constrained typevars were measured and
# rejected: they break binding inference and the base-consistency order guard.
N_co = TypeVar("N_co", bound=NodeSideBase, covariant=True)
S_co = TypeVar("S_co", bound=NodeSideBase, covariant=True)
D_co = TypeVar("D_co", bound=NodeSideBase, covariant=True)
S = TypeVar("S", bound=NodeSideBase)
D = TypeVar("D", bound=NodeSideBase)


class AbstractNode(NodeSideBase):
    """Category node: a graph-visible parent for concrete nodes.

    A category carries shared properties and can be an edge endpoint, but it is
    never a binding target and produces no records of its own. Declare a
    concrete child by mixing the category into a ``Node``.

    Example:
        ```python
        from kg_build_system import AbstractNode, Node, PropertySlot, property

        class AssetNode(AbstractNode):
            summary: PropertySlot[str] = property()

        class SiteNode(AssetNode, Node):
            name: PropertySlot[str] = property()
        ```
    """

    _framework_root: ClassVar[bool] = True
    options: ClassVar[Any] = NodeOptions()


class Node(NodeSideBase):
    """Concrete node base: bindable, terminal, and a sibling of AbstractNode.

    Declare a node by subclassing ``Node`` and assigning ``PropertySlot``
    attributes. A concrete node is the only kind a ``node_binding`` can target,
    and it cannot be subclassed.

    Example:
        ```python
        from kg_build_system import Node, PropertySlot, property

        class SiteNode(Node):
            name: PropertySlot[str] = property()
            region: PropertySlot[str | None] = property()
        ```
    """

    _framework_root: ClassVar[bool] = True
    options: ClassVar[Any] = NodeOptions()


class AbstractEdge(TopologyDeclarationBase, Generic[S_co, D_co]):
    """Category edge; endpoint parameters are covariant so children may descend.

    An abstract edge declares a relationship family. A concrete child may keep
    or narrow its endpoint pair, and the pair is part of the edge's meaning.

    Example:
        ```python
        from kg_build_system import AbstractEdge, Edge, Node

        class SiteNode(Node):
            ...

        class LinkedAbstractEdge(AbstractEdge[SiteNode, SiteNode]):
            ...

        class SiteLinkedEdge(LinkedAbstractEdge, Edge[SiteNode, SiteNode]):
            ...
        ```
    """

    _framework_root: ClassVar[bool] = True
    options: ClassVar[Any] = EdgeOptions()


class Edge(AbstractEdge[S, D], Generic[S, D]):
    """Concrete edge base; endpoint parameters stay invariant, as the
    binding matrix requires, while the covariant ``AbstractEdge`` parent
    makes endpoint descent through the terminal base checkable.

    Declare a directed relationship by subclassing ``Edge[Source, Target]``.
    Both parameters are node-side declarations; a concrete edge is terminal and
    is the only edge kind an ``edge_binding`` can target.

    Example:
        ```python
        from kg_build_system import Edge, Node, PropertySlot, property

        class SiteNode(Node):
            ...

        class UnitNode(Node):
            ...

        class HasUnitEdge(Edge[SiteNode, UnitNode]):
            since: PropertySlot[str | None] = property()
        ```
    """

    _framework_root: ClassVar[bool] = True


@dataclass(frozen=True, slots=True)
class Endpoint(Generic[N_co]):
    """A graph-identity reference to one concrete node component.

    Use :func:`endpoint` to create the value; constructing it directly skips
    the concrete-node check.

    Example:
        ```python
        from kg_build_system import Endpoint, Node, endpoint

        class SiteNode(Node):
            ...

        site = endpoint(SiteNode)
        assert isinstance(site, Endpoint)
        assert site.target is SiteNode
        ```
    """

    target: type[N_co]


def endpoint[N: Node](target: type[N]) -> Endpoint[N]:
    """Name a concrete node component as an edge-binding endpoint."""
    if not isinstance(target, type):
        raise TypeError(f"{target!r} is not a concrete node")
    if component_kind(target) != "node" or is_abstract_component(target):
        raise TypeError(f"'{target.__name__}' is not a concrete node")
    return Endpoint(target)


__all__ = [
    "AbstractEdge", "AbstractNode", "ComponentMetadata", "D", "D_co", "Edge",
    "EdgeOptions", "EdgeOptionsTemplate", "EdgeTemplate", "Endpoint",
    "GraphScalar", "GraphValue", "N_co", "Node", "NodeOptions",
    "NodeOptionsTemplate", "NodeSideBase", "NodeTemplate",
    "NonNullableGraphValue", "PropertyDeclaration", "PropertySlot",
    "S", "S_co", "TopologyDeclarationBase", "component_kind", "endpoint",
    "is_abstract_component", "is_concrete_component", "properties_for",
    "property",
]
