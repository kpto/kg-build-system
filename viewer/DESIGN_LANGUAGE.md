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
  canonical; a subject document is a node, edge, property, asset or abstract
  category opened from the Detail tree, a context menu or the command palette.
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
| Topology | What does the canvas show? | graph filters, labels, Show controls, legend, layout |
| Detail | What does the design contain? | graph meaning and the design tree used to open documents |

There is no mode switch. Opening a side-bar section changes the side bar, not
the active document or its editor. A graph selection is transient inspection;
a subject document is an explicit tab.

## Detail is earned

The first paint states the design, not every annotation.

- **Low detail is the default.** Topology labels hubs only; edge labels,
  containment, semantics badges and property lists are off. A subject document
  shows its meaning and properties; graph claims and frames are revealed on
  demand in the Detail section.
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
| Graph inspection | identity and description | properties with types | attached claims, frames and limitations |
| Subject document | subject meaning and properties | attached semantics along the path | property provenance, type/presence chain and trace |

Each subject document is a separate tab. There is no level switch in the editor;
opening a parent node, edge, asset or abstract category from the Detail tree
opens or activates that document.

## Panels and persistence

- The shell owns side-bar visibility, width and the split between its sections.
  A document never resizes the workbench.
- Both side-bar sections may be expanded at once. Each body sits directly below
  its header; the separator between the two open sections is adjustable. The
  title-bar toggle and `Cmd/Ctrl+B` change side-bar visibility, not purpose.
- Geometry is one workbench value per snapshot. Opening a side-bar section or a
  tab never changes it.
- The editor tab strip is one global document strip. Its tab views are **Graph**
  (pinned) and **subject documents** (node, edge, property, asset, abstract). A
  click on the canvas is transient inspection, not a document; it never opens a
  tab. Every tab is mounted in its own pane and keeps its own editor state and
  scroll position.
- A single click in the Detail tree opens or reuses one preview tab, like VS
  Code. Double-clicking the row, using **Open Detail**, choosing **Go to Detail**
  in a context menu, or using the command palette opens a permanent tab.
  Preview tabs are reused by the next single click; double-clicking a preview
  tab label pins it.
- There is no mode and no automatic coupling. Topology and Detail are side-bar
  sections; changing section never changes the active tab, and changing tab
  never changes the open section or panel geometry. Opening the same subject
  again activates its existing tab.
- Back and forward walk the activated-tab history (`Alt+←` / `Alt+→`, the arrows
  in the tab strip, or the mouse back/forward buttons). Opening, activating or
  closing a tab records one navigation step; changing selection inside the
  active tab does not.

## One region, one job

- The side bar carries canvas controls (Topology) and design navigation
  (Detail). It does not repeat the selected subject.
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
  Detail tree row or the command palette opens a document.
- A selection that a function cannot resolve falls back to that function's
  first valid subject, rather than an empty editor.

## Reading flows

**Orient.** Topology → filter or zoom → select a node or relation → read the
selection detail → open Detail for its properties, provenance and attached
claims and limits.

**Open detail.** Select a node or edge in Topology → read its properties and
meaning → **Open in Detail** → select a property to read its branches, lanes and
type/presence chain. When the question widens, open the parent subject from the
Detail tree; it becomes its own document tab.

**Read the design.** Detail's sidebar states the graph purpose and its full
claims and frames on demand; the editor states the selected subject's meaning
and properties before its provenance.

## Writing rules for the UI

- State the question, not the data type: "Where does this value come from?",
  not "Provenance".
- Name a hidden layer in its control: "Show limitations" reveals limitations.
- A count without a noun is noise: "9 claims", not "9".
- A control that only changes presentation is a toggle, chip or select. A
  control that changes scope is a row or tab.
- Never use audit vocabulary in the design reader: no finding, decision,
  coverage, sign-off, severity or review state.
