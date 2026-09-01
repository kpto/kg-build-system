# Node/Edge Hierarchy and Category Endpoints — Extension Spec

Status: implemented for `feat/node-edge-polymorphism`; folded into
`KG_BUILD_SYSTEM_SPEC.md` (§7 topology hierarchy and category endpoints, §10
blueprint schema v3). This document remains the detailed record of the model.

## 1. Public surface

Six public bases under one internal `@dataclass_transform` root,
**`_TopologyDeclarationBase`** (renamed from `GraphComponent`;
`GraphComponent` and `GraphComponentOptions` are withdrawn). Roots do not
generalize across domains — each authoring domain carries its own.

| Base | Tier | Bindable | In IR | Endpoint params |
|---|---|---|---|---|
| `NodeTemplate` / `EdgeTemplate` | mixin — share properties + annotations | no | no | — |
| `AbstractNode` / `AbstractEdge[S, D]` | category — graph-visible parent | no | yes (`abstract`) | covariant (edge side) |
| `Node` / `Edge[S, D]` | concrete component | yes | yes | invariant (edge side) |

- `Edge[S, D]` derives from `AbstractEdge[S, D]`; this derivation is what
  makes endpoint descent checkable. `Node` and `AbstractNode` are siblings.
- `AbstractNode` and `Node` share an internal **node-side root**; every
  endpoint-category parameter is bound to it, so an edge-kind type argument
  is statically impossible.
- Template inheritance shares; category inheritance *is* the graph
  parent/child declaration. Templates never enter the IR.
- The hierarchy is a tree: one category parent, any number of mixins.

## 2. Declaration shape

Canonical base order — normative: **templates, abstract parents, terminal
base last**. The order is load-bearing: with re-declared endpoints under an
abstract parent, a terminal base declared first fails the checker even when
the endpoints are valid (§6).

```python
class Audited(NodeTemplate):
    options = NodeOptionsTemplate(annotations=(AuditTrail(track="audit"),))
    revision: PropertySlot[str] = property()

class EntityNode(AbstractNode):
    options = NodeOptions(annotations=(NodeLabel("Entity"),))
    title: PropertySlot[str] = property()

class RecordNode(Audited, EntityNode, Node): ...

class ContainsEdge(Weighted, AbstractEdge[EntityNode, EntityNode]):
    options = EdgeOptions(annotations=(EdgeLabel("CONTAINS"),))

class ContainsMetricEdge(ContainsEdge, Edge[EntityNode, MetricNode]): ...
# descended; target category narrowed EntityNode -> MetricNode
```

## 3. Options

Every tier declares `options`; the options type identifies the tier.

| Tier | Options type | Fields |
|---|---|---|
| `AbstractNode` / `Node` | `NodeOptions` | name, description, annotations |
| `AbstractEdge` / `Edge` | `EdgeOptions` | name, description, annotations |
| `NodeTemplate` lineage | `NodeOptionsTemplate` | annotations only |
| `EdgeTemplate` lineage | `EdgeOptionsTemplate` | annotations only |

Effective resolution for an IR-visible class, over its framework lineage:

| Field | Effective value |
|---|---|
| name | own `options.name`, else own class name with the tier suffix stripped (`AbstractNode`/`AbstractEdge` for categories, `Node`/`Edge` for concrete) — never mixed |
| description | own `options.description`, else own docstring — never inherited; resolved at class creation |
| annotations | template options in C3 order — each template exactly once, collected wherever it enters the lineage, category parents included — then own `options.annotations` |

- A category's own options stay on the category's IR entry, reachable
  through `parent`; template annotations flow through it to descendants.
- Raise at class creation, with the redirect, for: a template given real
  options, cross-kind template options, or an un-wrapped sequence; an
  IR-visible class given template options; a kind-mismatched options type.
- Label uniqueness is enforced against the effective set at class creation.
- Sharing across a *set* of declarations is value sharing, not lineage:
  declare one frozen annotation tuple and reference it in each
  declaration's own `options` — content declared once, nothing flows to
  descendants. A template annotation is a rule over lineage; a tuple is an
  enumeration of present entries.

