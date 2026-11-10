# KG design viewer hierarchy

The viewer is one workbench with one document tab strip and two collapsible
side-bar sections. The visual rules are in `DESIGN_LANGUAGE.md` and
`DESIGN_BLENDER.md`; this file states the structure.

## Ladder

```text
Window        the KG design viewer
  Document    Graph | Workflow | Subject document: what the editor renders
    Side bar  Control | Detail: collapsible sections, not modes
      Section one question inside the active side-bar section
        Row   one node, relation, property, step, claim, frame or asset
          Field one value
```

A level may be absent. It is never reordered or nested inside the same kind.

## Window

| Region | Contents | Owner |
| --- | --- | --- |
| Title bar | brand, snapshot, command trigger, side-bar toggle, layout reset, settings | `workbench/TitleBar` |
| Side bar | collapsible **Control** and **Detail** sections | `workbench/SideBar` |
| Editor | global document tabs + one mounted pane per document | `workbench/EditorArea` |
| Status bar | snapshot, document view, selected subject, counts, compile-only, zoom | `workbench/StatusBar` |

The side bar is 220–520 px wide and is the only resizable panel. One
`WorkbenchLayout` is persisted per snapshot: the side-bar width and the split
between the Control and Detail sections. Side-bar visibility is shell state;
`Cmd/Ctrl+B` changes it, not panel purpose. The Graph document owns its floating
Inspector window; there is no bottom panel.

## Side-bar sections

| Section | Contents |
| --- | --- |
| **Control** | controls for the active view: graph canvas filters, labels, Show controls, legend and fit/zoom/pin; workflow component, instruction and text filters. |
| **Detail** | graph meaning and the design tree of assets, nodes, abstract categories, edges and their properties. Relations and projections are shown inside their asset document, not as tree rows that all resolve to that asset. |

The sections are collapsible and independent: both may be expanded at once.
Each expanded body sits directly below its own header. When both are open, a
horizontal separator sets their shares and the split is persisted. The open
sections are user state: opening or activating a tab never opens, closes or
switches them, and opening a section never changes the active document or its
editor. The Control body follows the active view. A tab is a standalone document
that retains its editor state and scroll position.

## Documents and tabs

| Document | Editor |
| --- | --- |
| **Graph** (pinned) | D3 force canvas, zoom/pan/drag and the floating **Inspect** window: graph purpose/overview, or the selected entity's identity, properties and meaning |
| **Workflow** (pinned) | step catalogue grouped by component, selected step instruction and payload, openings, connections and blueprint bindings |
| **Subject** (node, edge, property, asset, abstract) | design meaning, properties, attached semantics and, for a property, provenance lanes and type/presence |

A node or property click in the canvas only changes transient inspection.
Single-clicking a Detail tree row opens or reuses one preview tab; double-clicking
it, **Open Detail**, a right-click **Go to Detail**, or the command palette opens
a permanent tab. Middle-clicking a subject tab closes it; the pinned Graph and
Workflow tabs cannot be closed. Every tab's pane stays mounted. Back/forward walk
the document history.

## Removed surfaces

Audit, decisions, coverage, sign-off, review sidecars, findings, severity
filters, the semantic ledger, JSON/Data tabs, Map/Explore/Review campaign,
Outliner, whole-graph Blueprint, Dossier, Build audit, Diff destination, the old
properties rail, the left activity toolbar, and the global view mode switch are not part of the viewer.
