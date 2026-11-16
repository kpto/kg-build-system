# KG design viewer hierarchy

The viewer is one workbench with one document tab strip and two collapsible
side-bar sections. The visual rules are in `DESIGN_LANGUAGE.md`, the detail content contract is
in `DETAIL_CONTENT.md`, and the skin is in `DESIGN_BLENDER.md`; this file states
the structure.

## Ladder

```text
Window        the KG design viewer
  Document    Graph | Workflow | Subject document: what the editor renders
    Side bar  Control | Explorer: collapsible sections, not modes
      Section one question inside the active side-bar section
        Row   one node, relation, property, step, claim, frame or asset
          Field one value
```

A level may be absent. It is never reordered or nested inside the same kind.

## Window

| Region | Contents | Owner |
| --- | --- | --- |
| Side bar | snapshot search trigger (the KG name), collapsible **Control** and **Explorer** sections | `workbench/SideBar` |
| Editor | document tabs, the side-bar toggle at the right of the tab strip, and one mounted pane per document | `workbench/EditorArea` |

The side bar is 220–520 px wide and is the only resizable panel. One
`WorkbenchLayout` is persisted per snapshot: the side-bar width and the split
between the Control and Explorer sections. Side-bar visibility is shell state;
`Cmd/Ctrl+B` and the tab-strip toggle change it, not panel purpose. There is no
window header or status bar; the tab strip is the top of the frame. The Graph document owns its floating
Inspector window; there is no bottom panel.

## Side-bar sections

| Section | Contents |
| --- | --- |
| **Control** | controls for the active view: graph canvas filters, labels, Show controls, legend and fit/zoom/pin; workflow component, instruction and text filters. |
| **Explorer** | everything in the design: assets, nodes, abstract categories, edges and their properties; workflow components and their step catalogue. A context menu jumps graph subjects to the Graph and workflow items to the Workflow. A selected workflow component expands its step group; an explicit collapse sticks until the active subject changes. Tables and projections are outline groups; each row opens its own **Table** or **Projection** document. |

The sections are collapsible and independent: both are expanded by default at
a 50/50 split. Each expanded body sits directly below its own header. When both
are open, a horizontal separator sets their shares and the split is persisted. The open
sections are user state: opening or activating a tab never opens, closes or
switches them, and opening a section never changes the active document or its
editor. Control follows the active view; Explorer always states the whole
design. A tab is a standalone document that retains its editor state and scroll
position.

## Documents and tabs

| Document | Editor |
| --- | --- |
| **Graph** (pinned) | shared visualisation frame: a header with the view name, visible node/link counts and the **Inspect** toggle above a D3 force canvas; bottom-left zoom/fit navigation; floating Inspector shows graph purpose/overview when nothing is selected, or the selected entity's identity, properties and meaning; clicking empty space deselects |
| **Workflow** (pinned) | compositor-style component graph in the same visualisation frame; the header names the workflow or focused component, states component or step counts, and carries step-group actions; selecting a component and using **Open step group** drills into its step-level flow graph with one block per dependency layer, a large layer wrapping into aligned sub-columns, and boundary components aligned to the steps they feed; selecting a component, step or boundary node highlights its incident links and dims the other nodes in the same graph view, and entering another step group requires **Open step group**; drag to pan, wheel to zoom, Fit in the navigation cluster resets; Back returns to components; filters from Control narrow the step graph |
| **Step** | one workflow step's instruction, payload, openings, connections and blueprint bindings on the same detail surface as node and subject documents; opened from the workflow section of Explorer |
| **Table** | a relation's identity, owning asset, columns, indented expression outline from the table back through its fields to the asset, and attached semantics on the shared detail surface; the effective licence is in the banner |
| **Projection** | a projection's identity, owning asset, columns, row source, indented expression outline from each column back through its operators and row source to the asset, and attached semantics on the shared detail surface; the effective licence is in the banner |
| **Subject** (node, edge, property, asset, abstract) | provenance assets, tables and projections first for node, edge and property; asset, table and projection references are navigable to their own documents; the effective licence is in the banner; a pannable, zoomable narrowed workflow graph and an indented expression outline of the actual field and operator chain from the current item back to its provenance assets follows, then design meaning, properties, attached semantics and, for a property, provenance lanes and type/presence |

A node or property click in the canvas only changes transient inspection.
Single-clicking an Explorer row opens or reuses one preview tab; double-clicking
it, **Open Detail**, a right-click **Go to Detail**, or the command palette opens
a permanent tab. The same context menu offers **Go to Graph** for graph subjects
and **Go to Workflow** for workflow components and steps. Middle-clicking a subject or step tab closes it; the pinned Graph and
Workflow tabs cannot be closed. Every tab's pane stays mounted. Back/forward walk
the document history.

## Removed surfaces

Audit, decisions, coverage, sign-off, review sidecars, findings, severity
filters, the semantic ledger, JSON/Data tabs, Map/Explore/Review campaign,
Outliner, whole-graph Blueprint, Dossier, Build audit, Diff destination, the old
properties rail, the left activity toolbar, and the global view mode switch are not part of the viewer.
