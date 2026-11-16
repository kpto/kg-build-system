# Blender UI direction

This document is the **skin**: palette, widgets, graph and viewport style. The
ladder and detail rules are in `DESIGN_LANGUAGE.md`; the regions and owners are
in `HIERARCHY.md`. When they disagree about structure, the design language
wins; when they disagree about colour or a widget, this document wins.

Reference: Blender 4.x dark theme, not a generic dashboard.

## Core language

- **Areas, not floating cards.** The application is a workbench of flat
  rectangular regions separated by a 1px dark seam. Regions are plates, not
  cards: no glass, no floating panel stacks, and no drop, text or emboss shadow
  on any component. Selection bars and focus rings are state indicators, not
  shadows. A
  detail panel body has 10/12px padding and plates are separated by 4px.
- **One reading size.** Prose is 14px with a 1.46 line height; chrome is 13px;
  metadata is 11–12px. The panel title weight is 400, not 600.
- **No application header or status bar.** The tab strip is the top of the
  frame and the side-bar search trigger carries the snapshot name; transient
  context is shown where it belongs, not in a decorative footer.
- **Side-bar sections** are collapsible 25px headers: **Control** for the active
  view's controls, **Explorer** for the whole design.
- **Area headers** are 30px bands on `panel-raised` with a chevron, a 13px
  sentence-case title, the question the section answers, optional counts and
  right-aligned controls.
- **Editor tabs** belong to the main area, not the window. They name the
  document, not a global destination.
- **Side bar** is the function's subject browser and detail controls.
- **Node editor surfaces.** Dark canvas (#1a1a1a) with a locked 25px dot grid
  (#303030); neutral cards with a 2px semantic lane stripe, body, small sockets
  and bezier wires.
- **One visualisation frame.** Graph and Workflow share a 30px `panel` header
  (concept glyph, view name, live extent, the view's own actions) above a flat
  canvas. Every graph surface, including the detail Build steps canvas, shares
  the same bottom-left navigation cluster (`−`, percent, `+`, Fit). A view
  supplies its renderer and data; it does not supply chrome. The Graph's Inspect
  toggle lives in that header.
- **Selection is orange; active/accent is blue.** Do not use orange for ordinary
  buttons. Blue = focus/active/primary; orange = selected graph item.
- The scale is compact but readable (14.5px root). The UI font is Inter
  (Blender/BUI's UI font). Body type is 13.5–14px; panel titles are 14px
  sentence case; micro labels are 11–12px; a document title is 16px. No
  structural label is smaller than 11px.

## Workbench measurements

| Region | Size |
| --- | ---: |
| side bar | 220–520px, default 300px |
| tab strip | 32px |
| region seam | 1px |
| region / section radius | 4–5px |
| editor tab | 28px |
| section band header | 31px |
| compact row | 26px |

The main editor always fills the remaining width. At 1600px there is no
horizontal page overflow; the side bar and bottom panel are resizable and the
editor takes the remainder.

## Graph rules

Topology is a **force-directed** graph: repulsion, spring links, gravity and a
collision pass. Coordinates settle once; there is no mount animation and no
rank wrapping. Pan/zoom and focus are the answers, not folding.

- The canvas is a Blender node-editor surface: a 25px dot grid on a flat
  graphite ground (`#1a1a1a` dots `#303030`). No vignette, no gradient, no major
  rules behind the graph.
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
- Labels are 12.5px chips: a 24px dark backing, a 4px radius and the node label.
  Hub labels only by default; **All** is a named control in the side bar.
- No transitions, filters or drop shadows inside the SVG scene. Button motion
  is scoped to HTML controls so graph geometry never fades or translates.
- Strokes use `vector-effect="non-scaling-stroke"`; link cores are 1.55px
  ambient, 2.35px hover and 3.25px selected, with a canvas-coloured halo only
  on hover and selection. A 200% zoom keeps the stroke width.
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
abyss       #1a1a1a   editor / node canvas
panel       #303030   region background (Blender region_bg)
panel-raised#3d3d3d   panel header and back
panel-soft  #474747   raised control / hover
inset       #181818   tab strip, inset field
gutter      #101010   seam between regions
line        #545454   panel / widget outline
line-soft   #444444   row separator
line-strong #606060   control outline
edge        #8b96a3   graph connection, never a panel border
text        #e6e6e6
muted       #d0d0d0
faint       #adadad
accent      #4772b3   Blender blue: active/primary
accent-strong #71a8ff
accent-soft #2c4463
accent-ink  #0b1620
selection   #ed5700   Blender node-selected orange
selection-strong #ff7a2a
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
