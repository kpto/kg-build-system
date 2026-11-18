# Agent notes

This is the entry point for working in this repository. It has two domains: how
an agent works, and the framework model the work is reviewed against.

Domain boundary: a rule about how the work is done belongs to agent behaviour; a
rule about what the framework is belongs to the framework model.

## The model in one screen

Read this before the rules. A fresh agent fails here more often than in the code.

A graph is an argument, not a pipeline. It has two axes:

```text
records (graph/)                         relations (relation/)
what the graph asserts                   what the domain contains
  purpose, claims, limitations             contract: definition + meaning
        ▲                                        │
        └──────────── binding ───────────────────┘
                     fulfilment
```

- A **purpose** is one expected use; a **claim** is a contextless assertion; a
  **limitation** is what the purpose does not authorize. A definition is a claim;
  a prohibition is a limitation. A declaration with no positive use carries claims
  only; do not invent a purpose.
- A **relation is not an operator**. State it with no graph nouns and no operator
  verbs. "One condition severity per defect" is a relation; "join defects to
  conditions and drop nulls" is a row source. Keep the operator private.
- A **binding states the fulfilment**: name the record's use in a clause, then say
  how the relation answers it — grain, identity, coverage — and where it falls
  short. "Supply `HAS_DISEASE` edges from each row's `diseaseId`" is a row recipe.
  "The evidence relation fulfils the `HAS_DISEASE` use as the attribution that
  lets a consumer gather the release's evidence for one disease: each release row
  names the disease it is about and supplies one edge, keyed by the evidence and
  disease ids, covering every release row; it supplies the release's resolved
  term, not the source label" is a fulfilment.
- A **published relation must not know the record**. If it names the record's key,
  properties or endpoints, it is a stage in disguise and the binding is a copy.
- The **declaration is the product**; the build, planner, executor and database
  are replaceable mechanisms.

The test for anything you write: could a reviewer who has not seen the code say
what it is for, what it asserts and what it excludes? If not, the meaning is
missing, not the code.

## Agent behaviour

### Working

- Understand the current model before changing it.
- Separate the view hierarchy from the ViewModel hierarchy. They share a shape
  — window, task, panel, section, row, field — but they are different objects:
  a view is reusable, a ViewModel owns one purpose, projection, state and
  commands.
- A ViewModel is framework-agnostic and never owns a view. The composition root
  builds it and injects it; the view binds to it and keeps only presentation
  state. A conceptual level that cannot be built and asserted without the UI
  framework is not a level.
- An additive wave copies the code it needs and adapts its imports; the new
  package must not import the package it will replace.
- Think from the author's and the graph consumer's perspective: why the framework
  exists, what the author gains, and what a consumer can rely on. Do not reduce
  the work to code mechanics.
- Act as a product owner: challenge, remove, merge or reshape a feature when the
  model is incoherent.
- If the model is wrong, change the model rather than building around it.

### Delegation

- A subagent brief is an interface specification, not a task description.
- It names the exact exported and non-exported symbols, the allowed import
  edges, the compatibility shims that must remain, the wrapper shape and the
  command that judges the result.
- "Move the public material", "keep old paths" and "preserve behaviour" are not
  specifications; they leave the subagent to decide the interface.
- Write the acceptance test first and include it in the brief. If the brief
  cannot name what the test asserts, the interface is not decided yet.
- Reuse the subagent session for corrections. Send the same session a follow-up
  with the named defect and the acceptance command; do not spawn a new agent for
  the same component or take the edit over from the main agent. The session
  already holds the package context and the original brief.
- The reason is not agent management: a follow-up forces the correction to be
  stated as a decision. If the same session cannot apply it unambiguously, the
  decision is not precise enough.
- A finding is a snapshot. Re-derive the flagged unit against the current file
  before applying it, and report drift instead of applying a stale row.
- A semantic migration is authored again, not text-moved. The brief names the
  question each unit answers; "rename the old unit" is not an acceptance.
- A brief that touches meaning names the record's use, how the relation answers
  it, and the shortfall. A brief that only says "add the missing semantics" or
  "rewrite the purposes" leaves the decision to the subagent and is not ready.
- The acceptance command is the project gate the change affects, not a scoped
  proxy. A change to a shared helper, generated artifact or public surface runs
  the project check.

### Writing

- A knowledge base is a book: a linear argument in parts and chapters, with
  exact specifications and reference as appendices. A chapter may repeat a
  concept when the argument needs it; do not split a subject into parallel views.
  Order an explanation from meaning and design to data and implementation where
  the model permits, and say that the order is a reading order, not a law.
- A document states the current model as if it were the only one.
- Write for a reviewer who has not seen the conversation, an earlier version or
  the review: define terms, name the interface, file or type, and state the
  decision.
- State the decision, not the route to it.
- Write in point form, finalised and succinct; prefer a short signature and a
  concrete example to a narrative.
- Anything that only makes sense as a change, comparison or reply belongs in the
  change report.

### Review

- A change that crosses a subpackage boundary is proposed as an interface change
  before it is implemented.
- Author-facing interfaces are reviewed through the book and appendices in `docs/`;
  internal interfaces are reviewed through `docs/content/appendix/developer/`. The site is
  built by `docs/` in this repository.
