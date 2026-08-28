"""Proof of the abstract-endpoint binding pattern: endpoints reference a
component's identity, not one of its producers.

Expected pyright result: exactly 3 errors, all inside the `_misuse_*` block.
Expected runtime result: prints OK.
"""
from dataclasses import dataclass
from typing import Generic, TypeVar

from kg_build_system import (
    Field, Node, PropertySlot, Table, field, node_binding, property,
)
from kg_build_system.expressions import ValueExpression
from kg_build_system.topology import GraphComponent

N_co = TypeVar("N_co", bound=GraphComponent, covariant=True)
N = TypeVar("N", bound=Node)
S = TypeVar("S", bound=GraphComponent)
D = TypeVar("D", bound=GraphComponent)


class NodeTemplate(GraphComponent):
    """Inert mixin root."""


class AbstractNode(GraphComponent):
    """Category base."""


@dataclass(frozen=True)
class Endpoint(Generic[N_co]):
    target: type[N_co]


def endpoint[N: Node](target: type[N]) -> Endpoint[N]:
    if vars(target).get("_component_declaration_kind") != "node":
        raise TypeError(f"'{target.__name__}' is not a concrete node")
    return Endpoint(target)


class EdgeBase(GraphComponent, Generic[S, D]):
    """Stand-in for Edge; real Edge relaxes its endpoint bound to categories."""


def edge_binding(
    *,
    target: type[EdgeBase[S, D]],
    source_node: Endpoint[S],
    target_node: Endpoint[D],
    source_build_key: ValueExpression[str],
    target_build_key: ValueExpression[str],
) -> None: ...


# --- authoring -----------------------------------------------------------

class Audited(NodeTemplate):
    revision: PropertySlot[str] = property()


class EntityNode(AbstractNode):
    title: PropertySlot[str] = property()


class RecordNode(Audited, EntityNode, Node):
    city: PropertySlot[str] = property()


class MetricNode(EntityNode, Node):
    code: PropertySlot[str] = property()


class OutsideNode(Node):
    label: PropertySlot[str] = property()


class RecordsLegacy(Table):
    id: Field[str] = field()
    title: Field[str] = field()
    city: Field[str] = field()
    rev: Field[str] = field()


class RecordsStream(Table):
    record_key: Field[str] = field()
    title: Field[str] = field()
    city: Field[str] = field()
    rev: Field[str] = field()


class MetricsView(Table):
    record_id: Field[str] = field()
    code: Field[str] = field()
    title: Field[str] = field()


class ContainsEdge(EdgeBase[EntityNode, EntityNode]):
    pass


# one component, two producers -- the situation that forced the design
records_from_legacy = node_binding(
    target=RecordNode,
    build_key=RecordsLegacy.id.expression.prepend("record::"),
    properties=RecordNode(
        title=RecordsLegacy.title, city=RecordsLegacy.city,
        revision=RecordsLegacy.rev,
    ),
)
records_from_stream = node_binding(
    target=RecordNode,
    build_key=RecordsStream.record_key.expression.prepend("record::"),
    properties=RecordNode(
        title=RecordsStream.title, city=RecordsStream.city,
        revision=RecordsStream.rev,
    ),
)

# choice-free endpoint: identity is the component, not either producer
edge_binding(
    target=ContainsEdge,
    source_node=endpoint(RecordNode),
    target_node=endpoint(MetricNode),
    source_build_key=MetricsView.record_id.expression.prepend("record::"),
    target_build_key=MetricsView.code.expression.prepend("metric::"),
)


# --- misuses: each function must produce exactly one pyright error -------

def _misuse_abstract_endpoint() -> None:  # EXPECT-STATIC: abstract category
    edge_binding(
        target=ContainsEdge,
        source_node=endpoint(EntityNode),
        target_node=endpoint(MetricNode),
        source_build_key=MetricsView.record_id.expression,
        target_build_key=MetricsView.code.expression,
    )


def _misuse_wrong_category() -> None:  # EXPECT-STATIC: outside the endpoint category
    edge_binding(
        target=ContainsEdge,
        source_node=endpoint(OutsideNode),
        target_node=endpoint(MetricNode),
        source_build_key=MetricsView.record_id.expression,
        target_build_key=MetricsView.code.expression,
    )


def _misuse_raw_class() -> None:  # EXPECT-STATIC: class where identity token required
    edge_binding(
        target=ContainsEdge,
        source_node=RecordNode,
        target_node=endpoint(MetricNode),
        source_build_key=MetricsView.record_id.expression,
        target_build_key=MetricsView.code.expression,
    )


# --- runtime backstop for untyped/bypassed construction ------------------

def _runtime_backstop() -> None:
    try:
        endpoint(EntityNode)  # pyright: ignore[reportArgumentType]
        raise AssertionError("abstract component must be rejected at runtime")
    except TypeError:
        pass


if __name__ == "__main__":
    del records_from_legacy, records_from_stream
    _runtime_backstop()
    print("OK")
