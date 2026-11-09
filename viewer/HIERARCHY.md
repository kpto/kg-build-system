# KG Audit hierarchy

The current application is a four-function VS Code-style workbench. The visual
rules remain in `DESIGN_LANGUAGE.md` and `DESIGN_BLENDER.md`; this file states
the structure.

## Ladder

```text
Window        the KG Audit application
  Function    Proof | Audit | Semantics | Topology
    Side Bar  the function's subject/queue/filters
    Editor    the function's board, list or canvas
    Bottom    the function's selected detail, evidence or JSON
      Section one question inside a body
        Row   one subject, finding, unit, node or step
          Field one value
```

A level may be absent. It is never reordered or nested inside the same kind.

## Window

| Region | Contents | Owner |
| --- | --- | --- |
| Title bar | brand, active function, snapshot name/title, command trigger, panel toggles | `workbench/TitleBar` |
| Activity bar | Proof, Audit, Semantics, Topology, Search, Settings | `workbench/ActivityBar` |
| Side bar | active function's sidebar | feature `Sidebar` |
| Editor | tabs + active function body | feature `Editor` |
| Bottom panel | active function's detail tabs | feature `Bottom` |
| Status bar | snapshot, selected subject, decision counts, coverage, mode, zoom | `workbench/StatusBar` |

The side bar is 220–520 px, the bottom panel 120–480 px. Each function owns a
persisted `FunctionLayout` and selection; switching functions restores both.

## Functions

| Function | Side bar | Editor | Bottom |
| --- | --- | --- | --- |
| Proof | assets, relations, projections, nodes, edges, properties | level selector, branch selector, lane proof, type/presence chain, attached semantics | Trace, Evidence, Data |
| Audit | rule groups, severity, subject filters, counts | focused finding queue + selected finding detail + evidence + decision | Problems, Evidence, Data |
| Semantics | graph purpose, claims, frames/limitations, subject groups, status filters | purpose card, ledger, selected unit, decision form, coverage, sign-off | Decisions, Coverage, Data |
| Topology | node/edge filters, semantics/finding filters, legend, layout controls | D3 force graph | Selection, Data |

## Removed surfaces

Map, Explore, Review campaign, Outliner, whole-graph Blueprint, summary rubric,
separate Findings/Questions/Decisions pages, Dossier, Build audit, Diff
destination and the properties rail are not part of the workbench. Workflow
trace is a Proof/Audit detail; topology is the orientation view.
