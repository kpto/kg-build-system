---
title: Extending the toolchain
summary: Languages, linkers, planners, executors, emitters and providers composed
  as values.
section: subjects
perspective: hub
subject: extension
spec: SPEC-013
order: 130
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/kernel/service/public/pipeline.py
- kg_build_system/kernel/model/public/language.py
- kg_build_system/api.py
- kg_build_system/distribution/service/internal/emission.py
- kg_build_system/distribution/modules/python/service/_private/python.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Extending the toolchain</span><a href="/subjects/extension" class="active">Overview</a><a href="/operate/extend">Guide</a><a href="/spec/extension">Spec</a><a href="/reference/api">API</a><a href="/philosophy/design-in-semantics">Philosophy</a><a href="/review/architecture">Review</a></div>
<!-- END GENERATED:views -->

## In one view

Languages, linkers, planners, executors, emitters and providers composed as values.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/extension) | The subject in one place. |
| Guide | [Extend the toolchain](/operate/extend) | How to use it. |
| Spec | [SPEC-013](/spec/extension) | Binding requirements, API and evidence. |
| API | [API surface](/reference/api) | Exact public names and document shapes. |
| Philosophy | [Design in semantics](/philosophy/design-in-semantics) | Why it is designed this way. |
| Review | [Architecture](/review/architecture) | Invariants, limits and measured evidence. |

## Contract

- There MUST be no extension registry; a caller MUST compose a `Toolchain`.
- A language MUST transcribe one declaration to one symbol; there is no batch protocol.
- A new engine MUST implement the neutral `SqlEmitter`, not edit core.

## Where it sits

Upstream: [architecture](/subjects/architecture), [plan](/subjects/plan). Downstream: End of the dependency story..

## Next

[Specs](/spec/index) — the normative index.
