# Documentation survey: kg-build-system

Source: `/home/paul/Repos/kg-build-system` (read-only review).
HEAD at survey time: `68b569e` "Add the semantics and graph languages", 2026-11-06.
Scope: `docs/**`, `specs/**`, `README.md`, `AGENTS.md`, `ARCHITECTURE.md`,
`FRAMEWORK_STATE.md`, `DESIGN_ISSUES.md`, `STYLE.md`, `mkdocs.yml`, and
read-only git log/show.
Measured size: 42 Markdown pages under `docs/`, 13,224 lines; 2 files under
`specs/`, 327 lines.

Method: every docs page was read for its H1, headings and claim-bearing prose;
counts (code fences, links, admonitions, sections) were taken mechanically.
Claims below paraphrase the page, not the implementation. Where a page and HEAD
code disagree, the disagreement is reported in §6 rather than silently fixed.

## 1. Inventory of the 42 documentation pages

Order follows `mkdocs.yml`. "Purpose" is the page's job in the guide; "key
claims" are the 2-4 statements a reader is meant to retain.

| # | Path | H1 | Purpose | Key claims |
| --- | --- | --- | --- | --- |
| 1 | `docs/index.md` | kg-build-system documentation | Landing page and audience router. | Declarations become an inspectable knowledge graph; a build has data contracts, expressions, row sources and projections; `compile()` checks declarations and returns a `WorkflowPlan`; `execute()` runs it and writes planner-selected outputs. |
| 2 | `docs/philosophy.md` | Philosophy | Why the framework exists and the values behind it. | Meaning must be written down and published, not left in loaders or comments; nullability, grain, keys, joins and expansions are explicit; declarations are typed Python and checked before data is read; the plan is immutable and reproducible but not a compatibility promise; limits are stated honestly. |
| 3 | `docs/get-started/install.md` | Install kg-build-system | Install and verify a checkout. | Requires Python 3.12+; install with `pip install /path` or `uv add --editable`; verify the public import and `kbs --help`; the CLI only runs `generate`, while compile/execute are Python calls; the framework is experimental, so match the checkout to the guide. |
| 4 | `docs/get-started/first-graph.md` | Build your first graph | End-to-end tutorial on two CSVs. | Build `people_graph` in eight steps: tables, asset, topology, node binding, edge binding, compile, execute, inspect; `rows=` takes `Table.row_source()`, never a class; keys narrow with `alter_rows().drop_null()`; `compile()` scans the package and needs a `__main__` guard; output is `graph.jsonl` plus `workflow_plan.json` and `build_report.json`. |
| 5 | `docs/get-started/project-layout.md` | Project layout | Recommended package layout. | One importable package; `table/`, `topology/`, `bindings/` and `data/` are siblings; `assets.py` and `build.py` sit at the package root; dependencies point data → assets → table and topology, with no table/topology import either way; `build.py` is composition only; generated contract directories are owned by the generator; inputs live in `data/`, artifacts in `build/`. |
| 6 | `docs/concepts/index.md` | How a build works | Narrative tour of the whole pipeline. | A row becomes a record and its meaning is stated before the build; nine stages run from data contract through asset, expressions, grain, topology, bindings, semantics, planners and compile/execute; each part has one job; the declaration is the schema, with no separate mapping document. |
| 7 | `docs/concepts/data-contracts.md` | Data contracts | Row shapes and nested records. | `Table`, `Struct` and `ComputedStruct` cover the data side; `field()` is source-backed and `computed_field(selection)` is selection-backed; a field declares a value type and source reads are nullable; `ComputedStruct` members are type witnesses when carried by a row; `TableGroup` is a catalog, not a shape or union; an asset contract generates declarations. |
| 8 | `docs/concepts/types.md` | Types and nullability | Type vocabulary and the nullability contract. | Eight canonical scalars plus custom scalars; `Field[T]` never declares an optional type; source reads are nullable and computed reads follow their selection; a graph property is a scalar or flat array of non-null scalars; keys must be present scalars; temporal/uuid values have text form but no comparison operators; physical types widen only when meaning survives. |
| 9 | `docs/concepts/assets.md` | Assets | The logical source-data unit. | An asset is one logical unit and may back many tables; `AssetProfile` is required and `semantics` is optional; `AssetLayout` is descriptive metadata, not an access contract; tables name their asset with `Table[Asset]`; `DuckDbSourcePlanner` handles `parquet`, `json` and `csv` with no adapter registry; code generation is a separate frontend. |
| 10 | `docs/concepts/expressions.md` | Expressions | The `Selection` authoring model. | `Selection[T]` is the only authoring type and `NullableSelection[T]` is `Selection[Nullable[T]]`; nullability comes from the owner, so source access is nullable and projection output follows its selection; `default_to` keeps the row while `alter_rows().drop_null()` filters it; row effects are one-shot and type-gated; `extract`, `at`, `slice`, `lookup` and `zip` navigate values; arrays stay values until expanded. |
| 11 | `docs/concepts/row-sources.md` | Row sources | Grain and the relational algebra. | Grain is what one row represents and is a modelling decision; a row source is a value, not a declaration class; `where`, `distinct`, `order_by`, `unnest`, `union` and `join` derive one; a null join key never matches; `group_by` yields `{by, members}` and drops null keys; generated join/group shapes are statically `Any`. |
| 12 | `docs/concepts/projections.md` | Projections | Naming a grain and its outputs. | A projection is a named relation with exactly one row plan; it is pinned at class creation and an unpinned `Projection` is refused; outputs use `computed_field` and take its logical type; reading a projection field returns the materialised output, not a fresh selection; one row effect applies to every output; a second grain needs a second projection. |
| 13 | `docs/concepts/topology.md` | Topology | Graph meaning independent of data. | Topology declares node/edge types, properties, hierarchy and edge direction; properties are scalars or flat arrays and nested structures become nodes; templates are inert, categories are graph-visible but produce no records; base order is template, one category parent, terminal base; edge vs node reification and direction follow the assertion; topology declares no cardinality. |
| 14 | `docs/concepts/bindings.md` | Bindings | Mapping one row context to one record. | A node/edge binding names a row source, a present scalar key and every declared property exactly once; `rows=` accepts a row-source value and `bind` receives a typed proxy; a binding never aggregates and emits one record per received row; `drop_null()` filters the whole binding; endpoint tokens are required only for abstract sides; one target/one row context per binding; `debug_name` distinguishes producers. |
| 15 | `docs/concepts/semantics.md` | Semantics and annotations | Meaning as build data. | Descriptions, labels, annotations and semantics units are separate channels; meaning travels into the blueprint and outputs; an annotation is a frozen namespace/id/payload and stores no owner; labels are framework annotations and at most one matching label applies; template annotations flow in C3 order then host options; only reached declarations are published; bindings have no description. |
| 16 | `docs/concepts/semantics-language.md` | Semantics language | Claims, frames, purpose and the graph declaration. | `GraphSemantics` is the project meaning root with exactly one `Purpose`; `Semantics` is a declaration fragment read under that purpose; claims are contextless and limitations live under frames; zero or one graph declaration is allowed; semantics attach through declaration options/helpers and never `GraphSemantics`; `AssetProfile` is not semantics; documents omit empty optional members and source renders graph first. |
| 17 | `docs/concepts/planners-and-executors.md` | Planners and executors | Whole-graph stages after bindings. | A planner decides work for the whole graph and emits steps; an executor performs one exact instruction kind; the planner tuple is composition order with core inserted first; core has four planners sharing `component_id="core"`; deduplication, merging and conflict validation rewrite records; file, meta-graph and Neo4j publish outputs; every ordinary output needs a reader; compile-time configuration is in the payload, runtime fields are replaceable. |
| 18 | `docs/concepts/build-and-outputs.md` | Compile, execute and outputs | Pipeline artifacts and durability. | A build is blueprint → plan → execution; the blueprint is a frozen, reached-only model; `compile` reads no data; the plan owns components, steps, connections and provenance; `execute` dispatches exact instruction kinds and writes `workflow_plan.json` before the run and `build_report.json` after it; there is no schema migration path; only composed planners publish files. |
| 19 | `docs/developer/index.md` | Developer guide | Entry point for framework changers. | Developer docs state internal interfaces, boundaries and invariants; read philosophy → system design → data/expressions → testing; this is the canonical internal documentation; verification is pytest, pyright and strict mkdocs; the implemented tree includes a `frontend` monitor layer. |
| 20 | `docs/developer/philosophy.md` | Framework philosophy | Values that decide code placement. | Models are anemic and amnesic; semantics are contract; boundaries are explicit and subpackages own one responsibility; the kernel is a toolchain with build/compile/execute stages; a DTO is only a blueprint or workflow-plan member; source regeneration is a contract; one authoring type and one verb per transformation. |
| 21 | `docs/developer/system-design.md` | System design | Full implementation map (925 lines). | Kernel vocabulary is toolchain vocabulary and distribution vocabulary is graph vocabulary; every leaf uses model/service zones; the three verbs do not overlap; the linker owns roots, closure and order; the blueprint is semantic, the symbol graph is linker IR; planners group by component; runtime events/resources are explicit; `api.py` is the composition root; instruction kinds are exact. |
| 22 | `docs/developer/data-and-expressions.md` | Data and expressions | Ownership and boundaries for data/expressions. | `data` owns row sources, projections and their DTOs; `expressions` contributes operations/expression DTOs and owns no build part; a join change belongs to the row-source package; DTOs are small per-decision algebras; cross-symbol fields are typed refs; planning consumes the neutral relation plan; the blueprint source round trip is a contract test. |
| 23 | `docs/developer/testing.md` | Testing | Contract-test map. | Tests guard interfaces, not implementation; groups are kernel flow, planner, executor, distribution/DTO, and reference build; kernel tests use fakes and never import the distribution; codecs and source round trips are proved; naming forbids `IR` suffixes and `lower`; `Toolchain.compile` must not build; the reference and Open Targets projects are acceptance tests; the doc build is verification. |
| 24 | `docs/reference/index.md` | Authoring API reference | Reference entry and reading rules. | The reference gives exact signatures, arguments, errors and examples; learn a concept first, then use its reference; signatures show type parameters and defaults; reference pages state rules without re-explaining the model. |
| 25 | `docs/reference/types.md` | Types | Canonical type reference. | Eight canonical scalar units; representative types are aliases, not subclasses; custom scalars must be importable top-level classes; `Array` is the portable collection marker; structs are value shapes and `ComputedStruct` members are witnesses; nullability is owner-derived and flattened; keys are present scalars; the DuckDB disposition table is canonical/declared-only/refused. |
| 26 | `docs/reference/declarations.md` | Declarations | Declaration/field API. | `Table`, `TableGroup` and `Projection` are final; `field()` is source-backed and `computed_field()` selection-backed; `Field[T]` accepts only declared value types; a concrete `Table` must name an asset; `Struct` is never a row source; `ComputedStruct` is a value record; `TableGroup` is a catalog; `StructTemplate` is inert and annotation-only. |
| 27 | `docs/reference/assets.md` | Assets | Asset API reference. | An asset subclasses `Asset` with exactly one `options`; `AssetOptions` requires `profile` and accepts semantics/name/website/version/layout/governance/annotations; layout resolution is members → selector → locator with relative join; `Table[Asset]` is mandatory and every relation carries an `AssetRef`; `@asset_contract` is inert; `DuckDbSourcePlanner` is the generic planner. |
| 28 | `docs/reference/ingest.md` | Assets and ingest | Physical reading and checks. | Layout is descriptive and resolves per relation; the source planner emits one step per read relation and accepts only parquet/json/csv; table groups are catalogs and untaken members are dropped; credentials are names resolved at runtime; generated nullability has trust tiers and never changes the rendered `Field[T]`; the digest gate, widening, Parquet statistics pre-flight, guards and pre-read checks define the ingest boundary. |
| 29 | `docs/reference/expressions.md` | Expressions and selections | Selection API reference. | `Selection[T]` is the only expression surface and the compiler tree is private; source access is nullable and computed access follows the selection; `extract`, `default_to`, `alter_rows`, `at`/`slice`, `lookup`, array operations, `zip`, string/number/boolean operations and literals are enumerated; `any_of`/`all_of` have empty identities; errors are exact. |
| 30 | `docs/reference/row-sources.md` | Row sources | Row-source API reference. | `Table.row_source()`/`Projection.row_source()` return relation values; every derived operation returns another row source; `where` predicates are `Selection[bool]`; `unnest` expands one direct array member; `union` requires identical shapes; `join` has one equality and null keys never match; `group_by` yields `{by, members}`; generated shapes are `Any` to static checkers. |
| 31 | `docs/reference/projections.md` | Projections | Projection API reference. | `Projection(source)` pins one row source; subclass and declare at least one `computed_field`; `field()` is illegal for outputs; all outputs share one row plan and one driving source; expansions/drops apply to the whole projection; naming strips one `Projection` suffix; description is own-only. |
| 32 | `docs/reference/topology.md` | Topology declarations | Node/edge/property API. | `Edge[S, D]` is directed; concrete components are terminal; name inference strips tier suffixes; `PropertySlot[T]` accepts scalar, nullable, flat array or nullable array; templates are inert; base order is normative; abstract edges may declare category endpoints and concrete edges may keep or narrow them; endpoint tokens are required for abstract sides; only reached categories enter the blueprint. |
| 33 | `docs/reference/bindings.md` | Bindings | Binding API reference. | `node_binding`/`edge_binding` have direct and `rows=`/`bind=` forms that are exclusive; keys must be present scalars; every declared property is assigned once; `drop_null` is a row filter; endpoint tokens name concrete components; annotations are portable and `debug_name` distinguishes producers; binding identity derives from target, keys, selections, endpoints and plan; only module-level values are discovered. |
| 34 | `docs/reference/semantics.md` | Semantics | Annotation/label/description API. | An annotation is a frozen dataclass with stable namespace, id and JSON payload; the blueprint stores only those three; labels are framework annotations and at most one matching kind applies; descriptions are prose, own-only for components and declaring-class-owned for properties; template annotations flow in C3 order; only reached declarations are published. |
| 35 | `docs/reference/compile.md` | Compile and execute | create/compile/execute API. | `create_blueprint` takes no planners and has three declaration modes; `compile` accepts a blueprint or declaration mode, planners/toolchain and an optional `SqlEmitter`; `execute` needs an output directory, dispatches exact kinds and writes plan then report; `BuildRuntime` carries credentials, component overrides and DuckDB settings; `WorkflowReport` separates unresolved and recovered failures. |
| 36 | `docs/reference/planners-and-executors.md` | Planners and executors | Planner/executor API. | Planner and executor protocols have `component_id`/`version`/`runtime_fields` and exact `kinds`; core planners consume the neutral `SqlEmitter`; supplied planners cover dedup, merge, conflict validation, file, meta-graph and Neo4j; merge keeps the minimum per property and is not aggregation; executors return continuable or disrupting outcomes; the planner tuple is priority order; runtime configuration is validated before steps run. |
| 37 | `docs/reference/generation.md` | Generation | Code-generation contract. | `kbs generate` is a desired-state pass with exit 0 for CURRENT/CHANGED and 1 for STALE/failure; `@asset_contract` is inert and requires provider/configuration/package; discovery uses LibCST and does not import the project; providers return declarations and must be deterministic; `.kbs-generation.json` proves ownership/content; check/regenerate/watch have distinct source-observation rules; the built-in inference provider has a strict config and override contract. |
| 38 | `docs/reference/glossary.md` | Glossary | Vocabulary index. | Groups terms by data, types, assets, rows/graph meaning, compile/execute and generation; every entry links to the owning page; distinguishes look-alike terms and authoring names; defines blueprint, DTO, planner, executor, resource, instruction kind, trust tier and generation terms. |
| 39 | `docs/how-to/relations.md` | Join, group and union relations | Task guide for combining grains. | Choose join/group/union by the intended grain; a join has one equality and the key-pair form handles all scalar types while `equals` is present-text-only; group keys are scalar, non-null and unique; `union` accepts only identical shapes and never renames/casts/reorders; publish a shared derived grain as a projection; verify counts and nulls after the build. |
| 40 | `docs/how-to/custom-extensions.md` | Write an extension | One-file planner + executor tutorial. | An extension adds a language, linker, planner, executor or combination, not one monolithic interface; a planner needs `component_id`, `version`, `runtime_fields` and `plan`; an executor needs `kinds`, `resources` and `execute`; `ArtifactPattern` can consume all `core/graph/**` records; add objects with `default_toolchain` and `with_executors`; instruction kinds are exact; a custom language also needs a linker and `render`. |
| 41 | `docs/how-to/debug.md` | Debug a build | Failure-stage diagnosis. | Read the report first: unresolved/recovered failures and published artifacts; a successful compile isolates the problem to data, runtime or an executor; row-source/projection errors include null join keys and unpinned projections; declaration errors include duplicate names, missing sources/fields and finality/inheritance; successful-but-wrong builds need count/key/fan-out checks; inspect the blueprint for missing components/bindings. |
| 42 | `docs/how-to/patterns.md` | Apply recurring modelling patterns | Identity/grain/shape playbook. | Choose a build key that survives the build, composed deterministically when necessary; keep one grain per binding and use one binding per component/row context; make fan-out explicit and key by the item, not the parent; decide absent-value policy deliberately; choose edge endpoints/direction and use categories for shared meaning, not records; verify counts and dangling endpoint keys. |

