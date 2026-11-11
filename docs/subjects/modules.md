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
- docs/reference/planners-and-executors.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Modules, outputs and quality</span><a href="/subjects/modules" class="active">Overview</a><a href="/operate/outputs">Guide</a><a href="/spec/modules">Spec</a><a href="/reference/api">API</a><a href="/philosophy/anti-patterns">Philosophy</a><a href="/review/limits">Review</a></div>
<!-- END GENERATED:views -->

## In one view

Source, core, quality and target modules, and the exact instruction kinds they own.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/modules) | The subject in one place. |
| Guide | [Publish outputs](/operate/outputs), [Guard quality](/operate/quality) | How to use it. |
| Spec | [SPEC-012](/spec/modules) | Binding requirements, API and evidence. |
| API | [API surface](/reference/api) | Exact public names and document shapes. |
| Philosophy | [Anti-patterns](/philosophy/anti-patterns) | Why it is designed this way. |
| Review | [Limits](/review/limits) | Invariants, limits and measured evidence. |

## Contract

- A planner MUST emit steps; an executor MUST own one exact instruction kind.
- Deduplication MUST remove only exact full-row duplicates.
- Merging MUST take an explicit component scope; it is not a conflict check.

## Where it sits

Upstream: [execution](/subjects/execution). Downstream: [verification](/subjects/verification).

## Next

[Specs](/spec/index) — the normative index.
