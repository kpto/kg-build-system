# Viewer design language

The viewer is one application, not a collection of screens. It reads a graph
design through one document strip, two side-bar sections and one shared ladder. Each level answers one
question and owns one kind of chrome. A level may be omitted; it may not be
reordered, duplicated or wrapped in another level of the same kind.

The visible hierarchy is in `HIERARCHY.md`; the skin is in
`DESIGN_BLENDER.md`.

## The ladder

```text
Window        where am I, and what design am I reading?
  Document    Graph or a subject: what is the editor rendering?
    Panel     which region answers it: side bar or editor?
      Section which facet of the subject?
        Row   which item?
          Field what value?
            Control one action or reveal
```

- **Window** owns identity: brand, snapshot, global search, zoom, panel
  visibility.
- **Document** owns its editor content and pane state. The Graph document is
  canonical; the Workflow document is the compiled plan; a subject document is a
  node, edge, property, asset or abstract node opened from the Explorer tree,
  a context menu or the command palette; a step document is one workflow step
  opened from the workflow section of Explorer.
- **Panel** owns one region, one header and one body. A panel never contains
  another panel of the same kind.
- **Section** owns one question inside a panel. If it needs "and", it is two
  sections.
- **Row** is one subject: a node, relation, property, step, claim, frame or
  asset.
- **Field** is one value of that subject.
- **Control** is one action or one reveal. It never carries content.

## One frame, two side-bar sections

| Section | Question | What it contains |
| --- | --- | --- |
| Control | How is the current view configured? | graph filters, labels, Show controls, legend, layout; workflow component and instruction filters |
| Explorer | What does the design contain? | assets, nodes, abstract nodes and edges, properties and the workflow components and steps; it always lists the whole design |

There is no mode switch. Opening a side-bar section changes the side bar, not
the active document or its editor. Control follows the active view; a subject
document has no view controls. A graph selection is transient inspection; a
subject document is an explicit tab.

## Detail is earned

The first paint states the design, not every annotation.

- **Low detail is the default.** The Graph labels hubs only; edge labels,
  containment, meaning badges and property lists are off. A subject document
  states its overview in the banner and opens its full card deck; graph claims
  and limitations are revealed on demand in the Explorer section. The Workflow shows the compositor graph; a
  step document reveals complex payload values on demand.
- **A reveal is explicit.** Every hidden layer has one control that names it.
  A control's state is visible; a revealed layer is one click away from hidden.
- **A reveal does not change scope.** Turning on meaning labels adds evidence
  to the same graph; it does not switch function or selection.
- **No raw JSON in the default surface.** A design reader shows named values,
  not serialised models.
- **The body states its own extent.** A card header carries no count; the list,
  table or graph inside the card shows what it holds. A card title sits above
  the card body at the top-left, not in a banner bar or card surface. A section
  header is larger and bolder than its content; a caption is a label, not a
  header.

## Detail content

Every item detail view follows one content contract, stated in
[`DETAIL_CONTENT.md`](./DETAIL_CONTENT.md). The shared order is:

```text
Banner: Overview
Constitution → Meaning → Contribution → Members → Connections → Bindings
```

A binding document is the one exception to the record order:

```text
Banner: Overview
Constitution → Contribution → Meaning → Expression → Build steps
```

A kind includes or omits a section; it never renames one for itself.

A participant detail answers **constitution** and **contribution** only:

- **Constitution** is the full chain below the subject, back to the asset.
- **Contribution** is only the immediate level above the subject. An asset's
  contribution is its source relations; a relation's is the derived relations
  that scan it and the bindings that read it directly; a binding's is the
  record it writes; an abstract participant's is its immediate children; a
  step's is the steps that read its outputs.

Both directions use the same constitution DAG: the subject's purpose is the
anchor, its constitution hangs below it and its contribution sits above it.
When a contribution set is large, it is read at layer resolution: one linked
layer box per kind.

A **virtual collection** is a layer read as a group, not a declared subject. It
has no Meaning card and uses the layer's concept mark. Its order is:

```text
Banner: Collection
Constitution → Contribution → Items → Coverage
```

Its Constitution shows the collection's items and the actual participants below
them; its Contribution shows the items and the actual participants one level
above. There is no collection root. Items opens each participant; Coverage
counts the layer. A large set accepts items until the boundary reaches a
readable size and states how many items are shown; it never shows layer boxes
or links to another collection.

The boundary is ordered in vertical level bands: an asset below a source
relation, a source relation below a derived relation, a derived relation below
a binding, and a record above a binding. A Constitution puts the items in the
top band; a Contribution puts them in the bottom band. Assets have an explicit empty Constitution state:
they are the origin.

