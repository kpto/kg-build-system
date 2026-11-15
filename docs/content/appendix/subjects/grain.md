---
title: Grain, row sources and derived relations
summary: What one row means, how a row source changes it, and where a named derived
  relation pins it.
section: subjects
perspective: hub
subject: grain
spec: SPEC-004
order: 40
status: normative
verified: '2026-11-15'
sources:
- kg_build_system/distribution/languages/data/model/public/row_sources.py
- kg_build_system/distribution/languages/data/service/_private/rows.py
- kg_build_system/distribution/languages/expressions/model/public/selection.py
- kg_build_system/distribution/languages/data/service/_private/declarations.py
- docs/content/appendix/reference/row-sources.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Grain, row sources and derived relations</span><a href="/appendix/subjects/grain" class="active">Overview</a><a href="/book/part-2/05-grain-and-projections">Guide</a><a href="/appendix/spec/grain">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/design-in-meaning">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

What one row means, how a row source changes it, and where a named derived relation pins it.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/grain) | The subject in one place. |
| Guide | [8. Derived relations](/book/part-2/05-grain-and-projections) | How to use it. |
| Spec | [SPEC-004](/appendix/spec/grain) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/api) | Exact public names and document shapes. |
| Philosophy | [Design in meaning](/appendix/philosophy/design-in-meaning) | Why it is designed this way. |
| Review | [Contracts](/appendix/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- A binding MUST read a published row-source value, never a declaration class or a stage.
- A derived relation MUST pin exactly one row source and publish at least one computed field.
- A join MUST name one key expression per side; a null key never matches.

## Where it sits

Upstream: [data](/appendix/subjects/data), [selection](/appendix/subjects/selection). Downstream: [binding](/appendix/subjects/binding).

## Next

[Specifications](/appendix/spec/index) — the normative index.
