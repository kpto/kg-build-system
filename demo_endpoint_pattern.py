"""Proof of the abstract endpoint binding pattern: endpoints reference a
component's identity, not one of its producers.

The real framework provides every base, option tier, endpoint token, and
binding overload used here. The overload matrix keys each endpoint token on
the concreteness of the declared endpoint: the typevar inferred from
``target`` is bound to ``Node`` where the token is omittable and to the
node-side category base where it is required. No typevar bridging is
involved; each overload uses independent typevars.

The file also proves the endpoint-descent rule for edge hierarchy. A
concrete edge specializing an abstract edge re-declares its endpoints
through the terminal ``Edge[...]`` base, and each re-declared endpoint
must equal or descend from the abstract parent's. The checker enforces
this from base-class consistency alone: ``AbstractEdge``'s endpoint
parameters are covariant while ``Edge``'s stay invariant, so a narrower
specialization through the terminal base remains compatible with the
parent's pinned one, and widening, an edge-kind category, or a terminal
base declared before the abstract parent is rejected. The canonical base
order is therefore template, abstract parent, terminal base last --
mirroring the node side. The preparation walk enforces the same
``issubclass`` predicate at class creation, base-order insensitive.

The file also proves endpoint categories are node-side: every endpoint
type parameter is bound to the internal node-side root shared by
``AbstractNode`` and ``Node``, so an edge-kind type argument is statically
impossible, and the preparation guard rejects a ``type()``-bypassed
edge-kind specialization with the same predicate.

The file also proves the typed-options-per-tier contract: every tier
declares ``options`` and the options type identifies the tier -- the
IR-visible bases carry ``NodeOptions`` / ``EdgeOptions``, while a template
carries only the kind-matched, annotations-only
``options = NodeOptionsTemplate(...)`` / ``EdgeOptionsTemplate(...)``
value whose annotations mix into the declaring class, keeping plain
class attributes reserved for property declarations. A category's
options stay on the category -- including the abstract edge's, which
stay behind when a concrete child narrows its endpoints -- description
is never inherited, and a template given non-template or cross-kind
options, an un-wrapped sequence, or an IR-visible class given template
options all raise at class creation.

Expected pyright result: exactly 8 errors, all inside the `_misuse_*` block.
Expected runtime result: prints OK.
"""
import types
from dataclasses import dataclass

from kg_build_system import (
    AbstractEdge, AbstractNode, Annotation, Edge, EdgeOptions,
    EdgeOptionsTemplate, EdgeTemplate, EdgeLabel, Endpoint, Field, Node,
    NodeLabel, NodeOptions, NodeOptionsTemplate, NodeTemplate, PropertySlot,
    Table, edge_binding, endpoint, field, node_binding, property,
)


@dataclass(frozen=True)
class AuditTrail(Annotation):
    """Author-defined annotation used to trace options flow."""

    namespace = "demo_endpoint_pattern"
    annotation_id = "audit_trail"

    track: str


# --- authoring -----------------------------------------------------------

class Audited(NodeTemplate):
    """Share an audit-trail concern; documented by docstring."""

    options = NodeOptionsTemplate(annotations=(AuditTrail(track="record"),))
    revision: PropertySlot[str] = property()


class Weighted(EdgeTemplate):
    """Share a weight concern across relationships."""

    options = EdgeOptionsTemplate(annotations=(AuditTrail(track="edge"),))


class EntityNode(AbstractNode):
    options = NodeOptions(annotations=(NodeLabel("Entity"),))
    title: PropertySlot[str] = property()


class Sourced(NodeTemplate):
    """Share provenance; mixed into the category below reaches children."""

    options = NodeOptionsTemplate(annotations=(AuditTrail(track="sourced"),))
    origin: PropertySlot[str] = property()


class SourcedNode(Sourced, AbstractNode):
    """Category that inherited a template's options annotations."""


class RecordNode(Audited, EntityNode, Node):
    city: PropertySlot[str] = property()


