# Decision candidates: kg-build-system

Source: `/home/paul/Repos/kg-build-system` (read-only).
History window: the last 120 commit subjects, `HEAD` at `68b569e`
(2026-11-06). The window contains no commit bodies: all 120 bodies are empty,
so context is inferred from subject, changed paths and the surviving docs.
Rules sources: `AGENTS.md`, `DESIGN_ISSUES.md`, `FRAMEWORK_STATE.md`.

Status convention: `accepted` means the decision is visible in HEAD code/docs
and no later commit in the window reverses it. `superseded` and `refined` name
the later commit. This is an evidence-based reading, not a formal ADR status.
Dates are author dates.

Candidate count: **39**. Groups: kernel (13), expressions/data (7),
semantics/asset (6), topology/binding (3), interpreter (2), modules (2),
cli/api (2), docs/process (4).

## How to read a row

- **Decision**: present-tense rule the project follows.
- **Context**: the problem or pressure that produced it (one line).
- **Consequence**: what the rule changes for authors/reviewers (one line).
- **Evidence**: commit, test path, doc path. "then" marks a test path that
  existed at the commit but was later reorganized; current equivalent is named
  where one exists.
- **Areas**: affected subpackages/surfaces, not an exhaustive file list.

## Kernel

The kernel is the toolchain: language/declaration/symbol/linker/planner/
workflow-plan/runtime/executor/resource. These candidates define what stays
domain-agnostic and how the three stages compose.

