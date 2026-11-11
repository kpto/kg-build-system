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
- docs/reference/expressions.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Selection and nullability</span><a href="/subjects/selection" class="active">Overview</a><a href="/author/values">Guide</a><a href="/spec/selection">Spec</a><a href="/reference/api">API</a><a href="/philosophy/meaning-first">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

One typed value, its operations, its null policy and its explicit row effects.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/selection) | The subject in one place. |
| Guide | [Select values](/author/values) | How to use it. |
| Spec | [SPEC-003](/spec/selection) | Binding requirements, API and evidence. |
| API | [API surface](/reference/api) | Exact public names and document shapes. |
| Philosophy | [Meaning before mechanism](/philosophy/meaning-first) | Why it is designed this way. |
| Review | [Contracts](/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- `Selection[T]` MUST be the only authoring value; `NullableSelection[T]` MUST be an alias.
- A row effect MUST be reached through a one-shot `alter_rows()` handle.
- A null key MUST NOT match in a lookup or a join.

## Where it sits

Upstream: [data](/subjects/data). Downstream: [grain](/subjects/grain), [binding](/subjects/binding).

## Next

[Specs](/spec/index) — the normative index.
