---
title: Decisions
summary: The 39 dated rules the framework follows, aggregated from the decisions each page owns.
section: review
order: 40
status: normative
verified: 2026-11-10
sources:
  - AGENTS.md
  - FRAMEWORK_STATE.md
  - DESIGN_ISSUES.md
  - docs/developer/system-design.md
  - docs/developer/index.md
---

> [!lede]
> The register is generated from the rows each page owns. A decision ID is stable; its text is the rule, and the same ID must read the same on every page.

## What it is

The register holds 39 decisions, `D-001` to `D-039`, drawn from `research/decisions-candidates.md`. Each row names a rule the project follows at HEAD, its author date, its survival status and its evidence. The generated block below aggregates every decision row found on a page.

| Theme | IDs | Question it settles |
| --- | --- | --- |
| Kernel and architecture | `D-001`–`D-013` | Where does code belong, and how do the three stages compose? |
| Expressions and data | `D-014`–`D-020` | What is a value, a row source and a row effect? |
| Semantics, asset and generation | `D-021`–`D-026` | What is a source unit, a meaning and an edit-time product? |
| Topology and binding | `D-027`–`D-029` | What may a component carry, and how does a row become a record? |
| Interpreter and modules | `D-030`–`D-033` | How does the blueprint become a plan without an engine dependency? |
| CLI, API and docs | `D-034`–`D-039` | How are the public surface and the review process guarded? |

The invariants those rules protect are stated in [Contracts](/review/contracts). A decision that no longer matches its sources is a drift candidate; [Drift](/review/drift) defines when the page returns to review.

## Rules

- Every row uses an ID from the candidate file; never invent an ID, date or evidence path.
- A shared ID has identical decision text on every page. A mismatch is a validation error.
- A row exists because the decision governs the page, not because the page mentions it.
- The date is the author date of the decision; the status is `accepted` unless a later candidate supersedes it.
- Evidence names a test or doc path that still supports the rule.
- The generated block is the index; the page row is the claim it indexes.

## Evidence

