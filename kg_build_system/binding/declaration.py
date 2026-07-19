"""Class-based, type-aware binding declarations.

Bindings are declarative expressions. They name concrete input locations and
map typed topology references to typed input-column references; this module
does not implement data access or execute a query.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar, Generic, TypeVar, get_args, get_origin

from kg_build_system.topology import Edge, IdentifierRef, Node, PropertyRef

TValue = TypeVar("TValue")
TNode = TypeVar("TNode", bound=Node)
TEdge = TypeVar("TEdge", bound=Edge[Any, Any])


class BindingValidationError(ValueError):
    """Raised when a binding declaration is structurally invalid."""


class InputFormat(StrEnum):
    """Physical input formats supported by the initial binding model."""

    CSV = "csv"
    PARQUET = "parquet"


def _generic_python_type(reference: object) -> type[Any]:
    generic_type = getattr(reference, "__orig_class__", None)
    arguments = get_args(generic_type)
    if len(arguments) != 1 or not isinstance(arguments[0], type):
        message = "References must use one concrete type argument, such as ColumnRef[str]()."
        raise BindingValidationError(message)
    return arguments[0]


class ColumnRef(Generic[TValue]):
    """A typed, class-level reference to a column of an input relation."""

    def __init__(self, *, nullable: bool = True) -> None:
        self.nullable = nullable
        self.name: str | None = None
        self.owner: type[Relation] | None = None

    @property
    def python_type(self) -> type[TValue]:
        """The concrete type supplied as ``ColumnRef[T]``."""
        return _generic_python_type(self)

    def __set_name__(self, owner: type[Relation], name: str) -> None:
        # A binding may expose a relation column as an endpoint reference.
        # Python invokes __set_name__ for that alias too; retain the original
        # relation ownership rather than turning the column into a binding field.
        if self.owner is None:
            self.owner = owner
            self.name = name


class Relation:
    """A physical input relation with statically referenceable columns."""

    _binding_name: ClassVar[str]
    _binding_location: ClassVar[str]
    _binding_format: ClassVar[InputFormat]
    _binding_options: ClassVar[Mapping[str, str]]

    def __init_subclass__(
        cls,
        *,
        location: str,
        format: InputFormat,
        name: str | None = None,
        options: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)
        if not location:
            raise BindingValidationError("Relation locations must be non-empty.")
        cls._binding_name = name or cls.__name__
        cls._binding_location = location
        cls._binding_format = format
        cls._binding_options = dict(options or {})

    @classmethod
    def to_definition(cls) -> dict[str, Any]:
        """Compile this input declaration into a serialisable relation definition."""
        columns = [
            {
                "name": name,
                "python_type": value.python_type.__name__,
                "nullable": value.nullable,
            }
            for name, value in cls.__dict__.items()
            if isinstance(value, ColumnRef)
        ]
        return {
            "name": cls._binding_name,
            "location": cls._binding_location,
            "format": cls._binding_format.value,
            "options": dict(cls._binding_options),
            "columns": columns,
        }


class FieldBinding(Generic[TValue]):
    """A type-safe mapping from a topology field reference to an input column."""

    def __init__(
        self,
        target: IdentifierRef[TValue] | PropertyRef[TValue],
        source: ColumnRef[TValue],
    ) -> None:
        if target.python_type is not source.python_type:
            message = f"Cannot bind {target.python_type.__name__} to {source.python_type.__name__}."
            raise BindingValidationError(message)
        if source.name is None or source.owner is None:
            raise BindingValidationError("A bound source column must be declared on a Relation.")
        self.target = target
        self.source = source

    def to_definition(self) -> dict[str, str]:
        """Return the portable form of this typed field mapping."""
        if self.source.name is None:
            raise BindingValidationError("A bound source column has no name.")
        if isinstance(self.target, IdentifierRef):
            target = "identifier"
        elif self.target.name is not None:
            target = f"property:{self.target.name}"
        else:
            raise BindingValidationError("A bound topology property has no name.")
        return {"target": target, "source": self.source.name}


class NodeBinding(Generic[TNode]):
    """Base class for a binding that produces one declared node type."""

    _bound_relation: ClassVar[type[Relation]]

    def __init_subclass__(cls, *, relation: type[Relation], **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._bound_relation = relation

    @classmethod
    def to_definition(cls) -> dict[str, Any]:
        """Compile this node binding into a portable binding definition."""
        node = _generic_binding_target(cls, NodeBinding)
        mappings = _binding_members(cls)
        _validate_node_mappings(node, mappings, cls._bound_relation)
        return {
            "kind": "node",
            "target": node._topology_name,
            "relation": cls._bound_relation.to_definition(),
            "mappings": [mapping.to_definition() for mapping in mappings],
        }


class EdgeBinding(Generic[TEdge]):
    """Base class for a binding that produces one declared edge type."""

    _bound_relation: ClassVar[type[Relation]]

    def __init_subclass__(cls, *, relation: type[Relation], **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._bound_relation = relation

    @classmethod
    def to_definition(cls) -> dict[str, Any]:
        """Compile this edge binding into a portable binding definition."""
        edge = _generic_binding_target(cls, EdgeBinding)
        source = getattr(cls, "source", None)
        target = getattr(cls, "target", None)
        if not isinstance(source, ColumnRef) or not isinstance(target, ColumnRef):
            raise BindingValidationError(f"Edge binding {cls.__name__} must declare source and target ColumnRef values.")
        if source.python_type is not str or target.python_type is not str:
            raise BindingValidationError("Edge source and target columns must be ColumnRef[str].")
        mappings = _binding_members(cls)
        _validate_edge_mappings(edge, mappings, cls._bound_relation)
        if source.name is None or target.name is None:
            raise BindingValidationError("Edge endpoint columns must be declared on a Relation.")
        return {
            "kind": "edge",
            "target": edge._topology_name,
            "relation": cls._bound_relation.to_definition(),
            "source": source.name,
            "target_endpoint": target.name,
            "mappings": [mapping.to_definition() for mapping in mappings],
        }


@dataclass(frozen=True, slots=True)
class BindingSet:
    """The serialisable collection of bindings used by a topology build."""

    name: str
    node_bindings: Sequence[type[NodeBinding[Any]]]
    edge_bindings: Sequence[type[EdgeBinding[Any]]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "node_bindings": [binding.to_definition() for binding in self.node_bindings],
            "edge_bindings": [binding.to_definition() for binding in self.edge_bindings],
        }

    def to_json(self, *, indent: int = 2) -> str:
        """Return the portable JSON representation of these bindings."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


