# Node/Edge Hierarchy and Category Endpoints — Temp Spec

Status: design agreed, not yet implemented. Working spec for
`feat/node-edge-polymorphism`; intended to fold into `KG_BUILD_SYSTEM_SPEC.md`
when implemented. The executable companion and proof of record is
`demo_endpoint_pattern.py` (§9).

## 1. Purpose

Topology inheritance is composition-only today: the terminal `Node`/`Edge`
class collapses the hierarchy so downstream processing cannot see it. This
extension:

1. introduces **abstract components** — first-class, IR-visible categories
   that concrete components specialize;
2. allows an **edge to connect node categories**, instantiating concrete
   endpoint pairs in bindings;
3. gives core (meta graph, later) and targets (e.g., Neo4j labels) a
   hierarchy to consume without changing aggregation or execution.

Principles held throughout:

- What the framework must see is declared with framework bases; everything
  else the MRO discovers is authoring freedom and stays invisible downstream.
- The edit-time (pyright) and runtime contracts are enforced by the same
  predicate; silent divergence between them is structurally impossible.
- Instantiation stays explicit in bindings. No synthesized components, no
  implicit cross products.

## 2. Public declaration model

Six public bases, all descending from one internal decorated root:

| Base | Role | Bindable | In IR |
|---|---|---|---|
| `NodeTemplate` / `EdgeTemplate` | inert property-mixin chain root | no | no |
| `AbstractNode` / `AbstractEdge[S, D]` | category; specialization target | no | yes (`abstract`) |
| `Node` / `Edge[S, D]` | concrete component | yes | yes |

The shared root carries `@dataclass_transform`, is internal, and is named
without graph semantics: **`_DeclarationBase`** ("declaration" is existing
framework vocabulary). The current public `GraphComponent` /
`GraphComponentOptions` names are withdrawn (§8); authors reference only the
six bases and keep using `NodeOptions` / `EdgeOptions` — no abstract flag, the
base class is the marker.

```python
class Audited(NodeTemplate):                      # sharing only — no graph link
    revision: PropertySlot[str] = property()

class EntityNode(AbstractNode):                   # category — graph-visible
    options = NodeOptions(annotations=(NodeLabel("Entity"),))
    title: PropertySlot[str] = property()

class RecordNode(Audited, EntityNode, Node):      # specializes entity
    city: PropertySlot[str] = property()

class ContainsEdge(AbstractEdge[EntityNode, EntityNode]): ...
class ContainsMetricEdge(Edge[EntityNode, MetricNode], ContainsEdge): ...
```

Inheritance from a template creates no graph relationship; inheritance from an
abstract base *is* the parent/child declaration. The decision rule for an
author is one question: must this exist in the graph? Yes — abstract base;
no — template.

## 3. Structural rules (enforced at class creation)

Both the abstract and concrete preparation hooks validate the full MRO, not
just direct bases, so violations fail at their earliest declaration:

- **R1 — one category slot.** At most one abstract component of the matching
  kind (node or edge) in the MRO; any number of matching-kind templates.
  Framework bases are excluded from the count. A diamond such as
  `class Both(Named, Sourced)` from two abstracts fails at `Both`, not at a
  later concrete class.
- **R2 — framework-lineage MRO.** Every MRO class (below the component,
  above `object`) must descend from `_DeclarationBase`. This mirrors
  pyright's `dataclass_transform` scoping rule, which was empirically
  established: constructor-field visibility follows the *chain root*, so a
  `NodeTemplate`-rooted chain with plain intermediates is fully visible, and
  a non-framework-rooted chain is silently invisible to pyright. Enforcing
  the same predicate at class creation converts that silent edit-time
  failure into an immediate declaration-site error.
- **R3 — kind pairing.** Node-side preparations accept only `NodeTemplate`
  lineage, edge-side only `EdgeTemplate`. Cross-kind property sharing uses
  two templates.