Every Explorer header is two targets: the **body** opens the collection and the
**arrow** unfolds or folds the list. The body never toggles and the arrow never
opens a document. A workflow component header behaves the same way.

- **Overview** is the tab banner: identity and one fact row. It is not a band.
- **Constitution** shows how the subject comes to be: the subject at the top
  and only the declarations that produce it below, laid out as one layered DAG
  on the shared graph canvas. Every edge points from the supply to the
  consumer; a declaration shared by several consumers is one node with one edge
  per consumer, never a copy or a count. The subject box carries the subject's
  own concept mark, never the graph mark.
  - A record is one intact DAG. The subject and its graph ancestry share the
    GRAPH frame; the bindings are in the FULFILMENT frame and the relation
    provenance in the RELATION frame. The subject shares the graph ancestry
    column; the layered layout places the three frames without overlap. There
    is no separator.
  - A source relation shows its subject over its asset alone; a derived relation
    its subject over the source relations it scans and their assets. The subject
    and the asset or scanned sources share one RELATION frame. Neither carries
    a binding or a graph axis.
  - A binding shows its subject over the relations it reads, with their
    provenance. Its purpose is in the FULFILMENT frame and the relations in the
    RELATION frame. Its target record (purpose and identity only) is its
    Contribution, in the GRAPH frame. The record's graph ancestry belongs to the
    record's own constitution.
  - GRAPH, RELATION and FULFILMENT are the frame kinds, and every box sits
    inside one of them. A record's subject and graph ancestry share the GRAPH
    frame; a step boundary uses GRAPH; a collection boundary DAG uses the frame of
    its layer. The subject shares the graph ancestry column; the layered layout
    places the three frames without overlap.
  - An asset is the given source, so it has no Constitution card. A step is
    build machinery and has none either.
  When several arrows meet one box, their heads sit on a centred, evenly spaced
  set of points along that edge. Each box background is a tint of its own
  concept colour, and each box is led by its concept pill in the title role.
  The pill sits one stack gap above its purpose, closer than the box padding,
  so the header and its body read as one group while the rank gap separates
  boxes. The scene supplies nodes and edges;
  the layout computes ranks, ordering and edge routes. The canvas opens fitted
  and pans and zooms;
  selecting a node dims every other node and non-incident link, empty space
  clears, hovering or focusing reveals the full meaning, and a node label opens
  its document.
- **Meaning** leads with the subject's purpose, then sets the contextless
  claims and the limitations that bound that purpose as two labelled readings.
  Each group carries its own count, and the groups stack when the card is
  narrow. It is a separate card from the Constitution, so a reader can see the
  two axes and the subject's complete meaning in turn.
- **Expression** and **Build steps** belong to the binding document, not to the
  record detail. Expression shows the identity and property chains the binding
  writes; Build steps shows the plan around that binding. The record reaches
  them through its Bindings table and the Constitution's binding node. The
  binding banner states the rows read, so Sources is not a separate card.
- **Members** is one table grammar for properties, columns, fields,
  descendants and openings. The instance pill opens its document when one exists.
- **Connections** states endpoints, incident relations or ports.
- **Bindings** states which binding fulfils the subject; its pill opens the
  binding document.
- A binding document leads with its **Constitution**, then its **Meaning**
  (when the binding carries one), its **Expression** and its **Build steps**.
  The Constitution is the binding's purpose over the target record and the
  relations it reads.

A kind may state an absence instead of omitting a section. A step has no design
meaning and no release source, and it says so; it is build machinery.

Every tab — detail, Graph and Workflow — uses the same banner. It leads with
the kind's mark from the one concept catalogue and states the identity,
overview facts and the view's own actions. Graph and Workflow keep their
working-surface frame below the banner; every graph surface shares one
bottom-left navigation cluster.

One concept catalogue in `shared/ui/concepts.tsx` supplies the mark and
representative colour for every layer: graph, abstract node, abstract edge, node, edge,
property, asset, source relation, derived relation, field, binding, workflow,
step and meaning. A banner, a tab, a section reference, an expression row and a
membership row read the same catalogue, so an asset is the same green cylinder
mark wherever it appears. The marks share one grammar — a 24 px grid, a 1.6 px
stroke and round joins — and the concept's one filled element takes a 24% tint
when it is active. The viewBox is tight to each mark's visual bounds and the
stroke is scaled back to the grid, so every layer's logo reads at one visual
size and one stroke. Colour is a second cue; the silhouette and the label carry
the distinction alone.

