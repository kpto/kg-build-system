---
title: Data contracts and types
summary: The row shape, the canonical value types and where nullability belongs.
section: subjects
perspective: hub
subject: data
spec: SPEC-002
order: 20
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/distribution/languages/data/model/public/declarations.py
- kg_build_system/distribution/languages/data/model/public/fields.py
- kg_build_system/distribution/languages/data/model/public/row_sources.py
- kg_build_system/distribution/languages/topology/model/public/values.py
- docs/author/data.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Data contracts and types</span><a href="/subjects/data" class="active">Overview</a><a href="/author/data">Guide</a><a href="/spec/data">Spec</a><a href="/reference/api">API</a><a href="/philosophy/meaning-first">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

The row shape, the canonical value types and where nullability belongs.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/data) | The subject in one place. |
| Guide | [Declare data](/author/data) | How to use it. |
| Spec | [SPEC-002](/spec/data) | Binding requirements, API and evidence. |
| API | [API surface](/reference/api) | Exact public names and document shapes. |
| Philosophy | [Meaning before mechanism](/philosophy/meaning-first) | Why it is designed this way. |
| Review | [Contracts](/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- A `Table` MUST name its asset; a `Struct` MUST describe a nested source record.
- `Field[T]` MUST declare a value type, never `T | None`.
- The owner MUST decide presence: source reads are nullable, computed reads follow their selection.

## Where it sits

Upstream: [asset](/subjects/asset). Downstream: [selection](/subjects/selection), [topology](/subjects/topology), [binding](/subjects/binding).

## Next

[Specs](/spec/index) — the normative index.