### Inventory observations

- The inventory is dominated by the concept/reference pair: 11 concepts have a
  matching reference page (assets, bindings, expressions, projections,
  row-sources, topology, types, semantics, planners-and-executors, plus
  build-and-outputs → compile, data-contracts → declarations).
- Five H1s occur twice by design: Assets, Bindings, Planners and executors,
  Projections, Row sources.
- The longest pages are `developer/system-design.md` (925 lines),
  `reference/generation.md` (574), `reference/ingest.md` (466) and
  `reference/glossary.md` (463). The shortest are `reference/index.md` (65) and
  `developer/index.md` (73).
- The newest language is under-documented at the pipeline level: the concepts
  page describes the graph declaration, but the two pages that enumerate
  `GraphBlueprint` fields still say "four fields" and omit `graph_declaration`
  (see §6).

## 2. The documentation model

### 2.1 Diátaxis roles actually used

The site does not label Diátaxis quadrants in navigation; the roles are visible
from page shape and voice.

| Role | Pages | Count | How it appears |
| --- | --- | --- | --- |
| Tutorial / onboarding | `get-started/first-graph.md`; `install.md` and `project-layout.md` are setup procedures | 3 | Numbered steps, a running `people_graph` project, explicit verify commands. `first-graph` is the only true end-to-end lesson. |
| How-to | `how-to/relations.md`, `custom-extensions.md`, `debug.md`, `patterns.md` | 4 | Task-first H1s, "Before you begin", numbered steps, "Verify", "Troubleshoot", "Next steps". |
| Reference | all 15 `reference/*` pages | 15 | Signatures, argument tables, error tables, exact rules; `glossary` is a vocabulary reference. |
| Explanation | `philosophy.md`, `concepts/*` (13), `developer/philosophy.md`, `developer/index.md` | 16 | Problem → model → decisions → limits; concepts teach the authoring model. |
| Developer reference / hybrid | `developer/system-design.md`, `developer/data-and-expressions.md`, `developer/testing.md` | 3 | Interface inventories, package trees, invariants and contract-test maps; `system-design` is also narrative. |
| Navigation | `index.md`, `concepts/index.md`, `reference/index.md`, `developer/index.md` | 4 | Routers, reading order and diagrams; `concepts/index` doubles as a narrative tour. |