- Docs are author-facing, not simplified. Include anything an author might need
  to know: semantics, edge cases, limits, examples and the reasons behind a
  rule. Structure makes them readable, not the amount of detail.
- Author docs and developer docs may cover the same subject for different
  readers; they are not alternates.
- A developer doc states the interface: names, signatures, invariants, allowed
  dependencies and the authoring surface. Implementation detail is out of scope.
- The interface is the review surface; implementation is not. When the code and
  the developer doc disagree, the doc is the decision and one of them changes.
- A plan or a changelog is a change report, not a spec.
- The proposal is read in one screen:

| Field | Meaning |
| --- | --- |
| Responsibility | The subpackage or module that owns the decision |
| Interface delta | Public names, signatures and invariants, before and after |
| Dependency delta | Imports added or removed, and the direction |
| Authoring delta | What an author writes differently; the typecheck fixture |
| Deletions | Features removed or merged; no compatibility path |
| Contract tests | The tests that now guard the interface |
| Verification | Tests, type checker and any document build |

| Surface | Reader | What it states |
| --- | --- | --- |
| `docs/content/` | graph author | what to write, what the graph does, and the semantics and limits an author needs |
| `docs/content/appendix/developer/` | framework reviewer | internal interface, boundaries and invariants |

- If the interface delta does not explain the change, the change is not ready.
- A visual change is reviewed with a real browser screenshot at the target
  viewports and from measured geometry, not from code; a headless browser is
  acceptable. Compare the reference's structure, not its palette, and treat a
  widget restyle that leaves the layout intact as no redesign.
- A visualisation opens at the lowest detail that still answers its first
  question; every further layer is revealed by a named control, and raw JSON is
  not a default surface.
- A constitution is the subject's production account: the subject box at the
  top, the declarations that bring it into being below, and every edge from the
  supply to the consumer. A record is one DAG: the subject and its graph
  ancestry in the GRAPH frame, one box per binding in the FULFILMENT frame, and
  the relation provenance in the RELATION frame; the subject shares the graph
  ancestry column and the layered layout places the three frames without
  overlap. No separator divides the graph.
  A source relation shows only its asset; a derived relation only its scanned
  source relations and their assets; a binding shows the relations it reads; an
  asset is the origin and has no card. A source or derived relation puts its
  subject and provenance in one RELATION frame; a binding puts its subject in
  the FULFILMENT frame and its relations in the RELATION frame. Its target
  record is its contribution, in the GRAPH frame. GRAPH, RELATION and
  FULFILMENT are the frame kinds, and every box sits inside one of them. A
  collection's layer DAG uses the frame of its layer; a step boundary uses
  GRAPH. The subject shares the graph ancestry column; the layered layout places
  the three frames without overlap.
  A shared declaration is one node with one edge per consumer; a binding is
  never the parent of either side, and each box carries its own concept mark
  and concept-tinted background.
- A DAG scene is laid out by a layered layout, not by fixed columns: the scene
  supplies nodes, edges and any rank constraint the document requires, the
  layout computes the ranks, ordering and edge routes, and the renderer draws
  them. The view keeps only the document anchors, labels and frames.
- A graph surface opens fitted: it fits its scene on first display and whenever
  its document changes; a previous document's pan and zoom do not carry over.
  Within one document the view is the tab's state.
- An abstract category with children is a container node: the smallest circle
  enclosing its direct members, where a child abstract category is its own
  container inside it. Draw it behind the links, label it at the top-left, make
  it selectable, and terminate its declared edges on the container boundary.
- An inspector leads with identity and purpose in one screen. Meaning, members,
  properties and provenance are explicit chunks, not one long scroll. With no
  selection it previews the hovered entity, and the graph void returns to the
  overview; a selection always wins. The tab bar sits above the pinned identity,
  only applicable tabs are shown, and the active tab survives a change of
  inspected entity. An entity keeps the Properties tab even when it declares
  none, so the empty state is visible. A property list in an inspector uses the
  shared property pill, and the pill opens the property document.
- A record card names its members by the subject's vocabulary: Properties for a
  node or edge, Fields for a relation.
- A repeated item renders its units compactly. A heading is structural, not per
  unit: a table cell or list row does not repeat the section chrome. A member
  table fits the column it is in; a cell truncates or wraps rather than forcing
  the table to its max-content width, and the table scrolls only when its
  declared minimum columns cannot fit.
- A card uses one vertical gap between stacked items. A connector sits in that
  gap with the same clearance from the boxes it joins; a longer reach extends
  the shaft, not the gap.
- A connector's shaft and head meet at one point: place the head at the path
  endpoint, not near it, so a gap or rotation cannot separate them.
- Several connectors into one box share one centred, evenly spaced set of head
  positions along the edge they meet; the spacing is uniform and the set is
  symmetric about the edge midpoint.
- A control lives on the surface it changes. Expose the few choices that change
  the picture immediately and group the rest behind one named reveal, following
  Hick's Law and progressive disclosure; a control strip uses a familiar
  toolbar and popover shape near the canvas. The side bar is navigation only.