An inline mention of an instance is one pill: the layer's mark, a divider and
the instance name, all in the instance's colour. The same pill names a record
in a connection row, a property in a member table, a relation in a source list,
a field in an expression tree and a card in the fulfilment map. A pill resolves
and opens the instance's document itself, so a caller supplies identity, never
a click handler. A long name truncates in the pill; it never wraps.

## Theme tokens

`app/globals.css` owns every design value; `shared/ui/theme.ts` mirrors the same
tokens for React inline styling. A component reads a token instead of declaring
a local colour, type size, spacing step, radius, border width, shadow, weight,
tracking, layer or motion duration. Local geometry — widths, heights, grid
templates, media-query breakpoints and one-off positioning — stays with the
component because it describes that component's composition, not the system.

| Group | Tokens | What it governs |
| --- | --- | --- |
| Surface | `--color-abyss`, `--color-panel*`, `--color-inset`, `--color-gutter` | window, panel, raised body, inset well |
| Line | `--color-line*`, `--color-line-deep`, `--color-line-mid` | seams, borders, dividers |
| Text | `--color-text`, `--color-muted`, `--color-faint`, `--color-ink*` | reading hierarchy |
| Action | `--color-selection*`, `--color-accent*`, `--color-on-accent` | selected, focused, linked, pressed |
| State | `--color-critical*`, `--color-high`, `--color-medium`, `--color-low`, `--color-accepted`, `--color-open`, `--color-rejected` | verdicts and severity |
| Layer | `--color-asset`, `--color-source`, `--color-transform`, `--color-binding`, `--color-post`, `--color-target`, `--color-group-*` | data lanes |
| Concept | `--color-concept-*` | the 13 concept marks and reference pills |
| Type | `--text-micro` … `--text-display`, `--leading-*`, `--tracking-*`, `--weight-regular/medium/bold` | role, line height, tracking, weight |
| Space | `--space-hairline`, `--space-inline`, `--space-stack`, `--space-group`, `--space-section`, `--space-panel`, `--space-region`, `--space-page` | gap, padding and margin by role |
| Shape | `--border-*`, `--radius-*` | hairline and heavy strokes, corner radii |
| Depth | `--shadow-*` | popover, panel, modal, inset and selection rails |
| Motion | `--motion-fast/base/slow/pulse`, `--ease-*` | durations and easing |
| Layer order | `--z-*` | raised, sticky, header, overlay, modal, tooltip |

### Type roles

The scale is global: a size states a role, not a component.

| Role | Size | Use |
| --- | --- | --- |
| `--text-micro` | 11px | badges, pills, keyboard and canvas annotations |
| `--text-caption` | 12px | metadata, table headers, group labels and kickers |
| `--text-body` | 13px | dense secondary text and table values |
| `--text-label` | 14px | default UI, controls, inputs, claims and limitations |
| `--text-title` | 16px | purpose lead, emphasized values, brand and palette titles |
| `--text-heading` | 22px | banner, page and card titles |
| `--text-display` | 26px | gate and empty-document hero |

`--text-root` keeps the rem geometry at 12px; `--text-xs`/`sm`/`base`/`lg`/`xl`
resolve to the same roles, so a Tailwind length and a component token agree. A
section header is `--text-heading`, bold and sentence case. A side-bar
navigation header is `--text-title`, also sentence case. An uppercase
`--text-caption` is a label, not a section header. A component selects a role;
it does not invent a size. A missing size is a missing role, added here rather
than at the call site. `--color-faint` is the lightest reading tint and clears 4.5:1 on
every surface.

### Spacing roles

Spacing is one 4px grid; 2px is the optical hairline.

| Role | Value | Use |
| --- | --- | --- |
| `--space-hairline` | 2px | optical edge, dense icon alignment |
| `--space-inline` | 4px | icon and inline relationships |
| `--space-stack` | 8px | tightly related lines |
| `--space-group` | 12px | related groups and the gap between cards |
| `--space-section` | 16px | deck and panel inset, section internal |
| `--space-panel` | 24px | panel and field separation |
| `--space-region` | 32px | document body and large block separation |
| `--space-page` | 48px | page-level layout |

A smaller role binds, a larger role separates. Tailwind’s numeric space
utilities use the same `--spacing: 4px` base, so `gap-1` is 4, `gap-2` is 8,
`gap-3` is 12, `gap-4` is 16, `gap-6` is 24 and `gap-8` is 32. Numeric
utilities and role tokens cannot disagree about the grid.

### Borders and radii

