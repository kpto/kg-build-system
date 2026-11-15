---
title: Topology
summary: The node and edge types, their properties, their hierarchy and their direction.
section: subjects
perspective: hub
subject: topology
spec: SPEC-005
order: 50
status: normative
verified: '2026-11-15'
sources:
- kg_build_system/distribution/languages/topology/model/public/declarations.py
- kg_build_system/distribution/languages/topology/service/_private/class_creation.py
- kg_build_system/distribution/languages/topology/service/_private/transcription.py
- kg_build_system/distribution/languages/topology/model/public/options.py
- kg_build_system/distribution/languages/topology/model/public/values.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Topology</span><a href="/appendix/subjects/topology" class="active">Overview</a><a href="/book/part-2/02-topology">Guide</a><a href="/appendix/spec/topology">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/meaning-first">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

The node and edge types, their properties, their hierarchy and their direction.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/topology) | The subject in one place. |
| Guide | [5. Topology](/book/part-2/02-topology) | How to use it. |
| Spec | [SPEC-005](/appendix/spec/topology) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/api) | Exact public names and document shapes. |
| Philosophy | [Meaning before mechanism](/appendix/philosophy/meaning-first) | Why it is designed this way. |
| Review | [Contracts](/appendix/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- A concrete `Node` or `Edge` MUST be the binding target; a category MUST produce no records.
- An edge MUST declare both endpoints, and `Edge[Source, Target]` is directed.
- A property MUST be a scalar or a flat, non-null array of scalars.

## Where it sits

Upstream: [data](/appendix/subjects/data). Downstream: [binding](/appendix/subjects/binding), [meaning](/appendix/subjects/meaning).

## Next

[Specifications](/appendix/spec/index) — the normative index.