The fit is intentional but not strict Diátaxis: "Concepts" is explanation with
how-to habits (decisions, limits, next steps); `reference/ingest.md` is a second
assets reference rather than a separate quadrant; and the developer pages mix
explanation, reference and process rules. No page is a pure "tutorial" for
generation, planners or debugging. The guide's own rule is "a page covers one
concept" (`STYLE.md`), not "one quadrant". Role counts overlap because several
pages serve two roles; they are not a partition of the 42 pages.

### 2.2 Navigation depth and shape

`mkdocs.yml` defines six navigation sections plus two top-level pages: Home,
Philosophy, Get started (3), Concepts (13), How-to guides (4), Developer (5),
Reference (15). Maximum navigation depth is 2 (section → page); there are no
nested nav groups and no page is more than one click from a section index. Pages
use H2/H3 internally instead of deeper nav (`developer/system-design.md` has 22
H2 sections; `reference/generation.md` has H3 subsections).

Consequences:

- Concepts are ordered as the pipeline (how a build works → data → types →
  assets → expressions → rows → projections → topology → bindings → semantics →
  semantics language → planners → compile/execute), so the nav itself teaches
  the model.
- Reference mirrors the same order but starts with types/declarations and adds
  ingest and generation after compile/planners.
- How-to pages are not ordered by dependency; each is independently usable.
- There is no nav entry for `specs/` or the root markdown files. Their audience
  is repository reviewers, not site readers.