| ID | Decision | Date | Status | Context | Consequence | Evidence | Areas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-001 | Separate a domain-agnostic toolchain kernel from the KG distribution. | 2026-11-03 | accepted | The framework had graph vocabulary mixed into reusable pipeline mechanics. | `kernel/` imports no graph/table/topology/SQL package; `distribution/` supplies graph languages, interpreter and modules; the split is the primary review boundary. | `051732b`; `tests/kernel/test_import_isolation.py`; `docs/developer/system-design.md#the-package-tree`, `AGENTS.md#kernel-and-distribution` | kernel, distribution, architecture |
| D-002 | Use toolchain vocabulary in the kernel and domain vocabulary only in the distribution. | 2026-11-03 | accepted | Kernel and distribution shared words such as "module" and "build", hiding the dependency direction. | Kernel names language/declaration/symbol/linker/planner/workflow plan/runtime/executor/resource; graph/blueprint/node/edge/binding/projection/asset stay distribution-side. | `28311a6`; `tests/test_naming.py`; `AGENTS.md#kernel-and-distribution`, `docs/developer/system-design.md` | naming, kernel, distribution |
| D-003 | Treat canonical types as a kernel assumption and keep default implementations in the distribution. | 2026-11-03 | accepted | Each language could otherwise define its own type ontology, and libraries could drift into the kernel. | Every language, blueprint and plan shares one type ontology; protocols live in the kernel, default planners/executors/emitters live in the distribution. | `ba9906c`, `844307a`; `tests/kernel/test_kernel.py`; `AGENTS.md#kernel-and-distribution`, `docs/reference/types.md` | kernel, types, distribution |
| D-004 | Make compile a pure consumer of a separately assembled blueprint. | 2026-11-03 | accepted; supersedes `d61f886`, `5b724c1` | Earlier iterations mixed blueprint ownership into compile or hid the blueprint entirely. | `create_blueprint` assembles/validates; `compile` takes a blueprint (or the composition-root shortcut creates one) and never calls the blueprint package; the blueprint is public but its language DTOs are not. | `39f46e0`, `69720f0`; `tests/kernel/test_toolchain_flow.py`, `tests/kernel/test_import_isolation.py`; `docs/developer/system-design.md#the-three-verbs`, `DESIGN_ISSUES.md` | kernel, interpreter, api |
| D-005 | Make the workflow contract step-centric and instruction-based, with exact instruction kinds. | 2026-11-03 | accepted | A plan-level SQL field or prefix-matched kind coupled the workflow to one engine. | `Step` owns one `Instruction(kind, payload)`; `InstructionKind(operation, engine)` is exact and has no prefix matching; SQL is one kind, not a plan field. | `b97b225`, `46a8ab9`; `tests/kernel/test_kernel.py`; `docs/reference/compile.md`, `AGENTS.md#kernel-and-distribution` | kernel, workflow, modules |
| D-006 | Use Key-backed role types for every identity that crosses pipeline boundaries. | 2026-11-04 | accepted | Formatted strings were used as step/opening/artifact identities, so display text leaked into contracts. | `StepId`, `OpeningId`, `ArtifactType`, `ArtifactPattern`, `InstructionKind` wrap `Key`; `Step` keeps `component`/`name` and derives `.id`; a formatted string is display only. | `e5b50ae`; `tests/pipeline/test_pipeline_identity.py`; `docs/reference/compile.md`, `docs/developer/system-design.md#identity` | kernel, pipeline, workflow |
| D-007 | Emit pipeline events and let resource providers subscribe to lifecycle events. | 2026-11-04 | accepted | Resources were owned by the toolchain or closed ad hoc; monitors and providers had no single lifecycle. | Each run builds a fresh `EventBus`/`ResourceRegistry`; providers publish on `PipelineStarted` and dispose on `PipelineFinished`/`PipelineHalted`; executors receive only declared `ResourceView`s; a listener error fails the run. | `b802b38`; `tests/kernel/test_runtime_events.py`, `tests/kernel/test_runtime_resources.py`; `docs/developer/system-design.md#execution-resources-and-the-runtime` | kernel, runtime, resources |
| D-008 | Let the linker own root selection and resolve the authoring reference closure before transcription. | 2026-11-04 | accepted; per-declaration path replaced earlier batch transcription in `ac00c5b` | Languages cannot know which declarations a build reaches, and transcribing everything produced unreachable symbols. | `compute_key`/`get_references` run on authoring values; the linker selects roots, walks the closure, orders reachable declarations and calls `transcribe` once per declaration. | `98dafe9`, `ac00c5b`; `tests/distribution/test_blueprint_linker.py`; `docs/developer/system-design.md#declarations-symbols-and-the-linker`, `AGENTS.md#semantics-as-contract` | kernel, linker, languages |
| D-009 | Use one verb per transformation; make render the reverse of transcribe and move codecs out of `Language`. | 2026-11-03 | accepted; supersedes `74773e1` ("lowering is local") | "Lower" named several different transformations and serialization was on the language protocol. | Vocabulary is discover, key, transcribe, link, plan, assemble, emit, render, execute; a language transcribes and renders; `to_document`/`from_document` belong to the artifact codec. | `edc2e9e`, `395e98e`, `679ab07`, `0c85463`; `tests/test_naming.py`; `AGENTS.md#names-state-the-role`, `docs/developer/data-and-expressions.md#source-rendering-round-trip` | naming, languages, codecs |
| D-010 | Give every framework leaf the same model/service zone layout. | 2026-11-03 | accepted; CLI applied it first in `8221a9a`, then `5dbdc61` generalized it | Public surfaces, cross-package data and mechanisms were mixed in one directory. | `model/public`, `model/internal`, `model/_private`, `service/public`, `service/internal`, `service/_private`; empty zones are deleted; `__init__.py` is facade only. | `5dbdc61`, `3898466`; `tests/test_layout.py`, `tests/test_architecture.py`; `ARCHITECTURE.md`, `docs/developer/system-design.md#module-layout` | all packages, layout |
| D-011 | Keep private helpers out of interface zones and break service/private cycles with function-local imports. | 2026-11-03 | accepted; refined by `801b13c` (private code may read public model data) | Interface zones had accumulated mechanisms and `service.internal` eagerly imported private services. | No single-underscore helper in public/internal; a private helper stays beside its caller unless shared; `service.internal` delegates to `_private` with a function-local import. | `74b5250`, `6d463f5`, `068b7b7`, `99f4dff`; `tests/test_layout.py`; `AGENTS.md#explicit-boundaries`, `specs/README.md#zones` | all packages, imports |
| D-012 | Make public API methods anemic, documented wrappers with runnable examples. | 2026-11-02 | accepted | Public methods were re-exports or contained mechanism, so the authoring surface was not a designed interface. | A public method is a thin wrapper over `service.internal`/`service._private`, has a docstring and an `Example:`; mechanisms live below the facade. | `3ee7e50`, `6f77b72`, `28d7099`; `tests/test_public_docstrings.py`; `AGENTS.md#the-authoring-api-is-the-guard` | api, public surfaces, docs |
| D-013 | Keep debug names out of the blueprint fingerprint. | 2026-11-02 | accepted | A human-facing `debug_name` in the digest made otherwise identical bindings differ. | Binding identity derives from target, keys, selections, endpoints and row plan; `debug_name` distinguishes producers for display but not the content fingerprint. | `fc88283`; `specs/README.md#identity` (then); `docs/developer/system-design.md#identity`, `AGENTS.md#experimental`; no dedicated current test found | interpreter, identity, bindings |

