# Blender UI direction

This document is the **skin**: palette, widgets, graph and viewport style. The
ladder and detail rules are in `DESIGN_LANGUAGE.md`; the regions and owners are
in `HIERARCHY.md`. When they disagree about structure, the design language
wins; when they disagree about colour or a widget, this document wins.

Reference: Blender 4.x dark theme, not a generic dashboard.

## Core language

- **Areas, not floating cards.** The application is a workbench of flat
  rectangular regions separated by a 1px dark seam. Regions are plates, not
  cards: no glass, no floating panel stacks, no shadow between regions.
- **Application header** is a single 34px line on the `panel` surface: brand,
  snapshot, search, panel toggles, layout reset and settings.
- **Side-bar sections** are collapsible 25px headers: **Control** for the active
  view's controls, **Explorer** for the whole design.
- **Area headers** are 25px bands on `panel-raised` with an icon, an uppercase
  micro title, optional counts and right-aligned controls.
- **Editor tabs** belong to the main area, not the window. They name the
  document, not a global destination.
- **Side bar** is the function's subject browser and detail controls.
- **Node editor surfaces.** Dark canvas with a locked dot grid plus a 120px
  major grid; neutral cards with a 2px semantic lane stripe, body, small sockets
  and bezier wires.
- **Selection is orange; active/accent is blue.** Do not use orange for ordinary
  buttons. Blue = focus/active/primary; orange = selected graph item.
- The scale is compact (12.5px root). Micro type is 8.5–9.5px; body type is
  10–11px; a document title is 13px.

## Workbench measurements

| Region | Size |
| --- | ---: |
| title bar | 34px |
| side bar | 220–520px, default 300px |
| status bar | 20px |
| region seam | 1px |
| region / section radius | 2–3px |
| editor tab | 28px |
| section band header | 25px |
| compact row | 22px |

The main editor always fills the remaining width. At 1600px there is no
horizontal page overflow; the side bar and bottom panel are resizable and the
editor takes the remainder.

## Graph rules

Topology is a **force-directed** graph: repulsion, spring links, gravity and a
collision pass. Coordinates settle once; there is no mount animation and no
rank wrapping. Pan/zoom and focus are the answers, not folding.

- The canvas is a Blender node-editor surface: a 24px dot grid, a 120px major
  grid and a flat graphite ground. No vignette, no gradient behind the graph.
- A concrete node is a degree-sized disc tinted by its category; an abstract
  category is a dashed ring in the asset green. The selected node gets an orange
  ring, not an orange fill.
- Each category draws a faint convex-hull frame behind its nodes with an
  uppercase `CATEGORY · count` label. **Clusters** in Control toggles every
  frame; the frame follows the settled simulation.
- One relationship between two nodes is a **straight line**. Only parallel
  relationships between the same unordered pair curve, with small centred
  offsets and a perpendicular control point so reversed links do not retrace
  each other.
- Orange is the selected node outline and selected relationship only. A selected
  node's incident edges turn blue; every other edge dims. Hovering a node turns
  its incident edges blue.
- Labels are 9px chips: a dark backing, a 1px muted border and the node label.
  Hub labels only by default; **All** is a named control in the side bar.
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
- The inspector is an overlay panel on the right. The graph is fitted into the
  canvas that remains visible beside it, not underneath it; resizing the window
  or toggling the inspector refits the visible map.
- A selected entity is highlighted and mirrored in the inspector's identity and
  fulfilment sections.

## Tokens (single source)

```text
abyss       #1d1d1d   editor canvas
panel       #232323   region body
panel-raised#2b2b2b   area header / section band
panel-soft  #333333   raised control
inset       #191919   inset field
gutter      #111111   seam between regions
line        #3a3a3a
line-soft   #2c2c2c
line-strong #4a4a4a
edge        #8b96a3   graph connection, never a panel border
text        #e6e6e6
muted       #b0b0b0
faint       #808080
accent      #5b8bd0   Blender blue: active/primary
accent-strong #7aa7e6
accent-soft #24364d
accent-ink  #0b1620
selection   #ff9f43   Blender orange: selected graph item
selection-strong #e87d0d
selection-soft   #4a2c12
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
