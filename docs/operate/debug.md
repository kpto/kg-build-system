---
title: Debug a build
summary: Find the failed stage, read the report and the plan, and locate the first artifact that records it.
section: operate
order: 30
status: normative
verified: 2026-11-10
sources:
  - docs/operate/debug.md
  - kg_build_system/kernel/service/_private/runtime.py
  - kg_build_system/kernel/service/_private/report_codec.py
  - kg_build_system/kernel/service/internal/workflow_codec.py
  - kg_build_system/api.py
subject: verification
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Verification, limits and debugging</span><a href="/subjects/verification">Overview</a><a href="/operate/debug" class="active">Guide</a><a href="/spec/verification">Spec</a><a href="/reference/failures">API</a><a href="/philosophy/explainability-is-authored">Philosophy</a><a href="/review/decisions">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> A failure is local to one stage. A declaration error never reaches compile; a compile error never writes a report. Start at the earliest stage whose artifact exists.

## What it is

| Stage | Signal | First look |
| --- | --- | --- |
| Authoring | Static error or `TypeError` | The declaration and its reference page |
| `create_blueprint` | `ValueError` | The blueprint document: assets, graph, bindings |
| `compile` | `ValueError` or `AssemblyError` | The planner grouping; `plan.components`, `plan.steps` and `plan.connections` when a plan exists |
| `execute` | Unsuccessful `WorkflowReport` or a raised run error | `build_report.json`, then `workflow_plan.json` |

`workflow_plan.json` is written before execution starts, even when the run fails. `build_report.json` is written after the run returns. A run that halts before returning leaves no report.

## Rules

- Read the report first for an execution failure. It exposes `published_artifacts`, `recovered_failures`, `unresolved_failures` and `provenance`.
- `succeeded` can be true with recovered failures. A step failure is a `FAILED` outcome; a failure is unresolved only while it is active at a step that publishes, otherwise it is recovered.
- Each failure carries a `message`, a typed `step_id` and an `exception_type`. The report stores no traceback.
- Read the plan next. Locate the failing `step_id`, note its `instruction.kind`, then check which executor claims that exact kind.
- Read the blueprint document when the failure predates execution. It exposes `graph.nodes`, `graph.edges` and `bindings`.
- Keep the first check narrow. Most failures before any step are a missing resource, an unknown instruction kind or a bad runtime value, not a wrong record.

**Short catalogue.** The long table is in [Failures](/reference/failures).

| Message or symptom | Change |
| --- | --- |
| `workflow cannot be assembled` | Add the missing producer: an asset layout, source planner or output. |
| `nothing reads ...` | An ordinary output has no consumer; reorder planners or add a reader. |
| `no executor for instruction kind(s): ...` | Add an executor whose `kinds` contains that exact kind. |
| `workflow has a dependency cycle` | Repair the wiring, then recompile. |
| `executor ... requires missing resource(s)` | A provider did not publish a declared resource type. |
| `component names must be unique` | Fix the duplicate declaration or binding target. |

## Example

Print the failing steps from the written report:

```python
import json
from pathlib import Path

report = json.loads(Path("build/build_report.json").read_text())
for failure in report["unresolved_failures"]:
    print(failure["step_id"], failure["exception_type"], failure["message"])
```

`step_id` is a key array, not a string. The same values are on the report object returned by `execute`.

## Limits

- A halted run can leave no `build_report.json`; the exception and `workflow_plan.json` are then the evidence.
- A successful report is not a quality guarantee. It records publication, not grain, duplicate keys or dangling edges.
- The report does not include a traceback. Reproduce the failing step in a test to see one.
- Execution cannot repair a structural error. Fix declarations and compilation before reading data.
- An exact multiple of an expected count is fan-out; zero is a filter, a missing source or the wrong namespace. Neither has a dedicated message.
- Meta-graph counts cover only records that reached its executor; examples are approximate.
- The CLI has no debug or verbose flag. Use the Python API and the written artifacts. Publication details are in [Publish outputs](/operate/outputs) and [Execute a plan](/pipeline/execute).

## Next

[Extend the toolchain](/operate/extend) — add the missing planner or executor.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-007 | Emit pipeline events and let resource providers subscribe to lifecycle events. | 2026-11-04 | accepted | `tests/kernel/test_runtime_events.py`; `docs/developer/system-design.md` |