- A working surface and the declaration it renders are distinct documents: the
  pinned Graph and Workflow tabs are visualisations, and the graph declaration
  is its own Explorer item and detail document, with the shared deck rather than
  a visualisation frame.
- Present the design before an author workflow: a canonical view carries the
  facts a reader must know immediately, and a detail view shows the same object
  with more evidence rather than starting a separate task.
- Each region states one job in its header and does not repeat another region's
  content; a subject's detail belongs to one region.
- One workbench frame is shared by every view: panel geometry never changes
  with the document; documents live in one tab strip with back and forward.
  The side bar is the Explorer, not a control surface; a tab is a standalone
  document. A visualisation carries the controls that change it, and a tab
  changes its editor and those controls; the Explorer always lists the whole
  design. A tab never opens, closes or switches the side bar or another tab,
  and it preserves its own editor state and scroll position. A pinned document is unremovable: it has no
  close action and ignores close gestures. A control inside a tab may not
  replace the document that tab represents; navigating to another subject opens
  or activates that subject's document. The side bar is one collapsible section:
  its body sits below its own header. An automatic reveal is one-shot: an
  explicit collapse wins until the context changes again.
  Single-click navigation reuses one preview tab; only an explicit open pins a
  permanent tab. A middle click on a reference opens a permanent tab in the
  background without changing the active view. One subject has one document:
  navigation from any surface opens or activates the same tab, and identity
  ignores display-only fields such as a redundant name. Back and forward walk
  the view stack, not tab identity: each entry is a document view, and a view
  whose tab was closed is reopened in the preview slot when navigation reaches
  it, never resurrected as permanent. Inspection is
  transient and never opens a document; a document opens only on an explicit
  action and must show content that inspection does not. A navigation row must
  open the document it names; a facet without its own document level belongs
  inside its owner's document. Selection changes state, not geometry: selecting
  an item never pans, zooms or reflows the view; only an
  explicit fit, zoom or navigation control moves it. Selection and expansion are
  distinct: selecting an item never enters a group; entering requires an
  explicit control. Entering a group is a navigation action, and the group graph
  is fitted on entry. A detail document uses
  one shared surface: header, body, section rhythm and panel chrome do not vary
  by subject kind; a new kind adds content, not chrome. A detail banner leads with the kind's
  large logo and the tab names the document; a working surface such as the graph
  or workflow has no banner and carries its actions in a floating toolbar. A
  data-derived detail states its provenance and the narrowed workflow that
  produces it before its meaning; provenance is read from the bindings, including
  identity, source and target expressions, not only declared properties. The
  effective licence follows the provenance assets. One concept registry supplies
  the logo, colour and label for every concept; a banner, a tab, a section header
  and a reference read it rather than declaring their own visual; repeated items
  omit the header's mark, and a reference carries its target document, not a
  focus inside another document. A visualisation kind has one renderer and one
  selection rule for every node and link kind; workflow surfaces share one
  renderer and the provenance tree has its own, while every graph surface shares
  one pan/zoom viewport. A view named for a model renders that model's
  structure; an expression tree shows fields, operators and literals, not an
  ownership summary. Selecting a node dims every other node and non-incident
  link and never moves a settled node; empty space clears the selection. A new
  level or kind adds data, not a second renderer within a visualisation kind.
- An inline mention of a layer instance is one pill: the layer's mark, a
  divider and the instance name. The pill resolves and opens the instance's
  document itself, so a parent supplies identity, never a click handler; it
  truncates its name rather than wrapping.
- A pill previews its instance on hover or focus in one shared popup: concept
  mark and name, the concept name as the subtitle, key facts and the stated
  meaning. The facts carry the owner, container, source, target or endpoints; a
  concept may specialise its facts, not the popup chrome. The popup scrolls,
  dismisses on outside interaction, and never navigates; the pill remains the
  action.
- A component reads the shared design language for colour, type, space, shape,
  depth, motion and layer order; it declares only geometry that belongs to its
  own composition. A token names a role, not a measured value: spacing has no
  numbered steps. A theme check rejects a raw value or a numbered spacing token
  in a component stylesheet.
- Type flows through the shared role scale. A section header is larger and
  bolder than its content; an uppercase caption is a label, not a section
  header. A component selects a role; it does not invent a font size. A missing
  size is a missing role, added to the scale rather than at the call site.
- Spacing sits on one 4px grid; a smaller role binds and a larger role
  separates, and numeric utilities share the same base. A border is hairline
  unless it carries emphasis; a radius is a control, panel or overlay role, and
  a nested surface takes the step below its container.
- An overlay uses one border weight and radius on every side; an accent is not a
  one-sided border. A transient overlay dismisses on outside interaction only:
  scrolling or selecting inside its own surface leaves it open. Its placement
  uses the rendered height, so a short overlay hugs its anchor rather than
  reserving its maximum height.
- A component owns its stylesheet: the global file holds theme roles, base
  element behaviour and global utilities only. A parent passes context down; a
  child never styles an ancestor, and a component block never lives in the
  global file.
- A CSS module declares the keyframes it animates with: CSS Modules scopes the
  animation name, so a reference to a global keyframe silently loses its
  animation.
- A feature composes the shared primitive layer for panels, headers, rows,
  fields, controls, inputs and small type roles before declaring a local
  equivalent.
