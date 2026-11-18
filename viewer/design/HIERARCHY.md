# KG design viewer hierarchy

The viewer is one workbench with one document tab strip and one collapsible
side-bar section. The visual rules are in `DESIGN_LANGUAGE.md`, the detail content contract is
in `DETAIL_CONTENT.md`, and the skin is in `DESIGN_BLENDER.md`; this file states
the structure.

## Ladder

```text
Window        the KG design viewer
  Document    Graph | Workflow | Subject document: what the editor renders
    Side bar  Explorer: design navigation, not a mode
      Section one question inside the side-bar section
        Row   one node, relation, property, step, claim, frame or asset
          Field one value
```

A level may be absent. It is never reordered or nested inside the same kind.

## Window

| Region | Contents | Owner |
| --- | --- | --- |
| Side bar | collapsible **Explorer** section | `workbench/SideBar` |
| Editor | document tabs with the side-bar toggle at the right of the strip, and one mounted pane per document | `workbench/EditorArea` |

The side bar is 220–520 px wide and is the only resizable panel. One
`WorkbenchLayout` is persisted per snapshot: the side-bar width. Side-bar
visibility is shell state;
the tab-strip toggle and `Cmd/Ctrl+B` change it, not panel purpose. There is no
window header or status bar. The Graph document owns its floating Inspector
window; there is no bottom panel.

## Side-bar sections

| Section | Contents |
| --- | --- |
| **Explorer** | everything in the design: assets, nodes, abstract categories, edges and their properties, bindings; workflow components and their step catalogue. A context menu jumps graph subjects to the Graph and workflow items to the Workflow. A selected workflow component expands its step group; an explicit collapse sticks until the active subject changes. Source relations, derived relations and bindings are outline groups; each row opens its own document. |

The section is collapsible and expanded by default. Its body sits directly
below its header. Its open state is user state: opening or activating a tab
never opens or closes it, and opening it never changes the active document or
its editor. A visualisation carries the controls that change it: the Graph has
a compact toolbar and a View popover, and the Workflow has a filter bar.
Explorer always states the whole design. A tab is a standalone document that
retains its editor state and scroll position.

## Documents and tabs

| Document | Editor |
| --- | --- |
| **Graph** (pinned) | shared visualisation frame with a header (view name, visible node/link counts, **Inspect** toggle) above a D3 force canvas; bottom-left zoom/Fit navigation; floating Inspector shows graph purpose/overview when nothing is selected, or the selected entity's identity, properties and meaning; clicking empty space deselects |
| **Workflow** (pinned) | compositor-style component graph in the same visualisation frame; the header names the workflow or focused component, states component or step counts and carries step-group actions; selecting a component and using **Open step group** drills into its step-level flow graph with one block per dependency layer, a large layer wrapping into aligned sub-columns, and boundary components aligned to the steps they feed; selecting a component, step or boundary node highlights its incident links and dims the other nodes in the same graph view, and entering another step group requires **Open step group**; drag to pan, wheel to zoom, Fit in the navigation cluster resets; Back returns to components; the Workflow filter bar narrows the step graph |
| **Step** | one workflow step's instruction, payload, openings, connections and blueprint bindings on the same detail surface as node and subject documents; opened from the workflow section of Explorer |
| **Source relation** | a source relation's identity, contract, owning asset, columns, its Constitution (current purpose and fulfilment as the two top boxes on opposite sides of the separator, bound records, relation and asset branches), its full meaning in the Meaning band and its Bindings table; the effective licence is in the banner. Its bindings carry the expressions and build steps. |
| **Derived relation** | a derived relation's identity, contract, columns, row source, its Constitution (current purpose and fulfilment as the two top boxes on opposite sides of the separator, bound records, relation and asset branches), its full meaning in the Meaning band and its Bindings table; the effective licence is in the banner. Its bindings carry the expressions and build steps. |
| **Binding** | one binding's Meaning (when present), Expression and Build steps on the same detail surface; the banner states record, writes, identity, rows read, step and output; opened from the Explorer Bindings group, a record's Bindings table or a binding pill |
| **Subject** (node, edge, property, asset, abstract) | Meaning first, then the Constitution tree (current subject's purpose and fulfilment as the two top boxes on opposite sides of the separator, a horizontal fulfilment-to-purpose arrow, graph branch from its immediate parent down to the graph purpose, relation branch with its provenance branches below, axis legends at the bottom centre of each lane; hovering a box shows its full meaning, and a label opens that level), the subject's members/properties/connections and its Bindings table; the effective licence is in the banner |

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
