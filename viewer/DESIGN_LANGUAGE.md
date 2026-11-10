# Viewer design language

The viewer is one application, not a collection of screens. It reads a graph
design through two angles and one shared ladder. Each level answers one
question and owns one kind of chrome. A level may be omitted; it may not be
reordered, duplicated or wrapped in another level of the same kind.

The visible hierarchy is in `HIERARCHY.md`; the skin is in
`DESIGN_BLENDER.md`.

## The ladder

```text
Window        where am I, and what design am I reading?
  Function    Topology or Detail: how close am I looking?
    Panel     which region answers it: side bar, editor or bottom?
      Section which facet of the subject?
        Row   which item?
          Field what value?
            Control one action or reveal
```

- **Window** owns identity: brand, snapshot, global search, zoom, panel
  visibility.
- **Function** owns one question and one model slice. It is the only level that
  changes what the side bar, editor and bottom panel mean.
- **Panel** owns one region, one header and one body. A panel never contains
  another panel of the same kind.
- **Section** owns one question inside a panel. If it needs "and", it is two
  sections.
- **Row** is one subject: a node, relation, property, step, claim, frame or
  asset.
- **Field** is one value of that subject.
- **Control** is one action or one reveal. It never carries content.

## The two angles

| Function | Question | What it contains |
| --- | --- | --- |
| Topology | What exists, how is it connected, and what does each entity declare? | graph nodes, relations, categories, the selected entity's properties and attached meaning |
| Detail | What exactly is this subject? | its meaning, properties, provenance and attached semantics |

The functions share one design object, not a page. A node selected in Topology
is the same node opened in Detail. Topology states what an author must know
immediately; Detail adds the evidence and the full record.

## Detail is earned

The first paint states the design, not every annotation.

- **Low detail is the default.** Topology labels hubs only; edge labels,
  containment, semantics badges and property lists are off. Detail shows the
  selected subject's meaning and properties; graph claims and frames are
  revealed on demand.
- **A reveal is explicit.** Every hidden layer has one control that names it.
  A control's state is visible; a revealed layer is one click away from hidden.
- **A reveal does not change scope.** Turning on semantics labels adds evidence
  to the same graph; it does not switch function or selection.
- **No raw JSON in the default surface.** A design reader shows named values,
  not serialised models. JSON is not a tab in the bottom panel.
- **Counts are honest.** A collapsed section states how many items it holds, so
  the reader knows what is hidden without expanding it.

## Detail levels by surface

| Surface | Level 1 (default) | Level 2 | Level 3 |
| --- | --- | --- | --- |
| Topology | circles, thin relation links, hub labels, graph purpose | all labels, relation names | containment, semantics, property counts |
| Topology selection | identity and description | properties with types | attached claims, frames and limitations |
| Detail | subject meaning and properties | attached semantics along the path | property provenance, type/presence chain and trace |

The level switch is part of the function's own header or side bar. It is not a
global setting, because each question has its own useful first level.

## Panels and persistence

- The shell owns panel visibility, width and height. A function never resizes
  the workbench.
- Both panels are shown by default. The side bar is View/Browse; the bottom
  panel is Inspect/Evidence. The title bar toggle and `Cmd/Ctrl+J` change the
  bottom panel's visibility, not its purpose.
- Geometry is one workbench value per snapshot, not one per function. Switching
  activity changes the content inside the same side bar and bottom panel.
- The editor tab strip is one global document strip. Graph is a pinned tab;
  Detail subjects are closable tabs. Opening the same subject again activates
  its existing tab instead of duplicating it.
- Back and forward walk the activated-tab history (`Alt+←` / `Alt+→` or the
  arrows in the tab strip). Opening, activating or closing a tab records one
  navigation step; changing selection inside the active tab does not.
- The bottom panel is selection detail, not output. It has no Data tab.

## One region, one job

- The side bar carries controls or navigation for the active angle: **View** in
  Topology, **Browse** in Detail. It does not repeat the selected subject.
- The bottom panel carries the inspection of that subject: **Inspect** in
  Topology, **Trace/Evidence** in Detail. It is the only place where the
  selected subject's properties and meaning are expanded.
- Cognitive Load (Laws of UX): repeating the same properties in two regions is
  extraneous load — it consumes attention without adding understanding.
- Law of Common Region (Laws of UX): a boundary is a promise about what belongs
  inside it. Duplicating properties across the side bar and the bottom panel
  breaks that promise, so each region keeps one job.

## Selection

- Selection is one subject plus the function that owns its current reading.
- Orange is the selected graph item; blue is focus, active tab and primary
  action. They are not interchangeable.
- Selecting a row highlights the same subject in the side bar, editor and
  status bar. It does not open the bottom panel by itself.
- A selection that a function cannot resolve falls back to that function's
  first valid subject, rather than an empty editor.

## Reading flows

**Orient.** Topology → filter or zoom → select a node or relation → read the
selection detail → open Detail for its properties, provenance and attached
claims and limits.

**Open detail.** Select a node or edge in Topology → read its properties and
meaning → **Open in Detail** → select a property to read its branches, lanes and
type/presence chain, or switch level (node, edge, abstract, asset) when the
question widens.

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