### 2.3 Cross-linking conventions

- 426 relative Markdown links; zero external Markdown links. Three `http(s)`
  URLs appear only inside code examples (an asset website and a license URL),
  so the guide is deliberately self-contained as prose.
- Links are relative file paths (`../concepts/types.md`), with anchor fragments
  for exact rules (`types.md#duckdb-dispositions`, `ingest.md#digest-gate`).
  Anchors are used heavily and are part of the teaching pattern: a concept
  points at the reference rule, and the reference points back.
- Concept pages close with `## Next steps` (20 pages) and/or `## Reference`
  (14 pages). Reference pages close with `## What to remember`; across the whole
  guide 27 pages have that section, followed by a `Related:` line naming
  sibling pages.
- `reference/index.md` is the hub for the authoring API; `reference/glossary.md`
  is the vocabulary hub; `concepts/index.md` is the narrative hub.
- The reciprocal pattern is consistent but not universal: 4 how-to pages have
  no "What to remember"; 9 concepts pages have no "What to remember"; the
  glossary and both indexes are exempt. This is a style deviation from
  `STYLE.md`, which says "End each page with a short 'What to remember' list".
- `mkdocs build --strict` is the stated link/build gate (`README.md`,
  `FRAMEWORK_STATE.md`, `developer/testing.md`); the site uses Material's
  `navigation.sections`, `navigation.indexes`, code copy and search suggest.

