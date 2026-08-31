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
| `NodeTemplate` / `EdgeTemplate` | inert property-and-options mixin chain root | no | no |
| `AbstractNode` / `AbstractEdge[S, D]` | category; specialization target | no | yes (`abstract`) |
| `Node` / `Edge[S, D]` | concrete component | yes | yes |

The six bases share one internal decorated root:
**`_TopologyDeclarationBase`** — the carrier of the domain's
`@dataclass_transform(field_specifiers=(property,), kw_only_default=True)`,
which is what gives the property declarations their edit-time synthesized
constructor for binding input and, per R2, keeps template- and
category-mixed declarations visible in it. Decorated roots do not
generalize across domains: each authoring domain carries its own root with
its own declaration protocol (the table domain has no transform at all),
and there is no framework-wide declaration root — PEP 681's inheritance
would leak one domain's transform semantics into an unrelated chain. The
current public `GraphComponent` /
`GraphComponentOptions` names are withdrawn (§8); authors reference only the
six bases. Every tier declares `options`, and the options type identifies the
tier — `NodeOptions` / `EdgeOptions` on the IR-visible bases, kind-matched
`NodeOptionsTemplate` / `EdgeOptionsTemplate` on templates
— no abstract flag, the base class is the marker.

On the edge side the concrete base is declared above its abstract
counterpart: `Edge[S, D]` derives from `AbstractEdge[S, D]` — this
derivation is what makes endpoint descent checkable (§4). On the node
side, `Node` and `AbstractNode` are siblings under the node-side root.
Base order is canonical
and normative — template, abstract parents, terminal base last,
mirroring the node side — because the order is load-bearing for an edge
that re-declares endpoints under an abstract parent: the checker
rejects the terminal base declared first (§4).

```python
class Audited(NodeTemplate):                      # sharing only — no graph link
    options = NodeOptionsTemplate(annotations=(AuditTrail(),))  # AuditTrail is author-defined
    revision: PropertySlot[str] = property()

class EntityNode(AbstractNode):                   # category — graph-visible
    options = NodeOptions(annotations=(NodeLabel("Entity"),))
    title: PropertySlot[str] = property()

class RecordNode(Audited, EntityNode, Node):      # specializes entity
    city: PropertySlot[str] = property()

class ContainsEdge(AbstractEdge[EntityNode, EntityNode]): ...
class ContainsMetricEdge(ContainsEdge, Edge[EntityNode, MetricNode]): ...
```

Inheritance from a template creates no graph relationship; inheritance from an
abstract base *is* the parent/child declaration. The decision rule for an
author is one question: must this exist in the graph? Yes — abstract base;
no — template.

### One `options` attribute, typed per tier

Every tier declares `options`; the options *type* identifies the tier.
The four IR-visible bases carry kind-matched options by side:
`NodeOptions` on `AbstractNode` / `Node`, `EdgeOptions` on the edge side.
A mismatch raises at class creation beside the R3 lineage guard.
`NodeOptions` and `EdgeOptions` remain the only options types on
IR-visible declarations — the base class is still the abstract marker.

Templates also declare `options`, but only with a kind-matched template
type: `NodeOptionsTemplate` on `NodeTemplate` lineage,
`EdgeOptionsTemplate` on `EdgeTemplate` lineage. Options still configure
the declaration that holds them — the type gates which tier may hold
them, supplies constructor guidance, and keeps plain class attributes
reserved for property declarations; meta enters a declaration only
through the named special attribute:

```python
class Audited(NodeTemplate):
    options = NodeOptionsTemplate(annotations=(AuditTrail(track="audit"),))
    revision: PropertySlot[str] = property()
```

The template options types are frozen values whose only field is
`annotations: Sequence[Annotation]`, normalized like every options
field — `options.annotations` carries one meaning in every home. An
un-wrapped bare sequence is rejected. They hold no `name` or
`description`, so the identity fields have no template syntax to set —
the misuse is unrepresentable, not guarded. Misplacement is a
declaration-site error in both directions — a template given
`NodeOptions` / `EdgeOptions`, cross-kind template options, or an
un-wrapped sequence raises toward its kind's template options, and an
IR-visible class given template options raises toward its kind's real
options type. The withdrawn `GraphComponentOptions` was the only
vehicle for mixin metadata on intermediate classes; template options
replace it as the first-class channel.

Each IR-visible class (abstract or concrete) resolves its effective
options over its framework lineage:

