---
title: Extend the toolchain
summary: Compose a toolchain from a language, planner, executor and runtime; the framework has no extension registry.
section: operate
order: 40
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/kernel/service/public/pipeline.py
  - kg_build_system/kernel/model/public/language.py
  - kg_build_system/distribution/service/internal/emission.py
  - kg_build_system/distribution/modules/python/service/_private/python.py
  - kg_build_system/api.py
subject: extension
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Extending the toolchain</span><a href="/subjects/extension">Overview</a><a href="/operate/extend" class="active">Guide</a><a href="/spec/extension">Spec</a><a href="/reference/api">API</a><a href="/philosophy/design-in-semantics">Philosophy</a><a href="/review/architecture">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> There is no extension class and no extension registry. An extension is a value passed into a Toolchain; the kernel knows only protocols.

## What it is

| Point | Implement | Required surface |
| --- | --- | --- |
| Language | A frontend for one declaration syntax | `discover_declarations`, `compute_key`, `get_kind`, `get_identity`, `get_references`, `transcribe`, `render` |
| Linker | Roots, closure and assembly for one model | `link(languages, namespace)` |
| Planner | Steps for one component | `component_id`, `version`, `runtime_fields`, `plan(model, context)` |
| StepExecutor | One exact instruction kind | `kinds`, `resources`, `execute(context, instruction)` |
| ResourceProvider | A live resource lifecycle | `on_event(event)` |
| Runtime | Scheduling and dispatch | `execute(plan, executors, configuration=...)` |

Compose the protocols directly with `Toolchain(languages=..., linker=..., planners=..., executors=..., runtime=...)`, or start from `default_toolchain(planners=..., executors=...)`. The latter adds the generic source planner unless a planner claims `duckdb`, and the four core planners unless one claims `core`.

Plans are assembled in [Compile a plan](/pipeline/plan) and run in [Execute a plan](/pipeline/execute). The boundary is in [Architecture](/review/architecture); exported names are in [API surface](/reference/api).

## Rules

- A `Language` turns one declaration into one symbol. The linker calls `transcribe` once per reachable declaration; there is no batch protocol. The linker owns roots, order and closure.
- A `Planner` declares `component_id`, `version` and `runtime_fields`; `plan(model, context)` returns `Sequence[Step]`. Planners that share a component must agree on version and runtime fields.
- A `StepExecutor` declares the exact `kinds` it handles and the `resources` it reads; `execute` returns a `StepOutcome`. A `ResourceView` contains exactly those resource types; asking for another raises `KeyError`.
- `InstructionKind` is exact. There is no prefix matching, wildcard kind or family dispatch.
- A `ResourceProvider` subscribes to events, publishes resources on `PipelineStarted`, and disposes them on `PipelineFinished` or `PipelineHalted`.
- An engine supplies a neutral `SqlEmitter` implementation. Core consumes the relation plan and emitter; it imports no DuckDB module. A new engine implements the same boundary.
- The Python executor is not an extension point: `("python", "cpython")` carries `{module, qualname}`. It has no isolation, timeout or retry.
- Pass the same toolchain to `compile` and `execute`; `execute` builds its exact-kind map from that toolchain's executors.

## Example

```python
from kg_build_system.kernel import (
    ArtifactPattern,
    ArtifactType,
    Input,
    Instruction,
    InstructionKind,
    Key,
    Output,
    PlanContext,
    Step,
    StepId,
)


class ManifestPlanner:
    component_id = "manifest"
    version = "1"
    runtime_fields = ()

    def plan(self, model, context: PlanContext) -> tuple[Step, ...]:
        step = Step(
            component=self.component_id,
            name="write",
            inputs=(
                Input(
                    ArtifactPattern.of("core", "graph", "**"),
                    None,
                    "records",
                ),
            ),
            outputs=(
                Output(ArtifactType.of("manifest", "summary"), Key(("summary",))),
            ),
            instruction=Instruction(
                InstructionKind("manifest", "default"),
                {"path": "manifest.json"},
            ),
            assembly_preference="deferred",
        )
        assert step.id == StepId("manifest", "write")
        return (step,)
```

The executor owns the kind. `ManifestExecutor` must declare `kinds = (InstructionKind("manifest", "default"),)` and implement `execute`; the planner cannot register a kind. The ordinary `Output` also needs a later reader, or declare a `Publication` instead.

## Limits

- There is no `Extension` class, extension registry, plugin entry point or discovery by name. Every contribution is an ordinary object passed explicitly.
- A new language must implement the whole language surface. A helper may batch internally, but the linker calls `transcribe` per declaration.
- Execution is one exact-kind map. Two executors claiming one kind, or a plan kind with no executor, are refused before any step runs.
- There is no per-step timeout, retry, cancellation or memory quota. A Python target runs in the host process.
- A listener observes events and cannot change scheduling, resources or the report.
- A custom engine must supply the neutral emitter; the kernel does not inspect SQL or engine objects.

## Next

[Ship a build](/operate/ship) — test and run the extended toolchain.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-005 | Make the workflow contract step-centric and instruction-based, with exact instruction kinds. | 2026-11-03 | accepted | `tests/kernel/test_kernel.py`; `docs/reference/compile.md` |
| D-007 | Emit pipeline events and let resource providers subscribe to lifecycle events. | 2026-11-04 | accepted | `tests/kernel/test_runtime_events.py`; `docs/developer/system-design.md` |
| D-030 | Consume an engine-neutral relation plan and injected `SqlEmitter`; core imports no DuckDB module. | 2026-11-05 | accepted | `tests/distribution/planners/test_core_custom_emitter.py` |
