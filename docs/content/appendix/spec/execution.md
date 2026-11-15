---
title: Execution specification
summary: Execution runs a plan through exact kinds, fresh resources and a truthful report.
section: spec
perspective: spec
subject: execution
spec: SPEC-011
order: 110
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/api.py
  - kg_build_system/kernel/service/_private/pipeline.py
  - kg_build_system/kernel/service/_private/runtime.py
  - kg_build_system/kernel/model/public/runtime.py
  - kg_build_system/kernel/model/public/events.py
evidence:
  - tests/kernel/test_toolchain_flow.py
  - tests/kernel/test_runtime_events.py
  - tests/kernel/test_runtime_resources.py
  - tests/test_reference_build.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Runtime and execution</span><a href="/appendix/subjects/execution">Overview</a><a href="/book/part-3/03-execution-and-outputs">Guide</a><a href="/appendix/spec/execution" class="active">Spec</a><a href="/appendix/reference/documents">API</a><a href="/appendix/philosophy/explainability-is-authored">Philosophy</a><a href="/appendix/review/verification">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** Execution MUST build an exact-kind map from executor declarations; a duplicate instruction kind MUST be refused.
- **R2.** A plan instruction kind with no executor MUST be refused before any step runs.
- **R3.** Every run MUST create a fresh `EventBus` and `ResourceRegistry`; providers MUST open resources on `PipelineStarted` and close them on `PipelineFinished` or `PipelineHalted`.
- **R4.** Each executor MUST receive one `ResourceView` containing exactly the resource types it declares.
- **R5.** `SUCCEEDED` and `WARNING` MUST be continuable; `FAILED` and `SKIPPED` MUST disrupt downstream steps. A step failure MUST become an outcome, not escape as an exception.
- **R6.** A listener error MUST propagate and halt the run.
- **R7.** Steps MUST run in sequential dependency waves; steps in one wave MUST run one at a time in plan order.
- **R8.** The report MUST carry `published_artifacts`, `recovered_failures`, `unresolved_failures` and `provenance`; `succeeded` MUST be true only when no unresolved failure reaches a publishing step.
- **R9.** `execute` MUST write `workflow_plan.json` before execution and `build_report.json` only after a successful return.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/kernel/test_toolchain_flow.py` | A plan kind without an executor is refused before the runtime runs. |
| `tests/kernel/test_runtime_events.py` | Events arrive in lifecycle order; a listener error produces `PipelineHalted`; providers dispose on finish and halt. |
| `tests/kernel/test_runtime_resources.py` | A missing or duplicate resource is refused before steps; an executor sees only declared types; a failed step still disposes providers. |
| `tests/test_reference_build.py` | The reference build succeeds, publishes only final artifacts, and writes the plan and report documents. |

## API

| Public name | Role |
| --- | --- |
| `execute` | Canonical facade; writes the plan and report and returns a `WorkflowReport`. |
| `WorkflowRuntime.execute` | Owns the bus, providers, scheduling, outcomes and report assembly. |
| `WorkflowReport` | Published artifacts, recovered failures, unresolved failures and plan provenance. |
| `StepStatus` | `SUCCEEDED`, `WARNING`, `FAILED` and `SKIPPED`, with continuable and disrupting meanings. |
| `ExecutionContext` / `DisruptedExecutionContext` | The executor view of continuable inputs or disrupting inputs. |
| `PipelineStarted` / `PipelineFinished` / `PipelineHalted` | Provider lifecycle boundaries; started opens, finished and halted close. |
| `ResourceView` | Returns a declared resource and refuses any type the executor did not declare. |

## Limits

- `succeeded` does not prove that every step succeeded; `recovered_failures` may be non-empty.
- A failure in a branch that reaches no publishing step is classified as recovered.
- A run that raises leaves `workflow_plan.json` but not `build_report.json`, including a listener error.
- Execution is not parallel. Steps run one at a time in dependency waves.
- Only publications appear in `published_artifacts`; ordinary outputs stay internal to the run.
- A plan runs only where an executor exists for every exact instruction kind. There is no migration path.
- Resources and runtime values do not carry between runs.
- A monitor observes events and cannot change scheduling, resources or the report.

## Rationale

Execution is where authored meaning becomes data, so the runtime treats instructions and resources as opaque and refuses anything it cannot dispatch; this is the boundary described in [Design in meaning](/appendix/philosophy/design-in-meaning). A failure is recorded rather than hidden because the report is the operator's review surface. See [Review top-down](/appendix/philosophy/review-top-down).

## Next

[Execution subject](/appendix/subjects/execution) — lifecycle, report fields and related pages.
