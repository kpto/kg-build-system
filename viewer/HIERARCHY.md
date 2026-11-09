# Viewer hierarchy

This is the complete UI hierarchy of the viewer: what regions exist, what each
one contains, what question it answers, and which module owns it.

## The ladder

```text
Window      the campaign and the active task
  Task      Map, Explore or Review
    Panel   one rectangular region with one header and one body
      Section  one question inside the panel
        Row    one subject
          Field  one value
            Control  one action
```

A level may be absent. A level is never reordered, nested inside the same kind,
or represented by a second full-width bar.

## View and ViewModel hierarchies

A **view** is reusable. It knows how to render a contract — header, rail,
section list, row, field, graph surface — but not what the content means.

A **ViewModel** is purpose-specific. It owns the question, the projection, the
state and the commands for one level.

They have the same shape and must be coherent from top to bottom, but they are
not the same objects.

| Level | View | ViewModel | Reusable view |
| --- | --- | --- | --- |
| Window | window frame: header + status | `CampaignModel` | yes |
| Task | task layout: one/two/three panels | `OrientTaskModel`, `DiagnoseTaskModel`, `AuditTaskModel` | yes |
| Panel | panel frame: header + body + one scroll owner | `NavigatorModel`, `DiagnosisModel`, `PropertiesModel`, `TopologyModel`, `AuditModel` | yes |
| Section | section list: question, count, disclosure, body | `SectionModel` per question | yes |
| Row | row: subject, selected state, actions | `RowModel` per subject | yes |
| Field | field: label, value, copy | `FieldModel` | yes |

### Injection and binding

A ViewModel **never owns a view**. The composition root creates the ViewModel and
**injects** it into a view; the view **binds** to it.

```text
CampaignModel ──injected──▶ CampaignFrameView
  DiagnoseTaskModel ──injected──▶ DiagnoseLayoutView
    NavigatorModel ──injected──▶ NavigatorView
    DiagnosisModel ──injected──▶ ModelDiagnosisView
      ExecutionModel ──injected──▶ ExecutionGraphView
    PropertiesModel ──injected──▶ PropertiesView
```

The binding contract:

- The view receives its ViewModel as a prop or an injected context value. It
  does not construct the ViewModel itself.
- The view reads state, calls commands, and maps child ViewModels to child views:
  `model.sections.map((section) => <SectionView model={section} />)`.
- The ViewModel may expose **child ViewModels**, never child views.
- The ViewModel has no JSX, no React imports, no view components, no DOM and no
  view registry. It does not choose Cards vs Graph; that is the view's decision.
- The composition root may bind the same ViewModel to different views. The
  ViewModel is unchanged and unaware.

### Reuse rules

- A view receives a contract; it does not import a feature's state, types or
  ViewModel. `Section`, `Row`, `Field`, `PanelHeader`, `Rail`, `GraphSurface`
  and `CanvasOverlay` are shared views.
- A ViewModel never renders JSX. It exposes a question, a projection, state,
  commands and child ViewModels.
- One ViewModel may be bound to alternative views by the composition root
  (Cards/Graph for the same semantic model). One view may bind several
  ViewModels (a `Section` in Properties, a `Section` in Audit).
- A view level without a ViewModel is decoration. A ViewModel without a view
  level is dead code.
- A child ViewModel does not reach into its parent's state; commands bubble up.
  A parent does not mutate a child's local state.

### ViewModel state versus view state

| ViewModel state | View state |
| --- | --- |
| campaign snapshot, index, review, queue, selection | active rail, open section, expansion |
| derived evidence projection, grouping | Cards/Graph, whole graph, audit key |
| commands and mutations | fit/zoom, hover, canvas viewport |

A state belongs to the ViewModel when changing it changes the model’s meaning or
must be shared across views. A state belongs to the view when it only changes
how this view instance presents the model. A view does not put its presentation
state back into the ViewModel.

### Coherence test

For every visible level, answer:

1. What is the question?
2. Which ViewModel answers it?
3. Which state does that ViewModel own?
4. Which commands does it expose?
5. Which reusable view renders it?