## 4. Structural rules (class creation, full MRO)

- **R1 — one category slot.** At most one *direct* abstract parent of the
  matching kind; any number of matching-kind templates. Abstract chains are
  fine — each class has one category parent and the parent links form the
  tree. Two abstract bases among the direct bases fail at the diamond, not
  at a later concrete class.
- **R2 — framework-lineage MRO.** Every MRO class between the declaration and
  `object` descends from `_TopologyDeclarationBase` — pyright's
  `dataclass_transform` scope follows the chain root.
- **R3 — kind pairing.** Node-side preparations accept only `NodeTemplate`
  lineage, edge-side only `EdgeTemplate`; the options type is kind-paired at
  every tier.
- **R4 — endpoint inheritance and descent.** An edge inherits its endpoint
  categories from its abstract edge parent, and inheriting an abstract edge
  without re-declaring endpoints keeps the class abstract. Re-declaration is
  optional and only narrows: each re-declared endpoint equals or descends from
  every abstract edge ancestor's, so an abstract child may narrow a category
  and a concrete terminal base may narrow it further. An edge with neither a
  declaration nor an endpoint-bearing abstract parent fails at class creation.
  The checker enforces the narrowing predicate from base-class consistency;
  the preparation walk enforces the same predicate at class creation,
  base-order insensitively, and catches bypassed edge-kind categories.

## 5. Category endpoints and binding

```python
@dataclass(frozen=True)
class Endpoint(Generic[N_co]):            # N_co: node-side root, covariant
    target: type[N_co]

def endpoint[N: Node](target: type[N]) -> Endpoint[N]: ...   # concrete only

@overload
def edge_binding[S: Node, D: Node](
    *, target: type[Edge[S, D]], source_build_key: ..., target_build_key: ...,
    build_key: ..., properties: E,
): ...                                                        # both omittable
@overload
def edge_binding[S: Node, DC: NodeSide](
    *, target: type[Edge[S, DC]], target_node: Endpoint[DC],
    source_build_key: ..., target_build_key: ..., build_key: ..., properties: E,
): ...                                            # token required per abstract side
# mirrored category-source and both-category overloads; only independent
# per-overload typevars — no bridging
```

- Each endpoint token is required exactly when its declared endpoint,
  inferred from `target`, is abstract. Covariance of `Endpoint` enforces
  category membership; an explicit token naming a concrete declared
  endpoint stays valid.
- Identity is per component, not per producer: endpoints reference the
  component; each binding names the endpoint pair it uses, never the cross
  product of the declared categories. No synthesized components, no
  implicit cross products, no binding of abstracts.
- Blueprint validation: a supplied endpoint is concrete and a descendant of
  the declared category via the IR parent chain. Whether some node binding
  produces that endpoint is not a blueprint concern.

## 6. Measured facts (regression guards)

- `Edge` endpoint parameters stay **invariant** — covariant ones silently
  stop detecting category violations.
- `AbstractEdge` endpoint parameters stay **covariant** — invariant ones
  reject the descent case: descent becomes unrepresentable.
- Endpoint-category parameters, including `Endpoint`'s, bind to the
  **node-side root** — `_TopologyDeclarationBase` would admit edge-kind
  categories.
- Base order is load-bearing for re-declared narrowed endpoints:
  parent-before-terminal is the only accepted order statically; the runtime
  predicate is order-insensitive.
- Rejected mechanisms: constrained typevars (`TypeVar("S", AbstractNode,
  Node)`) — break binding inference and the order guard; PEP 695 bridging
  `def f[S, SC: S]` — broken in pyright; reading `__orig_bases__` by
  attribute lookup — it is inherited through the MRO, use `cls.__dict__`;
  reading `__doc__` after class creation — `dataclass()` stamps a generated
  signature into a docstring-less class's `__doc__`, so own-description must
  be resolved during preparation.

## 7. Blueprint and IR

