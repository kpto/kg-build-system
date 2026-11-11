---
title: Runtime and execution
summary: Resources, events, exact-kind executors and the report that records a run.
section: subjects
perspective: hub
subject: execution
spec: SPEC-011
order: 110
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/api.py
- kg_build_system/kernel/service/_private/pipeline.py
- kg_build_system/kernel/service/_private/runtime.py
- kg_build_system/kernel/model/public/runtime.py
- kg_build_system/kernel/model/public/events.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Runtime and execution</span><a href="/appendix/subjects/execution" class="active">Overview</a><a href="/book/part-3/03-execution-and-outputs">Guide</a><a href="/appendix/spec/execution">Spec</a><a href="/appendix/reference/documents">API</a><a href="/appendix/philosophy/explainability-is-authored">Philosophy</a><a href="/appendix/review/verification">Review</a></div>
<!-- END GENERATED:views -->

## In one view

Resources, events, exact-kind executors and the report that records a run.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/execution) | The subject in one place. |
| Guide | [12. Executing and publishing](/book/part-3/03-execution-and-outputs) | How to use it. |
| Spec | [SPEC-011](/appendix/spec/execution) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/documents) | Exact public names and document shapes. |
| Philosophy | [Explainability is authored](/appendix/philosophy/explainability-is-authored) | Why it is designed this way. |
| Review | [Verification](/appendix/review/verification) | Invariants, limits and measured evidence. |

## Contract

- Execution MUST refuse a duplicate kind and a plan kind with no executor before any step.
- A provider MUST publish on `PipelineStarted` and dispose on finish or halt.
- A failure MUST be a `StepOutcome`; a listener error MUST halt the run.

## Where it sits

Upstream: [plan](/appendix/subjects/plan). Downstream: [modules](/appendix/subjects/modules).

## Next

[Specifications](/appendix/spec/index) — the normative index.
