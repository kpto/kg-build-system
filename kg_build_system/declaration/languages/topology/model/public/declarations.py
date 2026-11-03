"""Typed node and edge declarations a graph author writes.

Declare a node by subclassing ``Node`` and an edge by subclassing
``Edge[Source, Target]``. Abstract categories are shared parents, templates add
properties and annotations without becoming graph components, and
``property()`` and ``endpoint()`` declare the two authoring references.

Example:
    ```python
    from kg_build_system import (
        AbstractNode, Edge, Node, PropertySlot, property,
    )

    class AssetNode(AbstractNode):
        summary: PropertySlot[str] = property()

    class SiteNode(AssetNode, Node):
        name: PropertySlot[str] = property()

    class UnitNode(Node):
        name: PropertySlot[str] = property()

    class HasUnitEdge(Edge[SiteNode, UnitNode]):
        since: PropertySlot[str | None] = property()
    ```
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar, dataclass_transform, cast

from kg_build_system.declaration.foundations.annotations.model.public import (
    Annotation,
)
from ..internal.model.metadata import ComponentMetadata, PropertyDeclaration
from .options import (
    EdgeOptions, EdgeOptionsTemplate, NodeOptions, NodeOptionsTemplate,
)
from .values import (
    GraphArray, GraphScalar, GraphValue, NonNullableGraphValue, PropertySlot,
)


def property[T: GraphValue](  # pyright: ignore[reportInvalidTypeVarUse]
    *, name: str | None = None, description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> PropertySlot[T]:
    """Declare a graph property accepting an authoring value of type ``T``.

    Assign the result to a class attribute annotated ``PropertySlot[T]``. The
    external name defaults to the attribute in snake case and the description
    defaults to the string literal directly below the assignment.

    Example:
        ```python
        from kg_build_system import Node, PropertySlot, property

        class SiteNode(Node):
            name: PropertySlot[str] = property()
            region: PropertySlot[str | None] = property(
                description="Region the register records, if any.",
            )
        ```
    """
    from .._private.properties import make_property

    return cast(PropertySlot[T], make_property(
        name=name, description=description, annotations=annotations,
    ))


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
        from ...service._private.class_creation import (
            prepare_topology_declaration,
        )

        prepare_topology_declaration(cls)


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
        from kg_build_system import Node, NodeTemplate, PropertySlot, property

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
        from kg_build_system import Edge, EdgeTemplate, Node, PropertySlot, property

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
    """Concrete edge base; endpoint parameters stay invariant.

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


__all__ = [
    "AbstractEdge", "AbstractNode", "D", "D_co", "Edge", "EdgeOptions",
    "EdgeOptionsTemplate", "EdgeTemplate", "Endpoint", "GraphArray",
    "GraphScalar", "GraphValue", "N_co", "Node", "NodeOptions",
    "NodeOptionsTemplate", "NodeSideBase", "NodeTemplate",
    "NonNullableGraphValue", "PropertySlot", "S", "S_co",
    "TopologyDeclarationBase",
]
