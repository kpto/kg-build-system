# KG design viewer hierarchy

The viewer is one workbench with one document tab strip and two collapsible
side-bar sections. The visual rules are in `DESIGN_LANGUAGE.md` and
`DESIGN_BLENDER.md`; this file states the structure.

## Ladder

```text
Window        the KG design viewer
  Document    Graph | subject document: what the editor renders
    Side bar  Topology | Detail: collapsible sections, not modes
      Section one question inside the active side-bar section
        Row   one node, relation, property, step, claim, frame or asset
          Field one value
```

A level may be absent. It is never reordered or nested inside the same kind.

## Window

| Region | Contents | Owner |
| --- | --- | --- |
| Title bar | brand, snapshot, command trigger, sidebar/bottom toggles, layout reset, settings | `workbench/TitleBar` |
| Side bar | collapsible **Topology** and **Detail** sections | `workbench/SideBar` |
| Editor | global document tabs + active document body | `workbench/EditorArea` |
| Bottom panel | Inspect for the Graph document; Trace/Evidence for a subject document | `workbench/BottomPanel` |
| Status bar | snapshot, document view, selected subject, counts, compile-only, zoom | `workbench/StatusBar` |

The side bar is 220–520 px, the bottom panel 120–480 px. One `WorkbenchLayout`
is persisted per snapshot. Panel visibility is shell state; both panels start
visible. The title-bar toggles and `Cmd/Ctrl+J`/`Cmd/Ctrl+B` change visibility,
not panel purpose.

## Side-bar sections

| Section | Contents |
| --- | --- |
| **Topology** | canvas filters, labels, Show controls, legend, fit/zoom/pin |
| **Detail** | graph meaning, design tree of assets, relations, projections, nodes, edges and properties |

The sections are collapsible; opening one collapses the other. The section
follows the active document type by default, but selecting a section never
changes the active document or its editor. A tab is a document, not a mode.

## Documents and tabs

| Document | Editor | Bottom |
| --- | --- | --- |
| **Graph** (pinned) | D3 force canvas, zoom/pan/drag, inspection | Inspect: graph purpose/overview, or selected entity identity, properties and meaning |
| **Subject** (node, edge, property, asset, abstract) | design meaning, properties, attached semantics and, for a property, provenance lanes and type/presence | Trace, Evidence |

A node or property click only changes transient inspection. A document opens
only through an explicit action: **Open Detail**, the Detail tree, a Detail
property row, or the command palette. Back/forward walk the document history.

## Removed surfaces

Audit, decisions, coverage, sign-off, review sidecars, findings, severity
filters, the semantic ledger, JSON/Data tabs, Map/Explore/Review campaign,
Outliner, whole-graph Blueprint, Dossier, Build audit, Diff destination, the old
properties rail, the left activity toolbar, and the global Topology/Detail mode
switch are not part of the viewer.