Consequences: the hierarchy is a tree (one parent), abstracts may not extend
concretes, and category errors raise with the redirect that maintains the
discipline ("class X has two abstract node bases — keep what it *is*, move
what it merely *has* to `NodeTemplate`"). Author-facing text speaks only in
public names.

**Why a tree, not a DAG.** One axis of meaning (the category chain: labels,
meta-graph edges, `parent`) plus N axes of invisible sharing (templates) is
the economy the whole model rests on; multiple category parents re-blur that
line and make merged category metadata (descriptions, annotations from the
losing MRO entry) silently lossy. Every multi-parent consumer would also
need newly specified canonical orderings for fingerprint determinism. The
constraint is also asymmetric in risk: tree → DAG is a compatible future
widening (`parent` becomes `parents`), DAG → tree is a breaking change.

## 4. Category endpoints and the binding layer

`Edge[S, D]` / `AbstractEdge[S, D]` accept node components — abstract or
concrete — as endpoint categories. One edge component covers all concrete
pairs actually bound in a build; the author pays only for pairs that exist.

`edge_binding` gains endpoint identity arguments, wrapped with `endpoint(...)`:

```python
@dataclass(frozen=True)
class Endpoint(Generic[N_co]):
    target: type[N_co]

def endpoint[N: Node](target: type[N]) -> Endpoint[N]: ...

def edge_binding(
    *,
    target: type[Edge[S, D]],
    source_node: Endpoint[S] | None,
    source_build_key: ValueExpression[Hashable],
    target_node: Endpoint[D] | None,
    target_build_key: ValueExpression[Hashable],
    build_key: ValueExpression[Hashable],
    properties: E,
): ...
```

`source_node` / `target_node` are required when the declared endpoint is
abstract, may be omitted when it is concrete (defaulting to the declared
component), and must resolve to the declared component itself when concrete
and supplied.

Rationale, each decision measured rather than assumed (see §9):

- **Not the class.** `source_node=RecordNode` cannot be fully checked:
  "descendant of S *and* concrete" needs an intersection with negation, which
  no Python checker expresses — `type[S]` always admits the abstract itself.
- **Not the node binding.** `source_node=record_binding` checks statically,
  but a component legitimately has multiple bindings from different sources;
  choosing one producer as the endpoint witness is meaningless, couples the
  edge to one producer's existence, and fails the moment a node has two
  bindings. Identity is per component; producers are per binding.
- **The wrapper.** `endpoint`'s `N: Node` bound makes an abstract class
  statically unable to become an endpoint, and covariance of the frozen
  wrapper enforces category membership by variance. The endpoint argument is
  then itself the witness that the component is declared; "must the namespace
  be instantiated" collapses into "does the argument exist."

Verified static behavior (demo, pyright): valid call with two `RecordNode`
producers in scope passes; abstract category, wrong category, and raw class
each fail statically; a bypassed runtime construction raises `TypeError`.

Two mechanical facts that are easy to regress: `Edge`'s endpoint type
parameters must stay **invariant** (covariant endpoints silently stop
detecting category violations — measured), and `Endpoint`'s covariant
parameter is bound to `_DeclarationBase` so it instantiates with abstract
categories. The PEP 695 bridging pattern (`def f[S, SC: S]`) is broken in
current pyright and must not be substituted.

`source_build_key` / `target_build_key` are unchanged: local scalar
expressions over the edge's own product. Expression identity does not
survive projection indirection (the reference project's edge keys are
projection fields of a different IR than the node bindings' keys), so key
cross-checking stays out of v1 (§7).

Blueprint validation (second line, precise wording): no binding may target
an abstract component; a supplied endpoint must be concrete, a descendant of
the declared endpoint category via the IR parent chain, and covered by at
least one node binding in the blueprint.

## 5. Blueprint and IR

- `ComponentIR` gains `abstract: bool = False` and `parent: str | None`
  (nearest abstract ancestor's symbol ID). Authoring and IR share the word.
- `BLUEPRINT_SCHEMA_VERSION` 2 → 3: semantics, not cosmetics. Codecs remain
  deterministic and round-trippable; fingerprints cover the new fields.
- The blueprint component closure walks binding targets, edge endpoints, and
  their full abstract chains, so unreferenced categories still enter the IR.
  Abstract names use the existing effective-name rule (strip one
  `Node`/`Edge` suffix).
- Internal "final" wording (`is_final_component`, related messages) migrates
  to "concrete".
- Core aggregation, workflow assembly, and execution are untouched;
  templates never enter the IR.

## 6. Staged: build-key namespacing in core

Not in this branch; the binding shape is designed to make it an
author-invisible follow-up. Today namespaces are hand-written into key
values (`record::…`) and the Neo4j "ID space" is decorative: imports resolve
endpoints by global value. Stage 2 moves namespace composition into core:
global identity = the component's endpoint identity ⊕ the local key value,
for node bindings and edge endpoints symmetrically. Cross-type endpoint
matches then become
unmatchable even against pathological data, the prefix discipline disappears
from authoring, and the remaining author duty shrinks to disjoint value
ranges within one's own components. `source_node`/`target_node` are the seam
that carries this migration without a binding-syntax change.

## 7. Non-goals

- Meta-graph generation (core) and Neo4j multi-label emission (target):
  later consumers of the same IR data, target-owned vocabulary as usual.
- DAG hierarchies, multi-parent categories.
- Synthesizing concrete edge subclasses per bound pair — explicit bindings
  already name every pair that exists.
- Binding abstract components or endpoints.
- Value-level cross-product key equality checks (data-contract territory;
  the expression/provenance rules already pin wiring).

## 8. Delivery notes

Breaking (pre-1.0 velocity): `GraphComponent` / `GraphComponentOptions` are
withdrawn from the public surface; blueprint schema bumps to v3. `Node` and
`Edge` authoring semantics are otherwise unchanged — the feature is purely
additive for existing builds. Preparation hooks follow the cooperative
super-first + kind-guard pattern already used by `TableTemplate` / `Table`.

Testing contracts: runtime unit tests for R1–R3 (including the diamond case
and the mixin-redirect message), endpoint factory guards, blueprint endpoint
validation, codec round-trip and fingerprint change; one
`tests/typecheck_topology_hierarchy.py` static-contract file for the
positive side only — pyright has no expect-error directive, so the negative
side is owned by runtime tests and pinned by the demo.

## 9. Model reference: `demo_endpoint_pattern.py`

The demo is the executable proof of the pattern and part of this spec. It
shows: the six-base shape (inert stand-in templates/abstracts under the real
decorated root), one component with two producers, a choice-free
`endpoint(...)` wrapper, and exactly three intended static misuses
(abstract category, wrong category, raw class) plus a runtime backstop.
Expected: `uv run pyright demo_endpoint_pattern.py` reports exactly 3 errors
inside the `_misuse_*` block; `uv run python demo_endpoint_pattern.py`
prints `OK`. Implementation replaces its stand-ins (`EdgeBase`, inert
`AbstractNode`) with the real machinery; keep the demo until the real tests
subsume it, then fold its cases into §8.
