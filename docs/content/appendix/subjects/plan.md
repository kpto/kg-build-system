---
title: Workflow plan
summary: Components, steps, openings and the checked wiring between them.
section: subjects
perspective: hub
subject: plan
spec: SPEC-010
order: 100
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/kernel/service/_private/pipeline.py
- kg_build_system/kernel/service/_private/assembly.py
- kg_build_system/kernel/model/public/workflow.py
- kg_build_system/api.py
- docs/content/appendix/reference/compile.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Workflow plan</span><a href="/appendix/subjects/plan" class="active">Overview</a><a href="/book/part-3/02-planning">Guide</a><a href="/appendix/spec/plan">Spec</a><a href="/appendix/reference/documents">API</a><a href="/appendix/philosophy/design-in-meaning">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

Components, steps, openings and the checked wiring between them.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/plan) | The subject in one place. |
| Guide | [14. Planning the work](/book/part-3/02-planning) | How to use it. |
| Spec | [SPEC-010](/appendix/spec/plan) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/documents) | Exact public names and document shapes. |
| Philosophy | [Design in meaning](/appendix/philosophy/design-in-meaning) | Why it is designed this way. |
| Review | [Contracts](/appendix/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- Planners that share a component MUST agree on version and runtime fields.
- Every step input MUST be fed and every ordinary output MUST be read; a publication is exempt.
- `InstructionKind` MUST be exact; there is no prefix matching.

## Where it sits

Upstream: [linking](/appendix/subjects/linking). Downstream: [execution](/appendix/subjects/execution).

## Next

[Specifications](/appendix/spec/index) — the normative index.
