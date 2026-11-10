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
  containment, semantics badges and property lists are off. A subject document
  shows its meaning and properties; graph claims and frames are revealed on
  demand in the Explorer section. The Workflow shows the compositor graph; a
  step document reveals complex payload values on demand.
- **A reveal is explicit.** Every hidden layer has one control that names it.
  A control's state is visible; a revealed layer is one click away from hidden.
- **A reveal does not change scope.** Turning on semantics labels adds evidence
  to the same graph; it does not switch function or selection.
- **No raw JSON in the default surface.** A design reader shows named values,
  not serialised models.
- **Counts are honest.** A collapsed section states how many items it holds, so
  the reader knows what is hidden without expanding it.

## Detail levels by surface

| Surface | Level 1 (default) | Level 2 | Level 3 |
| --- | --- | --- | --- |
| Graph document | circles, thin relation links, hub labels | all labels, relation names | containment, semantics, property counts |
| Graph inspection | graph purpose and counts when nothing is selected; otherwise identity and description | properties with types | attached claims, frames and limitations |
| Workflow document | one graph view with no banner: a compositor-style component graph, or a step-level flow graph where steps fill columns top-to-bottom after **Open step group**; selecting any node, including a boundary component, highlights its incident links and dims the other nodes in both; Back and the open actions sit in the canvas toolbar; drag to pan and wheel to zoom | aggregated connection counts and active components | the step catalogue in Explorer and its step documents |
| Step document | identity, instruction and openings on the shared detail surface | payload values | connections and blueprint bindings |
| Table document | identity, owning asset, columns and an expression tree from asset to fields; the effective licence is in the banner | column types and descriptions | attached semantics |
| Projection document | identity, owning asset, columns, row source and an expression tree from asset to fields; the effective licence is in the banner | column types and descriptions | attached semantics |
| Subject document | provenance references, the narrowed workflow graph and an expression tree from asset to the current item for node, edge and property; the effective licence is in the banner; then subject meaning and properties | attached semantics along the path | property provenance, type/presence chain and trace |

Every workflow graph, the narrowed detail graph and the expression tree use one
scene renderer and one pan/zoom canvas. A graph's scene is data; the canvas owns
only the viewport. Drag pans, the wheel zooms, Fit resets and clicking empty
space clears the selection.

Each subject or step document is a separate tab. There is no level switch in
the editor; opening a parent node, edge, asset or abstract category from the
Explorer tree opens or activates that document.

A graph layout settles to a stable map. Selecting or inspecting a node never
restarts the layout or moves the node; only a drag changes a node position, and
only an explicit fit, zoom or navigation control changes the viewport.

A detail document banner leads with a large logo for its kind: node, edge,
property, asset, abstract category or step. The Workflow and Graph documents are
working surfaces; they have no banner, and their actions live in floating canvas
toolbars. The tab already names the document.

Node, edge and property documents open with a **Provenance** section that lists
the resolved assets, tables and projections behind the subject, before design
meaning and properties. It is a summary; the property document's lineage canvas
shows the full branch. Each provenance group header carries its concept mark;
the values are text references, and each reference opens the asset document that
owns it; a table or projection reference opens its own Table or Projection
document. A node or edge with
no declared properties still derives provenance from its binding identity,
source and target expressions. The section ends with the **effective licence**
resolved from those provenance assets: one declared licence, a mixed list, or
`Not declared`.

Below provenance, a narrowed **Workflow** graph shows the steps that produce the
subject. It uses the same step scene and selection rule as the Workflow
document. An edge banner also names its source and target nodes as navigable
references. Section headers carry the concept mark of their subject.

One concept registry supplies the logo and representative colour for graph,
workflow, node, edge, property, asset, table, projection, abstract category and
step. A detail banner, a tab and a provenance reference read the same registry,
so an asset is the same green database mark wherever it appears.

## Interaction motion

- Motion is feedback, not decoration. Hover, selection and press changes use
  short transitions; entrance layers use opacity plus a small transform.
- The workbench curve is `--ease-instrument`. Micro-interactions stay under
  200ms; a settings dialog may take 200ms.
- Buttons press with a subtle scale. Tabs transition their surface and active
  indicator. Context menus enter from the pointer origin; the Graph inspector
  enters from the right.
- A graph node's dim or highlight fades; a settled node never moves.
- `prefers-reduced-motion` keeps the state change and removes movement.

## Panels and persistence

- The shell owns side-bar visibility, width and the split between its sections.
  A document never resizes the workbench.
- Both side-bar sections start expanded, split 50/50. Each body sits directly
  below its header; the separator between the two open sections is adjustable. The
  title-bar toggle and `Cmd/Ctrl+B` change side-bar visibility, not purpose.
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
  the Workflow graph expands its step group in Explorer. The title-bar folder button
opens another workflow or snapshot JSON without changing the workbench frame.
That reveal is one-shot:
  once the reader collapses the Workflow section or a component group, it stays
  collapsed until the active subject changes again.
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
  status bar. It does not open a document tab or change the panel geometry.
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
frames on demand when nothing is selected; the editor states the selected
subject's meaning and properties before its provenance.

## Writing rules for the UI

- State the question, not the data type: "Where does this value come from?",
  not "Provenance".
- Name a hidden layer in its control: "Show limitations" reveals limitations.
- A count without a noun is noise: "9 claims", not "9".
- A control that only changes presentation is a toggle, chip or select. A
  control that changes scope is a row or tab.
- Never use audit vocabulary in the design reader: no finding, decision,
  coverage, sign-off, severity or review state.
