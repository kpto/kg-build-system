---
title: Bindings
summary: The single place where a row context becomes a concrete node or edge record.
section: subjects
perspective: hub
subject: binding
spec: SPEC-006
order: 60
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/distribution/languages/binding/service/public/builders.py
- kg_build_system/distribution/languages/binding/service/_private/factories.py
- kg_build_system/distribution/languages/binding/service/_private/symbols.py
- kg_build_system/distribution/languages/binding/service/_private/transcription.py
- kg_build_system/distribution/languages/binding/model/public/values.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Bindings</span><a href="/appendix/subjects/binding" class="active">Overview</a><a href="/book/part-2/08-binding">Guide</a><a href="/appendix/spec/binding">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/binding-is-the-seam">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

The single place where a row context becomes a concrete node or edge record.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/binding) | The subject in one place. |
| Guide | [11. Binding as implementation detail](/book/part-2/08-binding) | How to use it. |
| Spec | [SPEC-006](/appendix/spec/binding) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/api) | Exact public names and document shapes. |
| Philosophy | [The binding is the seam](/appendix/philosophy/binding-is-the-seam) | Why it is designed this way. |
| Review | [Contracts](/appendix/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- A binding MUST supply a present scalar build key and every declared property exactly once.
- An edge binding MUST supply its own key, a source key and a target key.
- Binding identity MUST be content-derived; `debug_name` MUST NOT change the digest.

## Where it sits

Upstream: [grain](/appendix/subjects/grain), [topology](/appendix/subjects/topology). Downstream: [meaning](/appendix/subjects/meaning), [execution](/appendix/subjects/execution).

## Next

[Specifications](/appendix/spec/index) — the normative index.
