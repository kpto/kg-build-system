---
title: Semantics and graph purpose
summary: Claims, frames, limitations and the one purpose every declaration is read
  under.
section: subjects
perspective: hub
subject: meaning
spec: SPEC-007
order: 70
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/distribution/languages/semantics/model/public/units.py
- kg_build_system/distribution/languages/graph/model/public/options.py
- kg_build_system/distribution/languages/graph/model/public/declarations.py
- kg_build_system/distribution/languages/annotations/model/public/labels.py
- kg_build_system/distribution/interpreter/model/public/graph_blueprint.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Semantics and graph purpose</span><a href="/subjects/meaning" class="active">Overview</a><a href="/author/meaning">Guide</a><a href="/spec/meaning">Spec</a><a href="/reference/api">API</a><a href="/philosophy/semantic-hierarchy">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

Claims, frames, limitations and the one purpose every declaration is read under.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/meaning) | The subject in one place. |
| Guide | [Declare meaning](/author/meaning) | How to use it. |
| Spec | [SPEC-007](/spec/meaning) | Binding requirements, API and evidence. |
| API | [API surface](/reference/api) | Exact public names and document shapes. |
| Philosophy | [One purpose, read downward](/philosophy/semantic-hierarchy) | Why it is designed this way. |
| Review | [Contracts](/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- A project MUST have at most one `Graph`, and a `Graph` MUST carry one `Purpose`.
- A declaration MUST attach `Semantics`, never `GraphSemantics`.
- A `Limitation` MUST live under a `Frame`; a claim MUST NOT live under a frame.

## Where it sits

Upstream: [topology](/subjects/topology), [binding](/subjects/binding). Downstream: [linking](/subjects/linking).

## Next

[Specs](/spec/index) — the normative index.
