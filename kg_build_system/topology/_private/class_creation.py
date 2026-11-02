"""Class-creation mechanics: lineage, tier, options, properties and endpoints."""
from __future__ import annotations

from typing import Any, Generic, Literal, cast, get_args, get_origin

from ...annotations.internal import Annotation, EdgeLabel, NodeLabel
from ..internal.metadata import (
    ComponentMetadata, _metadata_for, component_kind, is_abstract_component,
)
from .properties import _resolve_properties, declaration_name


def _is_framework_root(cls: type[Any]) -> bool:
    return vars(cls).get("_framework_root", False) is True


def _record_template_annotations(cls: type[Any], kind: str, options: Any) -> None:
    """Record a template's own annotation contribution."""
    from ..public.options import (
        EdgeOptions, EdgeOptionsTemplate, NodeOptions, NodeOptionsTemplate,
    )

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
    from ..public.options import (
        EdgeOptions, EdgeOptionsTemplate, NodeOptions, NodeOptionsTemplate,
    )

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
    from ..public.declarations import NodeSideBase

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
    """Resolve an edge's declared endpoints, inheriting from its category."""
    from ..public.declarations import AbstractEdge, Edge

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


def _prepare_topology_declaration(cls: type[Any]) -> None:
    """One pass at class creation: lineage, tier, options, properties, endpoints."""
    if _is_framework_root(cls):
        return

    from ..public.declarations import (
        AbstractEdge, Edge, Node, NodeSideBase, NodeTemplate, EdgeTemplate,
        TopologyDeclarationBase,
    )

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


def make_endpoint(target: type[object]) -> object:
    """Validate a concrete node class and return its endpoint token."""
    from ..internal.metadata import component_kind, is_abstract_component
    from ..public.declarations import Endpoint

    if not isinstance(target, type):
        raise TypeError(f"{target!r} is not a concrete node")
    if component_kind(target) != "node" or is_abstract_component(target):
        raise TypeError(f"'{target.__name__}' is not a concrete node")
    return cast(Any, Endpoint(target))  # type: ignore[arg-type]


__all__ = ["_prepare_topology_declaration", "make_endpoint"]