If two levels cannot answer these independently, the View/ViewModel split is
leaking.

### The implemented split

Every level now has a purpose-specific ViewModel and a reusable view. The
campaign composition root builds the model tree; no view builds its own model.

| Level | ViewModel, framework-agnostic | Builder | View |
| --- | --- | --- | --- |
| Window | `CampaignModel` (`review/model/CampaignModel.ts`) | `buildCampaignModel` | `CampaignFrameView`, `CampaignHeaderView`, `CampaignStatusView` |
| Task | `AppTaskModel` (`OrientTaskModel`, `DiagnoseTaskModel`, `AuditTaskModel`) | `buildAppModel` | `review/tasks/OrientMapView`, `DiagnoseModelView`, `AuditBuildView` |
| Panel | `NavigatorModel`, `DiagnosisModel`, `PropertiesModel`, `TopologyModel`, `AuditModel` | one `build…Model` per panel | `NavigatorView`, `ModelDiagnosisView`, `PropertiesView`, `TopologyView`, `BuildAuditView` |
| Representation | `ExecutionModel`, `SemanticsModel`, `ProvenanceModel` | `buildExecutionModel`, `buildSemanticsModel`, `buildProvenanceModel` | `ExecutionGraphView`, `SemanticsGraphView`, `ProvenanceGraphView` |
| Section / row / field | `SectionModel`, `RowModel`, `FieldModel`, `ActionModel` | produced by the panel builder | `Section`, `Row`, `Field` |

The React binding (`review/binding/CampaignController.tsx`) owns controller
state and the shared presentation state, calls `buildAppModel`, and injects the
result. It is the composition root, not a ViewModel.

A ViewModel may expose child ViewModels (`DiagnosisModel.child`,
`PropertiesModel.sectionsFor`, `TopologyModel.navigatorFor`) and never a view.
A view maps child models to child views.

The execution, semantics and provenance bodies still each own a React Flow
shell. That duplication is a known graph-surface gap: a shared `GraphSurface`
view would take the React Flow frame, minimap and background, while each
representation view keeps its own node/edge mapping and overlays. It is a view
refactor, not a model change, so it does not alter any ViewModel.

## Full tree