- A shared component or model needs a consumer in more than one feature. A
  domain component with one consumer belongs to that feature; a generic
  component with one consumer also belongs to that feature.
- A concept's mark carries its type; do not repeat the type as visible text
  beside it. A mark's viewBox is tight to its visual bounds and its stroke is
  scaled to the shared grid, so every layer logo reads at one size and one
  stroke. An abstract node and an abstract edge reuse the node and edge marks in
  the abstract purple; there is no separate abstract category mark. A count
  appears once, in the region that owns the list.
- A detail card's mark is a section mark, not a concept. Each card on one page
  draws its own silhouette, no two cards repeat a mark, and every card mark
  takes the page header's colour; a section mark never reuses the header's
  concept mark and is never a pill or a navigation target. The index rail draws
  the same marks in the rail's text colour, not the subject colour. Section
  marks share the concept grammar and a tight content box, so every card logo
  reads at one size.
- A detail document is a horizontal deck of flat cards. The page margin on the
  left, top and bottom belongs to each card, not to the tab body, so the index
  rail starts at the tab edge and no margin sits left of it; the deck takes the
  right edge so the next-card peek is not covered. Each card fills the deck
  height, states its title above the body at the top-left in the heading role,
  and leaves the next card peeking as the cue for more. The card margin is
  larger than the gap between cards, so the document reads as one group. The
  card has no border, background or radius; the deck owns horizontal scroll and
  reserves its trailing peek space so the last card can snap to the deck start.
  The card body owns vertical scroll, except a graph or tree viewport, which
  fills the body and owns that scroll; a compact list or lane may cap its
  height. The index is the only card navigation and does not follow the scroll
  position. When the index is hidden, the body carries the page margin instead.
- A label stays with the group it names; do not push it to a shared baseline
  with auto spacing when that separates it from its content.
- Every tab uses one banner for identity, overview and view actions. A detail
  body starts at its first section, not an Overview band.
- A connection row states the edge and the other endpoint: `[edge pill] →
  [target pill]` for an outgoing relation or `[source pill] → [edge pill]` for
  an incoming one. Every row carries an **In/Out** column. The current subject is
  not repeated; an edge document states `source → edge` as `in` and
  `edge → target` as `out`.
- A record detail leads with its constitution, then meaning, members,
  connections and bindings. A binding document leads with its constitution,
  then meaning when present, expression and build steps; a record reaches the
  computation through its bindings.
- A card exists only when it has content for the subject. A section that does
  not apply to the kind is omitted, not shown as a card that says so.
- A participant detail states its full constitution and only the immediate
  contribution. A page that lists two levels up is wrong even when its rows are
  true. Constitution is the chain below, back to the asset; contribution is the
  one layer above. Both use the same constitution DAG, with the subject's
  purpose as the anchor.
- Every Explorer row is a document. A header's body opens its collection and
  its arrow unfolds the list; the arrow sits at the left of every row, the body
  never toggles and the arrow never opens the document. A filter reveals the
  matching sections and rows once; it does not override a fold, and changing
  the query reveals the matches again. Clearing the filter restores the folding
  state from before the filter. A virtual collection is a layer read as a
  group, not a declared subject: it has no Meaning card, uses the layer's
  concept mark, and carries Constitution (its items and the actual participants
  below them), Contribution (its items and the actual participants one level
  above), Items and Coverage, both directions in the same DAG. There is no
  collection root. A large set accepts items until the boundary reaches a
  readable size and states how many
  items are shown; it never shows layer boxes or links to another collection.
  The boundary assigns dependency levels and puts every box of one level in one
  horizontal row: an asset is below a source relation, a source relation below a
  derived relation, a derived relation below a binding, and a record above a
  binding. A Constitution puts the items in the top row; a Contribution puts
  them in the bottom row. Abstract nodes and edges are participants: an abstract
  constitution uses its own binding layer and its contribution is its immediate
  children only.
- Motion is feedback, not decoration: short ease-out transitions on transform and
  opacity, origin-aware entrances, and reduced motion removes movement. A
  card-to-card navigation scroll uses one short duration regardless of distance;
  distance changes the speed, not the time.
- End every change report with the rule-promotion result: none, refined or
  added.

### Rule promotion

- At the end of every change, and after a correction that applies beyond it,
  check for a rule that is general enough to govern future work.
- General means: it applies to a different task or subpackage and does not name
  the incident that produced it.
- Place it in the domain it governs: agent behaviour or framework model.
- Refine an existing point instead of adding a case; keep this file small.
- The point is a rule, not a record of the work. The main agent may add or refine
  it directly and report the result.
- Only the main agent edits this file; a subagent reports a proposed rule to the
  main agent.

### Verification

- Run the tests and the type checker for the area changed.
- Update the contract test and the authoring typecheck fixture with the
  interface.
- Do not rebuild the graph or regenerate artifacts unless asked.

---

## Framework model

### Kernel and distribution

- `kg_build_system.kernel` is domain-agnostic: language, declaration, symbol,
  key, reference, linker, planner, workflow plan, runtime, executor, resource
  and toolchain. It imports no table, topology, expression, engine or graph
  package.