## Expressions/data

`Selection[T]` is the single authoring value; the data language owns row
sources and projections; expressions contributes operations and DTOs.

| ID | Decision | Date | Status | Context | Consequence | Evidence | Areas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-014 | Unify authoring around `Selection[T]` with owner-derived nullability. | 2026-11-05 | accepted; supersedes `5a6ccbd` intermediate field unification | Separate nullable/value/array expression families duplicated operations and made absence a declaration concern. | `NullableSelection[T] = Selection[Nullable[T]]`; `Field[T]` never declares absence; source Table/Struct reads are nullable; computed Projection/ComputedStruct reads follow their selection; item nullability stays in the value type. | `330c09c`; `tests/test_authoring_api.py`, `tests/typecheck/authoring.py`; `docs/concepts/expressions.md#nullability-comes-from-the-owner`, `docs/reference/expressions.md` | expressions, data, authoring API |
| D-015 | Make bindings accept row-source values, not declaration classes. | 2026-10-29 | accepted | Passing `Table`/`Projection` classes hid which grain and which filters the binding read. | `rows=` takes `Table.row_source()`, `Projection.row_source()` or a derived source; a class is refused; filtering belongs in the row source. | `f726484`; then `tests/test_row_sources.py`, current `tests/test_authoring_api.py`; `docs/reference/row-sources.md#row_source`, `docs/concepts/bindings.md` | data, bindings |
| D-016 | Own the relational row-source algebra in the data language as a small frozen plan DTO. | 2026-10-29 | accepted; supersedes `3c78df0` initial implementation by `d7faad8` | Join/filter/union/group semantics risked leaking into planners and table declarations. | `where`, `unnest`, `union`, `join`, `group_by`, `distinct`, `order_by` derive row sources; planning consumes the DTO; a join change belongs to the row-source package. | `d7faad8`; then `tests/test_row_source_algebra.py`; `docs/developer/data-and-expressions.md#row-source-model`, `docs/reference/row-sources.md` | data, planning |
| D-017 | Require projections to be pinned to exactly one row source. | 2026-10-29 | accepted | An unpinned projection could silently read a different relation than its outputs implied. | `Projection(source)` is required; `Projection()` and `class P(Projection)` are refused; all outputs share the pinned plan and one driving source. | `7a3fe3d`, `893e3b4`; then `tests/test_provider_projection.py`; `docs/reference/projections.md#projectionsource`, `docs/concepts/projections.md` | data, projections |
| D-018 | Gate every row effect behind a one-shot `alter_rows()` handle. | 2026-10-29 | accepted | `drop_null`/`expand`/`drop_if` could be chained or applied where the selection did not support them. | Only valid effects appear on the handle; each effect returns a selection, so a second effect needs a second `alter_rows()`; `drop_null` filters the whole row/binding. | `893e3b4`; then `tests/test_row_effect_gate.py`; `docs/reference/expressions.md#alter_rows`, `docs/concepts/expressions.md#row-effects-are-explicit` | expressions, bindings |
| D-019 | Add `lookup`, `zip` and row-source `unnest` as explicit value/grain operations. | 2026-11-05 | accepted | Reading another relation, pairing arrays and expanding an array-as-grain had no composable authoring spelling. | `lookup` returns a nullable array and is ungated; `zip` pairs equal-length arrays into `Pair`; `RowSource.unnest` makes an array the relation grain while `Selection.expand` remains a row effect. | `d17d187`; `tests/distribution/test_expression_operations.py`; `docs/reference/expressions.md#lookup`, `docs/reference/row-sources.md#unnest` | expressions, data, SQL emission |
| D-020 | Use `extract` as the member-read name and remove compatibility aliases. | 2026-11-04 | accepted | `pick` and expression aliases preserved a second vocabulary after the model changed. | `extract` is the only member read; legacy aliases are gone; the same cleanup flattened the core planner layout in `9725c10`. | `79507c4`, `9725c10`; `tests/test_authoring_api.py`, `tests/test_public_api.py`; `docs/reference/expressions.md` | expressions, api, modules |

