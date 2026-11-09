# Blender UI direction

This document is the **skin**: palette, widgets, graph and viewport style. The
ladder and detail rules are in `DESIGN_LANGUAGE.md`; the regions and owners are
in `HIERARCHY.md`. When they disagree about structure, the design language
wins; when they disagree about colour or a widget, this document wins.

Reference: Blender 4.x dark theme, not a generic dashboard.

## Core language

- **Areas, not floating cards.** The application is a workbench of rounded
  rectangular regions separated by a 2px dark seam. Regions are plates, not
  cards: no glass, no floating panel stacks, no shadow between regions.
- **Application header** is a single line on the `inset` surface: brand,
  active function, snapshot, search, panel toggles and layout reset.
- **Activity bar** is a 48px vertical rail: Topology, Detail, then Search and
  Settings. The active item carries the orange selection edge.
- **Area headers** are 30–32px bands on `panel-raised` with an icon, a
  sentence-case title, optional counts and right-aligned controls.
- **Editor tabs** belong to the main area, not the window. They name the
  function's reading surface, not global destinations.
- **Side bar** is the function's subject browser and detail controls.
- **Bottom panel** is selection detail. It starts hidden and collapses from its
  own header or the title-bar toggle.
- **Node editor surfaces.** Dark canvas with a locked grid; neutral cards with a
  3px semantic lane stripe, body, small sockets and bezier wires.
- **Selection is orange; active/accent is blue.** Do not use orange for ordinary
  buttons. Blue = focus/active/primary; orange = selected graph item.
- Readability is raised (16.5px root + larger micro type). Preserve it.

## Workbench measurements

| Region | Size |
| --- | ---: |
| title bar | 38px |
| activity bar | 48px |
| side bar | 220–520px, default 300px |
| bottom panel | 120–480px, default 240px |
| status bar | 22px |
| region seam | 2px |
| region / section radius | 4px |
| editor tab | 30px |
| section band header | 28px |
| compact row | 26px |

The main editor always fills the remaining width. At 1600px there is no
horizontal page overflow; the side bar and bottom panel are resizable and the
editor takes the remainder.

## Graph rules

Topology is a **force-directed** graph: repulsion, spring links, gravity and a
collision pass. Coordinates settle once; there is no mount animation and no
rank wrapping. Pan/zoom and focus are the answers, not folding.

- One relationship between two nodes is a **straight line**. Only parallel
  relationships between the same unordered pair curve, with small centred
  offsets and a perpendicular control point so reversed links do not retrace
  each other.
- Orange is the selected node outline and selected relationship only. A selected
  node's incident edges stay muted grey; hovering a node may turn its incident
  edges blue.
- No transitions, filters or drop shadows inside the SVG scene. Button motion
  is scoped to HTML controls so graph geometry never fades or translates.
- Strokes use `vector-effect="non-scaling-stroke"`; a 200% zoom keeps 1px lines.
- Labels keep constant size, weight and position in every state. Cull
  overlapping labels deterministically with priority for selected, hovered,
  neighbours and high degree; the selected label is always visible.
- Default: hub labels only, relation names hidden, containment hidden,
  semantics badges hidden, property counts hidden. Each layer has a named
  control in the side bar.
- Containment links are dashed and quieter than relation links. Semantics
  presence is a small badge or ring, never a colour that replaces node kind.

## Graph viewport rules

- Open at a readable fit of the whole graph, with a readable floor. Explicit
  **Fit** may show everything at a smaller zoom; it is a user action, not the
  opening state.
- Wheel zoom and drag pan; node drag pins that node until **Reset pins**.
- Floating overlays never cover nodes. The legend and fit/reset/pin controls
  live in the side bar or a corner.
- A selected entity is highlighted and mirrored in the bottom selection detail.

## Tokens (single source)

```text
abyss       #171717   editor canvas
panel       #262626   region body
panel-raised#313131   area header / section band
panel-soft  #3a3a3a   raised control
inset       #1c1c1c   title bar / status bar
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
high     #df8a4f
asset    #6aa84f
source   #4a9edb
transform#9a7ad1
binding  #d6a34a
post     #d77f8f
target   #c9b958
```

Shared primitives: `.ui-panel`, `.ui-panel-header`, `.ui-section-label`,
`.ui-card`, `.ui-button`, `.ui-button-primary` (blue outline/tint, never a solid
loud pill), `.ui-button-ghost`, `.ui-icon-button`, `.ui-chip`, `.ui-chip-active`,
`.ui-input`, `.ui-kbd`, `.ui-hint`, `.ui-empty`, `.ui-selected` (orange),
`.ui-selected-row` (blue), `.ui-focus-ring`, `.ui-grain`, `.ui-area`,
`.ui-area-header`, `.ui-area-title`, `.ui-editor-tab`, `.ui-inset`, `.ui-node`,
`.ui-node-header`, `.ui-node-body`, `.ui-socket`, `.ui-wire`. Use
`shared/ui/theme.ts` for JS/SVG.

## Node rules

| Node | Size | Header |
| --- | --- | ---: |
| Detail lane node | 176×? | 22px |
| Topology hub | circle, degree radius | no header |
| Detail meaning card | content | 24px |

- Header 20–24px, 3–4px top corners, body 3–4px bottom corners.
- Category colour in the header or stripe only; body remains graphite.
- Sockets: 7–8px circles on left/right, labelled only when space allows.
- Wires: bezier curves, muted grey; active/trace/selected orange; hover blue.
- Selected node: 1px orange border + subtle orange glow, not a huge ring.
- Minimap and controls look like Blender viewport widgets: square corners, flat
  fill, no drop shadow.

## Surface ownership

No component defines a local palette. Preserve every existing `data-testid`.