```text
field          effective value
name           own options.name, else own class name — never mixed
               (template options carry no name)
description    own options.description, else own docstring — never mixed
               or inherited; resolved at class creation (see the
               docstring-stamp note in §8)
annotations    template options in C3 order — collected wherever they
               enter the lineage, through a category parent included, and
               each template contributing exactly once even when both the
               category and the child name it, so a shared template in a
               template diamond is safe — then own options.annotations
```

Description stays out of template options for the same reason it stays out of
identity: it is a single prose slot that cannot merge without silence —
two mixing templates with descriptions would drop one entry invisibly,
the lossy merge the tree rule exists to prevent — and a facet
description stamped onto every component that mixes the template is
wrong prose about the component. Family-wide prose belongs to the
category's own description, which consumers reach through the `parent`
chain; a template documents itself with its docstring.

A category parent likewise contributes nothing to a child's effective
options: the category's options *are* its own IR entry, reachable from
children through `parent`. Refusing its own contribution does not make a
category a wall — template lineage entering through it still mixes into
descendants; the walk skips the category's own options, not what passes
through it. Template annotations entering through a category are the category's contract
to its members, like inherited properties. Stopping templates at category
boundaries was rejected: it splits one intent across two declaration sites,
turns a forgotten restatement into silently lost metadata, and would be a
false protection while category membership already propagates structurally
through `parent`. The asymmetry with templates is structural, not
stylistic — a template is invisible in the IR, so its annotations reach the
IR only by mixing, while an abstract already has an IR home. Label
uniqueness ("at most one matching annotation", main spec §7) is therefore
enforced at class creation against the effective set — own plus template
contributions — so a category label never conflicts with a child's own, and
hierarchy consumers (meta graph, multi-label targets) compose own, mixed,
and chain metadata without any validity change.

Sharing across a *set* of declarations is value sharing, not lineage. To
tag N categories, or N concrete components, with the same annotation
without flowing anything to descendants, declare one frozen tuple and
reference it in each declaration's own options:

```python
ONTOLOGY = (OwlClass("Class"),)

class EntityNode(AbstractNode):
    options = NodeOptions(annotations=(*ONTOLOGY, NodeLabel("Entity")))

class EventNode(AbstractNode):
    options = NodeOptions(annotations=(*ONTOLOGY, NodeLabel("Event")))
```

Each entry holds the annotation as its own; the content is declared once
and nothing mixes elsewhere, because annotations are frozen values
serialised and fingerprinted per entry. The contrast is rule versus
enumeration: a tuple lists present entries, while a template annotation is
a rule over lineage — every member now or later, through a category or by
direct mixing, carries the mixed annotations as a consequence of its lineage choice,
and a template's annotations travel with its properties so the facet
describing them cannot drift. A "stops here" template variant is
rejected: flow is the entire meaning of a template, and an in-between
sharing channel would re-blur the template/category axis exactly as the
withdrawn `GraphComponentOptions` did.

## 3. Structural rules (enforced at class creation)

Both the abstract and concrete preparation hooks validate the full MRO, not
just direct bases, so violations fail at their earliest declaration:

- **R1 — one category slot.** At most one abstract component of the matching
  kind (node or edge) in the MRO; any number of matching-kind templates.
  Framework bases are excluded from the count. A diamond such as
  `class Both(Alive, Classified)` from two abstracts fails at `Both`, not at a
  later concrete class.
- **R2 — framework-lineage MRO.** Every MRO class (below the component,
  above `object`) must descend from `_TopologyDeclarationBase`. This mirrors
  pyright's `dataclass_transform` scoping rule, which was empirically
  established: constructor-field visibility follows the *chain root*, so a
  `NodeTemplate`-rooted chain with plain intermediates is fully visible, and
  a non-framework-rooted chain is silently invisible to pyright. Enforcing
  the same predicate at class creation converts that silent edit-time
  failure into an immediate declaration-site error.
- **R3 — kind pairing.** Node-side preparations accept only `NodeTemplate`
  lineage, edge-side only `EdgeTemplate`. Cross-kind property sharing uses
  two templates. The options kind guard applies at every tier —
  `NodeOptions` node-side, `EdgeOptions` edge-side on IR-visible bases;
  `NodeOptionsTemplate` / `EdgeOptionsTemplate` on their matching
  template lineage (§2).
