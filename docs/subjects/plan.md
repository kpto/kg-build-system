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
- docs/reference/compile.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Workflow plan</span><a href="/subjects/plan" class="active">Overview</a><a href="/pipeline/plan">Guide</a><a href="/spec/plan">Spec</a><a href="/reference/documents">API</a><a href="/philosophy/design-in-semantics">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

Components, steps, openings and the checked wiring between them.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/plan) | The subject in one place. |
| Guide | [Compile a plan](/pipeline/plan) | How to use it. |
| Spec | [SPEC-010](/spec/plan) | Binding requirements, API and evidence. |
| API | [API surface](/reference/documents) | Exact public names and document shapes. |
| Philosophy | [Design in semantics](/philosophy/design-in-semantics) | Why it is designed this way. |
| Review | [Contracts](/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- Planners that share a component MUST agree on version and runtime fields.
- Every step input MUST be fed and every ordinary output MUST be read; a publication is exempt.
- `InstructionKind` MUST be exact; there is no prefix matching.

## Where it sits

Upstream: [linking](/subjects/linking). Downstream: [execution](/subjects/execution).

## Next

[Specs](/spec/index) — the normative index.
