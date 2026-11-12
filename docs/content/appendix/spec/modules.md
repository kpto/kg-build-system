---
title: Modules specification
summary: Modules claim exact instruction kinds and state their quality and output limits.
section: spec
perspective: spec
subject: modules
spec: SPEC-012
order: 120
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/modules/duckdb/service/_private/executor.py
  - kg_build_system/distribution/modules/deduplication/service/_private/planner.py
  - kg_build_system/distribution/modules/merging/service/_private/planner.py
  - kg_build_system/distribution/modules/conflict_validation/service/_private/planner.py
  - docs/content/appendix/reference/planners-and-executors.md
evidence:
  - tests/distribution/planners/test_dedup_merge_conflict_planners.py
  - tests/distribution/planners/test_duckdb_source_planner.py
  - tests/distribution/executors/targets/
  - tests/distribution/executors/targets/test_conflict_report.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Modules, outputs and quality</span><a href="/appendix/subjects/modules">Overview</a><a href="/book/part-3/03-execution-and-outputs">Guide</a><a href="/appendix/spec/modules" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/anti-patterns">Philosophy</a><a href="/appendix/review/limits">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** Every instruction kind MUST be one exact pair from the module table; a module MUST NOT claim a prefix, family or fallback kind.
- **R2.** Deduplication MUST run `SELECT DISTINCT *` over the full bound row, including `_kg_binding_symbol`; it MUST NOT group by build key or choose a survivor.
- **R3.** Merging MUST group by `build_key` and take `min()` for every declared property. For an edge it MUST also minimize `source_build_key` and `target_build_key`.
- **R4.** Merging SHOULD take an explicit `components` scope; the default all-bound scope MUST NOT be used for edge families that retain parallel facts.
- **R5.** Conflict validation MUST count distinct non-null values per property per `build_key` and MUST flag a count above one. It SHOULD run before merging, after which it normally finds nothing.
- **R6.** Conflict validation MUST be blind to null-versus-value, endpoint keys, `_kg_binding_symbol`, unbound components and undeclared columns.
- **R7.** The file target MUST write JSON Lines for every received graph relation, adding `build_key`, `type` and `kind`.
- **R8.** The meta-graph target MUST write a JSON document and SHOULD write the optional self-contained HTML page.
- **R9.** Neo4j MUST export Parquet files and an `import_neo4j.py` script; it MUST NOT open a driver, Cypher session or live database connection.
- **R10.** The conflict report MUST stay in memory. With findings and `fail_on_error=False` it MUST publish and forward records; with `True` it MUST fail and MUST NOT forward records.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/distribution/planners/test_dedup_merge_conflict_planners.py` | Deduplication and merging use their exact kinds and outputs; merge scope selects components; findings and report steps carry their declared payloads and publications. |
| `tests/distribution/planners/test_duckdb_source_planner.py` | The shared DuckDB source planner emits its exact instruction kind and reads only the tables a binding uses. |
| `tests/distribution/executors/targets/` | File, meta-graph and Neo4j executors write only their documented artifacts, with the target tests in this directory. |
| `tests/distribution/executors/targets/test_conflict_report.py` | Findings publish a report; `fail_on_error` decides between forwarding and failing without forwarded records. |

## API

| Exact kind | Module surface | Contract |
| --- | --- | --- |
| `source_relation/duckdb` | `DuckDbSourcePlanner` + `DuckDbExecutor` | Opens one asset relation and warns when the source needs a fallback. |
| `sql/duckdb` | core planners + `DuckDbExecutor` | Materializes one SQL relation from the instruction payload. |
| `aggregate/duckdb` | `RecordsPlanner` + `DuckDbExecutor` | Unions every input relation under one aggregate view. |
| `deduplication/duckdb` | `DeduplicationPlanner` + `DuckDbExecutor` | Materializes `SELECT DISTINCT *` over the input relation. |
| `merging/duckdb` | `MergingPlanner` + `DuckDbExecutor` | Groups by `build_key` and selects `min()` per declared field. |
| `conflict_findings/duckdb` | `ConflictValidationPlanner` + `DuckDbExecutor` | Emits one finding per build key with more than one distinct non-null value. |
| `conflict_report/default` | `ConflictValidationPlanner` + `ConflictReportExecutor` | Publishes an in-memory report and decides whether to forward records. |
| `file/default` | `FilePlanner` + `FileExecutor` | Writes every received graph relation as JSON Lines. |
| `meta_graph/default` | `MetaGraphPlanner` + `MetaGraphExecutor` | Writes the meta-graph document and optional HTML page. |
| `neo4j/default` | `Neo4jPlanner` + `Neo4jExecutor` | Exports Parquet files and writes the import script. |
| `python/cpython` | custom planner + `PythonExecutor` | Imports `module.qualname` and turns its result into one step outcome. |

## Limits

- Deduplication removes exact duplicates only. A duplicate must match the build key, every property, both endpoints and the binding symbol.
- Merge is not a conflict check. `min()` is arbitrary for text and chooses the earliest temporal value; two real values silently become one.
- Merge assigns one record per build key per scoped component. It cannot preserve deliberately parallel facts inside one component.
- Conflict validation cannot repair, list or attribute competing values; a finding names only a count.
- Nulls, endpoints, binding symbols, unbound components and undeclared columns are outside validation.
- Nothing checks that an edge endpoint matches a node key; that failure appears at import, not at build time.
- Targets do not validate. Quality is an upstream decision.
- The file target rewrites its whole file. Neo4j is export only. The conflict report is not a file. The meta-graph is descriptive, not a query surface.

## Rationale

Modules are small, replaceable claims over bound records, not a second semantic layer; this follows [Semantic hierarchy](/appendix/philosophy/semantic-hierarchy). Quality modules rewrite or report, while targets publish, so a module never needs to know the whole graph model. The explicit merge scope keeps deliberate parallel facts out of a lossy default, in the spirit of [Anti-patterns](/appendix/philosophy/anti-patterns).

## Next

[Modules subject](/appendix/subjects/modules) — kinds, generated views and related pages.
