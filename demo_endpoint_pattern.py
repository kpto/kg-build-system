"""Proof of the abstract endpoint binding pattern: endpoints reference a
component's identity, not one of its producers.

The overload matrix keys each endpoint token on the concreteness of the
declared endpoint: the typevar inferred from ``target`` is bound to ``Node``
where the token is omittable and to the category base where it is required.
No typevar bridging is involved; each overload uses independent typevars.

The file also proves the typed-options-per-tier contract: every tier
declares ``options`` and the options type identifies the tier — the
IR-visible stand-in bases carry ``NodeOptions`` / ``EdgeOptions``, while
a template carries only the kind-matched, annotations-only
``options = NodeOptionsTemplate(...)`` / ``EdgeOptionsTemplate(...)``
value whose annotations mix into the declaring class, keeping plain
class attributes reserved for property declarations. A category's
options stay on the category, description is never inherited, and a
template given non-template or cross-kind options, an un-wrapped
sequence, or an IR-visible class given template options all raise at
class creation. The template hooks below are stand-ins for the real
preparation walk, which records each class's own contribution and
resolves it in one pass.

Expected pyright result: exactly 5 errors, all inside the `_misuse_*` block.
Expected runtime result: prints OK.
"""
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, Sequence, TypeVar, overload

from kg_build_system import (
    Annotation, EdgeOptions, Field, Node, NodeLabel, NodeOptions, PropertySlot,
    Table, field, node_binding, property,
)
from kg_build_system.annotations import annotation_tuple
from kg_build_system.expressions import ValueExpression
from kg_build_system.topology import GraphComponent

N_co = TypeVar("N_co", bound=GraphComponent, covariant=True)
S = TypeVar("S", bound=GraphComponent)
D = TypeVar("D", bound=GraphComponent)


@dataclass(frozen=True)
class AuditTrail(Annotation):
    """Author-defined annotation used to trace options flow."""

    namespace = "demo_endpoint_pattern"
    annotation_id = "audit_trail"

    track: str


@dataclass(frozen=True)
class NodeOptionsTemplate:
    """Node-side template options; stand-in for the real type."""

    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True)
class EdgeOptionsTemplate:
    """Edge-side template options; stand-in for the real type."""

    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


def _record_own_options(cls: Any, kind: str) -> None:
    """Stand-in for the real preparation walk's own-contribution recording.

    The real hook prepares every base; templates are shown here because
    they are the mixin side. The options type identifies the tier: a
    template accepts only its kind's template options, which carry no
    identity fields, so the identity fields have no syntax here.
    ``options`` is typed ``Any`` on the stand-in roots so misplacement
    stays a class-creation error rather than changing the demo's static
    error count.
    """
    cls._own_annotations = ()
    if "options" not in vars(cls):
        return
    template_options = NodeOptionsTemplate if kind == "node" else EdgeOptionsTemplate
    options = vars(cls)["options"]
    if isinstance(options, template_options):
        cls._own_annotations = tuple(options.annotations)
        return
    raise TypeError(
        f"{cls.__name__} is a {kind} template: its options must be a "
        f"{template_options.__name__} value — wrap it: "
        f"`options = {template_options.__name__}(annotations=(...))`"
    )


def _reject_template_options(cls: Any, own_options: type) -> None:
    """Stand-in for the real walk's tier guard: IR-visible classes own real options."""
    if isinstance(vars(cls).get("options"), (NodeOptionsTemplate, EdgeOptionsTemplate)):
        raise TypeError(
            f"{cls.__name__} is an IR-visible declaration: declare "
            f"{own_options.__name__}, not template options"
        )


class NodeTemplate(GraphComponent):
    """Inert property-and-options mixin root."""

    options: ClassVar[Any] = NodeOptionsTemplate()
    _own_annotations: ClassVar[tuple[Annotation, ...]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _record_own_options(cls, "node")


class EdgeTemplate(GraphComponent):
    """Inert edge property-and-options mixin root."""

    options: ClassVar[Any] = EdgeOptionsTemplate()
    _own_annotations: ClassVar[tuple[Annotation, ...]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _record_own_options(cls, "edge")


class AbstractNode(GraphComponent):
    """Category base."""

    options: ClassVar[Any] = NodeOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _reject_template_options(cls, NodeOptions)


@dataclass(frozen=True)
class Endpoint(Generic[N_co]):
    target: type[N_co]


def endpoint[N: Node](target: type[N]) -> Endpoint[N]:
    if vars(target).get("_component_declaration_kind") != "node":
        raise TypeError(f"'{target.__name__}' is not a concrete node")
    return Endpoint(target)


class EdgeBase(GraphComponent, Generic[S, D]):
    """Stand-in for Edge; real Edge relaxes its endpoint bound to categories."""

    options: ClassVar[Any] = EdgeOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _reject_template_options(cls, EdgeOptions)


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


class ContainsEdge(Weighted, EdgeBase[EntityNode, EntityNode]):
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

# endpoint coverage: every endpoint a binding names has a producer
metrics_from_view = node_binding(
    target=MetricNode,
    build_key=MetricsView.code.expression.prepend("metric::"),
    properties=MetricNode(title=MetricsView.title, code=MetricsView.code),
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


# --- options-tier flow contract ------------------------------------------

def _effective_options(cls: type) -> tuple[Annotation, ...]:
    """Stand-in for the real preparation walk's effective-annotation view.

    Each class contributes only its own declared annotations, so a shared
    template contributes exactly once and an IR-visible ancestor's options
    (which live on its own entry) never mix into a child.
    """
    own = vars(cls).get("options")
    own_annotations = () if own is None else tuple(own.annotations)
    inherited = tuple(
        annotation
        for base in reversed(cls.__mro__[1:])
        for annotation in vars(base).get("_own_annotations", ())
    )
    return inherited + own_annotations


def _effective_description(cls: type) -> str | None:
    """Effective description — own only; descriptions are never inherited."""
    own = vars(cls).get("options")
    if own is not None and own.description is not None:
        return own.description
    if "_component_declaration_kind" in vars(cls):
        # The real preparation hook resolved the author docstring before
        # dataclass() stamped a generated __init__ signature onto classes
        # that have no docstring; a post-creation reader must use that.
        return vars(cls).get("_metadata", {}).get("description")
    return vars(cls).get("__doc__") or None


def _mixin_proof() -> None:
    # template options mix into every declaring class
    assert _effective_options(RecordNode) == (AuditTrail(track="record"),)
    assert _effective_options(ContainsEdge) == (AuditTrail(track="edge"),)
    # category options stay on the category's own entry
    assert _effective_options(EntityNode) == (NodeLabel("Entity"),)
    assert _effective_options(MetricNode) == ()
    assert _effective_options(OutsideNode) == ()
    # a template mixed via a category still reaches concrete descendants,
    # while the category's own annotation stays behind on the category
    assert _effective_options(SourcedNode) == (AuditTrail(track="sourced"),)
    assert _effective_options(ArtifactNode) == (AuditTrail(track="sourced"),)
    # description is own-declared or silent — never inherited from a
    # template, a category, or anywhere else
    assert _effective_description(RecordNode) is None
    assert _effective_description(MetricNode) is None
    assert _effective_description(EntityNode) is None
    assert _effective_description(ContainsEdge) is None
    assert _effective_description(DirectEdge) == (
        "Both endpoints concrete: both tokens omittable."
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


if __name__ == "__main__":
    del records_from_legacy, records_from_stream, metrics_from_view
    _mixin_proof()
    _runtime_backstop()
    print("OK")
