"""Frozen graph-binding authoring models.

A binding stores facts only: the target component, the normalized property
values, the keys, the annotations and the optional row source. Validation and
normalization belong to :mod:`kg_build_system.binding.factories`; lowering
belongs to :mod:`kg_build_system.binding.language`.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from ..annotations.interfaces import Annotation, annotation_tuple
from ..expressions.interfaces import ValueExpression, ValueInput
from ..topology.interfaces import Edge, Node

N_co = TypeVar("N_co", bound=Node, covariant=True)
E_co = TypeVar("E_co", bound=Edge[Any, Any], covariant=True)
K = TypeVar("K")
SK = TypeVar("SK")
TK = TypeVar("TK")

# External property name paired with the expression the binding supplies for it.
type PropertyValues = tuple[tuple[str, ValueExpression[Any]], ...]


@dataclass(frozen=True)
class BindingOptions:
    """Portable metadata attached to one graph binding.

    Example:
    ```python
    from kg_build_system import BindingOptions

    options = BindingOptions()
    ```
    """

    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "annotations", annotation_tuple(list(self.annotations)),
        )


@dataclass(frozen=True)
class NodeValues(Generic[N_co, K]):
    """The row-derived values one node binding supplies.

    Example:
    ```python
    from kg_build_system import NodeValues, node_binding

    binding = node_binding(
        target=UnitNode,
        rows=UnitTable.row_source(),
        bind=lambda row: NodeValues(
            build_key=row.unit_ref,
            properties=UnitNode(name=row.unit_name),
        ),
    )
    ```
    """

    build_key: ValueInput[K]
    properties: N_co


@dataclass(frozen=True)
class EdgeValues(Generic[E_co, K, SK, TK]):
    """The row-derived values one edge binding supplies.

    The four parameters keep each key distinct: the edge key, the source node
    key and the target node key. Collapsing them into three would lose the
    static distinction between the two endpoint keys.

    Example:
    ```python
    from kg_build_system import EdgeValues, edge_binding

    binding = edge_binding(
        target=HasUnitEdge,
        rows=UnitTable.row_source(),
        bind=lambda row: EdgeValues(
            build_key=row.unit_ref,
            source_build_key=row.site_id,
            target_build_key=row.unit_ref,
            properties=HasUnitEdge(as_at=row.as_at),
        ),
    )
    ```
    """

    build_key: ValueInput[K]
    source_build_key: ValueInput[SK]
    target_build_key: ValueInput[TK]
    properties: E_co


@dataclass(frozen=True)
class NodeBinding(Generic[N_co]):
    """One row context mapped onto one concrete node component.

    Example:
    ```python
    from kg_build_system import NodeBinding, node_binding

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


@dataclass(frozen=True)
class EdgeBinding(Generic[E_co]):
    """One row context mapped onto one concrete edge component.

    Example:
    ```python
    from kg_build_system import EdgeBinding, edge_binding

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


type Binding = NodeBinding[Any] | EdgeBinding[Any]


__all__ = [
    "Binding", "BindingOptions", "EdgeBinding", "EdgeValues", "NodeBinding",
    "NodeValues", "PropertyValues",
]