```text
WINDOW — ReviewCampaign
│
├─ Campaign header — CampaignHeader
│  ├─ brand + snapshot identity
│  ├─ task switch: Map | Explore | Review
│  ├─ global search
│  ├─ import
│  └─ review badge
│
├─ TASK: OrientMapView
│  └─ Panel: Topology (TopologyView)
│     ├─ Header: ORIENTATION · topology
│     │  └─ canvas hint
│     ├─ Body: force-directed canvas
│     │  ├─ canvas items: entity nodes, relationship links
│     │  ├─ overlay: zoom −/%/+/Fit · Reset
│     │  ├─ overlay: group filters
│     │  ├─ overlay: hint + legend
│     │  └─ overlay: hovered relationship label
│     └─ Panel: Navigator
│        ├─ Header: NAVIGATOR · 63 nodes · 163 links
│        ├─ Section: Selection — what is selected?
│        │  ├─ Row: selected subject
│        │  └─ Fields: group, links, properties, annotations
│        ├─ Section: Groups — which parent groups exist?
│        │  └─ Rows: entity, evidence, ontology_term, uncategorized
│        ├─ Section: Properties — what defines it?
│        │  └─ Rows: property name, type, audit badges
│        └─ Section: Neighbours — what is it connected to?
│           └─ Rows: neighbour, relationship
│
├─ TASK: DiagnoseModelView
│  ├─ Panel: Outliner (NavigatorView)
│  │  ├─ Header: OUTLINER · counts · collapse all / expand all
│  │  ├─ Toolbar: filter · grouping chip (`by <grouping>`, read-only)
│  │  └─ Section: active navigation model
│  │     ├─ root: Workflow
│  │     │  ├─ Row: group (count)
│  │     │  │  └─ Row: step (component · instruction)
│  │     ├─ root: Topology
│  │     │  ├─ Row: parent group (count)
│  │     │  │  ├─ Row: entity (kind)
│  │     │  │  └─ Row: property (type)
│  │     └─ root: Provenance
│  │        └─ Row: parent group → entity → property
│  │     └─ Section: Source model (Blueprint/Lineage only)
│  │        └─ Rows: assets, data entities, bindings
│  │
│  ├─ Panel: Model (ModelDiagnosisView)
│  │  ├─ Header: EXECUTION | SEMANTICS | PROVENANCE
│  │  │  ├─ meta: counts for the active model
│  │  │  ├─ Tabs: Workflow | Blueprint | Lineage
│  │  │  └─ Controls: Fit · Read
│  │  └─ Body: active representation (owned by that representation)
│  │     ├─ ExecutionGraph
│  │     │  ├─ overlay: Group by Component | Instruction
│  │     │  ├─ overlay: Collapse all · Expand all
│  │     │  ├─ canvas items: group cards, group frames, step cards
│  │     │  ├─ trace banner
│  │     │  └─ step detail overlay
│  │     ├─ SemanticsGraph
│  │     │  ├─ overlay: Cards | Graph · Whole graph · Audit key
│  │     │  ├─ Cards:
│  │     │  │  └─ Section: parent group
│  │     │  │     └─ Row group: entity
│  │     │  │        └─ Row: property → Field: source
│  │     │  │           └─ Control: open lineage
│  │     │  └─ Graph:
│  │     │     ├─ canvas items: entity cards, edge cards, edges
│  │     │     ├─ minimap / controls
│  │     │     └─ annotation overlay
│  │     └─ ProvenanceGraph
│  │        ├─ overlay: source filter
│  │        ├─ canvas: lanes, lineage nodes, edges
│  │        ├─ Section: Proof receipt
│  │        │  └─ Rows: branch → source/operator/binding/target fields
│  │        ├─ Section: Impact radius
│  │        │  └─ Fields: upstream, downstream, targets, records, nodes, edges
│  │        ├─ Section: Decision rationale
│  │        │  └─ Rows: decision
│  │        ├─ Section: Compare branches
│  │        │  └─ Rows: branch → fields
│  │        └─ Section: Questions
│  │           └─ Rows: question → action
│  │
│  └─ Panel: Properties (PropertiesView)
│     ├─ Header: PROPERTIES · active question · subject · kind
│     ├─ Rail: Definition | Production | Emission | Dependencies | Context
│     │  (every rail answers; an explicit no-evidence section when none is recorded)
│     └─ Body: sections for the active question
│        ├─ Definition: what is this?
│        │  └─ identity, definition, binding, entity, properties, artifacts, payload
│        ├─ Production: how is it produced?
│        │  └─ branches, expressions, rows, layout, source
│        ├─ Emission: what does it emit?
│        │  └─ SQL preview, SQL
│        ├─ Dependencies: what depends on it?
│        │  └─ connections, provenance, impact, endpoints
│        └─ Context: what else is recorded?
│           └─ annotations
│        Each section:
│        ├─ Row: record or branch
│        └─ Field: label/value · copy
│
├─ TASK: AuditBuildView
│  └─ Panel: Audit (BuildAuditView)
│     ├─ Header: AUDIT · findings · coverage · decisions
│     ├─ Rail: Summary | Findings | Questions | Coverage | Decisions | Build | Diff | Dossier
│     │  (index into the audit body; sections remain stacked)
│     └─ Body
│        ├─ Section: Audit summary
│        │  ├─ Row: weighted score
│        │  ├─ Rows: rubric components (raw · weight · value)
│        │  ├─ Field: verification
│        │  ├─ Rows: severity legend
│        │  └─ Field: queue progress
│        ├─ Section: Findings queue
│        │  ├─ filters: severity · status · tag · rule
│        │  └─ Row: finding
│        │     ├─ subject · rule · severity
│        │     ├─ evidence · impact · meta-graph
│        │     └─ Controls: Acknowledge · Waive
│        ├─ Section: Design questions
│        │  └─ Row: question → Open subject · Acknowledge
│        ├─ Section: Coverage matrix
│        │  └─ Row: property × source relation · traced/literal/binding
│        ├─ Section: Decision ledger
│        │  └─ Row: decision → status · source · evidence
│        ├─ Section: Build health
│        │  └─ Rows: artifacts · failures · components
│        ├─ Section: Snapshot diff
│        │  └─ Fields: added/removed/changed
│        └─ Section: Dossier
│           └─ Controls: export Markdown · export JSON · copy
│
└─ STATUS — CampaignStatus
   ├─ counts: assets · tables · projections · nodes · edges · bindings · steps · connections
   ├─ review progress
   ├─ audit score
   ├─ impact
   └─ build mode: compile-only / build failures / meta-graph
```

