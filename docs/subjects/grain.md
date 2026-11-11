---
title: Grain, row sources and projections
summary: What one row means, how a row source changes it, and where a named projection
  pins it.
section: subjects
perspective: hub
subject: grain
spec: SPEC-004
order: 40
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/distribution/languages/data/model/public/row_sources.py
- kg_build_system/distribution/languages/data/service/_private/rows.py
- kg_build_system/distribution/languages/expressions/model/public/selection.py
- kg_build_system/distribution/languages/data/service/_private/declarations.py
- docs/reference/row-sources.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Grain, row sources and projections</span><a href="/subjects/grain" class="active">Overview</a><a href="/author/grain">Guide</a><a href="/spec/grain">Spec</a><a href="/reference/api">API</a><a href="/philosophy/design-in-semantics">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

What one row means, how a row source changes it, and where a named projection pins it.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/grain) | The subject in one place. |
| Guide | [Set the grain](/author/grain), [Project rows](/author/projections) | How to use it. |
| Spec | [SPEC-004](/spec/grain) | Binding requirements, API and evidence. |
| API | [API surface](/reference/api) | Exact public names and document shapes. |
| Philosophy | [Design in semantics](/philosophy/design-in-semantics) | Why it is designed this way. |
| Review | [Contracts](/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- A binding MUST read a row-source value, never a declaration class.
- A projection MUST pin exactly one row source and publish at least one computed field.
- A join MUST name one key expression per side; a null key never matches.

## Where it sits

Upstream: [data](/subjects/data), [selection](/subjects/selection). Downstream: [binding](/subjects/binding).

## Next

[Specs](/spec/index) — the normative index.
