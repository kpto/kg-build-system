---
title: Selection and nullability
summary: One typed value, its operations, its null policy and its explicit row effects.
section: subjects
perspective: hub
subject: selection
spec: SPEC-003
order: 30
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/distribution/languages/expressions/model/public/selection.py
- kg_build_system/distribution/languages/expressions/model/public/selections/effects.py
- kg_build_system/distribution/languages/expressions/service/public/boolean.py
- kg_build_system/distribution/languages/expressions/service/public/expression.py
- docs/appendix/reference/expressions.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Selection and nullability</span><a href="/appendix/subjects/selection" class="active">Overview</a><a href="/book/part-2/02-values-and-nullability">Guide</a><a href="/appendix/spec/selection">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/meaning-first">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

One typed value, its operations, its null policy and its explicit row effects.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/selection) | The subject in one place. |
| Guide | [5. Values and nullability](/book/part-2/02-values-and-nullability) | How to use it. |
| Spec | [SPEC-003](/appendix/spec/selection) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/api) | Exact public names and document shapes. |
| Philosophy | [Meaning before mechanism](/appendix/philosophy/meaning-first) | Why it is designed this way. |
| Review | [Contracts](/appendix/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- `Selection[T]` MUST be the only authoring value; `NullableSelection[T]` MUST be an alias.
- A row effect MUST be reached through a one-shot `alter_rows()` handle.
- A null key MUST NOT match in a lookup or a join.

## Where it sits

Upstream: [data](/appendix/subjects/data). Downstream: [grain](/appendix/subjects/grain), [binding](/appendix/subjects/binding).

## Next

[Specifications](/appendix/spec/index) — the normative index.