## Semantics/asset

The asset is a logical source unit; semantics is a value language with one
project purpose; generation is an edit-time frontend, not an asset field.

| ID | Decision | Date | Status | Context | Consequence | Evidence | Areas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-021 | Model an asset as one logical source unit and keep layout descriptive, not an access contract. | 2026-11-04 | accepted | Tables carried location/format/credential facts, coupling row shape to deployment. | `Table[Asset]` names the source; `AssetProfile` is required; `AssetLayout` describes `kind/locator/format/selector/members/properties` but opens no file and proves no relation. | `a9f7413`; `tests/distribution/test_asset_language.py`; `docs/concepts/assets.md`, `DESIGN_ISSUES.md` | asset, data, ingest |
| D-022 | Use a generic source planner for parquet/json/csv and reject an adapter registry. | 2026-11-04 | accepted | An adapter concept would add a second extension mechanism beside ordinary planners. | `DuckDbSourcePlanner` emits one `source.<relation>` step per read relation; another format is another ordinary module planner with its own instruction kind. | `a9f7413`; `tests/distribution/planners/test_duckdb_source_planner.py`; `docs/reference/ingest.md#the-generic-source-planner`, `DESIGN_ISSUES.md` | asset, duckdb, modules |
| D-023 | Add semantics and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | Meaning was expressed only through annotations/descriptions, with no claims/frames/purpose model. | `GraphSemantics(claims, purpose)` is the root; `Semantics(claims, frames)` is a declaration fragment; frames own limitations; zero or one graph declaration; `AssetProfile` replaces `AssetSemantics`. | `68b569e`; `tests/distribution/test_semantics_language.py`, `test_graph_language.py`; `specs/semantics-and-graph.md`, `docs/concepts/semantics-language.md` | semantics, graph, asset, interpreter |
| D-024 | Keep generation an inert edit-time frontend, separate from the asset model and blueprint. | 2026-11-04 | accepted | Codegen requests were becoming asset fields and leaking into `AssetDTO`/blueprint. | `@asset_contract(AssetContractOptions(...))` only validates and stores `_asset_contract`; no generation field exists in `AssetOptions`/`AssetDTO`; `kbs generate` runs before build. | `a9f7413`, `ac00c5b`; `tests/test_codegen_discovery.py`; `docs/reference/generation.md#request-model`, `DESIGN_ISSUES.md` | generation, asset, cli |
| D-025 | Treat observation as provenance: every generated source field renders `Field[T]`, never an optional annotation. | 2026-11-05 | accepted; refines `5ee6a1b`, `22fedcd` | Codegen inferred nullability from sampled data, turning an observation into a declaration. | Observed `DECLARED`/`ENFORCED`/`DEFAULTED` tiers feed the manifest, statistics and notes; the rendered annotation stays the value type; overrides are declaration-time requests, not runtime options. | `ac00c5b`, `22fedcd`; `tests/test_codegen_discovery.py`; `docs/reference/ingest.md#generated-nullability`, `docs/reference/generation.md#override-contract` | generation, ingest, types |
| D-026 | Formalise canonical DuckDB dispositions and widen physical types only when meaning survives. | 2026-09-03 | accepted; deduplicated by `004b3f7` | Physical types are wider than the graph vocabulary; silent narrowing would misstate data. | Each understood DuckDB type is canonical, declared-only or refused; declared-only needs an explicit override and a checked cast; integers that fit int64, FLOAT/DOUBLE and JSON/ENUM widen; refused types abort. | `1647dce`, `004b3f7`; then `tests/test_duckdb_type_digest.py`, `tests/test_source_widening.py`; `docs/reference/types.md#duckdb-dispositions` | types, generation, ingest |

## Topology/binding

