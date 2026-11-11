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
verified: '2026-11-10'
sources:
- FRAMEWORK_STATE.md
- pyproject.toml
- kg_build_system/kernel/model/public/runtime.py
- kg_build_system/api.py
- docs/operate/debug.md
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Verification, limits and debugging</span><a href="/subjects/verification" class="active">Overview</a><a href="/review/verification">Guide</a><a href="/spec/verification">Spec</a><a href="/reference/failures">API</a><a href="/philosophy/explainability-is-authored">Philosophy</a><a href="/review/decisions">Review</a></div>
<!-- END GENERATED:views -->

## In one view

The measured status, the review order and the boundaries the framework refuses to cross.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/subjects/verification) | The subject in one place. |
| Guide | [Verification](/review/verification), [Limits](/review/limits), [Drift](/review/drift), [Debug a build](/operate/debug), [Failures](/reference/failures) | How to use it. |
| Spec | [SPEC-016](/spec/verification) | Binding requirements, API and evidence. |
| API | [API surface](/reference/failures) | Exact public names and document shapes. |
| Philosophy | [Explainability is authored](/philosophy/explainability-is-authored) | Why it is designed this way. |
| Review | [Decisions](/review/decisions) | Invariants, limits and measured evidence. |

## Contract

- Counts MUST be reported as properties of a checkout, not as promises.
- A limit MUST be stated where a consumer meets it, not hidden as an implementation note.
- A green build MUST NOT be accepted as a design review.

## Where it sits

Upstream: [execution](/subjects/execution), [modules](/subjects/modules). Downstream: End of the dependency story..

## Next

[Specs](/spec/index) — the normative index.
