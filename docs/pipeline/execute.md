---
title: Execute a plan
summary: Execution opens resources, dispatches exact instruction kinds and returns a report of published artifacts and failures.
section: pipeline
order: 40
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/api.py
  - kg_build_system/kernel/service/_private/runtime.py
  - kg_build_system/kernel/model/public/runtime.py
  - kg_build_system/kernel/model/public/events.py
  - docs/pipeline/execute.md
subject: execution
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Runtime and execution</span><a href="/subjects/execution">Overview</a><a href="/pipeline/execute" class="active">Guide</a><a href="/spec/execution">Spec</a><a href="/reference/documents">API</a><a href="/philosophy/explainability-is-authored">Philosophy</a><a href="/review/verification">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> Execution is the only stage that opens data. It builds an exact-kind map, runs the plan in dependency waves and turns outcomes into artifacts plus a report.

## What it is

`execute(plan, output_directory=..., configuration=None, monitor=...)` returns a `WorkflowReport`. The output directory receives `workflow_plan.json` before the run and `build_report.json` after execution returns.

| Report field | Meaning |
| --- | --- |
| `published_artifacts` | publications that opened, in declaration order |
| `recovered_failures` | failures not active at a publishing step |
| `unresolved_failures` | failures active at a publishing step |
| `provenance` | the plan's provenance, copied into the report |
| `succeeded` | no unresolved failure remains |

<figure class="kb-plate">
  <img src="/_assets/lifecycle.svg" alt="A run opens resources, dispatches exact instruction kinds and closes with a report.">
  <figcaption>Providers subscribe before listeners. The run ends finished or halted.</figcaption>
</figure>

## Rules

- Execution builds an exact-kind map from the executors. A duplicate kind raises. A plan kind with no executor raises before any step runs.
- Every run creates a fresh `EventBus` and `ResourceRegistry`. Providers subscribe before listeners. The runtime emits `PipelineStarted`, validates executor declarations, builds one `ResourceView` per executor, emits `StepStarted`, `StepFinished` and `StepLogged`, then emits `PipelineFinished` or `PipelineHalted`.
- `SUCCEEDED` and `WARNING` are continuable. `FAILED` and `SKIPPED` are disrupting. A failed step is an outcome, not an exception. A listener error propagates and halts the run.
- Steps run in dependency waves. A step is ready when every producer of every taken input has completed. Steps in one wave run one at a time in plan order.
- `workflow_plan.json` is written before execution; `build_report.json` is written after a successful run.
- `report.succeeded` means no failure remains at a publishing step. It does not mean every step succeeded.
- A monitor is a listener. It observes events and cannot change scheduling, resources or the report.

## Example

```python
from pathlib import Path

from kg_build_system import execute

report = execute(
    plan,
    output_directory=Path("reference_project/build"),
    monitor=True,
)
print(report.succeeded)
print([artifact.opening for artifact in report.published_artifacts])
```

The plan this run consumes is described in [Compile a plan](/pipeline/plan).

## Limits

- `report.succeeded` does not prove that every step succeeded. `recovered_failures` may be non-empty.
- A failure in a branch that reaches no publishing step is also classified as recovered.
- A run that raises leaves `workflow_plan.json` but not `build_report.json`. That includes a failure before execution and a listener error.
- Steps run one at a time in dependency waves. Execution is not parallel.
- Only publications appear in `published_artifacts`. Ordinary outputs are internal to the run.
- A plan runs only where an executor exists for every exact instruction kind. There is no migration path; change a planner or executor and compile again.
- Runtime values and resources do not carry from one run to the next.

## Next

[Debug a build](/operate/debug) — start from the report and read the failing step.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-005 | Make the workflow contract step-centric and instruction-based, with exact instruction kinds. | 2026-11-03 | accepted | `tests/kernel/test_kernel.py` |
| D-007 | Emit pipeline events and let resource providers subscribe to lifecycle events. | 2026-11-04 | accepted | `tests/kernel/test_runtime_events.py` |
