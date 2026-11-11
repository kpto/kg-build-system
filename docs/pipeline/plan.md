---
title: Compile a plan
summary: Compile turns planners into components and assembles steps, typed ports and connections into one checked workflow plan.
section: pipeline
order: 30
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/kernel/service/_private/pipeline.py
  - kg_build_system/kernel/service/_private/assembly.py
  - kg_build_system/kernel/model/public/workflow.py
  - kg_build_system/api.py
  - docs/reference/compile.md
subject: plan
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Workflow plan</span><a href="/subjects/plan">Overview</a><a href="/pipeline/plan" class="active">Guide</a><a href="/spec/plan">Spec</a><a href="/reference/documents">API</a><a href="/philosophy/design-in-semantics">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> Compilation is pure. It consumes the blueprint and a planner composition, reads no data, writes no files, and returns a plan whose wiring is already checked.

## What it is

`compile(model)` groups planners by `component_id`, publishes one `Component` per group, asks every planner for steps and assembles those steps into a single `WorkflowPlan`.

| Part | Contents |
| --- | --- |
| Component | id, version and runtime fields; one per planner group |
| Step | `StepId(component, name)`, typed openings and one `Instruction` |
| Connection | a resolved output-to-input opening |
| Provenance | opaque plan data; `api.compile` adds the blueprint document |

Planners that share a component must agree on version and runtime fields. Every step in the group is assigned that component id.

<figure class="kb-plate">
  <img src="/_assets/modules.svg" alt="Planners emit steps and executors own exact instruction kinds.">
  <figcaption>A component groups planners. A step names one exact instruction kind; the plan carries the kind, not the engine.</figcaption>
</figure>

## Rules

- Planners sharing a `component_id` must agree on `version` and `runtime_fields`. One `Component` is published per group, and every step gets the component id.
- `StepId(component, name)` must be unique. Assembly refuses an unfed input, an unread ordinary `Output`, a cycle and a duplicate step id. A publication is exempt from being read.
- `InstructionKind` is exactly two segments, operation and engine, with no prefix matching. A `Step` owns one `Instruction(kind, payload)`. SQL is one kind, not a plan field.
- Wiring is deterministic: sole writer and reader first, then justified ports. Ranking prefers eager over deferred. Runtime order is dependency waves, not the ranking.
- `api.compile` records the source blueprint document at `plan.provenance["blueprint"]`. Kernel provenance is opaque. A serialized plan is self-contained.
- Assembly completes the plan: every input is fed and every ordinary output is read. A connection is always a resolved output opening to a resolved input opening.

## Example

```python
from pathlib import Path

from kg_build_system import compile, create_blueprint
from kg_build_system.distribution import FileConfiguration, FilePlanner

plan = compile(
    blueprint=create_blueprint(namespace_path=Path("reference_project")),
    planners=(FilePlanner(FileConfiguration("graph.jsonl")),),
)
```

A plan document has four top-level members:

```json
{
  "components": [
    {"id": "core", "version": "1", "runtime_fields": []},
    {"id": "file", "version": "1", "runtime_fields": []}
  ],
  "steps": [
    {"id": ["core", "node"],
     "instruction": {"kind": ["node", "python"], "payload": {}}},
    {"id": ["file", "write"],
     "instruction": {"kind": ["file", "write_result"], "payload": {}}}
  ],
  "connections": [
    {"input": ["file", "write", "input", "core.node"],
     "output": ["core", "node", "output", "core.node"]}
  ],
  "provenance": {"blueprint": {"graph": {}, "data": {}}}
}
```

The blueprint side of this handoff is described in [Assemble the blueprint](/pipeline/blueprint).

## Limits

- Compilation reads no data. Source, query and executor failures appear only at execution.
- One plan is one planner composition. A different composition needs a new compile.
- A plan is durable only where an executor exists for every exact instruction kind it names. There is no schema negotiation or migration.
- The plan carries no runtime values. Configuration is an execution input keyed by component id.
- Provenance is opaque except for the blueprint document that `api.compile` adds. The kernel does not interpret it.
- SQL is payload under one instruction kind, not a plan field. The plan promises no particular engine.
- Assembly validates structure, not executor availability. [Execute a plan](/pipeline/execute) checks the kinds.

> [!note] Extension point
> A model rule is not an extension point. Everything else names the object that replaces it; the ladder is in [Extend the toolchain](/operate/extend#extension-ladder).

## Next

[Execute a plan](/pipeline/execute) — resources, exact kinds and the report.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-004 | Make compile a pure consumer of a separately assembled blueprint. | 2026-11-03 | accepted | `tests/kernel/test_toolchain_flow.py` |
| D-005 | Make the workflow contract step-centric and instruction-based, with exact instruction kinds. | 2026-11-03 | accepted | `tests/kernel/test_kernel.py` |
| D-006 | Use Key-backed role types for every identity that crosses pipeline boundaries. | 2026-11-04 | accepted | `tests/pipeline/test_pipeline_identity.py` |
| D-030 | Consume an engine-neutral relation plan and injected `SqlEmitter`; core imports no DuckDB module. | 2026-11-05 | accepted | `tests/distribution/planners/test_core_custom_emitter.py` |