class ArtifactNode(SourcedNode, Node):
    """Concrete under a category; no direct template base."""


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


class ContainsEdge(Weighted, AbstractEdge[EntityNode, EntityNode]):
    """Abstract edge over entity endpoint categories."""

    options = EdgeOptions(annotations=(EdgeLabel("CONTAINS"),))


class ContainsMetricEdge(ContainsEdge, Edge[EntityNode, MetricNode]):
    """Concrete edge descended under the abstract edge; target category narrowed."""


class RelatesEdge(Edge[EntityNode, EntityNode]):
    """Both endpoints category: both tokens required."""

    note: PropertySlot[str] = property()


class DirectEdge(Edge[RecordNode, MetricNode]):
    """Both endpoints concrete: both tokens omittable."""


class MixedEdge(Edge[EntityNode, MetricNode]):
    """One category endpoint: the token is required only for that side."""

    note: PropertySlot[str] = property()


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

# endpoint coverage: every endpoint a binding names has a producer
metrics_from_view = node_binding(
    target=MetricNode,
    build_key=MetricsView.code.expression.prepend("metric::"),
    properties=MetricNode(title=MetricsView.title, code=MetricsView.code),
)

# choice-free endpoints: identity is the component, not either producer
edge_binding(
    target=RelatesEdge,
    source_node=endpoint(RecordNode),
    target_node=endpoint(MetricNode),
    build_key=MetricsView.record_id.expression.prepend("relates::"),
    source_build_key=MetricsView.record_id.expression.prepend("record::"),
    target_build_key=MetricsView.code.expression.prepend("metric::"),
    properties=RelatesEdge(note=MetricsView.title),
)

# descended edge: the narrowed concrete side needs no token
edge_binding(
    target=ContainsMetricEdge,
    source_node=endpoint(RecordNode),
    build_key=MetricsView.record_id.expression.prepend("contains::"),
    source_build_key=MetricsView.record_id.expression.prepend("record::"),
    target_build_key=MetricsView.code.expression.prepend("metric::"),
    properties=ContainsMetricEdge(),
)

# concrete endpoints: tokens default to the declared components
edge_binding(
    target=DirectEdge,
    build_key=MetricsView.record_id.expression.prepend("direct::"),
    source_build_key=MetricsView.record_id.expression.prepend("record::"),
    target_build_key=MetricsView.code.expression.prepend("metric::"),
    properties=DirectEdge(),
)

# concrete endpoints: explicit tokens naming the declared components stay valid
edge_binding(
    target=DirectEdge,
    source_node=endpoint(RecordNode),
    target_node=endpoint(MetricNode),
    build_key=MetricsView.record_id.expression.prepend("direct::"),
    source_build_key=MetricsView.record_id.expression.prepend("record::"),
    target_build_key=MetricsView.code.expression.prepend("metric::"),
    properties=DirectEdge(),
)

# mixed endpoints: only the abstract side needs a token
edge_binding(
    target=MixedEdge,
    source_node=endpoint(RecordNode),
    build_key=MetricsView.record_id.expression.prepend("mixed::"),
    source_build_key=MetricsView.record_id.expression.prepend("record::"),
    target_build_key=MetricsView.code.expression.prepend("metric::"),
    properties=MixedEdge(note=MetricsView.title),
)


# --- options-tier flow contract ------------------------------------------

