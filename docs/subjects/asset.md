---
title: Assets and source data
summary: One logical source unit, its profile, its descriptive layout and the tables
  that name it.
section: subjects
perspective: hub
subject: asset
spec: SPEC-001
order: 10
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/distribution/languages/asset/model/public/options.py
- kg_build_system/distribution/languages/asset/model/public/declarations.py
- kg_build_system/distribution/languages/asset/service/_private/declarations.py
- kg_build_system/distribution/modules/duckdb/service/public/planner.py
- docs/author/assets.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Assets and source data</span><a href="/subjects/asset" class="active">Overview</a><a href="/author/assets">Guide</a><a href="/spec/asset">Spec</a><a href="/reference/api">API</a><a href="/philosophy/meaning-first">Philosophy</a><a href="/review/limits">Review</a></div>
<!-- END GENERATED:views -->

## In one view

One logical source unit, its profile, its descriptive layout and the tables that name it.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/asset) | The subject in one place. |
| Guide | [Declare an asset](/author/assets), [Shape a project](/start/project) | How to use it. |
| Spec | [SPEC-001](/spec/asset) | Binding requirements, API and evidence. |
| API | [API surface](/reference/api) | Exact public names and document shapes. |
| Philosophy | [Meaning before mechanism](/philosophy/meaning-first) | Why it is designed this way. |
| Review | [Limits](/review/limits) | Invariants, limits and measured evidence. |

## Contract

- A table MUST name its logical asset with `Table[Asset]`.
- `AssetProfile` MUST be present; `AssetLayout` is descriptive and opens no file.
- One asset MAY back many tables; a table MUST NOT invent a second source.

## Where it sits

Upstream: Top of the dependency story.. Downstream: [data](/subjects/data), [generation](/subjects/generation).

## Next

[Specs](/spec/index) — the normative index.
