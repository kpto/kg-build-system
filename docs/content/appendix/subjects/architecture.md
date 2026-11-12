---
title: Kernel, distribution and contracts
summary: The domain-agnostic toolchain, the graph distribution, the zones and the
  dependency spine.
section: subjects
perspective: hub
subject: architecture
spec: SPEC-014
order: 140
status: normative
verified: '2026-11-10'
sources:
- AGENTS.md
- ARCHITECTURE.md
- kg_build_system/kernel/
- kg_build_system/distribution/
- tests/test_architecture.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Kernel, distribution and contracts</span><a href="/appendix/subjects/architecture" class="active">Overview</a><a href="/book/part-4/03-architecture-and-tests">Guide</a><a href="/appendix/spec/architecture">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/review-top-down">Philosophy</a><a href="/appendix/review/architecture">Review</a></div>
<!-- END GENERATED:views -->

## In one view

The domain-agnostic toolchain, the graph distribution, the zones and the dependency spine.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/architecture) | The subject in one place. |
| Guide | [20. Architecture and tests](/book/part-4/03-architecture-and-tests) | How to use it. |
| Spec | [SPEC-014](/appendix/spec/architecture) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/api) | Exact public names and document shapes. |
| Philosophy | [Review top-down](/appendix/philosophy/review-top-down) | Why it is designed this way. |
| Review | [Architecture](/appendix/review/architecture), [Contracts](/appendix/review/contracts), [Limits](/appendix/review/limits) | Invariants, limits and measured evidence. |

## Contract

- The kernel MUST import no distribution, SQL, DuckDB or generation package.
- A package MUST NOT import another package's `_private` zone.
- The dependency spine MUST run from kernel outward; a new edge is a model change.

## Where it sits

Upstream: Top of the dependency story. Downstream: [extension](/appendix/subjects/extension), [identity](/appendix/subjects/identity).

## Next

[Specifications](/appendix/spec/index) — the normative index.
