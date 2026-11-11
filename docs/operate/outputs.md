---
title: Publish outputs
summary: Turn published graph openings into JSON Lines, a meta-graph document, a Neo4j import bundle or an in-memory report.
section: operate
order: 10
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/modules/file/service/_private/planner.py
  - kg_build_system/distribution/modules/file/service/_private/executor.py
  - kg_build_system/distribution/modules/meta_graph/service/_private/executor.py
  - kg_build_system/distribution/modules/neo4j/service/_private/export.py
  - reference_project/build.py
subject: modules
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Modules, outputs and quality</span><a href="/subjects/modules">Overview</a><a href="/operate/outputs" class="active">Guide</a><a href="/spec/modules">Spec</a><a href="/reference/api">API</a><a href="/philosophy/anti-patterns">Philosophy</a><a href="/review/limits">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> A target does not build the graph. It publishes openings the graph already produced: one deferred step over every core.graph.** opening it receives.

## What it is

| Target | Planner and executor | Writes | Instruction kind |
| --- | --- | --- | --- |
| JSON Lines | `FilePlanner` + `FileExecutor` | `graph.jsonl` | `file/default` |
| Meta-graph | `MetaGraphPlanner` + `MetaGraphExecutor` | `meta_graph.json`, optional `meta_graph.html` | `meta_graph/default` |
| Neo4j | `Neo4jPlanner` + `Neo4jExecutor` | `nodes/*.parquet`, `relationships/*.parquet`, `import_neo4j.py` | `neo4j/default` |
| Conflict report | `ConflictValidationPlanner` + `ConflictReportExecutor` | In-memory report; no file | `conflict_report/default` |

The writing targets accept a configuration object; `FileConfiguration("graph.jsonl")` is the shortest. Every target is deferred and reads published graph openings. Execution and publication mechanics are in [Execute a plan](/pipeline/execute).

Rewriting planners decide what reaches a target, or whether the run continues: `DeduplicationPlanner`, `MergingPlanner` and `ConflictValidationPlanner` belong before the output planners.

<figure class="kb-plate">
  <img src="/_assets/modules.svg" alt="Source, rows, projection, binding and records feed quality modules and then file, meta-graph and Neo4j targets.">
  <figcaption>Quality modules sit before the target modules. A planner emits a step; an executor owns its exact instruction kind.</figcaption>
</figure>

## Rules

- `FileExecutor` writes every received `core.graph.**` relation. Each line is the record plus `build_key`, `type` and `kind`; the `file/write_result` summary counts nodes and edges.
- The design is one file target, not a database. There are no tables, indexes, transactions or queries; a consumer scans the file or imports it elsewhere.
- The meta-graph document carries a summary, the effective topology, per-component counts and approximate property examples. Counts are exact for records that reached the executor; `MetaGraphConfiguration(example_limit=..., include_html=...)` sets the sample size and the optional self-contained page.
- Neo4j is export only: Parquet files under `nodes/` and `relationships/` carry bulk-import headers (`:ID`, `:START_ID`, `:END_ID`, `:LABEL`/`:TYPE`), and a standalone `import_neo4j.py` runs `neo4j-admin`. There is no driver, Cypher, live connection or rollback.
- `ConflictReportExecutor` builds a report in memory only when it has findings. With no findings, or with `fail_on_error=False`, it forwards validated records. With `fail_on_error=True` the step fails and the report artifact is still returned; records are not forwarded.
- Instruction kinds are exact. A target cannot claim a prefix or a family of kinds.

## Example

```python
from kg_build_system import compile, execute
from kg_build_system.distribution import (
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
    MetaGraphPlanner,
    Neo4jPlanner,
)

planners = (
    DeduplicationPlanner(),
    FilePlanner(FileConfiguration("graph.jsonl")),
    MetaGraphPlanner(),
    Neo4jPlanner(),
)
plan = compile(planners=planners)
report = execute(plan, output_directory="build")
print([artifact.type.namespace for artifact in report.published_artifacts])
```

The run writes:

```text
build/graph.jsonl
build/meta_graph.json
build/meta_graph.html
build/neo4j-import/nodes/*.parquet
build/neo4j-import/relationships/*.parquet
build/neo4j-import/import_neo4j.py
build/workflow_plan.json
build/build_report.json
```

## Limits

- The JSON Lines target rewrites its whole file on every run. There is no incremental append, partial publish or per-component file.
- The file carries graph rows only; the blueprint, plan and report are separate documents. Their shapes are in [Documents](/reference/documents).
- Neo4j edges require bound source and target node components. An edge whose endpoint keys match no node is exported and fails later at import.
- The meta-graph is a description, not a query surface. It counts only records that reached its executor.
- The conflict report is not a file and has no repair. Its findings live in the run report unless a consumer reads the published artifact.
- Targets do not validate. Quality is an upstream decision; the accepted boundary is in [Review limits](/review/limits).

## Next

[Guard quality](/operate/quality) — choose which records reach these targets.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-005 | Make the workflow contract step-centric and instruction-based, with exact instruction kinds. | 2026-11-03 | accepted | `tests/kernel/test_kernel.py`; `docs/reference/compile.md` |
| D-022 | Use a generic source planner for parquet/json/csv and reject an adapter registry. | 2026-11-04 | accepted | `tests/distribution/planners/test_duckdb_source_planner.py` |
