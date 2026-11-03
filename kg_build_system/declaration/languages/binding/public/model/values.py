"""Binding values and options returned to a graph author.

``NodeBinding`` and ``EdgeBinding`` are the frozen results of the binding
factories; ``NodeValues`` and ``EdgeValues`` are the row-derived values a
``bind`` callable returns; ``BindingOptions`` attaches portable annotations.

Example:
    ```python
    from kg_build_system.declaration.languages.binding import (
        BindingOptions, NodeBinding, node_binding,
    )

    binding: NodeBinding[UnitNode] = node_binding(
        target=UnitNode,
        build_key=UnitTable.unit_ref,
        properties=UnitNode(name=UnitTable.unit_name),
        options=BindingOptions(),
    )
    ```
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar

from kg_build_system.declaration.foundations.annotations.internal import (
    Annotation,
    annotation_tuple,
)
from kg_build_system.declaration.foundations.expressions.public import (
    ValueExpression,
    ValueInput,
)
from kg_build_system.declaration.languages.topology import Edge, Node

N_co = TypeVar("N_co", bound=Node, covariant=True)
E_co = TypeVar("E_co", bound=Edge[Any, Any], covariant=True)
K = TypeVar("K")
SK = TypeVar("SK")
TK = TypeVar("TK")

# External property name paired with the expression the binding supplies for it.
type PropertyValues = tuple[tuple[str, ValueExpression[Any]], ...]
type BindingMode = Literal["declarative", "python"]


@dataclass(frozen=True, slots=True)
class PythonRef:
    """A stable reference to the callable that produced a Python binding.

    The reference carries no live callable. It names the module and qualified
    name plus the callable's source signature, so a consumer can report where a
    rows-form binding came from.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding import PythonRef

        reference = PythonRef("example.bindings", "build_unit", "(row)")
        ```
    """

    module: str
    qualname: str
    signature: str

    def __post_init__(self) -> None:
        if not self.module:
            raise ValueError("a Python reference requires a module")
        if not self.qualname:
            raise ValueError("a Python reference requires a qualified name")


@dataclass(frozen=True, slots=True)
class BindingOptions:
    """Portable metadata attached to one graph binding.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding import BindingOptions

        options = BindingOptions()
        ```
    """

    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "annotations", annotation_tuple(list(self.annotations)),
        )


@dataclass(frozen=True, slots=True)
class NodeValues(Generic[N_co, K]):
    """The row-derived values one node binding supplies.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding import NodeValues

        values = NodeValues(build_key=row.unit_ref, properties=UnitNode(...))
        ```
    """

    build_key: ValueInput[K]
    properties: N_co


@dataclass(frozen=True, slots=True)
class EdgeValues(Generic[E_co, K, SK, TK]):
    """The row-derived values one edge binding supplies.

    The four parameters keep each key distinct: the edge key, the source node
    key and the target node key.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding import EdgeValues

        values = EdgeValues(
            build_key=row.unit_ref,
            source_build_key=row.site_id,
            target_build_key=row.unit_ref,
            properties=HasUnitEdge(...),
        )
        ```
    """

    build_key: ValueInput[K]
    source_build_key: ValueInput[SK]
    target_build_key: ValueInput[TK]
    properties: E_co


@dataclass(frozen=True, slots=True)
class NodeBinding(Generic[N_co]):
    """One row context mapped onto one concrete node component.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding import NodeBinding

        binding: NodeBinding[UnitNode] = node_binding(
            target=UnitNode,
            build_key=UnitTable.unit_ref,
            properties=UnitNode(name=UnitTable.unit_name),
        )
        ```
    """

    debug_name: str | None
    target: type[N_co]
    build_key: ValueExpression[Any]
    properties: PropertyValues
    annotations: tuple[Annotation, ...] = ()
    rows: Any = None
    mode: BindingMode = "declarative"
    python_ref: PythonRef | None = None


@dataclass(frozen=True, slots=True)
class EdgeBinding(Generic[E_co]):
    """One row context mapped onto one concrete edge component.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding import EdgeBinding

        binding: EdgeBinding[HasUnitEdge] = edge_binding(
            target=HasUnitEdge,
            build_key=UnitTable.unit_ref,
            source_build_key=UnitTable.site_id,
            target_build_key=UnitTable.unit_ref,
            properties=HasUnitEdge(as_at=UnitTable.as_at),
        )
        ```
    """

    debug_name: str | None
    target: type[E_co]
    build_key: ValueExpression[Any]
    source_build_key: ValueExpression[Any]
    target_build_key: ValueExpression[Any]
    properties: PropertyValues
    annotations: tuple[Annotation, ...] = ()
    source_node: type[Node] | None = None
    target_node: type[Node] | None = None
    rows: Any = None
    mode: BindingMode = "declarative"
    python_ref: PythonRef | None = None


type Binding = NodeBinding[Any] | EdgeBinding[Any]


__all__ = [
    "Binding", "BindingMode", "BindingOptions", "EdgeBinding", "EdgeValues",
    "NodeBinding", "NodeValues", "PropertyValues", "PythonRef",
]