### 2.4 Code-example style

Measured code fences: 265 `python`, 39 `text`, 12 `bash`, 5 `json`, 2 `csv`,
1 `console`, 1 `powershell`. The 325 bare backtick-fence lines are closing
fences, not unlabelled code blocks.

- Python examples import from `kg_build_system` (107 top-level imports) and use
  a small running example: `estate` (`estate.assets`, `estate.table`) in
  concepts/reference, `people_graph` in get-started/how-to.
- `estate` is the reference project's package, not a package shipped inside
  `kg_build_system`; a reader cannot run those snippets without the reference
  project. This is a reproducibility gap in the examples, not a broken API.
- Examples are written as declarations plus one composition call, not as
  standalone scripts; the tutorial is the only place with full file paths and
  shell commands.
- `STYLE.md` requires valid Python from the current public API; the guide also
  uses `text`, `bash`, `json` and `csv` fences for artifacts and inputs.
- Warnings/notes are sparse: 10 `!!! warning`, 8 `!!! note`, 1 `!!! tip` across
  9 pages. The most safety-critical pages (`ingest`, `types`,
  `first-graph`, `project-layout`, `planners-and-executors`) carry them.

### 2.5 Tone and authoring rules

From `STYLE.md`:

- Write for a competent Python developer who has never seen the framework;
  start from the problem and what changes for the author; explain the idea
  before the API.
- Preserve the values: semantics as contract, explicit assumptions, typed
  authoring, reproducible builds, separation of meaning and execution.
- Write from the author's perspective; explain internals only when they change
  what the author writes or observes.
- Prefer continuous explanation with code over signature lists; tables only
  after the concept is understood.
- State null and row behaviour explicitly; those are the two things authors get
  wrong.
- Use admonitions for warnings/rules; link related pages relatively; one
  concept per page; sentence-case headings; do not invent features; inspect
  source or `reference_project/` when unsure.
- Teach: depth is welcome, do not simplify by omission; carry one running
  example; explain why a rule exists; end with "What to remember" and a next
  link.

From `AGENTS.md`:

- A document states the current model as if it were the only one; write for a
  reviewer who has not seen the conversation; define terms and name the
  interface/file/type; state the decision, not the route to it.
