---
title: Source generation and CLI
summary: An inert asset contract, static discovery and an owned package of ordinary
  declarations.
section: subjects
perspective: hub
subject: generation
spec: SPEC-008
order: 80
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/generation/code_generation/model/public/contract.py
- kg_build_system/generation/code_generation/service/_private/discovery.py
- kg_build_system/generation/code_generation/service/_private/engine.py
- kg_build_system/generation/code_generation/model/internal/providers.py
- kg_build_system/generation/code_generation/service/_private/builtins/provider.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Source generation and CLI</span><a href="/subjects/generation" class="active">Overview</a><a href="/author/generation">Guide</a><a href="/spec/generation">Spec</a><a href="/reference/api">API</a><a href="/philosophy/explainability-is-authored">Philosophy</a><a href="/review/limits">Review</a></div>
<!-- END GENERATED:views -->

## In one view

An inert asset contract, static discovery and an owned package of ordinary declarations.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/generation) | The subject in one place. |
| Guide | [Generate declarations](/author/generation), [CLI](/reference/cli) | How to use it. |
| Spec | [SPEC-008](/spec/generation) | Binding requirements, API and evidence. |
| API | [API surface](/reference/api) | Exact public names and document shapes. |
| Philosophy | [Explainability is authored](/philosophy/explainability-is-authored) | Why it is designed this way. |
| Review | [Limits](/review/limits) | Invariants, limits and measured evidence. |

## Contract

- `@asset_contract` MUST be inert and MUST NOT enter `AssetOptions` or the blueprint.
- Discovery MUST NOT import the author module; it MUST find a static request.
- Generated source MUST render `Field[T]`; observed nullability is provenance, not absence.

## Where it sits

Upstream: [asset](/subjects/asset), [data](/subjects/data). Downstream: [linking](/subjects/linking).

## Next

[Specs](/spec/index) — the normative index.
