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
<div class="kb-views"><span class="kb-views-subject">Runtime and execution</span><a href="/subjects/execution" class="active">Overview</a><a href="/pipeline/execute">Guide</a><a href="/spec/execution">Spec</a><a href="/reference/documents">API</a><a href="/philosophy/explainability-is-authored">Philosophy</a><a href="/review/verification">Review</a></div>
<!-- END GENERATED:views -->

## In one view

Resources, events, exact-kind executors and the report that records a run.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/execution) | The subject in one place. |
| Guide | [Execute a plan](/pipeline/execute) | How to use it. |
| Spec | [SPEC-011](/spec/execution) | Binding requirements, API and evidence. |
| API | [API surface](/reference/documents) | Exact public names and document shapes. |
| Philosophy | [Explainability is authored](/philosophy/explainability-is-authored) | Why it is designed this way. |
| Review | [Verification](/review/verification) | Invariants, limits and measured evidence. |

## Contract

- Execution MUST refuse a duplicate kind and a plan kind with no executor before any step.
- A provider MUST publish on `PipelineStarted` and dispose on finish or halt.
- A failure MUST be a `StepOutcome`; a listener error MUST halt the run.

## Where it sits

Upstream: [plan](/subjects/plan). Downstream: [modules](/subjects/modules).

## Next

[Specs](/spec/index) — the normative index.