def _mixin_proof() -> None:
    # template options mix into every declaring class
    assert RecordNode._component_annotations == (AuditTrail(track="record"),)
    assert ContainsEdge._component_annotations == (
        AuditTrail(track="edge"),
        EdgeLabel("CONTAINS"),
    )
    # the abstract edge's own label stays on its entry; the concrete child
    # that descends and narrows receives only the template options
    # annotations flowing through the category
    assert ContainsMetricEdge._component_annotations == (AuditTrail(track="edge"),)
    # category options stay on the category's own entry
    assert EntityNode._component_annotations == (NodeLabel("Entity"),)
    assert MetricNode._component_annotations == ()
    assert OutsideNode._component_annotations == ()
    # a template mixed via a category still reaches concrete descendants,
    # while the category's own annotation stays behind on the category
    assert SourcedNode._component_annotations == (AuditTrail(track="sourced"),)
    assert ArtifactNode._component_annotations == (AuditTrail(track="sourced"),)
    # description is own-declared or silent -- never inherited from a
    # template, a category, or anywhere else
    assert RecordNode._metadata.get("description") is None
    assert MetricNode._metadata.get("description") is None
    assert EntityNode._metadata.get("description") is None
    assert DirectEdge._metadata.get("description") == (
        "Both endpoints concrete: both tokens omittable."
    )
    assert ContainsMetricEdge._metadata.get("description") == (
        "Concrete edge descended under the abstract edge; target category narrowed."
    )
    # names are inferred from the declaration, never mixed across tiers
    assert (RecordNode._component_name, EntityNode._component_name) == ("record", "entity")
    assert ContainsMetricEdge._component_name == "contains_metric"
    # the category parent is recorded for every IR entry
    assert RecordNode._component_parent_class is EntityNode
    assert ContainsMetricEdge._component_parent_class is ContainsEdge
    assert ArtifactNode._component_parent_class is SourcedNode


# --- misuses: each function must produce exactly one pyright error -------

def _misuse_abstract_endpoint() -> None:  # EXPECT-STATIC: abstract category
    edge_binding(
        target=RelatesEdge,
        source_node=endpoint(EntityNode),
        build_key=MetricsView.record_id.expression,
        source_build_key=MetricsView.record_id.expression,
        target_node=endpoint(MetricNode),
        target_build_key=MetricsView.code.expression,
        properties=RelatesEdge(note=MetricsView.title),
    )


def _misuse_wrong_category() -> None:  # EXPECT-STATIC: outside the endpoint category
    edge_binding(
        target=RelatesEdge,
        source_node=endpoint(OutsideNode),
        build_key=MetricsView.record_id.expression,
        source_build_key=MetricsView.record_id.expression,
        target_node=endpoint(MetricNode),
        target_build_key=MetricsView.code.expression,
        properties=RelatesEdge(note=MetricsView.title),
    )


def _misuse_raw_class() -> None:  # EXPECT-STATIC: class where identity token required
    edge_binding(
        target=RelatesEdge,
        source_node=RecordNode,
        build_key=MetricsView.record_id.expression,
        source_build_key=MetricsView.record_id.expression,
        target_node=endpoint(MetricNode),
        target_build_key=MetricsView.code.expression,
        properties=RelatesEdge(note=MetricsView.title),
    )


def _misuse_missing_abstract_endpoint() -> None:  # EXPECT-STATIC: token omitted on abstract endpoint
    edge_binding(
        target=RelatesEdge,
        build_key=MetricsView.record_id.expression,
        source_build_key=MetricsView.record_id.expression,
        target_build_key=MetricsView.code.expression,
        properties=RelatesEdge(note=MetricsView.title),
    )


def _misuse_mixed_endpoint_omitted() -> None:  # EXPECT-STATIC: abstract side of a mixed edge omitted
    edge_binding(
        target=MixedEdge,
        build_key=MetricsView.record_id.expression,
        source_build_key=MetricsView.record_id.expression,
        target_build_key=MetricsView.code.expression,
        properties=MixedEdge(note=MetricsView.title),
    )


def _misuse_endpoint_widened() -> None:  # EXPECT-STATIC: endpoint widened past the abstract lineage
    class Widened(ContainsEdge, Edge[EntityNode, Node]): ...


def _misuse_terminal_base_first() -> None:  # EXPECT-STATIC: terminal base before the abstract parent
    class TerminalFirst(Edge[EntityNode, MetricNode], ContainsEdge): ...


