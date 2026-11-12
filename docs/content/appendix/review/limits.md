---
title: Limits
summary: The current composition boundaries, classified by kind, with the object that replaces each one.
section: review
order: 30
status: normative
verified: 2026-11-10
sources:
  - DESIGN_ISSUES.md
  - AGENTS.md
  - docs/content/appendix/reference/planners-and-executors.md
  - kg_build_system/distribution/modules/conflict_validation/
  - FRAMEWORK_STATE.md
subject: verification
perspective: review
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Verification, limits and debugging</span><a href="/appendix/subjects/verification">Overview</a><a href="/book/part-4/04-limits-and-evidence">Guide</a><a href="/appendix/spec/verification">Spec</a><a href="/appendix/reference/failures">API</a><a href="/appendix/philosophy/explainability-is-authored">Philosophy</a><a href="/appendix/review/decisions" class="active">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> A limit is a boundary the current composition chose. Read it as an interface: most limits name the object that replaces them; a model rule names why no composition should. The kernel changes only when the protocol set cannot carry the concept.

## What it is

A limit is a product boundary stated where a consumer meets it: the code refuses the unsupported case instead of approximating it. [Architecture](/appendix/review/architecture) explains the split; [Kernel protocols](/appendix/kernel/protocols) states the extension surface; [Quality](/book/part-3/04-quality-and-failure) and [Outputs](/book/part-3/03-execution-and-outputs) show its cost.

- **Model rule** — a semantic constraint; changing it is a model change. Example: a nested property is reified as nodes and edges.
- **Replaceable default** — the composition's choice, replaced by another implementation of the same protocol. Example: `DuckDbSqlEmitter` implements `SqlEmitter`.
- **Current algorithm** — the default implementation's method, replaced by another planner. Example: `group_by` collects but does not aggregate.
- **Not implemented** — absent from the current objects; a new object carries it. Example: no per-step timeout or retry.
- **Interface limit** — the public surface does not carry the concept; a public view or model change does. Example: public blueprint fields use internal language DTOs.
- **Empirical** — an unmeasured question, not an expressive boundary. Example: 5.9M annotations are unproven at scale.

| Boundary | Current choice | Kind | Extension point / why it is a model rule |
| --- | --- | --- | --- |
| Composition | `Toolchain` only; no registry | model rule | Compose another `Toolchain`; a language, planner or executor is a value, not a registry entry; a provider is added to the runtime. |
| SQL engine | DuckDB default emitter | replaceable default | Implement `SqlEmitter` and compose the executor. |
| Source formats | parquet, json, csv | replaceable default | Another ordinary planner; no adapter registry. |
| Row algebra | `group_by` collects; no aggregation or majority vote | current algorithm | A module: `Planner` + `StepExecutor`. |
| Source decoding | No semicolon-list decoder | not implemented | Source planner/executor or a language operation. |
| Python instruction payload | `{module, qualname}` reference | model rule | A new executor kind or external service. |
| Python execution | No isolation, timeout or retry | not implemented | A new executor or runtime. |
| Blueprint fields | Public fields use internal language DTOs | interface limit | Public view or opaque token; interface change. |
| Asset layout | Descriptive, not an access contract | model rule | No extension; a planner may interpret it. |
| Struct keys | Repeated struct names take a qualified key segment | model rule | No extension. |
| Instructions | Exact-kind map; unknown kind refused | model rule | Another executor claims another exact kind. |
| Dedup | Removes only identical rows | current algorithm | Another planner. |
| Merge | Build-key groups, `min()` per property, explicit scope | current algorithm | Another planner. |
| Conflict checks | Blind to null-vs-value, endpoints, `_kg_binding_symbol`, unbound components, extra columns | current algorithm | A new planner. |
| Neo4j | Export-only Parquet and import script | current algorithm | Another output module. |
| CLI | `kbs generate` only | interface limit | Compose Python calls; a new frontend adds commands. |
| Versioning | No schema version, plan or blueprint migration | not implemented | Versioned codec envelope; no compatibility promise. |
| Undirected edges | Directed `Edge[Source, Target]` only | model rule | Reify the assertion or add a language declaration kind; a model change. |
| Download/ingest | No network acquisition step | not implemented | `ResourceProvider` + executor, or an external script for reproducibility. |
| Licence enforcement | No built-in filter | not implemented | Resource facts + a filter module. |
| Incremental update | Whole-plan rebuild | not implemented | Runtime/planner extension. |
| Scale | 5.9M annotations unproven | empirical | Benchmark question, not an expressive limit. |
| CI | No CI configuration | empirical | Delivery gap, not a framework limit. |

Every row is one of the six kinds; the ladder is in [Extend the toolchain](/book/part-4/01-the-kernel-and-extension#the-extension-ladder).

## Rules

- Remove a limit only with the docs change in the same change; code that drops a limit while the docs keep it is a review defect.
- State the boundary where the consumer meets it, not as an implementation excuse.
- Refuse the unsupported case: exact instruction kinds, exact dedup, explicit merge scope.
- A new engine or format is an ordinary emitter or planner, never a registry entry.
- A model rule is not an extension point: no doc may say "the framework cannot" before checking the kernel protocol set; name the extension point and its cost.
- Keep the boundary out of the kernel; the dependency spine belongs to [Architecture](/appendix/review/architecture).
- Measure the cost before claiming a capability; [Quality](/book/part-3/04-quality-and-failure) and [Outputs](/book/part-3/03-execution-and-outputs) are the consumer-facing evidence.

## Evidence

| Claim | Measurement |
| --- | --- |
| Static types | `uv run pyright` reports 1 error, in `kg_build_system/api.py`. |
| Docs claim | The framework docs state 0 pyright errors; the same run reports 1. |
| CI | The repository has no CI configuration; every check is manual. |
| Open Targets | The 7-test suite is external and is not run in this checkout. |
| Counts | The framework docs state 259 tests and 1,858 subtests; the measured checkout reports 354 and 1,957. |
| Drift | The doc/code gaps are tabulated on [Verification](/appendix/review/verification). |

## Limits

- This page describes the current composition, not the framework's expressive boundary.
- This page describes the boundary at the source HEAD shown in [Verification](/appendix/review/verification); a checkout with local changes can differ.
- A limit can be intentional and still hurt. The table records the cost, not a promise to remove it.
- The conflict blind spots are structural, not a bug list; a new check is a new planner.
- No CI means no limit is enforced between manual runs.
- An external suite is evidence about another project, not this checkout.

## Next

[Verification](/appendix/review/verification) — the counts and doc/code gaps behind these claims.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-001 | Separate a domain-agnostic toolchain kernel from the KG distribution. | 2026-11-03 | accepted | `tests/kernel/test_import_isolation.py`; `AGENTS.md#kernel-and-distribution` |
| D-022 | Use a generic source planner for parquet/json/csv and reject an adapter registry. | 2026-11-04 | accepted | `tests/distribution/planners/test_duckdb_source_planner.py`; `DESIGN_ISSUES.md` |
| D-030 | Consume an engine-neutral relation plan and injected `SqlEmitter`; core imports no DuckDB module. | 2026-11-05 | accepted | `tests/distribution/planners/test_core_custom_emitter.py` |
| D-033 | Let the merge planner take an explicit component scope. | 2026-10-28 | accepted | `tests/distribution/planners/test_dedup_merge_conflict_planners.py`; `docs/content/appendix/reference/planners-and-executors.md#mergingplanner` |
