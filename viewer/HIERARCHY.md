# KG design viewer hierarchy

The current application is a two-function VS Code-style workbench. The visual
rules remain in `DESIGN_LANGUAGE.md` and `DESIGN_BLENDER.md`; this file states
the structure.

## Ladder

```text
Window        the KG design viewer
  Function    Topology | Detail
    Side Bar  the function's subjects, filters and detail controls
    Editor    the function's canvas or detail layout
    Bottom    the selected subject's inspection detail, shown by default
      Section one question inside a body
        Row   one node, relation, step, claim, frame or property
          Field one value
```

A level may be absent. It is never reordered or nested inside the same kind.

## Window

| Region | Contents | Owner |
| --- | --- | --- |
| Title bar | brand, active function, snapshot name/title, command trigger, sidebar/bottom toggles, layout reset | `workbench/TitleBar` |
| Activity bar | Topology, Detail, Search, Settings | `workbench/ActivityBar` |
| Side bar | active function's sidebar | feature `Sidebar` |
| Editor | tabs + active function body | feature `Editor` |
| Bottom panel | selected subject detail; shown by default | feature `Bottom` |
| Status bar | snapshot, selected subject, node/edge/binding counts, compile-only, zoom | `workbench/StatusBar` |

The side bar is 220–520 px, the bottom panel 120–480 px. Each function owns a
persisted `FunctionLayout` and selection; switching functions restores both.
The bottom panel's visibility is shell state and starts true.

## Functions

| Function | Side bar | Editor | Bottom |
| --- | --- | --- | --- |
| Topology | **View**: counts, filters, canvas detail controls, legend, fit/reset/pin | D3 force graph, zoom/pan/drag, selection | **Inspect**: graph purpose and selection instructions; when selected, identity, properties and meaning with **Open in Detail** |
| Detail | **Browse**: graph meaning summary and design tree | design meaning, property table, provenance lanes and type/presence chain, attached semantics | Trace, Evidence |

## Display defaults

| Control | Default | Meaning |
| --- | --- | --- |
| Topology labels | hubs | label hubs only; `off` and `all` are available |
| Topology properties | selected entity | property names and types appear in the sidebar as soon as a node or edge is selected |
| Topology meaning | selected entity | attached claims and frames appear beside the properties |
| Graph purpose | summary | full claims and frames have a named reveal |
| Topology edge labels | off | relation names hidden |
| Topology containment | off | category structure hidden |
| Topology semantics | off | no semantics badges |
| Topology properties | off | no property lists |
| Detail meaning | full | the selected subject's claims and frames are part of the detail layout |
| Detail provenance | on property | selecting a property shows its branches, lanes and type/presence chain |
| Bottom panel | shown | toggle in the title bar or `Cmd/Ctrl+J` |

## Removed surfaces

Audit, decisions, coverage, sign-off, review sidecars, findings, severity
filters, the semantic ledger, JSON/Data tabs, Map/Explore/Review campaign,
Outliner, whole-graph Blueprint, Dossier, Build audit, Diff destination and the
old properties rail are not part of the viewer. Proof is no longer an activity;
it is the provenance section of Detail. Meaning is no longer an activity; it is
part of both the canonical Topology card and the Detail layout.
