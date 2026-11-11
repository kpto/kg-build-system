---
title: Topology
summary: The node and edge types, their properties, their hierarchy and their direction.
section: subjects
perspective: hub
subject: topology
spec: SPEC-005
order: 50
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/distribution/languages/topology/model/public/declarations.py
- kg_build_system/distribution/languages/topology/service/_private/class_creation.py
- kg_build_system/distribution/languages/topology/service/_private/transcription.py
- kg_build_system/distribution/languages/topology/model/public/options.py
- kg_build_system/distribution/languages/topology/model/public/values.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Topology</span><a href="/subjects/topology" class="active">Overview</a><a href="/author/topology">Guide</a><a href="/spec/topology">Spec</a><a href="/reference/api">API</a><a href="/philosophy/meaning-first">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

The node and edge types, their properties, their hierarchy and their direction.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/topology) | The subject in one place. |
| Guide | [Declare topology](/author/topology) | How to use it. |
| Spec | [SPEC-005](/spec/topology) | Binding requirements, API and evidence. |
| API | [API surface](/reference/api) | Exact public names and document shapes. |
| Philosophy | [Meaning before mechanism](/philosophy/meaning-first) | Why it is designed this way. |
| Review | [Contracts](/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- A concrete `Node` or `Edge` MUST be the binding target; a category MUST produce no records.
- An edge MUST declare both endpoints, and `Edge[Source, Target]` is directed.
- A property MUST be a scalar or a flat, non-null array of scalars.

## Where it sits

Upstream: [data](/subjects/data). Downstream: [binding](/subjects/binding), [meaning](/subjects/meaning).

## Next

[Specs](/spec/index) — the normative index.
