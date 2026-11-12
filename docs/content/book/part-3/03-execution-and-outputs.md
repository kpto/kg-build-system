---
title: "15. Executing and publishing"
summary: "A run resolves exact kinds, opens resources, walks dependency waves and reports what it published."
section: book
perspective: book
part: III
chapter: 15
order: 33
status: normative
verified: 2026-11-11
sources:
  - kg_build_system/kernel/service/_private/runtime.py
  - kg_build_system/kernel/model/public/runtime.py
  - kg_build_system/api.py
  - docs/content/book/part-3/03-execution-and-outputs.md
  - docs/content/appendix/spec/execution.md
---

Until this point the site binding has been an expression tree and a set of plan steps. Execution makes it rows. The source step opens `sites.json`, the binding step evaluates `drop_null`, `default_to` and the nested `premises.contact.location.city` path, the aggregate step unions the binding's rows into the site record stream, and the file target writes the result. A run is where authored meaning meets the data that either supports it or refuses it.

`execute` is the public verb. It takes a plan, an output directory and optional runtime settings, runs the plan through an executor composition and returns a `WorkflowReport`. It writes `workflow_plan.json` before the run and `build_report.json` after the run returns. The report is not a log; it is the run's account of what it published and what failed.

## A plan does not run itself

A plan states work and wiring. It does not own a process, a database connection, a file handle or a runtime value. Those are execution inputs.

`execute(plan, output_directory=...)` supplies the directory. `BuildRuntime` supplies credentials, per-component runtime overrides and engine settings. A toolchain supplies the executors and resource providers. None of these values are part of the plan, which is why the same plan can run against a test directory and a production directory without recompiling.

The first thing `execute` does is write the plan to `workflow_plan.json`. The plan is written before execution so a failed run still leaves the work it attempted. The report is written only after the run returns; a run that raises leaves the plan document but no report.

The plan is not inspected for data. Compilation already checked that every input has a producer and every ordinary output has a reader. Execution adds the facts compilation cannot know: whether the source file exists, whether the SQL is valid against the actual rows, whether a resource provider can open its engine, and whether an executor returns the artifacts it declared.

That is why the runtime begins with a map, not a query.

## Exact kinds are resolved before the first step

An executor declares the exact instruction kinds it handles and the exact resource types it reads.

```python
class StepExecutor(Protocol):
    kinds: tuple[InstructionKind, ...]
    resources: tuple[type, ...]
    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome: ...
```

Execution builds a map from `kind` to executor before any step runs. The map is exact. `sql/duckdb` and `sql/postgres` are different keys; an executor that declares the first does not receive the second. There is no prefix matching and no family registration.

Two failures happen before the first step:

- a duplicate kind raises `duplicate executor for instruction kind sql/duckdb`;
- a plan kind with no executor raises `no executor for instruction kind(s): file/default`.

The first is a composition error: two executors claim one key. The second is a mismatch between a plan and a toolchain. Neither is a step failure, and neither produces a report with a recovered failure. They are refusals to start.

The site plan uses four kinds. `duckdb/source.sites` needs `source_relation/duckdb`; the binding step needs `sql/duckdb`; the aggregate step needs `aggregate/duckdb`; the file step needs `file/default`. The default `DuckDbExecutor` owns all three DuckDB kinds, and `FileExecutor` owns the file kind. Different steps, same executor object for the DuckDB ones. An executor may own many kinds; a kind may belong to only one executor in a run.

A custom executor follows the same rule. It declares its kinds, declares the resources it reads, and returns a `StepOutcome`. Adding it to the toolchain is enough; the runtime does not need a registry entry or a plugin manifest. The exact-key map is the registry.

## Resources belong to the run

Every run creates a fresh `EventBus` and a fresh `ResourceRegistry`. Providers subscribe to the bus before frontend listeners. The runtime emits `PipelineStarted`, and providers create their resources while handling that event. Then the runtime takes a snapshot of the registry and builds one `ResourceView` per executor.

A resource is keyed by its exact type. Two providers that supply the same type are refused with `duplicate resource type <module.qualname> provided by more than one provider`. A provider that fails to supply a type an executor declared produces `executor FileExecutor requires missing resource(s): <module.qualname>` before any step runs.

The site chain uses two providers without either executor knowing about them:

| Executor | Declared resources | Provider |
| --- | --- | --- |
| `DuckDbExecutor` | `DuckDbService` | `DuckDbResourceProvider` |
| `FileExecutor` | `RelationService`, `OutputStorage` | `DuckDbResourceProvider`, `RuntimeResources` |

`DuckDbResourceProvider` opens the engine on start and publishes `DuckDbService` and its `RelationService`. `RuntimeResources` creates the output and working directories, a private temporary root, and the credential resolver, and publishes `OutputStorage`, `WorkingStorage`, `TemporaryStorage` and `CredentialResolver`. The executors read only what they declared. `FileExecutor` can ask `context.resources.get(OutputStorage)`; it cannot ask for `DuckDbService`, even though the same run opened one for the DuckDB executor.

