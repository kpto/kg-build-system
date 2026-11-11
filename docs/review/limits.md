---
title: Limits
summary: The product boundaries a consumer must accept, and the evidence that keeps them honest.
section: review
order: 30
status: normative
verified: 2026-11-10
sources:
  - DESIGN_ISSUES.md
  - AGENTS.md
  - docs/reference/planners-and-executors.md
  - kg_build_system/distribution/modules/conflict_validation/
  - FRAMEWORK_STATE.md
subject: verification
perspective: review
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Verification, limits and debugging</span><a href="/subjects/verification">Overview</a><a href="/review/limits">Guide</a><a href="/spec/verification">Spec</a><a href="/reference/failures">API</a><a href="/philosophy/explainability-is-authored">Philosophy</a><a href="/review/decisions" class="active">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> A limit is a boundary the framework chose, not a defect it forgot. Read it as part of the interface: if a consumer needs the missing behaviour, the composition changes before the kernel does.

## What it is

A limit is a product boundary stated where a consumer meets it. The boundary is normative: the code refuses the unsupported case instead of approximating it. [Architecture](/review/architecture) explains why the split falls here; [Quality](/operate/quality) and [Outputs](/operate/outputs) show what the boundary costs in practice.

| Boundary | The limit |
| --- | --- |
| Composition | A `Toolchain` is the only composition unit. There is no registry; a caller passes planners and executors. |
| SQL engine | DuckDB is the default emitter. `DuckDbSqlEmitter` implements the neutral `SqlEmitter`; core imports no DuckDB module. |
| Python step | A Python instruction is a reference `("python", "cpython")` carrying `{module, qualname}`, not a live callable. There is no isolation, timeout or retry. |
| Blueprint fields | Public `GraphBlueprint` fields use internal language DTOs: `graph`, `data`, `assets`, `bindings` and `graph_declaration`. Those DTOs are not exported public names. |
| Source formats | There is no adapter registry. `DuckDbSourcePlanner` reads parquet, json and csv; another format is another ordinary planner. |
| Asset layout | `AssetLayout` is descriptive. It opens no file and proves no relation. |
| Struct keys | A repeated struct graph name takes its qualified Python name as an extra key segment. |
| Instructions | `execute` builds the exact-kind map before the first step and refuses an unregistered kind with `ValueError`. |
| Dedup | Deduplication removes only rows identical in every column. A repeated key with different values survives. |
| Merge | Merging groups by build key and keeps the SQL `min()` per property. It needs an explicit component scope and is not aggregation. |
| Conflict checks | Validation is blind to null-vs-value, edge endpoints, `_kg_binding_symbol`, unbound components and extra columns. Run after a merge, it finds nothing. |
| Neo4j | Neo4j output is export-only: Parquet files, an import script and a summary. There is no driver and no write-back. |
| CLI | `kbs` generates source. It does not build, compile or execute. |
| Versioning | There is no schema version, plan migration or blueprint migration. |

## Rules

- Remove a limit only with the docs change in the same change; code that drops a limit while the docs keep it is a review defect.
- State the boundary where the consumer meets it, not as an implementation excuse.
- Refuse the unsupported case: exact instruction kinds, exact dedup, explicit merge scope.
- A new engine or format is an ordinary emitter or planner, never a registry entry.
- Keep the boundary out of the kernel; the dependency spine belongs to [Architecture](/review/architecture).
- Measure the cost before claiming a capability; [Quality](/operate/quality) and [Outputs](/operate/outputs) are the consumer-facing evidence.

## Evidence

| Claim | Measurement |
| --- | --- |
| Static types | `uv run pyright` reports 1 error, in `kg_build_system/api.py`. |
| Docs claim | The framework docs state 0 pyright errors; the same run reports 1. |
| CI | The repository has no CI configuration; every check is manual. |
| Open Targets | The 7-test suite is external and is not run in this checkout. |
| Counts | The framework docs state 259 tests and 1,858 subtests; the measured checkout reports 354 and 1,957. |
| Drift | The doc/code gaps are tabulated on [Verification](/review/verification). |

## Limits

- This page describes the boundary at the source HEAD shown in [Verification](/review/verification); a checkout with local changes can differ.
- A limit can be intentional and still hurt. The table records the cost, not a promise to remove it.
- The conflict blind spots are structural, not a bug list; a new check is a new planner.
- No CI means no limit is enforced between manual runs.
- An external suite is evidence about another project, not this checkout.

## Next

[Verification](/review/verification) — the counts and doc/code gaps behind these claims.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-001 | Separate a domain-agnostic toolchain kernel from the KG distribution. | 2026-11-03 | accepted | `tests/kernel/test_import_isolation.py`; `AGENTS.md#kernel-and-distribution` |
| D-022 | Use a generic source planner for parquet/json/csv and reject an adapter registry. | 2026-11-04 | accepted | `tests/distribution/planners/test_duckdb_source_planner.py`; `DESIGN_ISSUES.md` |
| D-030 | Consume an engine-neutral relation plan and injected `SqlEmitter`; core imports no DuckDB module. | 2026-11-05 | accepted | `tests/distribution/planners/test_core_custom_emitter.py` |
| D-033 | Let the merge planner take an explicit component scope. | 2026-10-28 | accepted | `tests/distribution/planners/test_dedup_merge_conflict_planners.py`; `docs/reference/planners-and-executors.md#mergingplanner` |