def binding_set(
    name: str,
    *,
    node_bindings: Sequence[type[NodeBinding[Any]]],
    edge_bindings: Sequence[type[EdgeBinding[Any]]],
) -> BindingSet:
    """Create a serialisable set of class-based binding declarations."""
    return BindingSet(name=name, node_bindings=tuple(node_bindings), edge_bindings=tuple(edge_bindings))


def _generic_binding_target(cls: type[Any], root: type[Any]) -> type[Any]:
    for candidate in cls.__mro__:
        for base in getattr(candidate, "__orig_bases__", ()):
            if get_origin(base) is root:
                (target,) = get_args(base)
                if isinstance(target, type):
                    return target
    raise BindingValidationError(f"Binding {cls.__name__} must inherit from {root.__name__}[Target].")


def _binding_members(cls: type[Any]) -> Sequence[FieldBinding[Any]]:
    members: dict[str, FieldBinding[Any]] = {}
    for base in reversed(cls.__mro__):
        for name, value in base.__dict__.items():
            if isinstance(value, FieldBinding):
                members[name] = value
    return tuple(members.values())


def _validate_node_mappings(
    node: type[Node],
    mappings: Sequence[FieldBinding[Any]],
    relation: type[Relation],
) -> None:
    targets = set[str]()
    for mapping in mappings:
        if mapping.source.owner is not relation:
            raise BindingValidationError("Node mappings must use columns from the binding relation.")
        if isinstance(mapping.target, IdentifierRef):
            target = "identifier"
        else:
            if mapping.target.owner is None or not issubclass(node, mapping.target.owner):
                raise BindingValidationError("A node mapping references a property from another node type.")
            target = mapping.target.name or ""
        if target in targets:
            raise BindingValidationError(f"Node binding has duplicate mapping for {target!r}.")
        targets.add(target)
    if "identifier" not in targets:
        raise BindingValidationError(f"Node binding {node.__name__} must map its identifier.")


def _validate_edge_mappings(
    edge: type[Edge[Any, Any]],
    mappings: Sequence[FieldBinding[Any]],
    relation: type[Relation],
) -> None:
    for mapping in mappings:
        if mapping.source.owner is not relation:
            raise BindingValidationError("Edge mappings must use columns from the binding relation.")
        if not isinstance(mapping.target, PropertyRef):
            raise BindingValidationError("Edge bindings may only map edge properties.")
        if mapping.target.owner is None or not issubclass(edge, mapping.target.owner):
            raise BindingValidationError("An edge mapping references a property from another edge type.")