Topology declares graph meaning; bindings connect one row context to one
component. The candidates define inheritance, endpoints and property shape.

| ID | Decision | Date | Status | Context | Consequence | Evidence | Areas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-027 | Support polymorphic categories/templates with one normative base order. | 2026-09-01 | accepted; `22c4390` partly superseded by `e88a0ca` | Concrete components needed shared properties/endpoints without creating records. | Templates first, one abstract category parent, terminal base last; templates are inert; categories are graph-visible but produce no records; concrete components are terminal; endpoints may narrow but not widen. | `22c4390`, `e88a0ca`; then `tests/test_topology_hierarchy.py`; `docs/reference/topology.md#base-order`, `docs/concepts/topology.md` | topology, bindings |
| D-028 | Require an `endpoint(...)` token only when the declared edge side is abstract. | 2026-09-01 | accepted | An abstract endpoint did not say which concrete node a binding actually used; a concrete side did not need a token. | A token must name a concrete node equal to or descending from the declared side; required for abstract sides, optional documentation for concrete sides. | `22c4390`, `e88a0ca`; then `tests/test_topology_hierarchy.py`; `docs/reference/topology.md#endpoint`, `docs/reference/bindings.md#endpoint-tokens` | topology, bindings |
| D-029 | Restrict graph properties to scalars or flat arrays of non-null scalars, and type SQL output by the property type. | 2026-10-22 | accepted | Nested arrays/structs cannot be preserved by every target, and SQL output was not following topology types. | Property shape is scalar or `Array[scalar]`, one level, non-null items; nested richness becomes nodes/edges; relational/SQL emission carries the property's canonical type. | `c9e44bf`, `ddc69da`; then `tests/test_neo4j_module.py`, `tests/test_relational_lowering.py`; `docs/reference/types.md#graph-property-shape`, `docs/concepts/topology.md` | topology, types, duckdb |

## Interpreter

The interpreter assembles the semantic blueprint and exposes typed cross-symbol
references. It is distribution-side, not kernel.

| ID | Decision | Date | Status | Context | Consequence | Evidence | Areas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-030 | Consume an engine-neutral relation plan and injected `SqlEmitter`; core imports no DuckDB module. | 2026-11-05 | accepted; builds on `f7070a3` custom emitter threading | Core planners were importing DuckDB types/emitters, so a second engine required editing core. | The neutral plan and `SqlEmitter` live under `distribution/service/internal`; `DuckDbSqlEmitter` implements the protocol; core planners take an emitter and never import `modules/duckdb`. | `640f857`, `f7070a3`; `tests/distribution/planners/test_core_custom_emitter.py`, `test_planner_imports_no_pipeline.py`; `docs/developer/data-and-expressions.md#planning-boundary` | interpreter, core, duckdb, modules |
| D-031 | Build the blueprint from symbols and typed refs; group feature code into modules and type execution resources. | 2026-11-04 | accepted | Cross-symbol fields were strings and modules/resources had no typed boundary. | `NodeRef`/`EdgeRef`/`RelationRef`/`FieldRef`/`PropertyRef`/`AssetRef`/`OperationRef` wrap `SymbolRef`; paths/roles are typed; each feature is a module with planners/executors/resources. | `24c8cc2`; `tests/distribution/test_typed_refs.py`, `tests/pipeline/test_pipeline_identity.py`; `docs/developer/system-design.md#typed-references-and-expression-fragments`, `README.md#package-groups` | interpreter, refs, modules |

## Modules

Modules are feature packages: they supply planners/executors/resources and
contribute ordinary steps. There is no registry.

| ID | Decision | Date | Status | Context | Consequence | Evidence | Areas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-032 | Model an operation as one specification plus an emitter registry, not a dispatcher edit. | 2026-10-30 | accepted | Each new expression operator edited a central dispatcher in the DuckDB path. | An operation spec lives with expressions; the engine emitter registry adds the SQL; adding an operation does not edit a dispatcher. | `c16ec29`; `tests/test_custom_operation.py`; `AGENTS.md#kernel-and-distribution`, `docs/reference/expressions.md` | expressions, duckdb, modules |
| D-033 | Let the merge planner take an explicit component scope. | 2026-10-28 | accepted | Merging every bound component by minimum value is wrong for deliberately distinct edge families. | `MergingConfiguration(components=...)` restricts the rewrite; unnamed components keep every row; merge remains distinct from aggregation. | `c38b2b4`; `tests/distribution/planners/test_dedup_merge_conflict_planners.py`; `docs/reference/planners-and-executors.md#mergingplanner` | merging, modules, planners |

