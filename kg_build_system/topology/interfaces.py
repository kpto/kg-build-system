"""Framework-internal interface of the graph-topology domain.

Another subpackage reads declaration facts with the helpers here and lowers a
build through :class:`TopologyLanguage`. A graph author writes the names in
:mod:`kg_build_system.topology`; the compilation IR is
:mod:`kg_build_system.topology.ir`.

Every function in ``__all__`` is a thin wrapper defined here; the
implementation lives in :mod:`kg_build_system.topology.models` or
:mod:`kg_build_system.topology.language` and is imported under a private alias.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..annotations.interfaces import Annotation
from .ir import ComponentIR, PropertyIR
from .language import (
    TopologyLanguage,
    component_ir as _component_ir,
    decode_component as _decode_component,
    decode_topology_part as _decode_topology_part,
    encode_component as _encode_component,
    encode_topology_part as _encode_topology_part,
    symbol_id as _symbol_id,
)
from .models import (
    D,
    D_co,
    N_co,
    S,
    S_co,
    AbstractEdge,
    AbstractNode,
    ComponentMetadata,
    Edge,
    EdgeOptions,
    EdgeOptionsTemplate,
    EdgeTemplate,
    Endpoint,
    GraphScalar,
    GraphValue,
    Node,
    NodeOptions,
    NodeOptionsTemplate,
    NodeSideBase,
    NodeTemplate,
    NonNullableGraphValue,
    PropertyDeclaration,
    PropertySlot,
    TopologyDeclarationBase,
    component_kind as _component_kind,
    endpoint as _endpoint,
    is_abstract_component as _is_abstract_component,
    is_concrete_component as _is_concrete_component,
    properties_for as _properties_for,
    property as _property,
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
    return _property(
        name=name, description=description, annotations=annotations,
    )


def endpoint[N: Node](target: type[N]) -> Endpoint[N]:
    """Name a concrete node component as an edge-binding endpoint.

    Pass the token as ``source_node=`` or ``target_node=`` to
    ``edge_binding``. A token is required when the declared side is an abstract
    category and is optional for a concrete declared side.

    Example:
        ```python
        from kg_build_system import Node, endpoint

        class SiteNode(Node):
            ...

        site = endpoint(SiteNode)
        assert site.target is SiteNode
        ```
    """
    return _endpoint(target)


def properties_for(cls: type[Any]) -> dict[str, PropertyDeclaration]:
    """The resolved properties of one declaration, keyed by attribute.

    Inheritance follows normal Python shadowing: a subclass slot replaces an
    inherited slot with the same attribute name. The result is resolved once at
    class creation and is not rebuilt by this call.

    Example:
        ```python
        from kg_build_system import Node, PropertySlot, property
        from kg_build_system.topology.interfaces import properties_for

        class SiteNode(Node):
            name: PropertySlot[str] = property()

        assert properties_for(SiteNode)["name"].name == "name"
        ```
    """
    return _properties_for(cls)


def component_kind(cls: type[Any]) -> str | None:
    """Return ``"node"`` or ``"edge"`` for a declaration, else ``None``.

    A template and a plain class are not graph components and return ``None``.

    Example:
        ```python
        from kg_build_system import AbstractNode, Node
        from kg_build_system.topology.interfaces import component_kind

        class AssetNode(AbstractNode):
            ...

        class SiteNode(Node):
            ...

        assert component_kind(AssetNode) == "node"
        assert component_kind(SiteNode) == "node"
        assert component_kind(str) is None
        ```
    """
    return _component_kind(cls)


def is_concrete_component(cls: type[Any]) -> bool:
    """Whether the class declares a concrete, bindable node or edge.

    Example:
        ```python
        from kg_build_system import AbstractNode, Node
        from kg_build_system.topology.interfaces import is_concrete_component

        class AssetNode(AbstractNode):
            ...

        class SiteNode(Node):
            ...

        assert not is_concrete_component(AssetNode)
        assert is_concrete_component(SiteNode)
        ```
    """
    return _is_concrete_component(cls)


def is_abstract_component(cls: type[Any]) -> bool:
    """Whether the class declares a graph-visible abstract category.

    Example:
        ```python
        from kg_build_system import AbstractNode, Node
        from kg_build_system.topology.interfaces import is_abstract_component

        class AssetNode(AbstractNode):
            ...

        class SiteNode(Node):
            ...

        assert is_abstract_component(AssetNode)
        assert not is_abstract_component(SiteNode)
        ```
    """
    return _is_abstract_component(cls)


def component_ir(declaration: type[Any]) -> ComponentIR:
    """Lower one graph-visible declaration to its frozen IR value.

    The result carries the stable symbol ID, logical name, kind, properties,
    annotations, parent and, for an edge, the source and target component names.

    Example:
        ```python
        from kg_build_system import Node, PropertySlot, property
        from kg_build_system.topology.interfaces import component_ir

        class SiteNode(Node):
            name: PropertySlot[str] = property()

        component = component_ir(SiteNode)
        assert component.name == "site"
        assert component.kind == "node"
        ```
    """
    return _component_ir(declaration)


def symbol_id(kind: str, declaration: type[Any]) -> str:
    """The stable authoring identity of one component declaration.

    The ID combines the kind, the defining module and the qualified class name,
    so it does not depend on the logical name or on build order.

    Example:
        ```python
        from kg_build_system import Node
        from kg_build_system.topology.interfaces import symbol_id

        class SiteNode(Node):
            ...

        assert symbol_id("node", SiteNode).endswith(":SiteNode")
        ```
    """
    return _symbol_id(kind, declaration)




def encode_component(value: ComponentIR) -> dict[str, Any]:
    """Encode one component as a canonical JSON-compatible mapping.

    Example:
        ```python
        from kg_build_system import Node
        from kg_build_system.topology.interfaces import (
            component_ir, decode_component, encode_component,
        )

        class SiteNode(Node):
            ...

        encoded = encode_component(component_ir(SiteNode))
        assert encoded["name"] == "site"
        assert decode_component(encoded).name == "site"
        ```
    """
    return _encode_component(value)


def decode_component(value: Mapping[str, Any]) -> ComponentIR:
    """Decode one component mapping back into a frozen ``ComponentIR``.

    Example:
        ```python
        from kg_build_system import Node
        from kg_build_system.topology.interfaces import (
            component_ir, decode_component, encode_component,
        )

        class SiteNode(Node):
            ...

        encoded = encode_component(component_ir(SiteNode))
        assert decode_component(encoded).kind == "node"
        ```
    """
    return _decode_component(value)


def encode_topology_part(
    components: Sequence[ComponentIR],
) -> list[dict[str, Any]]:
    """Encode a topology part as a list of canonical JSON-compatible mappings.

    The sequence may be a blueprint's component tuple or any sequence of
    ``ComponentIR`` values.

    Example:
        ```python
        from kg_build_system import Node
        from kg_build_system.topology.interfaces import (
            component_ir, encode_topology_part,
        )

        class SiteNode(Node):
            ...

        values = encode_topology_part((component_ir(SiteNode),))
        assert values[0]["name"] == "site"
        ```
    """
    return _encode_topology_part(components)


def decode_topology_part(
    value: list[dict[str, Any]],
) -> tuple[ComponentIR, ...]:
    """Decode a topology part into a tuple of frozen components.

    Example:
        ```python
        from kg_build_system import Node
        from kg_build_system.topology.interfaces import (
            component_ir, decode_topology_part, encode_topology_part,
        )

        class SiteNode(Node):
            ...

        encoded = encode_topology_part((component_ir(SiteNode),))
        components = decode_topology_part(encoded)
        assert components[0].name == "site"
        ```
    """
    return _decode_topology_part(value)


__all__ = [
    "AbstractEdge", "AbstractNode", "ComponentIR", "ComponentMetadata",
    "D", "D_co", "Edge", "EdgeOptions", "EdgeOptionsTemplate", "EdgeTemplate",
    "Endpoint", "GraphScalar", "GraphValue", "N_co", "Node", "NodeOptions",
    "NodeOptionsTemplate", "NodeSideBase", "NodeTemplate",
    "NonNullableGraphValue", "PropertyDeclaration", "PropertyIR",
    "PropertySlot", "S", "S_co", "TopologyDeclarationBase", "TopologyLanguage",
    "component_ir", "component_kind", "decode_component",
    "decode_topology_part", "encode_component",
    "encode_topology_part", "endpoint", "is_abstract_component",
    "is_concrete_component", "properties_for", "property", "symbol_id",
]
