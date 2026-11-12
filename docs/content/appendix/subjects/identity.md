---
title: Identity, references and documents
summary: Keys, typed references, role identities and the stored blueprint, plan and
  report.
section: subjects
perspective: hub
subject: identity
spec: SPEC-015
order: 150
status: normative
verified: '2026-11-10'
sources:
- kg_build_system/kernel/model/public/key.py
- kg_build_system/kernel/model/public/symbol.py
- kg_build_system/kernel/model/public/workflow.py
- kg_build_system/distribution/model/public/refs.py
- kg_build_system/distribution/interpreter/service/_private/codec.py
generated: true
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Identity, references and documents</span><a href="/appendix/subjects/identity" class="active">Overview</a><a href="/book/part-3/01-linking-and-blueprint">Guide</a><a href="/appendix/spec/identity">Spec</a><a href="/appendix/reference/documents">API</a><a href="/appendix/philosophy/semantic-hierarchy">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## In one view

Keys, typed references, role identities and the stored blueprint, plan and report.

This subject has one overview and up to five views: guide, spec, API, philosophy and review.

## Perspectives

| View | Page | Answers |
| --- | --- | --- |
| Overview | [This page](/appendix/subjects/identity) | The subject in one place. |
| Guide | [13. Linking and the blueprint](/book/part-3/01-linking-and-blueprint) | How to use it. |
| Spec | [SPEC-015](/appendix/spec/identity) | Binding requirements, API and evidence. |
| API | [API surface](/appendix/reference/documents) | Exact public names and document shapes. |
| Philosophy | [One purpose, read downward](/appendix/philosophy/semantic-hierarchy) | Why it is designed this way. |
| Review | [Contracts](/appendix/review/contracts) | Invariants, limits and measured evidence. |

## Contract

- A cross-symbol field MUST be a role-typed reference, never a bare string.
- `StepId`, `OpeningId`, `ArtifactType`, `ArtifactPattern` and `InstructionKind` MUST wrap `Key`.
- A codec round trip MUST preserve the canonical document, not the original text.

## Where it sits

Upstream: [architecture](/appendix/subjects/architecture). Downstream: [linking](/appendix/subjects/linking), [plan](/appendix/subjects/plan), [execution](/appendix/subjects/execution).

## Next

[Specifications](/appendix/spec/index) — the normative index.
