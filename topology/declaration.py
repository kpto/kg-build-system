"""Statically referenceable Python declarations for topology authoring.

The declaration API is the Python authoring surface. It compiles class
attributes into the serialisable topology IR defined in :mod:`topology.model`.
For example, ``Target.symbol`` is a ``PropertyRef[str]`` that a future binding
can accept directly and type-check.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar, Generic, TypeVar, get_args, get_origin

from topology.model import Annotation, EdgeType, Identifier, NodeType, Property, Topology, TopologyValidationError, ValueType

TValue = TypeVar("TValue")
TSource = TypeVar("TSource", bound="Node")
TTarget = TypeVar("TTarget", bound="Node")


def _value_type_from_python_type(python_type: type[Any]) -> ValueType:
    if python_type is str:
        return ValueType.STRING
    if python_type is bool:
        return ValueType.BOOLEAN
    if python_type is int:
        return ValueType.INTEGER
    if python_type is float:
        return ValueType.FLOAT
    message = f"No portable topology value type is defined for {python_type!r}."
    raise TypeError(message)


def _generic_python_type(reference: object) -> type[Any]:
    generic_type = getattr(reference, "__orig_class__", None)
    arguments = get_args(generic_type)
    if len(arguments) != 1 or not isinstance(arguments[0], type):
        message = "References must be constructed with one concrete type argument, such as PropertyRef[str]()."
        raise TopologyValidationError(message)
    return arguments[0]


class PropertyRef(Generic[TValue]):
    """A typed, class-level reference to a declared node or edge property."""

    def __init__(
        self,
        *,
        nullable: bool = True,
        many: bool = False,
        description: str | None = None,
        annotations: Sequence[Annotation] = (),
    ) -> None:
        self.nullable = nullable
        self.many = many
        self.description = description
        self.annotations = tuple(annotations)
        self.name: str | None = None
        self.owner: type[Node] | type[Edge[Any, Any]] | None = None

    @property
    def python_type(self) -> type[TValue]:
        """The concrete type supplied as ``PropertyRef[T]``."""
        return _generic_python_type(self)

    def __set_name__(self, owner: type[Node] | type[Edge[Any, Any]], name: str) -> None:
        self.owner = owner
        self.name = name

    def to_definition(self) -> Property:
        """Create the serialisable property definition after class creation."""
        if self.name is None:
            raise TopologyValidationError("A property reference must be assigned to a class attribute.")
        return Property(
            name=self.name,
            value_type=_value_type_from_python_type(self.python_type),
            nullable=self.nullable,
            many=self.many,
            description=self.description,
            annotations=self.annotations,
        )


class IdentifierRef(Generic[TValue]):
    """A typed, class-level reference to a node identifier policy."""

    def __init__(
        self,
        *,
        description: str | None = None,
        annotations: Sequence[Annotation] = (),
    ) -> None:
        self.description = description
        self.annotations = tuple(annotations)
        self.name: str | None = None

    @property
    def python_type(self) -> type[TValue]:
        """The concrete type supplied as ``IdentifierRef[T]``."""
        return _generic_python_type(self)

    def __set_name__(self, owner: type[Node], name: str) -> None:
        self.name = name

    def to_definition(self) -> Identifier:
        """Create the serialisable identifier definition."""
        return Identifier(
            value_type=_value_type_from_python_type(self.python_type),
            description=self.description,
            annotations=self.annotations,
        )


class Node:
    """Base class for a statically declared node type."""

    _topology_name: ClassVar[str]
    _topology_description: ClassVar[str | None]
    _topology_annotations: ClassVar[Sequence[Annotation]]

    def __init_subclass__(
        cls,
        *,
        name: str | None = None,
        description: str | None = None,
        annotations: Sequence[Annotation] = (),
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)
        cls._topology_name = name or cls.__name__
        cls._topology_description = description
        cls._topology_annotations = tuple(annotations)

    @classmethod
    def to_definition(cls) -> NodeType:
        """Compile this declaration into the topology IR."""
        identifiers = [value for value in cls.__dict__.values() if isinstance(value, IdentifierRef)]
        if len(identifiers) != 1:
            message = f"Node {cls.__name__} must declare exactly one identifier()."
            raise TopologyValidationError(message)
        properties = tuple(value.to_definition() for value in cls.__dict__.values() if isinstance(value, PropertyRef))
        return NodeType(
            name=cls._topology_name,
            identifier=identifiers[0].to_definition(),
            properties=properties,
            description=cls._topology_description,
            annotations=cls._topology_annotations,
        )


class Edge(Generic[TSource, TTarget]):
    """Base class for a statically declared edge type."""

    _topology_name: ClassVar[str]
    _topology_description: ClassVar[str | None]
    _topology_annotations: ClassVar[Sequence[Annotation]]

    def __init_subclass__(
        cls,
        *,
        name: str | None = None,
        description: str | None = None,
        annotations: Sequence[Annotation] = (),
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)
        cls._topology_name = name or cls.__name__
        cls._topology_description = description
        cls._topology_annotations = tuple(annotations)

    @classmethod
    def to_definition(cls) -> EdgeType:
        """Compile this declaration into the topology IR."""
        source, target = _edge_endpoints(cls)
        properties = tuple(value.to_definition() for value in cls.__dict__.values() if isinstance(value, PropertyRef))
        return EdgeType(
            name=cls._topology_name,
            source=source._topology_name,
            target=target._topology_name,
            properties=properties,
            description=cls._topology_description,
            annotations=cls._topology_annotations,
        )


def topology(
    name: str,
    *,
    nodes: Sequence[type[Node]],
    edges: Sequence[type[Edge[Any, Any]]],
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Topology:
    """Compile statically declared node and edge types into a topology model."""
    return Topology(
        name=name,
        nodes=tuple(node.to_definition() for node in nodes),
        edges=tuple(edge.to_definition() for edge in edges),
        description=description,
        annotations=tuple(annotations),
    )


def _edge_endpoints(edge: type[Edge[Any, Any]]) -> tuple[type[Node], type[Node]]:
    for base in getattr(edge, "__orig_bases__", ()):
        if get_origin(base) is Edge:
            source, target = get_args(base)
            if isinstance(source, type) and isinstance(target, type) and issubclass(source, Node) and issubclass(target, Node):
                return source, target
    message = f"Edge {edge.__name__} must inherit from Edge[SourceNode, TargetNode]."
    raise TopologyValidationError(message)
