---
title: Modules, outputs and quality
summary: Source, core, quality and target modules, and the exact instruction kinds
  they own.
section: subjects
perspective: hub
subject: modules
spec: SPEC-012
order: 120
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/distribution/modules/duckdb/service/_private/executor.py
- kg_build_system/distribution/modules/deduplication/service/_private/planner.py
- kg_build_system/distribution/modules/merging/service/_private/planner.py
- kg_build_system/distribution/modules/conflict_validation/service/_private/planner.py
- docs/appendix/reference/planners-and-executors.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Modules, outputs and quality</span><a href="/appendix/subjects/modules" class="active">Overview</a><a href="/book/part-3/03-execution-and-outputs">Guide</a><a href="/appendix/spec/modules">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/anti-patterns">Philosophy</a><a href="/appendix/review/limits">Review</a></div>
<!-- END GENERATED:views -->

## In one view

Source, core, quality and target modules, and the exact instruction kinds they own.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/modules) | The subject in one place. |
| Guide | [15. Executing and publishing](/book/part-3/03-execution-and-outputs), [16. Quality, failures and debugging](/book/part-3/04-quality-and-failure) | How to use it. |
| Spec | [SPEC-012](/appendix/spec/modules) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/api) | Exact public names and document shapes. |
| Philosophy | [Anti-patterns](/appendix/philosophy/anti-patterns) | Why it is designed this way. |
| Review | [Limits](/appendix/review/limits) | Invariants, limits and measured evidence. |

## Contract

- A planner MUST emit steps; an executor MUST own one exact instruction kind.
- Deduplication MUST remove only exact full-row duplicates.
- Merging MUST take an explicit component scope; it is not a conflict check.

## Where it sits

Upstream: [execution](/appendix/subjects/execution). Downstream: [verification](/appendix/subjects/verification).

## Next

[Specifications](/appendix/spec/index) — the normative index.