- Agent-facing writing is point-form, finalised and succinct; author docs are
  not simplified and may cover the same subject as developer docs for a
  different reader ("they are not alternates").
- Author-facing interfaces are reviewed through `docs/`; internal interfaces
  through `docs/developer/`; a developer doc states names, signatures,
  invariants, allowed dependencies and the authoring surface, not
  implementation detail.
- When code and developer doc disagree, the doc is the decision and one of them
  changes. A plan or changelog is a change report, not a spec.

The guide largely follows these rules. The main deviations are structural, not
tonal: several concepts pages omit the mandated closing list, and the
concept/reference split repeats scope even when the prose is not copied.

## 3. Duplicates, near-duplicates and page types

### 3.1 Concept/reference pairs

These pairs cover the same subject for different readers. Verbatim overlap is
low (sentence-set Jaccard ≤ 0.02 for every pair measured), so they are
near-duplicates in scope and rules, not copied text. The split is deliberate
per `AGENTS.md`; the risk is drift, not redundancy.

| Concept page | Reference page | Overlap and drift risk |
| --- | --- | --- |
| `concepts/assets.md` | `reference/assets.md` + `reference/ingest.md` | Three pages cover one model: author narrative, API/options, physical ingest. Layout and planner rules are repeated in all three. |
| `concepts/bindings.md` | `reference/bindings.md` | Same key/property/endpoint rules; the reference adds signatures, errors and identity. |
| `concepts/data-contracts.md` | `reference/declarations.md` | Same `field`/`computed_field`/`Table`/`Struct` model; reference adds finality and options. |
| `concepts/expressions.md` | `reference/expressions.md` | Same selection/nullability model and many of the same operations; reference is the full method list. |
| `concepts/projections.md` | `reference/projections.md` | Same pinning/output/one-row-plan rules; reference adds naming/errors. |
| `concepts/row-sources.md` | `reference/row-sources.md` | Same algebra and generated-shape rules; reference adds signatures. |
| `concepts/topology.md` | `reference/topology.md` | Same hierarchy/template/endpoint model; reference adds exact option/error tables. |
| `concepts/types.md` | `reference/types.md` | Same nullability/value/property/key rules; reference adds the full DuckDB disposition table. |
| `concepts/semantics.md` | `reference/semantics.md` | Same annotation/label/description channels; reference adds payload/error detail. |
| `concepts/planners-and-executors.md` | `reference/planners-and-executors.md` | Same supplied planners; reference adds protocol signatures, ordering and publications. |
| `concepts/build-and-outputs.md` | `reference/compile.md` | Same three-stage pipeline and output files; reference adds signatures, `BuildRuntime` and `WorkflowReport`. |

### 3.2 Other duplicate or near-duplicate clusters

| Cluster | Pages | Finding |
| --- | --- | --- |
| Semantics language | `concepts/semantics.md`, `concepts/semantics-language.md`, `reference/semantics.md`, `specs/semantics-and-graph.md` | Four surfaces: channel overview, meaning units, annotation API, implementation spec. They are distinct jobs, but the same claim/frame/purpose rules appear in at least three. |
| Root/developer architecture | `ARCHITECTURE.md`, `FRAMEWORK_STATE.md`, `specs/README.md`, `developer/system-design.md` | The package tree and dependency spine are repeated four times; `ARCHITECTURE.md` is explicitly the short map and the developer page the full model. |
| Philosophy | `philosophy.md`, `developer/philosophy.md` | Same value set (semantics, explicit assumptions, typed authoring, reproducible builds, separation) at author and framework depth. |
| Landing/overview | `README.md`, `docs/index.md`, `concepts/index.md` | Three overviews: package/product, site router, and pipeline story. `README` and `docs/index` share the "declarations → graph" pitch. |
| Tutorial/layout | `get-started/first-graph.md`, `get-started/project-layout.md` | Both repeat the `people_graph` tree, `assets.py`, `build.py` and the `__main__` guard; the layout page is partly a second tutorial. |
| Planners/outputs | `concepts/planners-and-executors.md`, `concepts/build-and-outputs.md`, `reference/planners-and-executors.md`, `reference/compile.md` | Output planners and the plan/report lifecycle are explained in both concepts and both references. |

No page is a wholesale copy of another; the duplication is conceptual coverage
and repeated rules. That makes the pairs useful for readers but expensive to
keep consistent: a single rule change touches two to four pages (for example,
the `GraphBlueprint` field count is now stale in two of them).

### 3.3 Pure reference, narrative and procedural

| Type | Pages | Notes |
| --- | --- | --- |
| Pure reference | 15 `reference/*` pages | Signatures, options, errors, tables; `glossary` is lookup-only; `reference/index` is a hub. |
| Narrative/explanation | `docs/index`, `philosophy`, 13 `concepts/*`, `developer/index`, `developer/philosophy` | 17 pages; `concepts/index` is a narrative pipeline tour; the rest teach a model or value. |
| Procedural/tutorial | `get-started/install`, `get-started/first-graph`, `get-started/project-layout`, 4 `how-to/*` | 7 pages; install/layout are setup procedures, first-graph is the only full tutorial, how-tos are task recipes. |
| Developer hybrid | `developer/system-design`, `developer/data-and-expressions`, `developer/testing` | Interface reference with explanatory prose; `system-design` is the longest and most table-heavy. |

