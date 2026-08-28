"""Proof of the abstract endpoint binding pattern: endpoints reference a
component's identity, not one of its producers.

The overload matrix keys each endpoint token on the concreteness of the
declared endpoint: the typevar inferred from ``target`` is bound to ``Node``
where the token is omittable and to the category base where it is required.
No typevar bridging is involved; each overload uses independent typevars.

Expected pyright result: exactly 5 errors, all inside the `_misuse_*` block.
Expected runtime result: prints OK.
"""
from dataclasses import dataclass
from typing import Generic, TypeVar, overload

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


@overload
def edge_binding[S: Node, D: Node](
    *,
    target: type[EdgeBase[S, D]],
    source_build_key: ValueExpression[str],
    target_build_key: ValueExpression[str],
) -> None: ...
@overload
def edge_binding[S: Node, DC: GraphComponent](
    *,
    target: type[EdgeBase[S, DC]],
    source_build_key: ValueExpression[str],
    target_node: Endpoint[DC],
    target_build_key: ValueExpression[str],
) -> None: ...
@overload
def edge_binding[SC: GraphComponent, D: Node](
    *,
    target: type[EdgeBase[SC, D]],
    source_node: Endpoint[SC],
    source_build_key: ValueExpression[str],
    target_build_key: ValueExpression[str],
) -> None: ...
@overload
def edge_binding[SC: GraphComponent, DC: GraphComponent](
    *,
    target: type[EdgeBase[SC, DC]],
    source_node: Endpoint[SC],
    source_build_key: ValueExpression[str],
    target_node: Endpoint[DC],
    target_build_key: ValueExpression[str],
) -> None: ...
def edge_binding(**_kwargs: object) -> None:
    """Stand-in implementation; the real binding enforces the same contract."""


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


class DirectEdge(EdgeBase[RecordNode, MetricNode]):
    """Both endpoints concrete: both tokens omittable."""


class MixedEdge(EdgeBase[EntityNode, MetricNode]):
    """One category endpoint: the token is required only for that side."""


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
    source_build_key=MetricsView.record_id.expression.prepend("record::"),
    target_node=endpoint(MetricNode),
    target_build_key=MetricsView.code.expression.prepend("metric::"),
)

# concrete endpoints: tokens default to the declared components
edge_binding(
    target=DirectEdge,
    source_build_key=MetricsView.record_id.expression.prepend("record::"),
    target_build_key=MetricsView.code.expression.prepend("metric::"),
)

# concrete endpoints: explicit tokens naming the declared components stay valid
edge_binding(
    target=DirectEdge,
    source_node=endpoint(RecordNode),
    source_build_key=MetricsView.record_id.expression.prepend("record::"),
    target_node=endpoint(MetricNode),
    target_build_key=MetricsView.code.expression.prepend("metric::"),
)

# mixed endpoints: only the abstract side needs a token
edge_binding(
    target=MixedEdge,
    source_node=endpoint(RecordNode),
    source_build_key=MetricsView.record_id.expression.prepend("record::"),
    target_build_key=MetricsView.code.expression.prepend("metric::"),
)


# --- misuses: each function must produce exactly one pyright error -------

def _misuse_abstract_endpoint() -> None:  # EXPECT-STATIC: abstract category
    edge_binding(
        target=ContainsEdge,
        source_node=endpoint(EntityNode),
        source_build_key=MetricsView.record_id.expression,
        target_node=endpoint(MetricNode),
        target_build_key=MetricsView.code.expression,
    )


def _misuse_wrong_category() -> None:  # EXPECT-STATIC: outside the endpoint category
    edge_binding(
        target=ContainsEdge,
        source_node=endpoint(OutsideNode),
        source_build_key=MetricsView.record_id.expression,
        target_node=endpoint(MetricNode),
        target_build_key=MetricsView.code.expression,
    )


def _misuse_raw_class() -> None:  # EXPECT-STATIC: class where identity token required
    edge_binding(
        target=ContainsEdge,
        source_node=RecordNode,
        source_build_key=MetricsView.record_id.expression,
        target_node=endpoint(MetricNode),
        target_build_key=MetricsView.code.expression,
    )


def _misuse_missing_abstract_endpoint() -> None:  # EXPECT-STATIC: token omitted on abstract endpoint
    edge_binding(
        target=ContainsEdge,
        source_build_key=MetricsView.record_id.expression,
        target_build_key=MetricsView.code.expression,
    )


def _misuse_mixed_endpoint_omitted() -> None:  # EXPECT-STATIC: abstract side of a mixed edge omitted
    edge_binding(
        target=MixedEdge,
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
