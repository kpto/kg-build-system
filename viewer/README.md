# KG graph review viewer

An independent Next.js viewer for a `kg-build-system` blueprint and workflow
contract. It reads viewer snapshots; it does not import the Python framework at
runtime, execute a graph build or call a model.

The conceptual hierarchy and ownership are in `HIERARCHY.md`; the visual rules
are in `DESIGN_LANGUAGE.md`; the palette and widget skin are in
`DESIGN_BLENDER.md`.

```console
cd viewer
npm install
npm run dev -- --hostname 0.0.0.0
```

For remote browsing, serve the production build:

```console
npm run build
npx next start --hostname 0.0.0.0 --port 3000
```

Open <http://127.0.0.1:3000>.

If the page stays on `Loading viewer snapshot…`, a stale `.next` directory or
two Next processes sharing one `.next` is the usual cause. Stop every Next
process for this project, delete `viewer/.next`, and start one server only:

```console
fuser -k 3000/tcp
rm -rf .next
npm run build && npx next start --hostname 0.0.0.0 --port 3000
```

## Default data and backend

The default is the current **Open Targets 26.09** compile:

| Artifact | Value |
| --- | --- |
| Blueprint | 63 nodes, 163 edges, 61 tables, 9 projections, 239 bindings |
| Workflow | 998 steps, 1,419 connections |
| Mode | compile-only; the graph was not executed |

The viewer has a thin read-only backend:

- `/api/snapshot` reads `public/data/opentargets.snapshot.json.gz` (≈845 KB)
  and returns it as gzip bytes; the browser decompresses with
  `DecompressionStream`.
- `/api/review` reads `public/data/opentargets.review.json`.
- The page itself is a small static shell. All indexes, lineage, audit,
  coverage, impact, decisions, diff and dossier export run in the browser.

A static host can fall back to the plain
`public/data/opentargets.snapshot.json` (≈8 MB), but the API path is what makes
remote loading practical. There is no database, job queue, execution engine or
server-side review persistence.

The older reference estate remains available for comparison and tests:

```text
http://127.0.0.1:3000/?snapshot=reference
```

Its data is `reference.snapshot.json` + `reference.review.json`.

## What it is for

The viewer is a review cockpit, not only a renderer. It answers four questions:

1. **What is the graph?** Workflow steps grouped by component or instruction
   emitter, plus the topology and data model.
2. **How is a property produced?** A property opens a focused lineage from asset
   and table through projection, binding, post-processing and publication.
3. **What did the design leave implicit?** Deterministic audit findings, design
   questions and a decision ledger with evidence and rationale status.
4. **What changes if this decision changes?** Impact radius, coverage matrix,
   pinned-baseline diff and an exportable review dossier.

## Architecture

The viewer is organised by **ownership**, not by component type. Each domain owns
one panel (or one representation) and is split into a framework-agnostic model
and a React view.

```text
app/                 Next.js entry: page, layout, globals.css, API routes
lib/                 snapshot loading, indexes, audit, lineage, diff, dossier (pure)
shared/
  model/             hierarchy vocabulary: Field, Row, Section, Rail, Panel, Action
  types/             cross-panel contracts (InspectorSelection)
  ui/                PanelHeader, Section, Row, Field, theme, AnnotationPopover
  graph/             shared flow geometry and initializer
review/
  model/             CampaignModel, buildCampaignModel, buildAppModel (composition)
  binding/           CampaignController: the only React state + model assembly
  view/              CampaignFrameView, CampaignHeaderView, CampaignStatusView
  tasks/             OrientMapView, DiagnoseModelView, AuditBuildView
navigation/model|view   Outliner
properties/model|view   Properties
topology/model|view     Map + Navigator
diagnosis/model|view    Model panel (header, representation tabs)
  execution/model|view  Workflow body
  semantics/model|view  Blueprint body
  provenance/model|view Lineage body
audit/model|view        Audit panel
```

| Layer | Knows | Does not know |
| --- | --- | --- |
| `lib/` | snapshots, indexes, analysis | UI, React, panels |
| `*/model/` | questions, projections, state, commands, child models | React, JSX, DOM, views |
| `*/view/` | how to render its level and bind child models to child views | domain meaning, another panel's state |
| `review/binding/` | controller state, URL, queue, model assembly | view internals |

