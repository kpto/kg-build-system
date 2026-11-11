---
title: Linking and the blueprint
summary: How declarations become symbols, reachable closure and the semantic blueprint.
section: subjects
perspective: hub
subject: linking
spec: SPEC-009
order: 90
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/distribution/interpreter/service/_private/link.py
- kg_build_system/distribution/interpreter/service/internal/adapters/kernel_linker.py
- kg_build_system/kernel/model/public/language.py
- kg_build_system/kernel/model/public/symbol.py
- kg_build_system/distribution/model/public/refs.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Linking and the blueprint</span><a href="/appendix/subjects/linking" class="active">Overview</a><a href="/book/part-3/01-linking-and-blueprint">Guide</a><a href="/appendix/spec/linking">Spec</a><a href="/appendix/reference/documents">API</a><a href="/appendix/philosophy/semantic-hierarchy">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

How declarations become symbols, reachable closure and the semantic blueprint.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/linking) | The subject in one place. |
| Guide | [13. Linking and the blueprint](/book/part-3/01-linking-and-blueprint) | How to use it. |
| Spec | [SPEC-009](/appendix/spec/linking) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/documents) | Exact public names and document shapes. |
| Philosophy | [One purpose, read downward](/appendix/philosophy/semantic-hierarchy) | Why it is designed this way. |
| Review | [Contracts](/appendix/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- A declaration MUST NOT carry a key; `compute_key` MUST derive it.
- The linker MUST own roots, closure and dependencies-first order.
- `GraphBlueprint` MUST have graph, data, assets, bindings and optional graph declaration.

## Where it sits

Upstream: [asset](/appendix/subjects/asset), [data](/appendix/subjects/data), [topology](/appendix/subjects/topology), [binding](/appendix/subjects/binding), [meaning](/appendix/subjects/meaning). Downstream: [plan](/appendix/subjects/plan).

## Next

[Specifications](/appendix/spec/index) — the normative index.