A `ResourceView` is not a service locator. `get` accepts a type and returns exactly that type, or raises `KeyError`. There is no fallback, no subtype search and no ambient global. That is what makes an executor's resource declaration reviewable: the tuple is the complete list of live objects it may touch.

Resources close on `PipelineFinished` or `PipelineHalted`. The runtime emits `PipelineFinished` with the report after a completed run and `PipelineHalted` with the error when the run raises. Providers dispose on either event, so a failed step still closes the engine and removes the temporary root. A listener error propagates through the bus, halts the run and re-raises; the runtime does not convert a presentation failure into a step failure.

Runtime values do not carry between runs. A second run creates a new bus, a new registry and new resources. A cached connection or a reused temporary directory is not part of the execution model.

## Work moves in dependency waves

The runtime schedules by dependency, not by the plan's step order. A step is ready when every producer of every taken input has completed. All ready steps form a wave. Steps in one wave run one at a time, in plan order.

The site chain is four waves: `source.sites`, then `binding.6`, then `aggregate.site`, then `write`. The file step is last not because it appears last in the plan but because its inputs come from every graph-record producer, including the site aggregate. If another node had a longer chain, the file step would wait for that chain too.

Execution is not parallel. There is no thread pool and no concurrent SQL. The wave structure states ordering, not concurrency. It also gives a clear failure boundary: when a step in a wave is disrupted, the next wave sees the disruption and its dependants can be skipped without running.

A step's outcome has one of four statuses.

| Status | Meaning downstream |
| --- | --- |
| `SUCCEEDED` | The step ran and its artifacts are continuable |
| `WARNING` | The step ran with a caveat; its artifacts are continuable |
| `FAILED` | The step failed; the failure disrupts its dependants |
| `SKIPPED` | The step did not run; the inherited failure disrupts its dependants |

`SUCCEEDED` and `WARNING` feed downstream steps. `FAILED` and `SKIPPED` do not. A downstream step with any disrupted input receives a `DisruptedExecutionContext` containing the disruptions and the continuable inputs that did arrive. The default disrupted policy is `skipped(context)`: it returns a `SKIPPED` outcome without running the executor's normal branch and carries the failure forward.

This is why a failure does not have to abort the run. If the survey binding fails but the site binding succeeds, the site aggregate can still produce site records. The file target's site input is continuable; its survey input is disrupted. Whether the run publishes a usable file depends on the target's policy, but the runtime does not decide that for it. It classifies the failure and lets the plan's structure determine which publications are reachable.

A component's runtime configuration is validated before its step runs. A required field that is missing, an unknown field, or a value of the wrong scalar type is refused at that point. An unknown component key is refused before the first step. Runtime configuration is not part of the plan and is not cached across runs.

## A failure is an outcome, not an exception

An executor may return `FAILED` explicitly. It may also raise. The runtime catches an exception from `executor.execute` and turns it into a `FAILED` outcome with a `Failure` carrying the message, the typed `step_id` and the exception class name. The exception does not escape the step.

A listener error is the exception. The bus records it and re-raises; the runtime emits `PipelineHalted` and the whole run raises. The distinction is deliberate: an executor failure is data about the build, while a broken listener is a broken observer of the build.

A `Failure` is not the same as an unresolved failure. The report separates failures by whether one is still active at a publishing step:

- a **recovered failure** is a failure that no publishing step inherited;
- an **unresolved failure** is a failure still active at a publishing step.

A failure in a branch that reaches no publisher is recovered, even if its step failed. A failure that skips the only file target is unresolved. `report.succeeded` is true exactly when `unresolved_failures` is empty. It does not mean every step succeeded; a report may be successful with a non-empty `recovered_failures`.

The site chain gives the distinction a concrete shape. If the binding step fails and the aggregate and file steps are skipped, the file publication never happens. The binding failure is active at the file step, so it is unresolved and `succeeded` is false. If a separate experimental branch fails but no publication depends on it, the same failure is recovered and the file publication can still succeed.

Only failures that occurred are reported. The runtime does not invent a failure for a step that was never scheduled, and it does not report a step as failed when an executor returned `SKIPPED` with no failure of its own. A skipped step with an inherited failure carries that failure forward; the original failure remains the explanation.

## The report is the run's evidence

`WorkflowReport` has four data fields and one derived property.

| Field | Meaning |
| --- | --- |
| `published_artifacts` | The publications that produced an artifact, in declaration order |
| `recovered_failures` | Failures not active at a publishing step |
| `unresolved_failures` | Failures active at a publishing step |
| `provenance` | The plan's provenance, copied into the report |
| `succeeded` | True exactly when `unresolved_failures` is empty |

A published artifact carries its `OpeningId`, its `ArtifactType` and its value. The opening is what distinguishes two publications of the same type: the type says `file/write_result`, while the opening says which step and which publication name produced it. A value is executor-defined and JSON-safe where the target publishes JSON.

Only publications appear. `aggregate.site`'s `core/graph/node/site` output is internal to the run; the file target consumes it and publishes `file/write_result`. The report does not list every intermediate relation, because intermediates are not the build's product. The plan document lists them; the report lists the outcomes.

