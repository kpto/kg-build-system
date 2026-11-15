---
title: Meaning and graph purpose
summary: One root purpose, local purposes that narrow it, contextless claims, and
  the limitations of each purpose.
section: subjects
perspective: hub
subject: meaning
spec: SPEC-007
order: 70
status: normative
verified: '2026-11-15'
sources:
- kg_build_system/distribution/languages/meaning/model/public/units.py
- kg_build_system/distribution/languages/graph/model/public/options.py
- kg_build_system/distribution/languages/graph/model/public/declarations.py
- kg_build_system/distribution/languages/annotations/model/public/labels.py
- kg_build_system/distribution/interpreter/model/public/graph_blueprint.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Meaning and graph purpose</span><a href="/appendix/subjects/meaning" class="active">Overview</a><a href="/book/part-2/01-meaning-and-purpose">Guide</a><a href="/appendix/spec/meaning">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/semantic-hierarchy">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

One root purpose, local purposes that narrow it, contextless claims, and the limitations of each purpose.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/meaning) | The subject in one place. |
| Guide | [4. Meaning and purpose](/book/part-2/01-meaning-and-purpose) | How to use it. |
| Spec | [SPEC-007](/appendix/spec/meaning) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/api) | Exact public names and document shapes. |
| Philosophy | [Two axes, one fulfilment](/appendix/philosophy/semantic-hierarchy) | Why it is designed this way. |
| Review | [Contracts](/appendix/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- A project MUST have at most one `Graph`, and its `Meaning` MUST carry the root `Purpose`.
- A non-graph declaration MAY carry one local `Purpose`; it MUST narrow the graph purpose.
- A `Limitation` MUST live inside a `Purpose`; a `Claim` MUST remain contextless.

## Where it sits

Upstream: [topology](/appendix/subjects/topology), [binding](/appendix/subjects/binding). Downstream: [linking](/appendix/subjects/linking).

## Next

[Specifications](/appendix/spec/index) — the normative index.