## CLI/API

The composition root and CLI are thin surfaces over the distribution; the
facade stays static for external type checkers.

| ID | Decision | Date | Status | Context | Consequence | Evidence | Areas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-034 | Give the CLI the same public/internal/private layout as every other leaf. | 2026-11-02 | accepted | The CLI was outside the package-layout contract and could accumulate mechanism. | `cli/` follows model/service zones; architecture tests cover it; the layout rule is universal, not framework-only. | `8221a9a`; `tests/test_architecture.py`, `tests/test_public_docstrings.py`; `ARCHITECTURE.md`, `specs/README.md#zones` | cli, layout, architecture |
| D-035 | Keep the lazy facade statically readable for external type checkers and expose an explicit authoring export table. | 2026-11-04 | accepted | A purely dynamic `__getattr__` facade hid public names from pyright and IDEs. | `kg_build_system/__init__.py` has a literal `__all__`, a lazy group table and typed re-exports; the authoring surface is explicit rather than incidental imports. | `c3e2cab`, `af003c0`; `tests/test_facades.py`, `tests/test_public_api.py`; `README.md#package-groups`, `FRAMEWORK_STATE.md#current-tree` | api, facades, typing |

## Docs/process

These are rules about how the work is reviewed and written, stated in
`AGENTS.md`/`STYLE.md` and enforced by tests or docs structure.

| ID | Decision | Date | Status | Context | Consequence | Evidence | Areas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-036 | Require a rule-promotion check at the end of every change. | 2026-10-29 | accepted | Fixes were repeated because no general rule was captured; incident-specific notes accumulated. | A change report ends with none/refined/added; a general rule goes to agent behaviour or framework model; refine an existing point rather than add a case; only the main agent edits `AGENTS.md`. | `1bfcc1f`, `f919662`; no test; `AGENTS.md#rule-promotion` | process, AGENTS |
| D-037 | Make a subagent brief an interface specification with an acceptance test, and reuse the same session for corrections. | 2026-11-02 | accepted | Task-description briefs left interface decisions to subagents; fresh correction sessions lost context. | The brief names exact symbols, import edges, shims, wrapper shape and judging command; the acceptance test is written first; corrections go to the same session with the named defect and command. | `64a622c`, `e39c988`, `df419a3`; no test; `AGENTS.md#delegation` | process, delegation |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted; `5bcdcea` aggregate-spec approach superseded by `44bc4fe` | Early docs were simplified author summaries mixed with internal interface specs. | `docs/` is author-facing and detailed; `docs/developer/` is the canonical interface guide; `specs/` defers to it; the site splits tutorial/concepts/how-to/reference. | `49a3ec7`, `3a74687`, `a88299b`, `44bc4fe`; no test; `STYLE.md`, `docs/developer/index.md`, `specs/README.md` | docs, specs, process |
| D-039 | Guard the architecture with a contract test and a reviewer briefing. | 2026-11-02 | accepted | Architecture rules existed only as prose and drifted from the package tree. | `tests/test_architecture.py` checks zones/imports/layout; `FRAMEWORK_STATE.md` gives reviewers the current tree, verification and limits; `DESIGN_ISSUES.md` records limits. | `7f0ea1b`; `tests/test_architecture.py`; `FRAMEWORK_STATE.md`, `docs/developer/testing.md#distribution-and-dto-scope` | architecture, tests, docs |

## Supersession and refinement ledger

