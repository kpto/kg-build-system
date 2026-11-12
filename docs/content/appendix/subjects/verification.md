---
title: Verification, limits and debugging
summary: The measured status, the review order and the boundaries the framework refuses
  to cross.
section: subjects
perspective: hub
subject: verification
spec: SPEC-016
order: 160
status: normative
verified: '2026-11-11'
sources:
- FRAMEWORK_STATE.md
- pyproject.toml
- kg_build_system/kernel/model/public/runtime.py
- kg_build_system/api.py
- docs/content/book/part-3/04-quality-and-failure.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Verification, limits and debugging</span><a href="/appendix/subjects/verification" class="active">Overview</a><a href="/book/part-4/04-limits-and-evidence">Guide</a><a href="/appendix/spec/verification">Spec</a><a href="/appendix/reference/failures">API</a><a href="/appendix/philosophy/explainability-is-authored">Philosophy</a><a href="/appendix/review/decisions">Review</a></div>
<!-- END GENERATED:views -->

## In one view

The measured status, the review order and the boundaries the framework refuses to cross.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/verification) | The subject in one place. |
| Guide | [21. Limits and evidence](/book/part-4/04-limits-and-evidence), [Verification](/appendix/review/verification), [Limits](/appendix/review/limits), [Drift](/appendix/review/drift), [Failures](/appendix/reference/failures) | How to use it. |
| Spec | [SPEC-016](/appendix/spec/verification) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/failures) | Exact public names and document shapes. |
| Philosophy | [Explainability is authored](/appendix/philosophy/explainability-is-authored) | Why it is designed this way. |
| Review | [Decisions](/appendix/review/decisions) | Invariants, limits and measured evidence. |

## Contract

- Counts MUST be reported as properties of a checkout, not as promises.
- A limit MUST be stated where a consumer meets it, not hidden as an implementation note.
- A green build MUST NOT be accepted as a design review.

## Where it sits

Upstream: [execution](/appendix/subjects/execution), [modules](/appendix/subjects/modules). Downstream: End of the dependency story.

## Next

[Specifications](/appendix/spec/index) — the normative index.
