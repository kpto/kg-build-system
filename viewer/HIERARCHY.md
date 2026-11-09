# KG design viewer hierarchy

The current application is a three-function VS Code-style workbench. The visual
rules remain in `DESIGN_LANGUAGE.md` and `DESIGN_BLENDER.md`; this file states
the structure.

## Ladder

```text
Window        the KG design viewer
  Function    Topology | Proof | Meaning
    Side Bar  the function's subjects, filters and detail controls
    Editor    the function's canvas, proof or reading surface
    Bottom    the selected subject's detail, hidden by default
      Section one question inside a body
        Row   one node, relation, step, claim, frame or property
          Field one value
```

A level may be absent. It is never reordered or nested inside the same kind.

## Window

| Region | Contents | Owner |
| --- | --- | --- |
| Title bar | brand, active function, snapshot name/title, command trigger, sidebar/bottom toggles, layout reset | `workbench/TitleBar` |
| Activity bar | Topology, Proof, Meaning, Search, Settings | `workbench/ActivityBar` |
| Side bar | active function's sidebar | feature `Sidebar` |
| Editor | tabs + active function body | feature `Editor` |
| Bottom panel | selected subject detail; starts hidden | feature `Bottom` |
| Status bar | snapshot, selected subject, node/edge/binding counts, compile-only, zoom | `workbench/StatusBar` |

The side bar is 220–520 px, the bottom panel 120–480 px. Each function owns a
persisted `FunctionLayout` and selection; switching functions restores both.
The bottom panel's visibility is shell state and starts false.

## Functions

| Function | Side bar | Editor | Bottom |
| --- | --- | --- | --- |
| Topology | node/edge and abstract filters; selected-entity navigation; Detail controls for labels, edge labels, containment, semantics and properties; legend; fit/reset/pin | D3 force graph, zoom/pan/drag, selection | Selection detail with **Open in Proof** and **Open in Meaning** |
| Proof | assets, relations, projections, nodes, edges, properties | level selector, branch selector, lane proof, type/presence chain, attached semantics | Trace, Evidence |
| Meaning | purpose summary, frame/claim counts, subject-kind filter and search | purpose card, frames and limitations, claims, attached subject semantics | Details |

## Detail defaults

| Control | Default | Meaning |
| --- | --- | --- |
| Topology labels | hubs | label hubs only; `off` and `all` are available |
| Topology edge labels | off | relation names hidden |
| Topology containment | off | category structure hidden |
| Topology semantics | off | no semantics badges |
| Topology properties | off | no property lists |
| Meaning claims | collapsed | counts only until **Show claims** |
| Meaning frames | collapsed | limitations appear only after expanding a frame |
| Meaning subjects | collapsed | no 5,941-unit dump on first paint |
| Bottom panel | hidden | toggle in the title bar or `Cmd/Ctrl+J` |

## Removed surfaces

Audit, decisions, coverage, sign-off, review sidecars, findings, severity
filters, the semantic ledger, JSON/Data tabs, Map/Explore/Review campaign,
Outliner, whole-graph Blueprint, Dossier, Build audit, Diff destination and the
old properties rail are not part of the viewer. Topology is the orientation
surface; Proof and Meaning are readers of the same design.