- **R4 — endpoint descent.** Every edge declaration — abstract or
  concrete — states its endpoint categories explicitly, and each
  re-declared endpoint must equal or
  descend from every abstract edge ancestor's declared endpoint. The
  checker enforces this at edit time from base-class consistency (§4);
  the preparation walk enforces the same `issubclass` predicate at
  class creation, base-order insensitively, and also catches what the
  checker cannot see — an edge inheriting endpoint lineage without
  re-declaring it, or declaring no endpoints at all.

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
An edge descended under an abstract edge — concrete or abstract —
re-declares its endpoints through its terminal base specialization, and
each re-declared endpoint must
equal or descend from the parent's declared category (R4). Descent is
statically checkable because `AbstractEdge`'s endpoint parameters are
covariant while `Edge`'s stay invariant: the child's narrower
specialization through `Edge` stays subtype-compatible with the parent's
pinned specialization, and pyright's base-consistency rule rejects every
incompatible re-declaration at the declaration site (measured).

`edge_binding` gains endpoint identity arguments, wrapped with `endpoint(...)`,
as an overload matrix that makes each token required exactly when its declared
endpoint is abstract:

```python
@dataclass(frozen=True)
class Endpoint(Generic[N_co]):
    target: type[N_co]

def endpoint[N: Node](target: type[N]) -> Endpoint[N]: ...

@overload
def edge_binding[S: Node, D: Node](
    *, target: type[Edge[S, D]], source_build_key: ...,
    target_build_key: ..., build_key: ..., properties: E,
): ...  # both sides concrete: tokens omittable
@overload
def edge_binding[S: Node, DC](  # DC: node-side category base
    *, target: type[Edge[S, DC]], source_build_key: ...,
    target_node: Endpoint[DC], target_build_key: ...,
    build_key: ..., properties: E,
): ...  # concrete source, category target
@overload
def edge_binding[SC, D: Node](  # SC: node-side category base
    *, target: type[Edge[SC, D]], source_node: Endpoint[SC],
    source_build_key: ..., target_build_key: ...,
    build_key: ..., properties: E,
): ...  # category source, concrete target
@overload
def edge_binding[SC, DC](  # both: node-side category base
    *, target: type[Edge[SC, DC]], source_node: Endpoint[SC],
    source_build_key: ..., target_node: Endpoint[DC],
    target_build_key: ..., build_key: ..., properties: E,
): ...  # both sides category
```

Each endpoint slot appears in exactly the overloads where its side's typevar,
inferred from `target`, is bound to the category base rather than to `Node`.
An abstract declared endpoint cannot satisfy the `Node` bound, so the call
falls to an overload whose signature demands the token — the same
concreteness predicate that gates the `endpoint(...)` factory and the runtime
guard, with only independent per-overload typevars (the banned bridging
pattern is not involved). A supplied endpoint must resolve to the declared
component itself when concrete — explicit tokens naming it stay valid — and
to a concrete descendant when the declaration is abstract; the runtime
implementation enforces the identical rule for bypassed callers.

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

Verified static behavior (demo, pyright): valid calls pass for a concrete
edge over two abstract categories with both tokens while two `RecordNode`
producers are in scope, for a descended edge with a token only on its
remaining category side, for a
fully concrete edge with both tokens omitted, for a concrete edge with
explicit tokens naming the declared components, and for a mixed edge with a
token only on the category side; abstract category, wrong category, raw
class, an omitted token on a category-declared side, a terminal base whose
endpoint widens past the abstract parent, a terminal base declared
before its abstract parent, and an edge-kind endpoint category each fail statically;
a bypassed runtime construction raises `TypeError`.

