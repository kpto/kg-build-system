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
<div class="kb-views"><span class="kb-views-subject">Kernel, distribution and contracts</span><a href="/subjects/architecture" class="active">Overview</a><a href="/review/architecture">Guide</a><a href="/spec/architecture">Spec</a><a href="/reference/api">API</a><a href="/philosophy/review-top-down">Philosophy</a><a href="/review/limits">Review</a></div>
<!-- END GENERATED:views -->

## In one view

The domain-agnostic toolchain, the graph distribution, the zones and the dependency spine.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/architecture) | The subject in one place. |
| Guide | [Architecture](/review/architecture), [Contracts](/review/contracts) | How to use it. |
| Spec | [SPEC-014](/spec/architecture) | Binding requirements, API and evidence. |
| API | [API surface](/reference/api) | Exact public names and document shapes. |
| Philosophy | [Review top-down](/philosophy/review-top-down) | Why it is designed this way. |
| Review | [Limits](/review/limits) | Invariants, limits and measured evidence. |

## Contract

- The kernel MUST import no distribution, SQL, DuckDB or generation package.
- A package MUST NOT import another package's `_private` zone.
- The dependency spine MUST run from kernel outward; a new edge is a model change.

## Where it sits

Upstream: Top of the dependency story.. Downstream: [extension](/subjects/extension), [identity](/subjects/identity).

## Next

[Specs](/spec/index) — the normative index.