- A ViewModel never owns a view. The composition root builds it and injects it;
  the view binds to it.
- A view may be reused for different purposes. `Section`, `Row`, `Field`,
  `PanelHeader` and the graph geometry are shared views; the ViewModel supplies
  the meaning.
- View state stays in the view: active rail, open section, Cards/Graph,
  whole graph, audit key, fit/zoom, hover. Model state is what changes meaning
  or must be shared: campaign record, selection, grouping, collapsed groups,
  trace, filters that scope a projection.
- Only the campaign composition root imports across features and calls builders.
  `npm run test` runs `scripts/check-architecture.mjs`, which fails a React/JSX
  import in any `model/` directory, a `.tsx` file outside `view/`, `binding/`
  or `tasks/`, a builder call outside `review/`, a cross-feature import, or a
  return of the deleted `@/components` tree.

`tests/model-hierarchy.test.ts` builds the campaign, task and panel ViewModels
from the reference fixture and asserts the questions, rails, tabs and child
models without React, JSX or the DOM. That is the conceptual hierarchy under
test; the rendered `data-level` audit is the view hierarchy under test.

## Visual system

One theme is shared by every surface:

- semantic Tailwind tokens in `app/globals.css`;
- `shared/ui/theme.ts` for SVG/React Flow colors and shared class joining;
- `.ui-*` primitives for panels, buttons, chips, inputs and focus states.

Graph connections use `theme.edge` (`#8b96a3`), separate from the panel-border
token `theme.line`; a graph edge is never styled with the border grey.

Components do not define local palettes or one-off button/card recipes. The
current direction is Blender 4.x dark editor language: graphite regions, blue
active/primary controls, orange graph selection, compact header strips,
Outliner-style explorer, Properties-style inspector, and node-editor nodes with
sockets and bezier wires. See `DESIGN_BLENDER.md`.

The structural contract is `DESIGN_LANGUAGE.md`: Window → Workspace → Panel →
Section → Row → Field → Control. It defines what each level owns, what may nest,
where actions and counts live, and when selection is blue (lists) versus orange
(graphs). `DESIGN_BLENDER.md` supplies the palette and widget skin for that
hierarchy; `HIERARCHY.md` holds the full region-by-region tree.

### Area workbench

The shell is a workbench, not a page with cards:

```text
application header 32px   logo · Map | Explore | Review · search · import
Outliner 17.5rem          editor area flex-1          Properties 22rem
area header 32px          area header 32px            area header 32px
tree rows                 Workflow | Blueprint |      30px icon rail +
                          Lineage + view controls      collapsible sections
status bar 25px           counts · review · score · compile-only
```

- The application header owns the workspace switch, search and import.
- Every area owns a 32px header with an editor-type icon, sentence-case title, optional counts and
  right-aligned controls. Areas are flat rectangles separated by 1px rules.
- Workflow, Blueprint and Lineage are **editor tabs in the main area header**,
  not global tabs. Map and Review are their own editors.
- Map has no Outliner or Properties area; its right side is a `Navigator` area.
  Review has no side areas; it is one full-width editor with a Properties-style
  section rail.
- Panel headers use the shared `shared/ui/PanelHeader.tsx`; the Properties rail
  and Review rail use `shared/ui/theme.ts` and `.ui-*` primitives. No surface
  defines a local header or palette.
- Every panel header is rendered **by its own panel**, inside it. The aligned
  header row is three (or two) panel-local headers, not a global toolbar.
- There are exactly two chrome bars: the campaign header and the panel-header
  row. Canvas controls are overlays that float over the canvas they change.

## Workspaces

The viewer has three top-level workspaces:

- **Map** (default): a force-directed topology viewport with a `Navigator` area.
  It shows 63 entity bubbles and 163 relationship links (147 rendered; 16
  self-loops are omitted from the force geometry). Clicking a bubble or
  link opens drill-down details and neighbours; actions open the selected entity
  or property in Explore.
- **Explore**: Workflow, Blueprint and Lineage with a **contextual Outliner** on
  the left and Properties on the right. The Outliner is the navigation model for
  the active representation: Workflow groups → steps, Blueprint parent group →
  entity → property, Lineage provenance group → entity → property. The
  Properties rail switches the evidence question — Definition, Production,
  Emission, Dependencies, Context — and only the sections that answer the active
  question are visible.