| Role | Value | Use |
| --- | --- | --- |
| `--border-hairline` | 1px | default containment and dividers |
| `--border-heavy` | 2px | selected, focused or emphasized boundary |
| `--radius-sm` | 4px | controls, rows and inline surfaces |
| `--radius-md` | 8px | panels and cards |
| `--radius-lg` | 12px | overlays, popovers and dialogs |
| `--radius-pill` | 999px | pills and status chips |

Use the smallest border that separates; a border is never the only signal for
selection, focus or error. Borders are hairline or heavy; the focus outline
uses the heavy width. Radius is a role, not a decoration: a nested surface uses
the step below its container.

Every component stylesheet is checked by `scripts/check-theme.mjs`; `npm test`
runs that check before the unit tests. A raw colour, type size, radius, spacing
value, weight, tracking, layer or motion duration in a component fails the
build. Spacing has no numbered tokens: a gap states its role in the
composition, not a pixel step. `app/globals.css` is the only file allowed to declare raw values, and it
may do so only in an `@theme` token line.

### Style ownership

Styles flow down; a child never styles its parent or sibling.

| Level | Owns | Examples |
| --- | --- | --- |
| Global | theme roles, base elements, global utilities | `@theme`, `html`, focus ring, scrollbar |
| Shared primitive | one reusable visual unit | viewport frame, concept mark, pill |
| Parent component | a region's composition | workbench shell, side bar, editor area |
| Current component | its own layout, rows, controls and states | palette, tabs, tree, detail band |
| Local geometry | dimensions true only here | grid templates, canvas sizes, breakpoints |

A selector belongs to the component that renders it. A parent passes context
with props or a scoped CSS variable; it does not reach into the child with a
global descendant selector. A component-specific block in the global file is a
boundary violation.

A **shared domain component** knows the graph or semantic vocabulary and has a
consumer in more than one feature. The current set is `DesignMeaning` and the
concept presentation (`ConceptMark`, `concepts`). A domain component with one
feature consumer belongs to that feature: `Constitution`, `ConceptPill` and
`ConceptReference` are detail components. A generic component with one
consumer also belongs to that feature; only a reusable or cross-feature
component stays under `shared/`.
A CSS module declares the keyframes it animates with. CSS Modules scopes the
animation name, so a reference to a global keyframe would silently lose its
animation.

The generic primitive layer is `shared/ui/Primitives.tsx` with
`shared/ui/primitives.module.css`: `Panel`, `PanelHeader`, `Label`, `Meta`,
`Row`, `RowButton`, `Field`, `Control`, `Input`, `Select`, `Empty`, `Hint` and
`Kbd`. A feature composes these before it declares a local panel, row, field or
control style. The compound primitives — viewport, pill, concept mark and
context menu — own their own modules.

An item-detail card is not a generic primitive. `DetailBand` is the detail
feature's one card primitive: it composes the flat `Panel` and places the card
title above the body at the top-left, with the concept mark. The card question
is the section's accessible label, not a visible line. Cards are static and
backgroundless; the detail body never folds them. A view may not re-declare a
card surface, header or title; those belong to `DetailBand`.

A detail body pairs one left index pane with a horizontal deck of flat cards
inside one page margin. The index is a static view: it centres its tiles in the
pane, lists the top-level cards in reading order and does not track the scroll
position; the tile group carries one side line. The deck fills the height left
by the margin; each card fills the deck height, carries its title at the
top-left and leaves the next card's edge visible. The deck owns horizontal
scroll and reserves its trailing peek space so the last card can snap to the
deck start. The card body owns vertical scroll, except a graph or tree
viewport, which fills the body and owns its scroll; a compact list or lane may
cap its height. The index disappears below the width where a card would lose
its reading measure.

## Interaction motion

- Motion is feedback, not decoration. Hover, selection and press changes use
  short transitions; entrance layers use opacity plus a small transform.
- The workbench curve is `--ease-instrument`. Micro-interactions stay under
  200ms; a palette or dialog may take 200ms.
- Buttons press down by 1px. Tabs transition their surface and active
  indicator. Context menus enter from their anchor; the Graph inspector enters
  from the right. A document switch is instant.
- A graph node's dim or highlight fades; a settled node never moves.
- `prefers-reduced-motion` keeps the state change and removes movement.

- A detail document orders its cards by immediate reader need. Every card is
  open and static; the index rail carries navigation and the deck reads left to
  right. The order is per kind, not a global section list.

## Panels and persistence

- The shell owns side-bar visibility, width and the split between its sections.
  A document never resizes the workbench.
- Every detail document shares one section rhythm: the deck uses the same group
  gap between cards, and each card body starts a group gap below its title. A
  view does not add its own section margins.
