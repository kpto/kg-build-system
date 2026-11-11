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
- docs/book/part-2/01-source-and-rows.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Data contracts and types</span><a href="/appendix/subjects/data" class="active">Overview</a><a href="/book/part-2/01-source-and-rows">Guide</a><a href="/appendix/spec/data">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/meaning-first">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

The row shape, the canonical value types and where nullability belongs.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/data) | The subject in one place. |
| Guide | [4. Source and rows](/book/part-2/01-source-and-rows) | How to use it. |
| Spec | [SPEC-002](/appendix/spec/data) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/api) | Exact public names and document shapes. |
| Philosophy | [Meaning before mechanism](/appendix/philosophy/meaning-first) | Why it is designed this way. |
| Review | [Contracts](/appendix/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- A `Table` MUST name its asset; a `Struct` MUST describe a nested source record.
- `Field[T]` MUST declare a value type, never `T | None`.
- The owner MUST decide presence: source reads are nullable, computed reads follow their selection.

## Where it sits

Upstream: [asset](/appendix/subjects/asset). Downstream: [selection](/appendix/subjects/selection), [topology](/appendix/subjects/topology), [binding](/appendix/subjects/binding).

## Next

[Specifications](/appendix/spec/index) — the normative index.