- **Review**: the audit editor with its own section rail.

The application header switches between them. `m` also opens Map.

### Map

- Deterministic **force-directed** layout: phyllotaxis start, repulsion, spring
  links, gravity and a final collision pass. No animation and no randomness, so
  the map is stable for the same snapshot.
- Graph connections use the shared `theme.edge` token (`#8b96a3`), not the panel
  border grey: ordinary edges 1.25px / 0.70, edges incident to the selected node
  1.45px / 0.80, selected/hovered 2.5px / 0.95.
- Labels are limited to hubs and the selected neighbourhood; every other node
  labels on hover, so the graph does not become a wall of overlapping names.
- `Reset` clears selection, group filter and focus, then fits the force graph.
- **Drag to pan**, wheel zoom, zoom controls and a visible interaction hint.
  Dragging never selects; a short click does.
- Parent-group chips filter the map.
- **Focus neighbours** dims everything outside the selected node and its
  neighbours.
- The right `Navigator` is one panel with four sections — Selection, Groups,
  Properties, Neighbours — built from rows and fields. Navigator selection is
  blue; the canvas selection is orange.
- **Open in Explorer** selects the entity in Blueprint/Cards; property rows open
  the lineage directly; Review opens the corresponding review subject.

### Workflow

- All steps and connections on a Blender node-editor canvas.
- Group by component or exact instruction emitter. Large graphs default to
  collapsed emitter groups so the overview is usable.
- Collapsed groups form a **natural left-to-right group flow** (aggregated
  cross-group edges, dagre LR), not a forced grid. The view opens at 0.9 on the
  flow (0.7 on a narrow viewport); pan or pick a group in the Outliner to follow
  it. `Fit` is
  the explicit whole-flow overview. `Group by` and `Collapse all` / `Expand all`
  are a compact canvas overlay; the Outliner shows the grouping read-only in its
  toolbar (`by instruction`) and lists the groups.
- Expanding a group reflows its steps into wide, shallow columns (at most 10
  per column) and fits the frame plus its header, so the explicit `Collapse`
  control is always reachable. Collapsing returns to the overview.
- Step cards are 232×112 with a category header, sockets and bezier wires.
  Orange is selection/trace, blue is focus.
- Hover a step's info button for component version, runtime contract,
  producer/consumer counts, artifacts and findings.
- **Trace** highlights the transitive upstream/downstream path and dims the rest.
- **Fit** shows the whole graph. **Read** zooms to a readable level.

### Explore / Blueprint

- **Cards** mode for large graphs: a **semantic index**. A parent group is a
  sticky 28px band, an entity a 26px subject row (description + hover actions),
  a property a 26px row with type, source and a status dot. There are no entity
  cards, tinted title strips or borders inside the panel. Property selection is
  blue; graph selection is orange.
- **Graph** mode: directed React Flow topology with neutral cards, a 3px
  semantic stripe, bezier wires, minimap, Fit/Read and property → lineage.
- `Cards | Graph` is a segmented control in the panel header. `Whole graph`,
  the audit key and counts are one compact canvas overlay row.
- Open Targets defaults to Cards because 226 topology cards are unreadable in a
  fitted graph. Graph opens a **local focused composition**: the parent group
  plus the endpoints of its edges, laid out as source → relationship → target.
  Parallel relationships that share one source and target are grouped into a
  single edge card (`association · 6 edges`) that keeps every relationship id
  inside it. The five-card composition opens at ≈0.86 (0.7 at 1280); **Whole
  graph** switches to the 226-card overview.
- The audit key is part of the compact Graph overlay, never a floating layer
  over the nodes.
- Every property row carries `traced`, `literal`, `fallback`, `multi-source`,
  `risk:<n>` and `impact:<n>` badges.
- Annotation pills open viewport-level popovers with namespace, id, arguments,
  description, examples and observed meta-graph counts when supplied.
- Clicking a property opens its lineage. “Review” opens the Review tab filtered
  to that node or edge.

### Lineage

- Focused node-editor DAG with lanes: asset, source/table,
  transformation/projection, binding, post-processing and target. Opens at 0.8
  on the selected node; **Fit** shows all 21 nodes. The contextual Outliner
  opens the active property’s provenance branch.