- Both side-bar sections start expanded, split 50/50. Each body sits directly
  below its header; the separator between the two open sections is adjustable. The
  tab-strip toggle and `Cmd/Ctrl+B` change side-bar visibility, not purpose.
- Geometry is one workbench value per snapshot. Opening a side-bar section or a
  tab never changes it.
- The editor tab strip is one global document strip. Its tab views are **Graph**
  (pinned), **Workflow** (pinned), subject documents (node, edge, property,
  asset, abstract) and step documents. A click on the canvas is transient
  inspection, not a document; it never opens a tab. Every tab is mounted in its
  own pane and keeps its own editor state and scroll position.
- A single click in the Explorer tree opens or reuses one preview tab, like VS
  Code. Double-clicking the row, using **Open Detail**, choosing **Go to Detail**
  in a context menu, or using the command palette opens a permanent tab. The
  context menu also offers **Go to Graph** for graph subjects and **Go to
  Workflow** for workflow items. A workflow component selected in Control or in
  the Workflow graph expands its step group in Explorer. That reveal is
  one-shot: once the reader collapses the Workflow section or a component group,
  it stays collapsed until the active subject changes again.
  Preview tabs are reused by the next single click; double-clicking a preview
  tab label pins it. Middle-clicking a subject or step tab closes it; pinned
  Graph and Workflow tabs cannot be closed.
- There is no mode and no automatic section switching. Control and Explorer are
  side-bar sections; changing section never changes the active tab, and changing
  tab never opens, closes or switches the open sections or panel geometry.
  Control shows controls for the active view; Explorer always states the whole
  design. Opening the same subject again activates its existing tab.
- Back and forward walk the activated-tab history (`Alt+←` / `Alt+→`, the arrows
  in the tab strip, or the mouse back/forward buttons). Opening, activating or
  closing a tab records one navigation step; changing selection inside the
  active tab does not.

## One region, one job

- The side bar carries view controls (Control) and design navigation (Explorer).
  It does not repeat the selected subject.
- The Graph document carries the graph inspection as a floating **Inspect**
  window. A subject document carries its own meaning and properties. The two
  never share a panel, so opening a tab cannot change inspection.
- Cognitive Load (Laws of UX): repeating the same properties in two regions is
  extraneous load — it consumes attention without adding understanding.
- Law of Common Region (Laws of UX): a boundary is a promise about what belongs
  inside it. Duplicating properties across the side bar and the Graph inspector
  breaks that promise, so each region keeps one job.

## Selection

- Selection is one subject plus the function that owns its current reading.
- Orange is the selected graph item; blue is focus, active tab and primary
  action. They are not interchangeable.
- Selecting in the canvas highlights the same subject in the Graph inspector and
  tab strip. It does not open a document tab or change the panel geometry.
- Inspection and documents are different: inspection is transient state on the
  canvas or in the floating Inspector; a document is a tab. A canvas click
  updates inspection. **Open Detail**, **Go to Detail** in a context menu, a
  Explorer tree row or the command palette opens a document.
- A selection that a function cannot resolve falls back to that function's
  first valid subject, rather than an empty editor.

## Reading flows

**Orient.** Control → filter or zoom → select a node or relation → read the
selection detail → open Detail for its properties, provenance and attached
claims and limits.

**Open detail.** Select a node or edge in the Graph → read its properties and
meaning → **Open in Detail** → select a property to read its branches, lanes and
type/presence chain. When the question widens, open the parent subject from the
Explorer tree; it becomes its own document tab.

**Read the workflow.** Open **Workflow** → read the component map → click a
component to select it; its aggregated links highlight → **Open step group** →
filter with Control → click a step node; its connections highlight the same way
→ **Open step** → read its openings, instruction payload, connections and
blueprint bindings. A boundary node selects like any other node; **Open step
group** enters that component. **Back** returns to the component map.

**Read the design.** Inspect states the graph purpose and its full claims and
limitations on demand when nothing is selected; the editor reads the selected
subject in the shared order, from the banner overview through fulfilment, sources, build
steps, expression, members, connections and bindings.

## Writing rules for the UI

- State the question, not the data type: "Where does this value come from?",
  not "Provenance".
- Name a hidden layer in its control: "Show limitations" reveals limitations.
- A count without a noun is noise: "9 claims", not "9".
- A control that only changes presentation is a toggle, chip or select. A
  control that changes scope is a row or tab.
- Never use audit vocabulary in the design reader: no finding, decision,
  coverage, sign-off, severity or review state.
