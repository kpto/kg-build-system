---
title: Assets and source data
summary: One logical source unit, its profile, its descriptive layout and the source
  relations that name it.
section: subjects
perspective: hub
subject: asset
spec: SPEC-001
order: 10
status: normative
verified: '2026-11-15'
sources:
- kg_build_system/distribution/languages/asset/model/public/options.py
- kg_build_system/distribution/languages/asset/model/public/declarations.py
- kg_build_system/distribution/languages/asset/service/_private/declarations.py
- kg_build_system/distribution/modules/duckdb/service/public/planner.py
- docs/content/book/part-2/03-source-and-rows.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Assets and source data</span><a href="/appendix/subjects/asset" class="active">Overview</a><a href="/book/part-2/03-source-and-rows">Guide</a><a href="/appendix/spec/asset">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/meaning-first">Philosophy</a><a href="/appendix/review/limits">Review</a></div>
<!-- END GENERATED:views -->

## In one view

One logical source unit, its profile, its descriptive layout and the source relations that name it.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/asset) | The subject in one place. |
| Guide | [6. Source and rows](/book/part-2/03-source-and-rows), [3. A project](/book/part-1/03-a-project) | How to use it. |
| Spec | [SPEC-001](/appendix/spec/asset) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/api) | Exact public names and document shapes. |
| Philosophy | [Meaning before mechanism](/appendix/philosophy/meaning-first) | Why it is designed this way. |
| Review | [Limits](/appendix/review/limits) | Invariants, limits and measured evidence. |

## Contract

- A source relation MUST name its logical asset with `SourceRelation[Asset]`.
- `AssetProfile` MUST be present; `AssetLayout` is descriptive and opens no file.
- One asset MAY back many source relations; a source relation MUST NOT invent a second source.

## Where it sits

Upstream: Top of the dependency story. Downstream: [data](/appendix/subjects/data), [generation](/appendix/subjects/generation).

## Next

[Specifications](/appendix/spec/index) — the normative index.