| Earlier decision/commit | Later commit | What changed | Candidate |
| --- | --- | --- | --- |
| `d61f886` "blueprint the only public DTO and hide it on the canonical path" | `39f46e0` then `69720f0` | Assembly separated from compile; compile became a pure consumer and the blueprint a public handle. | D-004 |
| `5b724c1` "blueprint a public artifact and compile a pure consumer" | `69720f0` | Compile no longer calls the blueprint package; the composition root creates the blueprint. | D-004 |
| `74773e1` "define lowering as local to one layer" | `edc2e9e`, `395e98e` | "Lowering" was removed from the naming rule; the verbs are discover/transcribe/link/plan/emit/render. | D-009 |
| `3c78df0` initial relational row-source algebra | `d7faad8` | The algebra was merged into the unified data/field model and its DTOs. | D-016 |
| `5a6ccbd` unify field declarations and source nullability | `330c09c` | Replaced by the single `Selection[T]` model with owner-derived nullability. | D-014 |
| `22c4390` explicit abstract inheritance requirement | `e88a0ca` | The requirement and the "at least one node producer" constraint were removed; base order and endpoint narrowing remain. | D-027 |
| `5bcdcea` aggregate internal specs and align author docs | `44bc4fe` | The aggregate spec directory was reduced to an index that defers to `docs/developer/`; author pages were rewritten for the final pipeline. | D-038 |
| `5ee6a1b` removed source data tracking; `22fedcd` added column override | `ac00c5b` | Generation stopped inferring nullability; observation is provenance and overrides stay declaration-time. | D-025 |
| `3d95933` pure contract + rename build to execution | `051732b` | The two-stage pipeline was replaced by the three stages build/compile/execute with a toolchain kernel. | not carried forward |

## Notes on evidence quality and uncertainty

- **No commit bodies.** `git log` for the last 120 commits returned 0 non-empty
  bodies. Context/consequence are reconstructed from subjects, `--stat` paths
  and the HEAD docs. A commit subject is not a rationale; where the docs do not
  repeat the rule, the candidate is marked with a narrower evidence base.
- **Author dates are not merge dates.** All dates are `%ad` (author date), as
  requested. Several same-day commits (`28311a6`/`051732b`, `39f46e0`/
  `69720f0`, `22c4390`/`e88a0ca`) are ordered by `git log`, not by a separate
  merge record.
- **Historical test paths.** Tests were reorganized repeatedly
  (`tests/test_*.py` → `tests/distribution/...`, `tests/kernel/...`). Rows use
  "then" for a path that existed at the commit and name a current equivalent
  only when it genuinely covers the same boundary. A missing current test is
  not evidence that the decision was reverted; docs and code still carry it.
- **"Accepted" is survival, not a vote.** There is no ADR directory and no
  status field in the repository. A candidate is accepted when HEAD code/docs
  still express it and no later commit in the window reverses it. The
  supersession ledger names every reversal/refinement found by reading subjects
  and diffs.
- **Counts in `FRAMEWORK_STATE.md`/`README.md` were not re-run.** This survey
  was read-only; "259 tests, 1858 subtests, pyright 0 errors" is reported as a
  project claim, not a measured result.
- **Some early decisions are underspecified.** D-026 (DuckDB type matrix) and
  D-027/D-028 (topology inheritance) originate in September commits whose test
  paths have moved; their current statements in `reference/types.md` and
  `reference/topology.md` are the clearest evidence, with the commit as origin.
- **Potential missing candidates.** Commits about the legacy assembler
  (`29ebdae`, `693b234`), the reference project and documentation copy-edits
  were not promoted: they are implementation waves or change reports, not
  durable rules. `dcb5eb6` (table → data language rename) is represented by
  D-002/D-010 rather than a separate candidate.

## Areas index

| Area | Candidates |
| --- | --- |
| kernel | D-001, D-002, D-003, D-004, D-005, D-006, D-007, D-008 |
| pipeline/workflow | D-005, D-006, D-007 |
| linker/languages | D-008, D-009 |
| layout/imports | D-010, D-011, D-034 |
| authoring API/facades | D-012, D-014, D-035 |
| expressions | D-014, D-018, D-019, D-020, D-032 |
| data/row sources | D-015, D-016, D-017, D-018, D-019 |
| asset/ingest | D-021, D-022, D-025, D-026 |
| semantics/graph | D-023, D-025 |
| generation | D-024, D-025, D-026 |
| topology/bindings | D-027, D-028, D-029 |
| interpreter/refs | D-030, D-031 |
| modules/planners | D-022, D-030, D-032, D-033 |
| cli/api | D-034, D-035 |
| docs/process | D-036, D-037, D-038, D-039 |