## 4. Gaps: questions an end user would ask that no page answers

The gaps below were checked by searching the whole `docs/` tree for the topic
and reading the nearest page. "Closest page" means the reader can assemble part
of an answer, not that the question is answered.

| # | User question | Why no page answers it | Closest page |
| --- | --- | --- | --- |
| 1 | How do I test my own graph project (unit-test a binding, assert records, use fixtures)? | `developer/testing.md` tests the framework's contract boundaries with fakes; it never shows an author testing declarations, bindings or outputs. | `developer/testing.md`, `how-to/debug.md` |
| 2 | How do I run a build in CI or on a schedule? | The guide says compile/execute are Python calls and the CLI only generates; there is no CI, entry-point, exit-code or scheduling page. | `get-started/install.md`, `get-started/project-layout.md` |
| 3 | Can I build incrementally or rebuild only changed relations? | Every `execute` runs the whole plan; generation has `--check`/`--regenerate` staleness, but builds have no cache, partial-run or incremental contract. | `reference/generation.md`, `concepts/build-and-outputs.md` |
| 4 | How do I size or tune a build (memory, threads, spilling, parallelism)? | `BuildRuntime` exposes `duckdb_storage`, `duckdb_threads`, `duckdb_memory_limit` and `duckdb_compression`, but no page explains when to use them or what the limits are. | `reference/compile.md`, `concepts/build-and-outputs.md` |
| 5 | What happens when a hand-written contract's source schema changes (column removed/renamed/widened)? | Generation documents source drift, but there is no rule for hand-written tables at runtime beyond the ingest checks and guards. | `reference/ingest.md`, `reference/generation.md` |
| 6 | How do I deploy the Neo4j bundle to a real database and verify/roll it back? | The guide stops at writing `nodes/`, `relationships/` and `import_neo4j.py`; no import, permission, verification or rollback procedure. | `reference/planners-and-executors.md`, `concepts/build-and-outputs.md` |
| 7 | How do I install or pin a released version? | Install only documents a local checkout (`pip install /path`, `uv add --editable`); there is no package-index, version pin or upgrade page. | `get-started/install.md` |
| 8 | How do I compose several projects/packages or share declarations across builds? | `create_blueprint`/`compile` take one namespace or explicit bindings; no page covers multi-package composition or shared libraries. | `reference/compile.md`, `how-to/patterns.md` |
| 9 | Where do I look up an exact error message and its fix? | Errors live in per-page tables; there is no error index, message catalogue or cross-reference from runtime failures to declarations. | `how-to/debug.md`, reference error tables |
| 10 | How do I add a new source format end to end? | Concepts and the design limits say "another module planner", but the how-to only builds a graph-record planner/executor, not a source planner with `AssetLayout`, payload and source step. | `how-to/custom-extensions.md`, `reference/ingest.md` |
| 11 | What compatibility can a consumer rely on for a stored plan or blueprint? | Both concepts and limits say there is no schema negotiation or migration; no page states what a consumer may safely persist or how to detect incompatibility. | `concepts/build-and-outputs.md`, `DESIGN_ISSUES.md` |
| 12 | How do I contribute to the repository (dev setup, test layout, review flow)? | `developer/` explains the model and contract tests but not environment setup, running subsets, or the change-report/interface-review workflow. | `developer/index.md`, `AGENTS.md` |

Gaps 1-4 and 8 are the most likely to block adoption: they are normal
production questions, and the guide is otherwise strong on the authoring model.
Gap 9 is an information-architecture problem more than missing knowledge.

## 5. Relationship between docs/, specs/ and the root markdown files

### 5.1 Surface map

| Surface | Audience | Role | Authority and overlap |
| --- | --- | --- | --- |
| `docs/` | Graph author | What to write, what the graph does, semantics and limits | Author-facing review surface (`AGENTS.md`). Concepts + how-to + tutorial + reference; 42 pages. |
| `docs/developer/` | Framework reviewer | Internal interfaces, boundaries, invariants, contract tests | Canonical developer guide; `specs/README.md` explicitly defers to it. Overlaps `ARCHITECTURE.md` and `FRAMEWORK_STATE.md`. |
| `specs/README.md` | Framework reviewer | Index of developer surfaces and model/service boundaries | Says it does not duplicate `docs/developer/`; repeats the model/service table, zones and dependency spine. |
| `specs/semantics-and-graph.md` | Implementer/reviewer | Interface contract for the `semantics` and `graph` languages | The only spec with acceptance tests and Open Targets migration notes; added in the same commit as the author page, not linked from the site nav. |
| `README.md` | New repository visitor | Product overview, package groups, authoring model, verification | Derivative summary; repeats `docs/index` pitch and `FRAMEWORK_STATE` numbers. |
| `AGENTS.md` | Agent/contributor | Working rules, delegation, review, rule promotion, framework model | Normative for process and for the framework model; the largest rule source (411 lines). |
| `ARCHITECTURE.md` | Reviewer | Short implementation map and dependency spine | Explicitly short; defers the full model to `docs/developer/system-design.md`. |
| `FRAMEWORK_STATE.md` | Reviewer | Current implementation, verification, remaining limits | Reviewer briefing/current-state snapshot, not a promise; repeats tree and limits. |
| `DESIGN_ISSUES.md` | Reviewer/consumer | Remaining design limits | Normative limit list; repeats limits already in `FRAMEWORK_STATE.md`. |
| `STYLE.md` | Doc author | Writing rules | Normative for the guide; not linked from the site nav. |
| `mkdocs.yml` | Site builder | Navigation, theme, Markdown extensions | The de facto statement of the public docs surface (42 pages, depth 2). |

