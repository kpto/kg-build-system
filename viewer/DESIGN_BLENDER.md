# Blender UI direction

This document is the **skin**: palette, widgets, node and viewport style.
The hierarchy of Window → Workspace → Panel → Section → Row → Field and the
rules for nesting, actions, selection and detail flow are in
`DESIGN_LANGUAGE.md`. When the two disagree about structure, the design language
wins; when they disagree about colour or a widget, this document wins.

Reference: Blender 4.x dark theme, not a generic dashboard.

## Core language

- **Areas, not floating cards.** The application is a workbench of rounded
  rectangular regions separated by a 2px dark seam. Regions are plates, not
  cards: no glass, no floating panel stacks, no shadow between regions.
- **Application header** is a 32px single line on the `inset` surface: logo,
  `Map | Explore | Review`, search, import. It owns workspace switching only.
- **Area headers** are 32px bands on `panel-raised` with an editor-type icon, a
  sentence-case title, optional counts and right-aligned controls. The Outliner,
  main editor, `Navigator`, `Properties` and the Review rail each render one
  from the shared `shared/ui/PanelHeader.tsx`.
- **Editor tabs.** `Workflow | Blueprint | Lineage` are tabs in the main area
  header, not global tabs. Map and Review are their own editors.
- **Outliner left.** Tree rows with expand chevrons, collection icons, a quiet
  indent guide per depth, blue rounded selection, right-aligned counts and a
  compact filter field.
- **Properties right.** A 42px vertical icon rail with a filled-blue active tab,
  then rounded section bands, two-column label/value fields (right-aligned
  label), wrapping evidence and copy actions.
- **Node editor surfaces.** Dark canvas with a locked grid; neutral cards with a
  3px semantic lane stripe, body, small sockets and bezier wires. Group frames
  have a header bar and explicit collapse chevron.
- **Selection is orange; active/accent is blue.** Do not use orange for ordinary
  buttons. Blue = focus/active/primary; orange = selected graph item/node.
- Readability is raised (16.5px root + larger micro type). Preserve it.

## Workbench measurements

| Region | Size |
| --- | ---: |
| application header | 32px |
| area header | 32px |
| status bar | 28px |
| region seam | 2px |
| region / section radius | 4px |
| Outliner | 17.5rem |
| Properties | 22rem |
| Properties rail | 42px |
| Review rail | 42px |
| Outliner row | 24px |
| section band header | 28px |
| compact row | 26px |

The main editor always fills the remaining width. Map and Review render no
Outliner/Properties area. At 1280px there is no horizontal page overflow; the
Properties area is fixed and the editor takes the remainder.

## Graph edge rules

The Map is a deterministic **force-directed** graph: repulsion, spring links,
gravity and a final collision pass, with no animation. It must never wrap a
rank or a neighbourhood into a new line to make it fit; pan/zoom and focus are
the answers, not folding. Graph connections use `theme.edge`, not the panel
border `theme.line`.

- One relationship between two nodes is a **straight line**. Only parallel
  relationships between the same unordered pair curve, with small centred
  offsets (±10/±20) and a perpendicular control point so reversed links do not
  retrace each other.
- Orange is the selected relationship (and selected node outline) only. A
  selected node's incident edges stay muted grey; hovering a node may turn its
  incident edges blue.
- No transitions, filters or drop shadows inside the SVG scene. The shared
  button motion is scoped to HTML controls so `<g role="button">` cannot fade or
  translate graph geometry.
- Strokes use `vector-effect="non-scaling-stroke"`; a 200% zoom keeps 1px lines.
- Labels keep constant size, weight and position in every state. Cull
  overlapping labels deterministically with priority for selected, hovered,
  neighbours and high degree; the selected label is always visible.
- The layout is static and deterministic. No mount animation.

## Graph viewport rules

- Never open a graph at an unreadable fit. Fit to the focused group with a
  readable floor:
  - Workflow collapsed overview: natural group flow (aggregated cross-group
    edges, dagre LR), opening at a readable zoom; `Fit` is the overview.
  - Workflow expanded group: at most 10 nodes per column, whole frame fit
    (≈0.75 at 1920) with the `Collapse` header visible.
  - Blueprint Graph: local focused composition (parent group + edge endpoints)
    laid out source → relationship → target, no rank wrapping; Whole graph is
    the 226-card overview.
  - Lineage: selected node centred at 0.8 (≈189px nodes).
- Explicit **Fit** may show the whole graph at a small zoom; it is a user action,
  not the opening state.
- Floating overlays never cover nodes. Legends live in the toolbar or a corner.

## Tokens (single source)

```text
abyss       #171717   editor canvas
panel       #262626   region body
panel-raised#313131   area header / section band
panel-soft  #3a3a3a   raised control
inset       #1c1c1c   application header / status bar
gutter      #0c0c0c   seam between regions
line        #3c3c3c
line-soft   #292929
line-strong #4e4e4e
edge        #8b96a3   graph connection, never a panel border
text        #dedede
muted       #b6b6b6
faint       #858585
accent      #4772b3   Blender blue: active/primary
accent-strong #5b8bd0
accent-soft #2c4463
accent-ink  #0d1622
selection   #ed9e5c   Blender orange: selected graph item
selection-strong #f5b47a
selection-soft   #5a3a23
critical #e05a5a
high     #df8a4f
medium   #d6b84a
low      #4a90d9
info     #9a9a9a
asset    #6aa84f
source   #4a9edb
transform#9a7ad1
binding  #d6a34a
post     #d77f8f
target   #c9b958
group-7..10: #7d9d5a #b47a9b #6f8fae #b07f5f
```

Shared primitives: `.ui-panel`, `.ui-panel-header`, `.ui-section-label`,
`.ui-card`, `.ui-button`, `.ui-button-primary` (blue outline/tint, never a solid
loud pill), `.ui-button-ghost`, `.ui-icon-button`, `.ui-chip`, `.ui-chip-active`,
`.ui-input`, `.ui-kbd`, `.ui-hint`, `.ui-empty`, `.ui-selected` (orange),
`.ui-selected-row` (blue), `.ui-focus-ring`, `.ui-grain`, `.ui-area`,
`.ui-area-header`, `.ui-area-title`, `.ui-workspace-tab`, `.ui-editor-tab`,
`.ui-outliner-row`, `.ui-properties-rail-tab`, `.ui-inset`, `.ui-node`,
`.ui-node-header`, `.ui-node-body`, `.ui-socket`, `.ui-wire`. Use
`shared/ui/theme.ts` for JS/SVG.

## Node rules

| Node | Size | Header |
| --- | --- | ---: |
| Workflow step | 232×112 | 22px |
| Collapsed group card | 224×64 | 22px |
| Workflow group frame | content + 14px pad | 26px |
| Blueprint card | 280×248 | 24px |
| Lineage node | 236×96 | 22px |

- Header 20–24px, 3–4px top corners, body 3–4px bottom corners.
- Category colour in the header only; body remains graphite.
- Sockets: 7–8px circles on left/right, labelled only when space allows.
- Wires: bezier curves, muted grey; active/trace/selected orange; hover blue.
- Selected node: 1px orange border + subtle orange glow, not a huge ring.
- Group frame: dashed grey/blue border, header strip with label, counts and an
  explicit `Collapse`/`Expand` control; never a giant rounded blob.
- Minimap and controls look like Blender viewport widgets: square corners, flat
  fill, no drop shadow.

## Surface ownership

No component defines a local palette. Preserve every existing `data-testid`.