- The kernel holds what is inseparable from the framework: protocols, workflow
  values, plan vocabulary and the canonical type system. A package that can be
  omitted or replaced is not kernel.
- Canonical types are a kernel assumption. Every language, the blueprint and the
  workflow plan use the same type ontology; no language defines its own.
- `Nullable[T]` and `T | None` are one canonical type: `Nullable` is the
  authoring alias for the union. Generated contracts, declarations and
  selections use one spelling, and a present selection satisfies a nullable
  slot.
- The kernel uses toolchain vocabulary: language, declaration, symbol, linker,
  planner, workflow plan, runtime, executor and resource. The distribution uses
  domain vocabulary: graph, blueprint, node, edge, binding, projection and
  asset. The kernel model is opaque; the distribution implements it.
- A default distribution is one composition of the kernel protocols. Do not
  state that the framework cannot express a concept until the kernel protocol
  set has been checked; name the extension point and its cost. "Not in the
  default distribution" is not "not in the framework."
- A workflow composes by artifact ports, not step dependencies. A consumer
  declares an artifact type or pattern, never a producer identity; assembly
  derives the connection. Priority orders the assembly scan, not data
  availability, and it does not resolve two producers of one artifact type.
- A language and its package share one name: `DataLanguage`, language `data`,
  package `languages/data`. The authoring class names the syntax (`Table`,
  `Node`); the language is named for the model it produces.
- A package shared only inside one system belongs to that system. It does not
  become a `foundation` package just because several languages use it. Only a
  package every system needs, and cannot replace, moves to the kernel.
- The package tree shows the primary dependency spine. A shared artifact or
  interface is the root of its consumer cluster. A tree cannot encode every
  edge; the dependency tests enforce the rest.
- `annotations`, `expressions`, `asset`, `data`, `topology`, `binding`,
  `semantics` and `graph` are distribution languages. `core`, `deduplication`,
  `merging`, `conflict_validation`, `file`, `meta_graph`, `neo4j`, `duckdb`,
  `python` and `runtime` are distribution modules.
- `semantics` is a value language: claim, limitation and purpose values are
  embedded in declaration DTOs; it needs no kernel `Language` adapter.
  Annotations are the other value language.
- `graph` has at most one declaration per project. It carries the project's
  purpose and graph-level semantics; every declaration semantics is read under
  that purpose.
- A module is a feature package, not a protocol and not a registry entry. It
  groups one feature's planners, executors, resources and configuration.
- An asset is a logical unit of source data, like a package; one asset may back
  many tables. A table names its asset through `Table[Asset]`, and a relation
  carries that identity as an `AssetRef`.
- Asset layout is optional descriptive metadata, not an access contract. There
  is no adapter concept in the toolchain and no adapter registry; a module
  contributes ordinary relation-producing steps. `DuckDbSourcePlanner` resolves
  compatible `parquet`, `json` and `csv` layouts.
- No code-generation field belongs to the asset model. `@asset_contract` is a
  generation-frontend decorator on an `Asset` subclass; it is inert and outside
  `AssetOptions` and the blueprint.
- The runtime owns the resource providers; `Toolchain` has no `resources` field.
  The pipeline emits events; a monitor is a frontend listener and a provider is
  an event subscriber that creates resources on pipeline start and disposes them
  on finish or halt. An executor declares the exact `resources` it reads and
  receives a `ResourceView`; the runtime validates the declarations against the
  resource registry. A listener error is a pipeline failure.
- `api.py` is the composition root. It owns `default_toolchain`,
  `DEFAULT_TOOLCHAIN`, `create_blueprint`, `compile` and `execute`; the
  distribution supplies implementations only.
- A project manifest declares composition values (`Blueprint`, `Workflow`);
  importing it builds nothing. A command finds the values by type, not by name.
- Several planners may share one component when their `version` and
  `runtime_fields` agree. The component is published once and each step gets its
  `component_id`; a step identity still may not repeat.
- An operation is one specification plus one instruction emitter. Adding one
  does not edit a dispatcher.
- A planner emits steps; it does not execute them. An executor executes one
  exact instruction kind and declares the resources it reads; it does not plan.
  A component that needs both is two objects.
- An extension declares the surfaces it extends: a language, a linker, a
  planner and/or an executor. It does not implement one module interface.
- Instruction kinds are exact namespaced tuples such as `("sql", "duckdb")`.
  There is no prefix matching and no shared `"sql"` kind.
- A custom language and a custom planner and executor compile and execute
  without the default distribution; a graph build is one distribution, not the
  kernel.

### Semantics as contract

- The graph's meaning is part of the delivered contract, not a comment or an
  implementation detail.
- A node or edge type states its meaning, direction, identity, absence and limits.
- A source adapter bridges a physical source to a relation and the SQL boundary.
  It preserves the source's schema, null assumptions, grain and identity; it
  decodes and casts only, and does not carry domain joins, filters, identifier
  translation, deduplication, aggregation, array expansion or graph meaning. A
  data operation belongs in an expression operation and becomes graph meaning
  only as a named, referenceable projection with semantics; a pipeline-local
  relation is not a projection.