### 5.2 Authority and precedence

- `AGENTS.md` states the review contract: author-facing interfaces are reviewed
  through `docs/`, internal interfaces through `docs/developer/`, and when code
  and the developer doc disagree, the doc is the decision and one of them
  changes.
- `specs/README.md` defers to `docs/developer/` as canonical and says the
  directory does not duplicate it. `specs/semantics-and-graph.md` is the
  exception: it is an implementation contract with acceptance tests, not a
  second author guide.
- Root markdown files are summaries and state snapshots. `README.md`,
  `ARCHITECTURE.md` and `FRAMEWORK_STATE.md` repeat the package tree; none is
  the canonical interface statement.
- `DESIGN_ISSUES.md` is the normative "remaining limits" list; `FRAMEWORK_STATE`
  repeats it for reviewers, and `README` repeats the verification counts.
  Repetition is intentional for reviewer convenience but creates four places to
  update.

### 5.3 Current inconsistencies found

| Finding | Evidence | Impact |
| --- | --- | --- |
| `GraphBlueprint` is described as having four fields, but HEAD has five (`graph_declaration` was added). | `docs/concepts/build-and-outputs.md:53`, `docs/reference/compile.md:76`; `kg_build_system/distribution/interpreter/model/public/graph_blueprint.py` | Author and reference both omit the project meaning root added by `68b569e`; a reader cannot discover `graph_declaration` from the API reference. |
| `frontend/` is omitted from the root package trees but exists and is documented in `docs/developer/`. | `README.md` package groups, `ARCHITECTURE.md` tree, `FRAMEWORK_STATE.md` tree; `docs/developer/index.md`, `docs/developer/system-design.md`; `kg_build_system/frontend/` | Reviewer-facing maps disagree about the implemented tree; the monitor layer is invisible in the short map. |
| Verification numbers are repeated in three places and were not re-run in this read-only survey. | `README.md`, `FRAMEWORK_STATE.md`, `docs/developer/philosophy.md` ("259 tests, 1858 subtests") | Treat as a claim from the last doc pass, not a live measurement. |
| `specs/semantics-and-graph.md` describes the same language as `docs/concepts/semantics-language.md` but is not in the nav. | `specs/semantics-and-graph.md`; `mkdocs.yml` nav | Site readers see the author version only; implementers must know the spec exists. |
| `STYLE.md` mandates a closing "What to remember" list, but only 27 of 42 pages have one. | `STYLE.md`; section counts | A consistency defect, concentrated in concepts and how-to pages. |
| Examples import `estate`, a reference-project package not shipped in `kg_build_system`. | 25 `from estate...` imports in concepts/reference; `reference_project/` | Snippets are valid against the repo but not copy-runnable from a fresh install. |

### 5.4 What the documentation model gets right

- The pipeline order is taught once narratively (`concepts/index`) and then
  repeated at reference depth, so a reader can move from "why" to "exact name"
  without a second information architecture.
- The concept/reference reciprocity is disciplined: the concept page states the
  decision and its consequence, the reference states the signature and error.
- Limits are stated in the author guide, not hidden in developer notes:
  `alter_rows` gating, one row plan per projection, no aggregation in bindings,
  no adapter registry, no schema migration, generated provenance.
- The semantics language is documented as a contract (claims/frames/purpose,
  graph declaration, source round trip), not as a metadata afterthought.

## 6. Method and uncertainty

- Git history has no commit bodies in the last 120 commits: every subject was
  present, every body was empty. Intent in the companion decisions survey is
  therefore inferred from subjects, changed paths and the resulting docs, not
  from author rationale.
- Page claims were paraphrased from HEAD docs. Where docs and code disagreed,
  the code path is named; no source file was modified.
- Counts (pages, lines, fences, links, admonitions, section presence) are
  mechanical and reproducible from HEAD; they are not estimates.
- The 42-page count includes the four index pages and the glossary. It excludes
  `specs/`, root markdown and `reference_project/`.
- "Gap" means no dedicated page answers the question; a partial answer may exist
  in a nearby page, which is named.