<!-- BEGIN GENERATED:decisions -->
| ID | Decision | Date | Status | Page | Evidence |
| --- | --- | --- | --- | --- | --- |
| D-001 | Separate a domain-agnostic toolchain kernel from the KG distribution. | 2026-11-03 | accepted | [review/architecture](/review/architecture), [review/decisions](/review/decisions), [review/limits](/review/limits) | `tests/kernel/test_import_isolation.py` |
| D-002 | Use toolchain vocabulary in the kernel and domain vocabulary only in the distribution. | 2026-11-03 | accepted | [review/architecture](/review/architecture), [review/decisions](/review/decisions) | `tests/test_naming.py` |
| D-003 | Treat canonical types as a kernel assumption and keep default implementations in the distribution. | 2026-11-03 | accepted | [author/data](/author/data), [review/decisions](/review/decisions) | `tests/kernel/test_kernel.py` |
| D-004 | Make compile a pure consumer of a separately assembled blueprint. | 2026-11-03 | accepted | [pipeline/blueprint](/pipeline/blueprint), [pipeline/link](/pipeline/link), [pipeline/plan](/pipeline/plan), [review/contracts](/review/contracts), [review/decisions](/review/decisions) | `tests/kernel/test_toolchain_flow.py` |
| D-005 | Make the workflow contract step-centric and instruction-based, with exact instruction kinds. | 2026-11-03 | accepted | [operate/extend](/operate/extend), [operate/outputs](/operate/outputs), [pipeline/execute](/pipeline/execute), [pipeline/plan](/pipeline/plan), [review/contracts](/review/contracts), [review/decisions](/review/decisions) | `tests/kernel/test_kernel.py`; `docs/reference/compile.md` |
| D-006 | Use Key-backed role types for every identity that crosses pipeline boundaries. | 2026-11-04 | accepted | [pipeline/blueprint](/pipeline/blueprint), [pipeline/plan](/pipeline/plan), [review/contracts](/review/contracts), [review/decisions](/review/decisions) | `tests/pipeline/test_pipeline_identity.py` |
| D-007 | Emit pipeline events and let resource providers subscribe to lifecycle events. | 2026-11-04 | accepted | [operate/debug](/operate/debug), [operate/extend](/operate/extend), [pipeline/execute](/pipeline/execute), [review/decisions](/review/decisions) | `tests/kernel/test_runtime_events.py`; `docs/developer/system-design.md` |
| D-008 | Let the linker own root selection and resolve the authoring reference closure before transcription. | 2026-11-04 | accepted | [pipeline/link](/pipeline/link), [review/contracts](/review/contracts), [review/decisions](/review/decisions) | `tests/distribution/test_blueprint_linker.py` |
| D-009 | Use one verb per transformation; make render the reverse of transcribe and move codecs out of Language. | 2026-11-03 | accepted | [pipeline/link](/pipeline/link), [review/decisions](/review/decisions) | `tests/test_naming.py` |
| D-010 | Give every framework leaf the same model/service zone layout. | 2026-11-03 | accepted | [review/architecture](/review/architecture), [review/decisions](/review/decisions) | `tests/test_layout.py` |
| D-011 | Keep private helpers out of interface zones and break service/private cycles with function-local imports. | 2026-11-03 | accepted | [review/architecture](/review/architecture), [review/decisions](/review/decisions) | `tests/test_layout.py` |
| D-013 | Keep debug names out of the blueprint fingerprint. | 2026-11-02 | accepted | [author/bindings](/author/bindings), [philosophy/binding-is-the-seam](/philosophy/binding-is-the-seam), [review/decisions](/review/decisions) | `docs/developer/system-design.md#identity` |
| D-014 | Unify authoring around `Selection[T]` with owner-derived nullability. | 2026-11-05 | accepted | [author/data](/author/data), [author/values](/author/values), [review/contracts](/review/contracts), [review/decisions](/review/decisions) | `tests/test_authoring_api.py` |
| D-015 | Make bindings accept row-source values, not declaration classes. | 2026-10-29 | accepted | [author/bindings](/author/bindings), [author/grain](/author/grain), [philosophy/binding-is-the-seam](/philosophy/binding-is-the-seam), [review/decisions](/review/decisions) | `tests/test_authoring_api.py` |
| D-016 | Own the relational row-source algebra in the data language as a small frozen plan DTO. | 2026-10-29 | accepted | [author/grain](/author/grain), [review/decisions](/review/decisions) | `docs/developer/data-and-expressions.md#row-source-model` |
| D-017 | Require projections to be pinned to exactly one row source. | 2026-10-29 | accepted | [author/projections](/author/projections), [philosophy/binding-is-the-seam](/philosophy/binding-is-the-seam), [review/decisions](/review/decisions) | `docs/reference/projections.md#projectionsource` |
| D-018 | Gate every row effect behind a one-shot `alter_rows()` handle. | 2026-10-29 | accepted | [author/values](/author/values), [review/decisions](/review/decisions) | `tests/test_authoring_api.py` |
| D-019 | Add `lookup`, `zip` and row-source `unnest` as explicit value/grain operations. | 2026-11-05 | accepted | [author/grain](/author/grain), [author/projections](/author/projections), [author/values](/author/values), [review/decisions](/review/decisions) | `tests/distribution/test_expression_operations.py` |
| D-020 | Use `extract` as the member-read name and remove compatibility aliases. | 2026-11-04 | accepted | [author/values](/author/values), [review/decisions](/review/decisions) | `tests/test_authoring_api.py` |
| D-021 | Model an asset as one logical source unit and keep layout descriptive, not an access contract. | 2026-11-04 | accepted | [author/assets](/author/assets), [philosophy/meaning-first](/philosophy/meaning-first), [review/decisions](/review/decisions) | `tests/distribution/test_asset_language.py` |
| D-022 | Use a generic source planner for parquet/json/csv and reject an adapter registry. | 2026-11-04 | accepted | [author/assets](/author/assets), [operate/outputs](/operate/outputs), [review/decisions](/review/decisions), [review/limits](/review/limits) | `tests/distribution/planners/test_duckdb_source_planner.py` |
| D-023 | Add semantics and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | [author/meaning](/author/meaning), [philosophy](/philosophy/), [philosophy/anti-patterns](/philosophy/anti-patterns), [philosophy/design-in-semantics](/philosophy/design-in-semantics), [philosophy/explainability-is-authored](/philosophy/explainability-is-authored), [philosophy/meaning-first](/philosophy/meaning-first), [philosophy/review-top-down](/philosophy/review-top-down), [philosophy/semantic-hierarchy](/philosophy/semantic-hierarchy), [review/contracts](/review/contracts), [review/decisions](/review/decisions) | `tests/distribution/test_semantics_language.py` |
| D-024 | Keep generation an inert edit-time frontend, separate from the asset model and blueprint. | 2026-11-04 | accepted | [author/generation](/author/generation), [review/decisions](/review/decisions) | `tests/test_codegen_discovery.py` |
| D-025 | Treat observation as provenance: every generated source field renders `Field[T]`, never an optional annotation. | 2026-11-05 | accepted | [author/data](/author/data), [author/generation](/author/generation), [review/decisions](/review/decisions) | `tests/test_codegen_discovery.py` |
| D-027 | Support polymorphic categories/templates with one normative base order. | 2026-09-01 | accepted | [author/topology](/author/topology), [philosophy/semantic-hierarchy](/philosophy/semantic-hierarchy), [review/decisions](/review/decisions) | `docs/reference/topology.md#base-order` |
| D-028 | Require an `endpoint(...)` token only when the declared edge side is abstract. | 2026-09-01 | accepted | [author/bindings](/author/bindings), [author/topology](/author/topology), [review/decisions](/review/decisions) | `docs/reference/bindings.md#endpoint-tokens` |
| D-029 | Restrict graph properties to scalars or flat arrays of non-null scalars, and type SQL output by the property type. | 2026-10-22 | accepted | [author/data](/author/data), [author/meaning](/author/meaning), [author/topology](/author/topology), [review/decisions](/review/decisions) | `docs/reference/types.md#graph-property-shape` |
| D-030 | Consume an engine-neutral relation plan and injected `SqlEmitter`; core imports no DuckDB module. | 2026-11-05 | accepted | [operate/extend](/operate/extend), [pipeline/plan](/pipeline/plan), [review/architecture](/review/architecture), [review/decisions](/review/decisions), [review/limits](/review/limits) | `tests/distribution/planners/test_core_custom_emitter.py` |
| D-031 | Build the blueprint from symbols and typed refs; group feature code into modules and type execution resources. | 2026-11-04 | accepted | [philosophy/design-in-semantics](/philosophy/design-in-semantics), [philosophy/meaning-first](/philosophy/meaning-first), [pipeline/blueprint](/pipeline/blueprint), [review/architecture](/review/architecture), [review/decisions](/review/decisions) | `tests/distribution/test_typed_refs.py` |
| D-033 | Let the merge planner take an explicit component scope. | 2026-10-28 | accepted | [operate/quality](/operate/quality), [review/decisions](/review/decisions), [review/limits](/review/limits) | `tests/distribution/planners/test_dedup_merge_conflict_planners.py`; `docs/reference/planners-and-executors.md#mergingplanner` |
| D-036 | Require a rule-promotion check at the end of every change. | 2026-10-29 | accepted | [operate/ship](/operate/ship), [review/decisions](/review/decisions), [review/design-notes](/review/design-notes), [review/drift](/review/drift) | `AGENTS.md#rule-promotion` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | [philosophy](/philosophy/), [philosophy/anti-patterns](/philosophy/anti-patterns), [philosophy/explainability-is-authored](/philosophy/explainability-is-authored), [philosophy/review-top-down](/philosophy/review-top-down), [review/decisions](/review/decisions), [review/design-notes](/review/design-notes), [review/drift](/review/drift) | `STYLE.md`; `docs/developer/index.md` |
| D-039 | Guard the architecture with a contract test and a reviewer briefing. | 2026-11-02 | accepted | [operate/ship](/operate/ship), [philosophy/anti-patterns](/philosophy/anti-patterns), [philosophy/explainability-is-authored](/philosophy/explainability-is-authored), [philosophy/review-top-down](/philosophy/review-top-down), [review/architecture](/review/architecture), [review/decisions](/review/decisions), [review/verification](/review/verification) | `tests/test_architecture.py` |
<!-- END GENERATED:decisions -->

## Limits

- `accepted` records survival in the history window, not a vote or a formal ADR status. The repository has no ADR directory and no status field.
- The candidate survey read commit subjects and changed paths, not commit bodies; context and consequence are inferred.
- Test paths moved during the project. A missing current test is not evidence that a decision was reversed.
- Some decisions are underspecified at their origin; the current doc is the clearer statement than the commit.
- The history window ends at the source HEAD named in the candidate file. Later commits are not assessed.
- A decision is not a compatibility promise; no plan or blueprint migration follows from it.

## Next

[Contracts](/review/contracts) — the invariants these decisions protect.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-039 | Guard the architecture with a contract test and a reviewer briefing. | 2026-11-02 | accepted | `tests/test_architecture.py`; `FRAMEWORK_STATE.md`; `DESIGN_ISSUES.md` |
