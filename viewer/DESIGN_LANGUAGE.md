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
  node, edge, property, asset or abstract category opened from the Explorer tree,
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
| Explorer | What does the design contain? | assets, nodes, abstract categories, edges, properties and the workflow components and steps; it always lists the whole design |

There is no mode switch. Opening a side-bar section changes the side bar, not
the active document or its editor. Control follows the active view; a subject
document has no view controls. A graph selection is transient inspection; a
subject document is an explicit tab.

## Detail is earned

The first paint states the design, not every annotation.

- **Low detail is the default.** The Graph labels hubs only; edge labels,
  containment, meaning badges and property lists are off. A subject document
  shows its overview, constitution and meaning; graph claims and limitations are revealed on
  demand in the Explorer section. The Workflow shows the compositor graph; a
  step document reveals complex payload values on demand.
- **A reveal is explicit.** Every hidden layer has one control that names it.
  A control's state is visible; a revealed layer is one click away from hidden.
- **A reveal does not change scope.** Turning on meaning labels adds evidence
  to the same graph; it does not switch function or selection.
- **No raw JSON in the default surface.** A design reader shows named values,
  not serialised models.
- **Counts are honest.** A collapsed section states how many items it holds, so
  the reader knows what is hidden without expanding it.

## Detail content

Every item detail view follows one content contract, stated in
[`DETAIL_CONTENT.md`](./DETAIL_CONTENT.md). The shared order is:

```text
Banner: Overview
Constitution → Meaning → Sources → Build steps → Expression
         → Members → Connections → Bindings
```

A kind includes or omits a section; it never renames one for itself.

- **Overview** is the tab banner: identity and one fact row. It is not a band.
- **Constitution** puts the current subject's purpose and Fulfilment as the
  two top boxes, on opposite sides of a dashed divider; a horizontal arrow runs
  from Fulfilment to Purpose. The Graph branch below Purpose is the record axis,
  ordered from the subject's immediate parent down to the graph purpose. The
  Relation branch below Fulfilment is the relation axis; it carries its
  provenance branches below its relation. Fulfilment is the relation side's top
  box, not a relation declaration. Every stacked item uses the same vertical
  gap. Each box states only its own purpose and clamps; arrows point up to the
  purpose it supports. Hovering or focusing a box reveals its full meaning in a
  portal card; a box label opens that level's document. A grouped branch shows
  the first item and `+N`. The axis legend sits at the bottom centre of each
  lane.
- **Meaning** is the full meaning of the current subject: purpose, the
  limitations it owns, then contextless claims. It is a separate card from the
  Constitution, so a reader can see the two axes and the subject's complete
  meaning in turn.
- **Sources**, **Build steps** and **Expression** are three visualisations of
  one traversal. Sources names the release data; Build steps shows the plan;
  Expression shows the field and operator chain. The UI never uses the labels
  "Provenance" or "Lineage"; the model keeps those words.
- **Members** is one table grammar for properties, columns, fields,
  descendants and openings. The instance pill opens its document when one exists.
- **Connections** states endpoints, incident relations or ports.
- **Bindings** states which binding fulfils the subject.

A kind may state an absence instead of omitting a section. A step has no design
meaning and no release source, and it says so; it is build machinery.

Every tab — detail, Graph and Workflow — uses the same banner. It leads with
the kind's mark from the one concept catalogue and states the identity,
overview facts and the view's own actions. Graph and Workflow keep their
working-surface frame below the banner; every graph surface shares one
bottom-left navigation cluster.

One concept catalogue in `shared/ui/concepts.tsx` supplies the mark and
representative colour for every layer: graph, abstract category, node, edge,
property, asset, source relation, derived relation, field, binding, workflow,
step and meaning. A banner, a tab, a section reference, an expression row and a
membership row read the same catalogue, so an asset is the same green cylinder
mark wherever it appears. The marks share one grammar — a 24 px grid, a 1.6 px
stroke and round joins — and the concept's one filled element takes a 24% tint
when it is active. Colour is a second cue; the silhouette and the label carry
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
feature's one card primitive: it composes `Panel` and `PanelHeaderButton` and
adds the section title, concept mark, collapse state and, while collapsed, one
count. The section question is the header's title and accessible description,
not a visible line. The card may not re-declare a surface or header; those
belong to the generic layer.

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

- A detail document orders its cards by immediate reader need. A **primary**
  card opens by default; a **secondary** card starts collapsed. The order and
  class are per kind, not a global section list.

## Panels and persistence

- The shell owns side-bar visibility, width and the split between its sections.
  A document never resizes the workbench.
- Every detail document shares one section rhythm: the body is a column with the
  same gap between provenance, workflow, expression tree, meaning and proof
  regions. A view does not add its own section margins.
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