def _misuse_edge_kind_endpoint() -> None:  # EXPECT-STATIC: edge-kind endpoint category
    class Bogus(Edge[ContainsEdge, MetricNode]): ...


# --- runtime backstop for untyped/bypassed construction ------------------

def _runtime_backstop() -> None:
    try:
        endpoint(EntityNode)  # pyright: ignore[reportArgumentType]
        raise AssertionError("abstract component must be rejected at runtime")
    except TypeError:
        pass
    try:
        node_binding(
            target=EntityNode,  # pyright: ignore[reportArgumentType]
            build_key=MetricsView.title,
            properties=EntityNode(title=MetricsView.title),  # pyright: ignore[reportArgumentType]
        )
        raise AssertionError("binding an abstract component must be rejected")
    except TypeError:
        pass
    try:
        edge_binding(
            target=RelatesEdge,  # pyright: ignore[reportArgumentType]
            build_key=MetricsView.record_id,
            source_build_key=MetricsView.record_id,
            target_build_key=MetricsView.code,
            properties=RelatesEdge(note=MetricsView.title),
        )
        raise AssertionError("endpoint tokens must be required for abstract endpoints")
    except TypeError:
        pass
    try:
        edge_binding(
            target=RelatesEdge,  # pyright: ignore[reportArgumentType]
            source_node=endpoint(OutsideNode),
            target_node=endpoint(MetricNode),
            build_key=MetricsView.record_id,
            source_build_key=MetricsView.record_id,
            target_build_key=MetricsView.code,
            properties=RelatesEdge(note=MetricsView.title),
        )
        raise AssertionError("an endpoint outside the declared category must be rejected")
    except TypeError:
        pass
    try:
        class WrongTier(NodeTemplate):
            options = NodeOptions(name="identity")
        raise AssertionError("a template declaring non-template options must be rejected")
    except TypeError:
        pass
    try:
        class CrossKind(EdgeTemplate):
            options = NodeOptionsTemplate()
        raise AssertionError("a template declaring cross-kind options must be rejected")
    except TypeError:
        pass
    try:
        class Unwrapped(NodeTemplate):
            options = (AuditTrail(track="unwrapped"),)
        raise AssertionError("an un-wrapped template options value must be rejected")
    except TypeError:
        pass
    try:
        class Mislabeled(AbstractNode):
            options = NodeOptionsTemplate()
        raise AssertionError("an IR-visible class declaring template options must be rejected")
    except TypeError:
        pass
    try:
        class Widened(ContainsEdge, Edge[EntityNode, Node]):  # pyright: ignore[reportGeneralTypeIssues]
            ...
        raise AssertionError("endpoints widened past the abstract lineage must be rejected")
    except TypeError:
        pass
    try:
        class Leaf(ContainsEdge):
            ...
        raise AssertionError("an edge inheriting lineage without declaring endpoints must be rejected")
    except TypeError:
        pass
    try:
        class Undeclared(AbstractEdge):
            ...
        raise AssertionError("an edge declaring no endpoints must be rejected")
    except TypeError:
        pass
    try:
        # types.new_class bypasses the static node-side bound entirely
        types.new_class("EdgeKindBypass", (AbstractEdge[ContainsEdge, MetricNode],), {})  # pyright: ignore[reportInvalidTypeArguments]
        raise AssertionError("an edge-kind endpoint category must be rejected")
    except TypeError:
        pass
    # the canonical base order is checker-only: the preparation guard is
    # order-insensitive, so the flipped declaration passes the same predicate
    class TerminalFirst(Edge[EntityNode, MetricNode], ContainsEdge):  # pyright: ignore[reportGeneralTypeIssues]
        ...
    assert TerminalFirst._metadata["target"] is MetricNode


if __name__ == "__main__":
    del records_from_legacy, records_from_stream, metrics_from_view
    _mixin_proof()
    _runtime_backstop()
    print("OK")