## Panel contracts

| Panel | Header | One question | Body | Owner |
| --- | --- | --- | --- | --- |
| Topology | Orientation | What exists and how is it connected? | force canvas | `topology/view/TopologyView` |
| Navigator | Navigator | What is selected and connected? | four sections | `topology/view/TopologyView` |
| Outliner | Outliner | Which subject can I inspect? | tree sections | `navigation/view/NavigatorView` |
| Model | Execution/Semantics/Provenance | What is this model? | representation body | `diagnosis/view/ModelDiagnosisView` + representation view |
| Properties | Properties | What defines the selected subject? | rail + sections | `properties/view/PropertiesView` |
| Audit | Audit | Is the build trustworthy, and what do we do? | rail + sections | `audit/view/BuildAuditView` |

Every header belongs to its panel. The aligned header row is three or two
panel-local headers, not a global toolbar.

## Section catalog

| Panel | Sections |
| --- | --- |
| Outliner | Workflow / Topology / Provenance root; Source model |
| Model / Execution | no sections; canvas items + overlays |
| Model / Semantics | parent group sections; entity row groups; property rows |
| Model / Provenance | Proof receipt; Impact radius; Decision rationale; Compare branches; Questions |
| Navigator | Selection; Groups; Properties; Neighbours |
| Properties | Definition; Production; Emission; Dependencies; Context |
| Audit | Summary; Findings; Questions; Coverage; Decisions; Build; Diff; Dossier |

## Row forms

- **Compact row** — 20–24px, one line, one action. Used for navigation,
  properties, proof branches, coverage and decision lists.
- **Subject row** — auto height up to three lines, used for a finding, a
  decision or an entity that carries its own description and actions.
- A **row group** is a subject row plus its evidence rows as siblings. Blueprint
  entities use row groups; they are not nested sections.
- A **canvas item** (step card, entity card, group frame, lineage node) is not a
  row or a section. It belongs to the canvas.

## Control placement

| Control | Owner |
| --- | --- |
| Map / Explore / Review, search, import | Campaign header |
| Group by, Collapse all, Expand all | ExecutionGraph overlay (the canvas it changes) |
| Workflow / Blueprint / Lineage | `ModelDiagnosisView` header |
| Fit, Read | `ModelDiagnosisView` header (view state) |
| Cards / Graph, Whole graph, Audit key | SemanticsGraph overlay |
| Source filter | ProvenanceGraph overlay |
| Navigator zoom / focus / reset | Topology canvas overlay |
| Outliner filter, expand/collapse | `NavigatorView` |
| Group toggle per group | `NavigatorView` group row |
| Properties rail and section disclosure | `PropertiesView` |
| Audit rail, filters, acknowledge/waive, show all | `BuildAuditView` |

A control lives with the state it changes. A control that changes another panel
is a defect, not a convenience.

## State ownership

| State | Owner |
| --- | --- |
| Snapshot, index, review, queue, baseline, URL, selection | `review/ReviewCampaign` |
| Representation, grouping, collapsed groups, fit/read mode | `review/tasks/DiagnoseModel` |
| Grouping, collapsed groups, trace, focus step | `diagnosis/execution/model/ExecutionModel`; step detail and hover are view state |
| Blueprint cards/graph projection, audit legend | `diagnosis/semantics/model/SemanticsModel`; Cards/Graph, whole graph and audit key are view state |
| Lineage graph, proof, impact and questions | `diagnosis/provenance/model/ProvenanceModel`; selected branch and viewport are view state |
| Map graph and Navigator projection | `topology/model/TopologyModel`; map selection, group filter, viewport and focus are view state |
| Navigable tree projection | `navigation/model/NavigatorModel`; filter query and open branches are view state |
| Evidence rails and sections | `properties/model/PropertiesModel`; active rail and disclosure are view state |
| Audit sections, rows and actions | `audit/model/AuditModel`; filters, waiver draft and open sections are view state |

