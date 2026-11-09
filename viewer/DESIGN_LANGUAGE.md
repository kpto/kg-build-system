# Viewer design language

The viewer is one application, not a collection of screens. It reads a graph
design through three functions and one shared ladder. Each level answers one
question and owns one kind of chrome. A level may be omitted; it may not be
reordered, duplicated or wrapped in another level of the same kind.

The visible hierarchy is in `HIERARCHY.md`; the skin is in
`DESIGN_BLENDER.md`.

## The ladder

```text
Window        where am I, and what design am I reading?
  Function    Topology, Proof or Meaning: which question am I asking?
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

## The three functions

| Function | Question | Model slice |
| --- | --- | --- |
| Topology | What exists, and how is it connected? | graph nodes, relations, categories |
| Proof | Where does this value come from? | one property's bindings, sources, operators and target |
| Meaning | What does the design claim, and within which limits? | graph purpose, frames, claims and attached subject semantics |

The functions share a scope, not a page. A selected node in Topology, a proof
subject, and a semantic subject are the same design object seen through three
slices. Switching function keeps the selection where the slice can resolve it.

## Detail is earned

The first paint states the design, not every annotation.

- **Low detail is the default.** Topology labels hubs only; edge labels,
  containment, semantics badges and property lists are off. Meaning shows the
  purpose and counts; frames, limitations, claims and subjects are collapsed.
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
| Topology | circles, thin relation links, hub labels | all labels, relation names | containment, semantics, property counts |
| Proof | property lanes and type chain | node/edge/abstract union | asset reverse index |
| Meaning | purpose and counts | claims and frames | limitations and attached subject semantics |

The level switch is part of the function's own header or side bar. It is not a
global setting, because each question has its own useful first level.

## Panels and persistence

- The shell owns panel visibility, width and height. A function never resizes
  the workbench.
- The bottom panel starts hidden. The title bar toggle and `Cmd/Ctrl+J` open it.
- Sizes and selection persist per snapshot and function. Switching function
  restores that function's arrangement; content changes never resize a panel.
- The bottom panel is selection detail, not output. It has no Data tab.

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
selection detail → open Proof or Meaning when the question changes.

**Prove.** Proof → search a property in the side bar → read the branch's lanes
and type/presence chain → switch level (node, edge, abstract, asset) when the
question widens.

**Read meaning.** Meaning → read the purpose → expand frames and limitations →
reveal claims → search attached subject semantics → read a subject's claims and
frames in the editor.

## Writing rules for the UI

- State the question, not the data type: "Where does this value come from?",
  not "Provenance".
- Name a hidden layer in its control: "Show limitations" reveals limitations.
- A count without a noun is noise: "9 claims", not "9".
- A control that only changes presentation is a toggle, chip or select. A
  control that changes scope is a row or tab.
- Never use audit vocabulary in the design reader: no finding, decision,
  coverage, sign-off, severity or review state.