- **Proof receipt**: one row per binding branch:
  `field -> operator chain -> binding -> aggregate -> dedup -> targets`.
- **Branch comparison**: multi-source components such as Open Targets
  `synonym` are shown side by side.
- **Design questions** for the selected subject with evidence and review action.
- **Lineage inspector**: a full-width 3fr/2fr area split by a 1px rule — proof
  receipt on the left, impact/decisions on the right, stacked at 1280.
- **Impact radius**, matching **decision rationale**, source filter and
  Properties area with expression tree and SQL preview.

### Review

- One full-width editor with a 30px Blender Properties-style section rail:
  Summary, Findings, Questions, Coverage, Decisions, Build, Diff, Dossier.
  Each is a `.ui-section` with a question-bearing 26px header; score, rubric and
  verification are facets of one summary section. Finding rows use blue list
  selection; orange is reserved for graph canvases.
- Audit summary with a transparent weighted rubric. The Open Targets
  compile-only snapshot scores **49/100**; the reference estate scores 71.
  Verification is 0 for a compile-only snapshot because the graph was not
  executed.
- Findings queue with severity/rule/status/tag filters, acknowledge and
  waive-with-note; persisted in `localStorage` per snapshot name.
- Design questions phrased for a human reviewer.
- Coverage matrix: topology property × source relation, with traced-field,
  literal and binding counts; click a cell to open the filtered lineage.
- Decision ledger: sidecar decisions first, then cards derived from asset
  semantics, component runtime fields, build report and annotations. AI model,
  prompt or run identity is shown only when the snapshot carries it.
- Build health: published artifacts, failures, component versions and runtime
  fields. A compile-only snapshot says explicitly that the graph was not
  executed.
- Snapshot diff: pin the current snapshot as a baseline, import another
  snapshot, and review added/removed/changed steps, connections, topology and
  bindings.
- Review dossier: Markdown/JSON with the rubric, findings, evidence, queue state,
  decisions and selected property receipt.

### Global

- Deep links:
  `?view=lineage&kind=node&component=target&property=approvedSymbol`.
- Keyboard: `/` search, `m` map, `w` workflow, `b` explorer/blueprint, `l` lineage, `r` review,
  `f` fit, `j`/`k` next/previous finding, `Enter` open the finding subject,
  `?` shortcut sheet, `Esc` close/clear.
- File import/drop for a full snapshot, bare blueprint or bare workflow plan.
- Status bar: artifact counts, review progress, audit score, impact and
  compile/build health.

## Snapshot contract

```ts
{
  format: "kg-viewer-snapshot", version: 1, name, title,
  blueprint: { graph, data, assets, bindings },
  workflow: { components, steps, connections, provenance },
  report: { published_artifacts, recovered_failures, unresolved_failures, provenance },
  metaGraph?: { nodes, edges, summary, ... },
  review?: ReviewSidecar
}
```

A `review` sidecar carries decisions, notes and AI provenance:

```ts
{
  format: "kg-viewer-review", version: 1,
  ai?: { model?, runId?, generatedAt?, note? },
  decisions: [{ id, title, status, rationale, evidence, subject?, tags? }],
  notes?: [{ id, author?, text, createdAt?, subject? }]
}
```

## Rebuilding the Open Targets snapshot

The live compile worker is:

```console
cd ~/Repos/opentargets-kg
uv run python /home/paul/Repos/kg-build-system/viewer/scripts/compile_opentargets_snapshot.py \
  --project . \
  --output /home/paul/Repos/kg-build-system/viewer/public/data/opentargets.snapshot.json \
  --review-output /home/paul/Repos/kg-build-system/viewer/public/data/opentargets.review.json
```

It calls `create_kg_blueprint()` and `compile_kg()` only, serialises
`blueprint_to_document` / `workflow_plan_to_document` directly, writes the gzip
form and marks the report as `compile-only`. It does not read parquet data or
publish artifacts.

`build_opentargets_snapshot.py` is the historical converter for the older
`workflow_contract.json` build artifact; it is no longer the default path.

## Audit model

Findings are **deterministic observations with evidence, not proof of
correctness**. Implemented rules include:

`literal-only-property`, `hard-coded-fallback`, `missing-description`,
`nullable-identity`, `multi-source-component`, `duplicate-target`,
`unused-relation`, `unused-asset`, `orphan-step`, `unconsumed-output`,
`build-failure`, `recovered-failure`, `runtime-contract`, `version-drift`,
`observe-vs-declare`, `unreachable-lineage`, `shared-nullable-key` and
`open-decision`.

The health score is a weighted rubric:

```text
score = round(sum(component.value * component.weight))
```

Weights and raw values are shown in the UI. `magic-sql` is intentionally not
implemented: the SQL contains binder and error-message literals, so a string scan
would report boilerplate rather than graph decisions.

## Live updates

The event-based watcher is **not implemented yet**. The compile worker above is
the intended subprocess boundary. The next step is:

```text
debounced file watcher -> compile worker -> atomic snapshot -> SSE event
-> browser fetches revision -> diffSnapshots(previous, next) -> review banner
```

SSE (`/api/events`) is preferable to WebSocket for one-way events through remote
proxies. The backend should watch only an explicitly configured project path,
compile one change at a time, emit `compiling` / `snapshot-ready` /
`compile-error`, and mark the meta-graph/build report stale because compile-only
does not execute the graph.

## Verification

```console
cd viewer
npx tsc --noEmit
npm run test
npm run build
```

Current verification: **94 tests in 12 files**, TypeScript clean, Next.js
production build clean, ownership and MVVM boundary check clean. Browser
acceptance covers:

- conceptual hierarchy: `tests/model-hierarchy.test.ts` asserts campaign tabs,
  three Explore panel models, five Properties rails, three diagnosis tabs, the
  active child representation, execution groups/steps, semantics cards/legend
  and the four Navigator sections with no React or DOM;
- Open Targets: 8 workflow groups in a natural group flow at a readable opening
  zoom, a 6×10 expanded group at 0.745 with its Collapse control visible, 226
  blueprint cards with a locally laid-out focused Graph, 189px lineage nodes at
  0.8, 428 findings, 237 decisions, the Review rail and compile-only labeling;
- view hierarchy: panel headers 32px, section bands 28px, rows 26px, no `.ui-card`
  inside a panel, `.ui-section .ui-section` zero, no nested rows, every section
  has a question, and all `data-level` markers are present;
- contextual Outliner: Workflow groups, Blueprint topology and Lineage
  provenance trees; closed branches are lazy (Blueprint DOM rows 2,924 → 163);
- 1280×800 and 1920×1200: no horizontal overflow on any workspace;
- reference `?snapshot=reference`: 60 steps, 14 topology cards, annotation
  hover, condition-rating proof receipt, coverage filter, review queue, baseline
  diff, dossier download, search, trace, keyboard shortcuts and no console
  errors.

## Performance

Profiled in Chromium at 1920×1200:

- initial Map shell + graph: ~0.38 s;
- Map → Workflow: ~0.07 s; Workflow → Blueprint: ~0.25 s;
  Blueprint → Review: ~0.35 s; Review → Map: ~0.06 s;
- expanded workflow group: ~0.10 s; collapse: ~0.05 s.

The heavy work is deferred rather than hidden:

- audit is computed on idle after first paint;
- coverage and decisions are computed only when Review opens;
- impact is memoized and property rows share component-level impact;
- large Blueprint grids mount only one parent group by default;
- the Outliner mounts only open branches and collapsed sections do not mount
  their bodies;
- Review mounts at most 120 coverage rows and 60 decisions until expanded;
- Map pan/zoom mutates one scene transform and the scene is memoized.

Screenshots are in `screenshots/`. Dev scripts:

```console
# reference dataset
VIEWER_SNAPSHOT=reference uv run --with selenium python viewer/scripts/capture.py
VIEWER_SNAPSHOT=reference uv run --with selenium python viewer/scripts/acceptance.py
```

They use the system Firefox through geckodriver and write temporary files under
`viewer/.tmp-acceptance/` (ignored). Open Targets screenshots were captured with
Playwright Chromium at 1920×1200.

## Limits

- The default Open Targets snapshot is compile-only: observed counts,
  nullability observations, meta-graph enrichment and published artifacts are
  absent until a full build is run.
- The viewer is read-only; it does not execute the workflow or validate SQL.
- The audit is a set of heuristics; an empty finding list is not proof.
- Queue and baseline state are browser-local.
- If a snapshot has no review sidecar or AI provenance, the ledger says so.
