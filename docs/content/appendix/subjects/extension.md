---
title: Extending the toolchain
summary: Kernel protocols, composition values and the object that carries each extension.
section: subjects
perspective: hub
subject: extension
spec: SPEC-013
order: 130
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/kernel/service/public/pipeline.py
- kg_build_system/kernel/model/public/language.py
- kg_build_system/api.py
- kg_build_system/distribution/service/internal/emission.py
- kg_build_system/distribution/modules/python/service/_private/python.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Extending the toolchain</span><a href="/appendix/subjects/extension" class="active">Overview</a><a href="/book/part-2/06-extension">Guide</a><a href="/appendix/spec/extension">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/design-in-semantics">Philosophy</a><a href="/appendix/review/architecture">Review</a></div>
<!-- END GENERATED:views -->

## In one view

Kernel protocols, composition values and the object that carries each extension.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/extension) | The subject in one place. |
| Guide | [9. Extending the semantics model](/book/part-2/06-extension), [18. The kernel and the extension surface](/book/part-4/01-the-kernel-and-extension) | How to use it. |
| Spec | [SPEC-013](/appendix/spec/extension) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/api) | Exact public names and document shapes. |
| Philosophy | [Design in semantics](/appendix/philosophy/design-in-semantics) | Why it is designed this way. |
| Review | [Architecture](/appendix/review/architecture), [Limits](/appendix/review/limits) | Invariants, limits and measured evidence. |

## Contract

- The kernel protocol set MUST be the extension surface; a language, linker, planner or executor MUST be an ordinary value passed to `Toolchain`, and a provider MUST be passed to the runtime.
- A new source, syntax, derivation, engine or resource MUST compose a different `Toolchain`; no registry exists as the consequence.
- A new engine MUST implement the neutral `SqlEmitter`, not edit core.

## Where it sits

Upstream: [architecture](/appendix/subjects/architecture), [plan](/appendix/subjects/plan). Downstream: End of the dependency story.

## Next

[Specifications](/appendix/spec/index) — the normative index.