- `ComponentIR` gains `abstract: bool = False` and `parent: str | None`
  (nearest abstract ancestor's symbol ID). Blueprint schema v2 → v3;
  codecs stay deterministic; fingerprints cover the new fields.
- The component closure walks binding targets, edge endpoints, and their
  full abstract chains; unreferenced categories still enter the IR.
  Abstract names use the existing suffix-stripping rule; internal "final"
  wording migrates to "concrete".
- Component annotations enter the IR as the effective set (§3). Core
  aggregation, workflow assembly, and execution are untouched.
- Staged, no authoring change: build-key namespacing composed from the
  endpoint identity inside core (`source_node`/`target_node` is the seam).
  Until targets consume the per-binding endpoint identity, a target that
  maps edge endpoints onto node ID spaces (Neo4j) keys off the edge's
  declared endpoints and rejects a bound edge whose declared endpoints are
  abstract; category-endpoint edges are consumed by targets that take the
  per-binding view (file output).

## 8. Enforcement layers

| Layer | Enforces |
|---|---|
| Checker (pyright) | token optionality matrix; endpoint descent via invariant→covariant base consistency; node-side endpoint bound; canonical base order |
| Class creation (preparation walk) | R1–R4, options-tier guards, label conflicts, description resolution — same predicates, order-insensitive, bypass-proof |
| Blueprint validation | no abstract binding targets; endpoints concrete and descended |

## 9. Non-goals

Meta-graph generation and Neo4j multi-label emission (later consumers of the
same IR data) · DAG categories · synthesized edge subclasses per bound pair
· binding abstract components or endpoints · value-level cross-product key
equality checks.

## 10. Model reference

```python
NodeSide = AbstractNode | Node      # stands in for the internal node-side root
S_co = TypeVar("S_co", bound=NodeSide, covariant=True); D_co = ...
S = TypeVar("S", bound=NodeSide);   D = TypeVar("D", bound=NodeSide)

class AbstractEdge(_TopologyDeclarationBase, Generic[S_co, D_co]):
    """Category edge; covariant parameters let children descend."""
class Edge(AbstractEdge[S, D], Generic[S, D]):
    """Concrete edge; invariant parameters, as the binding matrix requires."""

# Preparation guards at class creation (order-insensitive, same predicates):
#   endpoint categories are node-side
#   own spec equal-or-descended from every inherited spec
#   a bare edge inherits its parent's endpoints; with no lineage it must declare

# Valid binding shapes (RelatesEdge[Entity,Entity], ContainsMetricEdge descended,
# DirectEdge[Record,Metric], MixedEdge[Entity,Metric]):
edge_binding(target=RelatesEdge, source_node=endpoint(RecordNode), ...,
             target_node=endpoint(MetricNode), ...)              # both tokens
edge_binding(target=ContainsMetricEdge, source_node=endpoint(RecordNode), ...)
edge_binding(target=DirectEdge, ...)                             # both omitted
edge_binding(target=DirectEdge, source_node=endpoint(RecordNode),
             target_node=endpoint(MetricNode), ...)              # explicit stay valid
edge_binding(target=MixedEdge, source_node=endpoint(RecordNode), ...)
```

The eight static misuses the model must reject at the checker: abstract
endpoint passed to `endpoint(...)`, endpoint outside the declared category,
raw class instead of an endpoint token, tokens omitted on an
abstract-declared side (fully abstract and mixed), an endpoint widened past
its abstract parent, a terminal base declared before its abstract parent,
and an edge-kind endpoint category. The runtime backstops the same
predicates for bypassed construction.

## 11. Delivery

- Breaking (pre-1.0): `GraphComponent` / `GraphComponentOptions` withdrawn;
  blueprint schema v3. Existing authoring is otherwise unchanged — purely
  additive.
- Tests: runtime unit tests for R1–R4, options-tier semantics, and endpoint
  descent (all layers of §8); a positive-side static typecheck file
  (`tests/typecheck_topology_hierarchy.py`). The checker-side negative
  matrix (token misuse, widened endpoints, reversed base order, edge-kind
  categories) was exercised by the endpoint-pattern demo, since removed;
  no repo artifact owns it today.
