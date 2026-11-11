---
title: Plan specification
summary: Compilation turns one planner composition into a checked, self-contained plan.
section: spec
perspective: spec
subject: plan
spec: SPEC-010
order: 100
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/kernel/service/_private/pipeline.py
  - kg_build_system/kernel/service/_private/assembly.py
  - kg_build_system/kernel/model/public/workflow.py
  - kg_build_system/api.py
  - docs/reference/compile.md
evidence:
  - tests/kernel/test_toolchain_flow.py
  - tests/pipeline/test_pipeline_identity.py
  - tests/distribution/planners/test_plan_assembly.py
  - tests/test_reference_build.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Workflow plan</span><a href="/subjects/plan">Overview</a><a href="/pipeline/plan">Guide</a><a href="/spec/plan" class="active">Spec</a><a href="/reference/documents">API</a><a href="/philosophy/design-in-semantics">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** `compile` MUST group planners by `component_id`, publish one `Component` per group, and assign that component id to every step the group emits.
- **R2.** Planners sharing a component MUST agree on `version` and `runtime_fields`; a disagreement MUST be refused before assembly.
- **R3.** `StepId(component, name)` MUST be unique within a plan; assembly MUST refuse a duplicate identity.
- **R4.** Assembly MUST feed every input and MUST require every ordinary `Output` to be read. A `Publication` MUST be exempt from that read requirement.
- **R5.** Assembly MUST refuse a cycle or any wiring that leaves an input unfed.
- **R6.** `InstructionKind` MUST have exactly two non-empty segments, operation and engine, with no prefix matching. A `Step` MUST own exactly one `Instruction`.
- **R7.** Wiring SHOULD be deterministic: sole writer and sole reader first, then justified ports. Ranking MUST prefer eager over deferred and MUST NOT define runtime order.
- **R8.** `api.compile` MUST record the source blueprint document at `plan.provenance["blueprint"]`; a serialized plan MUST remain self-contained.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/kernel/test_toolchain_flow.py` | Shared planners produce one component; version and runtime-field disagreement are refused; a duplicate step id is refused; the plan round-trips. |
| `tests/pipeline/test_pipeline_identity.py` | Duplicate step ids are refused; kinds are exact and two-segment; the plan codec preserves identity. |
| `tests/distribution/planners/test_plan_assembly.py` | An unread deduplication output is refused, while a consumer lets the plan assemble. |
| `tests/test_reference_build.py` | The compiled plan carries the source blueprint document at `provenance["blueprint"]` and builds. |

## API

| Public name | Role |
| --- | --- |
| `compile` | Canonical facade: prepares a blueprint, compiles it, and attaches the blueprint document. |
| `Toolchain.compile` | Kernel seam: groups planners, validates components, and calls plan assembly. |
| `Component` | One value per planner group, carrying the agreed version and runtime fields. |
| `Step` / `StepId` | Step facts and derived identity; each step carries one `Instruction`. |
| `InstructionKind` | Exact two-segment key with no prefix or family matching. |
| `WorkflowPlan` | The checked plan document; provenance is opaque to the kernel. |
| `assemble_plan` | Turns component contributions into the wired plan or raises an assembly error. |

## Limits

- Compilation reads no data. Source, query and executor failures appear only at execution.
- One plan covers one planner composition. A different composition needs a new compile.
- Assembly validates structure, not executor availability. A plan kind needs a matching executor at execution.
- A plan carries no runtime values. Configuration is an execution input keyed by component id.
- Provenance is opaque except for the blueprint document that `api.compile` adds.
- Ranking is not runtime order. Execution schedules dependency waves after compilation.
- A `Publication` is exempt from being read; an ordinary `Output` is not.
- There is no schema negotiation or migration path. Recompile against the model.

## Rationale

Compilation is pure because meaning is authored once and the plan is the explanation that crosses into execution; see [Meaning first](/philosophy/meaning-first) and [Explainability is authored](/philosophy/explainability-is-authored). The assembler refuses an incomplete wiring instead of deferring ambiguity to runtime. That keeps the plan a reviewable artifact rather than a partially resolved intent.

## Next

[Plan subject](/subjects/plan) — composition, generated views and related pages.