Three mechanical facts that are easy to regress: `Edge`'s endpoint type
parameters must stay **invariant** (covariant endpoints silently stop
detecting category violations — measured); `AbstractEdge`'s endpoint
parameters must stay **covariant** (with invariant parameters pyright
rejects the descent case too — endpoint descent becomes unrepresentable —
measured); and every endpoint-category parameter — `Edge`/`AbstractEdge`
endpoint parameters and `Endpoint`'s parameter — is bound to the
**node-side root**, an internal base shared by `AbstractNode` and `Node`
(`_TopologyDeclarationBase` is too loose: it would admit edge-kind categories).
The bound instantiates with abstract node categories and makes an
edge-kind type argument statically impossible. Constrained typevars
(`TypeVar("S", AbstractNode, Node)`) were measured and rejected as the
mechanism: they break `type[Edge[S, D]]` inference for the binding matrix
and silently disable the base-consistency order guard — they must not be
substituted. Base order is load-bearing exactly where lineage narrowing is
involved: the abstract parent must precede the terminal `Edge[...]` base,
and a terminal-first declaration fails the checker even with valid
endpoints (measured) — which is what makes the canonical
template → abstract → terminal-last order normative. The PEP 695 bridging
pattern (`def f[S, SC: S]`) is broken in
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
- Component annotations enter the IR as the effective set of §2 — own plus
  template-mixed; category contributions stay on the category's entry and
  are reachable only through `parent`. Names and descriptions follow the
  same options rules.
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
The preparation walk records each class's *own* `options` — the options
type identifies the tier — and the effective view resolves them in a single
C3 pass; the current
accumulate-and-append annotation merge double-counts a shared template once
template diamonds are legal. Own-description resolution must read the author
docstring during preparation: on current CPython, `dataclass()` stamps a
generated `__init__` signature into the `__doc__` of a docstring-less class
(measured; the demo's stand-in walk was misled by exactly this stamp), so a
post-creation docstring read silently reports a signature as a description.

Testing contracts: runtime unit tests for R1–R4 (including the diamond case
and the mixin-redirect message), endpoint factory and omitted-token guards
(static overload matrix plus the runtime backstop), options-tier
semantics (template options annotations reach the abstract's and concrete's effective
sets, including a template entering through a category parent; a template
given real options, cross-kind template options, or an un-wrapped
sequence, and an IR-visible class given template options, each raise with
the redirect; a shared template
in a diamond contributes once; cross-kind options raise on IR-visible
bases; category annotations never mix into children; description is never
inherited; label conflicts name the contributing declarations), endpoint
descent (equal and descended specializations accepted; widened or
unrelated endpoints rejected at declaration; inherited lineage without a
re-declared endpoint and an edge with no endpoint declaration rejected at
class creation, order-insensitively; edge-kind endpoint categories
rejected statically by the node-side bound and at class creation by the
same predicate), blueprint
endpoint validation, codec round-trip and fingerprint change; one
`tests/typecheck_topology_hierarchy.py` static-contract file for the
positive side only — pyright has no expect-error directive, so the negative
side is owned by runtime tests and pinned by the demo.

## 9. Model reference: `demo_endpoint_pattern.py`

The demo is the executable proof of the pattern and part of this spec. It
shows: the six-base shape — template, abstract, and concrete bases under
their eventual names, as stand-ins under the real decorated root, later
renamed `_TopologyDeclarationBase` (the
node side uses the real `Node`; the edge side a stand-in `Edge` derived
from the covariant stand-in `AbstractEdge` with its own parameters
invariant; endpoint parameters bound to `AbstractNode | Node`, the
stand-in for the internal node-side root) —, the per-tier typed options with a stand-in preparation walk
pinning the flow contract (template options annotations flow into the
declaring class; category options do not; description is never inherited —
proved on both sides, with the abstract edge's own label staying on its
entry when a concrete child descends and narrows), one component with two
producers, a choice-free `endpoint(...)` wrapper, the endpoint-optionality
overload matrix, endpoint descent enforced through invariant-into-covariant
base consistency, and exactly eight intended static misuses (abstract
category, wrong category, raw class, omitted tokens on a fully abstract
edge, omission on the category side of a mixed edge, a terminal base
widening an endpoint past its abstract parent, a terminal base
declared before its abstract parent, and an edge-kind endpoint category) plus runtime backstops for
the endpoint factory, the options-tier guards, and endpoint descent
(widening rejected, inherited lineage without a re-declared endpoint
rejected, an edge declaring no endpoints at all rejected, a
`type()`-bypassed edge-kind specialization rejected, and an
order-flipped valid declaration accepted — proving the
base-order rule checker-only and the preparation predicate
order-insensitive). Expected:
`uv run pyright demo_endpoint_pattern.py` reports exactly 8 errors inside the
`_misuse_*` block; `uv run python demo_endpoint_pattern.py` prints `OK`.
Implementation replaces the stand-in edge `Edge` and abstract
`AbstractEdge`, the inert `AbstractNode`, the template roots and template
options types, and the
options-tier and endpoint-lineage guards
with the real machinery; keep the demo until the real tests
subsume it, then fold its cases into §8.