- The build preserves those statements and publishes them for consumers.
- A meaning that cannot be stated is recorded as a limit; it is not invented.
- A unit answers one question: a purpose says what the subject is for, a claim
  what it is, a limitation what that purpose does not authorize. A definition or
  measurement in a purpose, a prohibition in a claim, or a figure in a
  limitation is a misplaced unit, not a wording defect.
- A measurement is evidence for a boundary, not the boundary. The figure is a
  claim beside the purpose; the limitation states only the excluded reading.
- A unit states one thing. A category prefix is a label, not a field; model
  grouping rather than encoding it in text.
- A declaration with no positive use carries claims only. Two declarations share
  a purpose only when the use is identical.
- A declaration states a meaning or the explicit `Omitted` marker; there is no
  implicit absence. The graph declaration, a published contract and a binding
  cannot opt out, and a field definition never satisfies a meaning.
- A declaration carries no description and no docstring; a display surface reads
  the purpose, the first claim or the field definition. One text is maintained,
  not two that drift.
- A binding is the one declaration whose `name` is a display handle, excluded
  from its content identity; every other `name` is part of identity.
- A binding requires a meaning with a purpose, and that purpose states the
  fulfilment it performs: it names the record's use in a clause, then says how
  the relation answers it — which relation, at which grain, identity and coverage
  — and where it falls short. A row recipe or a restatement of the record's
  purpose is not a fulfilment. The record's meaning
  stays on its node or edge; the relation's meaning stays on the relation.
- A relation is a contract: a definition (grain and identity) and a meaning. A
  derived relation requires a meaning with a purpose; a source relation may state
  claims only. A declared contract is complete, never half-stated.
- A stage is a private derived relation: a definition, no contract meaning, and
  no bindable row source. It composes inside one published relation and owns no
  consumer contract.
- A field definition lives on the field: what the value is, its unit and its null
  meaning. Name, type, source and provenance are derived, never copied.
- A project attaches the framework meaning units directly. A project-local
  builder with its own grammar is a second meaning model, not a convenience.
- Published provenance names the release declarations a value is read from. A
  computed relation resolves to the base relations and fields behind it; its
  internal computed name is not a source dataset.
- Observation is provenance. A generated field renders its value type; an
  observed source nullability may inform the manifest, statistics and notes but
  never adds `| None` to generated source.
- The blueprint is the semantic model of the graph, not a snapshot of the
  declarations that produced it. It carries the graph declaration (including
  its purpose), the topology, data, assets, bindings and the semantics attached
  to each declaration. Topology reads as nodes, edges, labels,
  endpoints and properties; it does not carry Python paths, declaration
  expressions or symbol IDs.
- A DTO is a member of the blueprint or the workflow plan. A value outside those
  two artifacts is in-memory: a model, a plan, a render input or a build result.
  It is not a DTO and is not expected to deserialise.
- A language discovers declarations, derives a key with `compute_key`, reports
  direct references from the authoring value and transcribes one declaration
  into one symbol; a batch implementation stays internal. A declaration has no
  key; a symbol carries key, kind, value and references. The linker selects
  roots, resolves the closure before transcription, orders declarations and
  assembles the model.
- A language DTO does not know the blueprint. It knows only the languages it
  depends on. The interpreter links the language DTOs into one semantic model.
- The kernel has three stages: `build` (languages -> declarations -> symbols ->
  model), `compile` (model -> planners -> `WorkflowPlan`) and `execute` (runtime
  -> resources -> executors). The public verbs are `compile` and `execute`;
  `create_blueprint` is the distribution's build shortcut.
- `compile` reads a linked model and runs planners to produce a `WorkflowPlan`.
  It does not assemble a blueprint and does not call the blueprint package. The
  composition root calls `create_blueprint` and then `compile`.
- The blueprint is the semantic model, not a symbol table. The symbol graph is
  linker IR: it exists to key declarations, resolve references and order
  transcription. The delivered blueprint names semantic roles, not symbols.
- The blueprint is public: a user may obtain a blueprint handle. The language
  DTOs it references are not exported public names. The canonical flow is the
  compile shortcut that creates and consumes the blueprint without exposing it.
- Cross-symbol fields are typed refs such as `NodeRef`, `FieldRef`,
  `PropertyRef`, `RelationRef`, `AssetRef` and `OperationRef`; there is no bare
  cross-symbol string.
- `Selection[T]` is the single authoring type; `NullableSelection[T]` is
  `Selection[Nullable[T]]`. A field declares a value type, never absence: source
  access is nullable and computed access follows the selection. A field never
  exposes the compiler expression tree. `alter_rows()` gates every row effect
  one-shot; `lookup`, `zip` and row-source `unnest` state grain explicitly.
- Expressions are inline fragments, not symbols. Their leaves are typed refs; a
  shared or named expression is a computed field or a projection output.