For the reference build, the file publication's value is a small summary rather than the graph itself:

```json
{
  "opening": ["file", "write", "output", "result"],
  "type": ["file", "write_result"],
  "value": {"edges": 21, "nodes": 21, "location": "reference_project/build/graph.jsonl"}
}
```

The count is exact for the records that reached the executor. It is not a count of source rows and it is not a promise about what a consumer will parse. The graph rows themselves are in `graph.jsonl`, one JSON object per line, each carrying `build_key`, `type`, `kind` and the component's properties. An edge also carries `source_build_key` and `target_build_key`, and a record that has not passed through a merging step carries `_kg_binding_symbol`.

Provenance is copied from the plan. When the plan came through `api.compile`, it contains the source blueprint document under `blueprint`; a plan compiled directly through the kernel may carry different provenance or none. The report does not edit it. A report can therefore be read beside the plan and the blueprint without a fourth artifact that explains where the work came from.

```python
from pathlib import Path

from kg_build_system import compile, execute
from kg_build_system.distribution import FileConfiguration, FilePlanner

plan = compile(
    namespace_path=Path("reference_project"),
    planners=(FilePlanner(FileConfiguration("graph.jsonl")),),
)
report = execute(plan, output_directory=Path("reference_project/build"))

file_result = next(
    artifact for artifact in report.published_artifacts
    if artifact.type.namespace == "file"
)
print(file_result.opening)              # file/write/output/result
print(file_result.value["nodes"])       # 21
print(report.succeeded)                 # True
print(report.unresolved_failures)       # ()
```

A runtime override changes where a target writes without changing the plan. The file component declares `relative_path`; the value is supplied at execution.

```python
from pathlib import Path

from kg_build_system import BuildRuntime

runtime = BuildRuntime(
    component_configuration={
        "file": {"relative_path": "graph/current.jsonl"},
    },
)
report = execute(plan, output_directory=Path("build"), runtime=runtime)
```

The override is validated against the component's declared runtime fields. A value of the wrong type is refused; an undeclared key is refused. The plan still says what the component can be configured with, and the run says what this execution chose.

## Outputs are targets, not runtimes

The file target, the meta-graph target and the Neo4j target are three planner and executor pairs. They are not three runtimes.

| Target | Planner and executor | Publication | Writes |
| --- | --- | --- | --- |
| JSON Lines | `FilePlanner` + `FileExecutor` | `file/write_result` | `graph.jsonl` |
| Meta-graph | `MetaGraphPlanner` + `MetaGraphExecutor` | `meta_graph/meta_graph_document` | `meta_graph.json`, optional HTML |
| Neo4j | `Neo4jPlanner` + `Neo4jExecutor` | `neo4j/import_bundle` | Parquet files and an import script |

Each target ends in a deferred publication step. The file target and the meta-graph target read the graph-record pattern `core/graph/**`; the Neo4j target reads the per-component exports it produced and publishes the import bundle. No target builds the graph or owns a separate execution model. Each receives the records that the rewriting planners produced and publishes a summary of what it wrote. A composition with all three targets produces three publications in one report from one plan and one runtime.

The difference between the targets is what they write, not how execution works. The file target writes one JSON Lines file and has no tables, indexes, transactions or queries. The meta-graph target writes a description of the effective topology, with exact counts for the records that reached it and approximate property examples. The Neo4j target writes bulk-import Parquet and a standalone script; it does not open a driver, run Cypher or hold a live connection. All three are deferred because they run after the records they consume exist.

The runtime does not know which target is present. `DuckDbExecutor` runs SQL, `FileExecutor` writes a file, `MetaGraphExecutor` writes a document and `Neo4jExecutor` writes an export bundle. The composition of planners decides which of those steps exist; the composition of executors decides whether they can run. Adding a fourth target means adding an ordinary planner and an ordinary executor with its own exact kind, not adding a fourth runtime.

The conflict report is the in-memory case. `ConflictValidationPlanner` emits findings steps and a deferred report step; `ConflictReportExecutor` publishes a report only when it has findings. With no findings, or with `fail_on_error=False`, it forwards validated records; with the default `fail_on_error=True`, the step fails and the report artifact is still returned. The artifact is a publication even though no file is written. That is the same publication rule as the file target, applied to a value that never leaves the run.

One target can fail without preventing another from publishing, provided the failures are recovered at the publishing steps. The report then shows a successful artifact for one target and a recovered failure for the other. The operator reads the failure entry, not a missing file, and the report remains the single account of what happened.

That account is where the next question starts. A run can succeed structurally and still publish records that are wrong: a null became a sentinel, a duplicate key was merged, a property conflict was ignored. Execution reports what it did; quality decides whether what it did is acceptable. The next chapter starts from the report and the plan, and asks which failures and which records deserve to stop a build.

## Next

[16. Quality, failures and debugging](/book/part-3/04-quality-and-failure) — how to choose which records reach a target and how to read a failed run.