The campaign owns the evidence **record**; the panel owns its evidence
**projection**; the section owns the question; the field owns the form; the
control owns the action.

## Code map

| Visible region | Module |
| --- | --- |
| Window frame | `review/view/CampaignFrameView` |
| Window bar / status | `review/view/CampaignHeaderView`, `review/view/CampaignStatusView` |
| React binding / composition root | `review/binding/CampaignController` |
| Task layout | `review/tasks/OrientMapView`, `review/tasks/DiagnoseModelView`, `review/tasks/AuditBuildView` |
| Outliner | `navigation/view/NavigatorView` + `navigation/model/NavigatorModel` |
| Model panel | `diagnosis/view/ModelDiagnosisView` + `diagnosis/model/DiagnosisModel` |
| Execution body | `diagnosis/execution/view/ExecutionGraphView` + `diagnosis/execution/model/ExecutionModel` |
| Semantics body | `diagnosis/semantics/view/SemanticsGraphView` + `diagnosis/semantics/model/SemanticsModel` |
| Provenance body | `diagnosis/provenance/view/ProvenanceGraphView` + `diagnosis/provenance/model/ProvenanceModel` |
| Map + Navigator | `topology/view/TopologyView` + `topology/model/TopologyModel` |
| Properties | `properties/view/PropertiesView` + `properties/model/PropertiesModel` |
| Audit | `audit/view/BuildAuditView` + `audit/model/AuditModel` |
| Panel header / section / row / field | `shared/ui/PanelHeader`, `Section`, `Row`, `Field` |
| Model vocabulary | `shared/model/hierarchy.ts`, `shared/model/campaign.ts` |

Every feature has the same three zones: `model/` (framework-agnostic
ViewModels and their builders), `view/` (React views that bind to an injected
model) and, in `review/`, `binding/` (the composition root) and `tasks/` (task
layout views).

Features may import `shared/` and `lib/`, and their own feature. Only the
campaign composition root (`review/`) imports across features and calls
builders. The old `components/` tree is deleted.

## Invariants

- One panel header per panel, inside the panel.
- Two chrome bars only: campaign header and the panel-header row. A canvas
  overlay is not a bar.
- One scroll owner per panel; closed branches do not mount.
- No `.ui-card` inside a panel; sections are rounded bands separated by surface and 6px margins.
- No nested sections; a subject plus its evidence rows is a row group.
- No nested rows.
- Every section carries a question.
- Blue selection in lists and navigation; orange selection in canvases.
- No feature imports another feature's panel.
- 32px panel headers, 28px section bands, 26px rows; 2px seams between regions.
- 1280 and 1920 have no horizontal overflow.

## Verification

- Conceptual hierarchy: `tests/model-hierarchy.test.ts` builds the campaign,
  task and panel ViewModels from the reference fixture and asserts questions,
  rails, tabs and child models **without React, JSX or the DOM**.
- Static ownership and MVVM: `scripts/check-architecture.mjs`, run by
  `npm run test`. It rejects a React/JSX/`.tsx`/view import in any `model`
  directory, a feature `.tsx` outside `view/`, `binding/` or `tasks/`, a builder
  call outside the `review/` composition root, a cross-feature import, and a
  return of the deleted `@/components` tree.
- Runtime hierarchy: `data-level` audit across all tasks (panels, sections,
  rows, fields; no cards in panels; no nested sections or rows; every section
  has a question; no overflow).
- `npx tsc --noEmit`, `npm run test`, `npm run build`.
- Design acceptance: Map pan/zoom, Workflow expand/collapse, Blueprint property
  lineage, Review bounds, 1280/1920.
- Reference Selenium acceptance.