- Identity is a qualified name (`Key` segments). A fingerprint or digest may be
  recorded beside a value; symbols are not content-addressed by default (a
  binding without a debug name is the distribution's stable-digest exception).
- Source generation is the responsibility of the language that owns the DTO. A
  language renders its own DTO using its dependency languages' renderers; the
  interpreter only delegates to each language and assembles the fragments.
- The blueprint must regenerate equivalent authoring source. The round trip
  `blueprint -> generated source -> blueprint` is a contract test, not a
  convenience.

### Experimental

- The API is not stable; breaking changes are expected.
- The framework has no schema versions and no compatibility negotiation or
  migration path.
- If an artifact needs a fingerprint, derive it from its content and record it
  beside the artifact's identity; symbols are keyed by qualified name, not by a
  content address.

### Interfaces

- A **subpackage** is a directory that owns one responsibility.
- An **interface** is the set of names another subpackage may use: types,
  protocols, functions, errors and their invariants.
- The interface is not `__all__`; it is the surface designed to be depended on.
- The reviewer supervises interfaces; implementation is replaceable behind them.
- A public annotation states the narrowest type true of the value: no `Any`;
  an opaque value is `object`, an open payload is `JsonValue`, and an invariant
  generic top is a named non-generic root or a variance decision. A decoder that
  validates its input takes `object` and narrows at the boundary.
- An implementation detail is sampled only when it suggests the interface or the
  responsibility is wrong.
- An interface change is a model change, visible before implementation.

### Separation of responsibilities

- One module owns one decision; its path and name tell the reviewer which one.
- If the purpose needs "and", it is more than one module.
- The test is local change: a join-semantics change lives in the row-source
  algebra and does not require editing table declarations, the planner and the
  authoring API.
- A small feature that forces edits across several subpackages means the boundary
  is wrong; fix the boundary, not the call sites.
- Avoid god modules, duplicated plan models, duplicated codecs, and helpers that
  exist only because two modules could not agree on an interface.

### Explicit boundaries

- Each subpackage declares its responsibility, its interface and the subpackages
  it may import.
- Every framework subpackage uses the same model/service layout:
  - `__init__.py` — the facade; a docstring, imports, a literal `__all__` and
    import/re-export machinery (`__getattr__`, `__dir__`, a lazy group table).
    It contains no business logic: no service, planner, codec, validation,
    feature registry or default instance;
  - `model/public/` — authoring models, returned values and public DTOs;
  - `model/internal/` — cross-package data: `dto/` and `model/`;
  - `model/_private/` — private plans, render models and SQL types;
  - `service/public/` — author-facing methods; thin wrappers;
  - `service/internal/` — service interfaces, codec/assembly wrappers and
    `adapters/`;
  - `service/_private/` — codecs, transcription, rendering, validation,
    assembly, planning, engines and runtime.
- A leaf contains only the zones it uses; an empty zone is deleted. The
  top-level lazy export table lives in `kg_build_system/__init__.py`; lazy
  loading is import machinery, not business logic.
- `model.public` and `service.public` are the definition sites for author-facing
  names. A public function or method is a thin wrapper over `service._private` or
  `service.internal`; the mechanism is not in `service.public`.
- Another subpackage imports `pkg.model.public`, `pkg.model.internal`,
  `pkg.service.public` or `pkg.service.internal`. It never imports `_private`.
- A subpackage may have no author-facing surface when nothing in it is written by
  a graph author; `model/public/` or `service/public/` states that, it does not
  pretend to be a facade.
- Implementing another package's protocol is a separate file under
  `service/internal/adapters/<protocol>.py`. The file names the protocol and
  delegates to `service._private`; it is not buried in a model or factory.
- DTO and model values are anaemic: frozen data with no owner, no service and no
  behaviour beyond its own invariants. Derived rules are functions beside them.
- A protocol is the internal interface of a dependency direction: a module
  implements it, a runtime calls it. Do not carry a live service inside a data
  model.
- The dependency direction is one graph; a cycle or a new edge is a model change.
- A new edge may be right, but it is proposed with its reason; the reviewer
  decides whether the model changes.
- A join change belongs to the row-source package. If a planner needs a
  generated join shape, the row-source interface exposes that shape; the planner
  does not import a private module to find it.

### The authoring API is the guard

- The **authoring API** is what a graph author writes; it is the product model,
  not a convenience shortcut over internals.
- A public API method is a thin wrapper over an internal implementation, with a
  docstring and a runnable example. It is not a bare re-export.
- A structural builder may accept a semantics value and pass it through; it must
  not accept purpose, claim or limitation text. Meaning is written at the
  declaration, and a helper that assembles it is an adaptation.
- It makes the intended use easy and the wrong use impossible.
- A scaffold carries structure and an unanswered argument; a worked example is a
  separate tree, chosen explicitly, never the default.
- A capability handle exposes only the operations its subject supports and is consumed by its first use; an unsupported operation is absent from the handle type, not present and refused at runtime.
- It exposes only what an author may write; internal types stay internal.
- A type in a public signature is a public type. If the value is an internal model, the
  public function returns either an opaque token or a public view of it; it does
  not expose the model under an internal name.
- A feature that cannot be expressed cleanly through it is probably wrong.
- Typecheck fixtures exercise the public surface and guard it.
- A project-local value operation is one operation spec plus a typed handle in the expressions language; its engine emitter is a module and the operation set is an explicit language composition, not a registry. A row effect, grain change or aggregate is not a value operation.
- A relation operation is one input row source, one declared output shape and one grain; its engine emitter is a module, and its output is plan-local until a `Stage`/`DerivedRelation` publishes it with a matching grain.
- A public row-source result names a concrete shape; `Shape` is a bound and a runtime marker, never a result type. Derive the generated shape or require it explicitly, and validate the runtime member names and logical types against it.

### Names state the role

- A command surface names itself once: usage, help, banners and errors use the
  product's vocabulary; a package or directory name is not a user-facing term.
- `IR` is not a synonym for internal data. Do not use it as a module or class
  suffix.
- A serialisable model is a DTO, and its module names the artifact it belongs
  to: `blueprint_dto.py`, `workflow_dto.py`, `instruction_dto.py`,
  `render_dto.py`.
- A type in a DTO module carries the `DTO` suffix: `ComponentDTO`,
  `BindingDTO`.
- A model that is not serialised is not a DTO: name it an in-memory `model` or
  an engine-neutral `plan`. A DTO whose artifact cannot be named is not a DTO.
- Use one verb per transformation. A language **discovers** declarations,
  **computes keys** and **transcribes** symbols; the linker **links** languages
  and symbols into a model; a planner **plans** a model into `Step`s; the runtime
  **executes** a `WorkflowPlan`; an engine **emits** SQL from a plan; source
  generation **renders** a DTO or symbol value to authoring source. Do not use
  `lower` for any of them.
- A derived row source attributes its surviving fields to the relation it scans.
  An unnest narrows one field; it does not move the shape onto an anonymous
  digest, and provenance resolves through the scan.
- A relation is a source relation or a derived relation; `projection` names the
  SQL/plan operator only, and `table` a physical or generated table only.
- A project directory states the axes: `asset/`, `graph/`, `relation/source/`,
  `relation/derived/`, `binding/`. A declaration is a file, a package is a
  grouping, and an `__init__.py` is a facade with no declaration.
- A language transcribes declarations into symbols and renders a symbol value
  back to authoring source. Transcribe and render are the two directions of the
  same language.
- A declaration does not own a key; `compute_key` derives it. A symbol carries
  its key, kind, value and references.
- An identity that crosses a planner, executor, runtime or codec boundary is a
  role type over `Key`: `StepId`, `OpeningId`, `ArtifactType`,
  `ArtifactPattern`, `InstructionKind`. A formatted string is display only,
  never an identity. Direction is part of an opening identity when one name
  can denote more than one port.
- The workflow plan owns structure: steps, inputs, outputs, connections and
  provenance. The composition root records the source blueprint document under
  plan provenance, so a serialized plan carries the model that produced it. A
  step owns its instruction. SQL is one instruction kind, not a plan field.
- A planner emits steps and an executor executes one exact instruction kind. SQL
  and Python are instruction kinds; a Python instruction is a stable reference,
  not a live callable.
- A wrapper is named for what it produces, not for the function it calls. When
  it composes a function of the same base name from another level, the import is
  aliased so the two levels never expose one name with two signatures.
- A leading underscore means module-private or package-private. A private helper
  inside one service module is allowed; a private name exported from
  `model/public/`, `model/internal/`, `service/public/` or `service/internal/`,
  or imported or read as an attribute across a module boundary, is not. Shared
  mechanisms belong in `_private`.
- A private helper stays beside its caller. Move it to `_private` only when it is
  shared by several modules or is independently replaceable; otherwise the move
  splits one decision and adds an import edge.
- `model.public`, `model.internal`, `service.public` and `service.internal`
  contain no mechanism: data, protocols, adapters and thin delegations only.
  Codecs, transcription, rendering, validation, assembly and planning live in
  `_private`.
- Consequently, these four zones define no single-underscore helper. Dunder
  protocol methods are not private helpers and remain.
- A codec is private to its language. Another package calls the language's codec
  interface; it never imports the codec implementation.
- A shared artifact package owns its model and, at most, its document codec. It
  does not own the algorithm that produces it; the producing system owns the
  planner. A workflow package is not a planner.
- A package that only re-exports another package's model is not a package. Expose
  the names from the top-level facade or import the definition site; do not add a
  package with no model or service of its own.
- Data is the lowest part inside a package. `model._private` may import
  `model.public` and `model.internal`; `service._private` may also import
  `model.public` and `model.internal`. `_private` may use public model data but
  not public service behaviour. `model.public` and `model.internal` import no
  service and no `_private`. `service.internal` delegates to `service._private`
  with a function-local import. `service/internal/__init__.py` does not eagerly
  import a service that imports `_private`.
- A language does not encode or decode. Serialisation belongs to the DTO codec,
  which names its artifact: `to_document` / `from_document`. The blueprint codec
  composes the language codecs.

### Models are anaemic and amnesic

- The framework uses anaemic models deliberately: a model is frozen data holding
  the facts it owns, not a service object.
- Behaviour that needs more than those facts is a function beside the data.
- This keeps the data portable, the tests local and the location of behaviour
  explicit.
- A model has no reference to an owner or a wider context and stores no identity
  that can be derived.
- A relationship is stored once, in the direction that states it; the reverse
  relationship is derived from it, never stored beside it.
- Anaemic is about behaviour; amnesic is about ownership and identity. Both are
  deliberate.
- A second type that differs only in which members are required is a validation
  rule at the attachment site, not a second model.
