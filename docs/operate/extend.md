---
title: Extend the toolchain
summary: Compose a toolchain from kernel protocols; the default distribution is one composition, and an extension is an ordinary object.
section: operate
order: 40
status: normative
verified: 2026-11-11
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
> The kernel protocol set is the extension surface: `Language`, `Linker`, `Planner`, `StepExecutor`, `ResourceProvider` and `Runtime`. A language, linker, planner or executor is an ordinary value passed to `Toolchain`; a provider is passed to the runtime. The default distribution is one composition. A new source, syntax, derivation, engine or resource is another composition, not a framework change. There is no registry: composition is explicit.

## What it is

| Name | Required surface |
| --- | --- |
| Language | `discover_declarations, compute_key, get_kind, get_identity, get_references, transcribe, render` |
| Linker | `link(languages, namespace)` |
| Planner | `component_id, version, runtime_fields, plan(model, context)` |
| StepExecutor | `kinds, resources, execute(context, instruction)` |
| ResourceProvider | `on_event(event)` |
| Runtime | `execute(plan, executors, configuration=...)` |

These six are kernel protocols; the canonical statement is [Kernel protocols](/kernel/protocols). A language, linker, planner or executor is composed with `Toolchain(...)` or `default_toolchain(planners=..., executors=...)`; a provider is composed into the runtime. `default_toolchain` adds the source planner unless one claims `duckdb` and the core planners unless one claims `core`. `SqlEmitter` is a neutral distribution service protocol, not kernel; `Toolchain` is a frozen composition value, not a protocol.

## Extension ladder

| Question | If yes, extend | Where | Cost |
| --- | --- | --- | --- |
| Does the source need new I/O? | Source planner/executor, or a frontend script | A source module | Decoding |
| Declaration syntax? | Language | `Language`, `languages/<name>` | Language surface |
| Derived relation? | Module | `Planner` + `StepExecutor` | Module, tests |
| New query engine? | Emitter and executor | `SqlEmitter`, module | Adapter |
| New lifecycle resource? | Provider | `ResourceProvider` | Provider |
| Different scheduling or assembly? | Linker or runtime | `Linker` / `Runtime` | Runtime |
| Changed graph meaning? | Model change | `docs/developer/` and review | Review |

The ladder changes "can the framework do X?" to "which object carries X?".

## Example: a consensus module

The default row algebra groups with `group_by` but has no majority vote. Consensus over interaction assertions is a module a reader composes, not a shipped planner or kind.

```python
from collections.abc import Sequence

from kg_build_system.kernel import (
    Artifact,
    ArtifactPattern,
    ArtifactType,
    DisruptedExecutionContext,
    ExecutionContext,
    Input,
    Instruction,
    InstructionKind,
    Key,
    PlanContext,
    Publication,
    Step,
    StepOutcome,
    StepStatus,
)


class ConsensusPlanner:
    component_id = "consensus"
    version = "1"
    runtime_fields = ()

    def plan(self, model, context: PlanContext) -> Sequence[Step]:
        del model, context
        return (
            Step(
                component=self.component_id,
                name="assertions",
                inputs=(
                    Input(
                        ArtifactPattern.of("core", "graph", "**"), None, "records",
                    ),
                ),
                outputs=(
                    Publication(
                        ArtifactType.of("consensus", "assertion"),
                        Key(("assertion",)),
                    ),
                ),
                instruction=Instruction(
                    InstructionKind("consensus", "default"),
                    {
                        "subject": "source",
                        "object": "target",
                        "relation": "interacts_with",
                        "threshold": 0.5,
                    },
                ),
            ),
        )


class ConsensusExecutor:
    kinds = (InstructionKind("consensus", "default"),)
    resources = ()

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        if isinstance(context, DisruptedExecutionContext):
            return StepOutcome(context.step_id, StepStatus.SKIPPED)
        rows = tuple(
            item.artifact.value
            for item in context.inputs["records"]
            if item.artifact is not None
        )
        assertion = majority(rows, instruction.payload)
        if assertion is None:
            return StepOutcome(context.step_id, StepStatus.WARNING)
        given = context.step.outputs[0]
        assert given.opening_name is not None
        return StepOutcome(
            context.step_id,
            StepStatus.SUCCEEDED,
            (Artifact(given.opening_name, given.type, assertion),),
        )
```

`majority` is module-local. The planner reads `core/graph/**` and publishes `consensus/assertion`; the executor votes locally. The code is the shape, not a complete implementation: a real module supplies `majority`, error handling and its contract tests.

```python
from kg_build_system import DEFAULT_TOOLCHAIN, default_toolchain

toolchain = default_toolchain(
    planners=(ConsensusPlanner(),),
    executors=(*DEFAULT_TOOLCHAIN.executors, ConsensusExecutor()),
)
```

A SQL-backed variant owns `("consensus", "duckdb")`: its planner takes `SqlEmitter` and its executor declares the DuckDB resource.

The module's contract tests cover conflicts, a tie, one resource and provenance: the supported object wins, a tie returns `WARNING`, and sources are preserved.

## Where the boundary falls

| Case | Object | Cost |
| --- | --- | --- |
| Semicolon lists | Source planner/executor or a language operation, not a model rule | Decoding |
| ID translation, orthology | Module or graph facts (`CrossReference`, `OrthologOf`) | Mapping |
| Consensus | Module | Tests |
| Download | `ResourceProvider` + executor, or a frontend script kept outside for reproducibility | Script |
| Undirected edges | Reify the assertion or add a language declaration kind | Model choice |
| Licence filter | Resource facts + filter module | Facts |

## What the framework does not decide

- **Acquisition:** `ResourceProvider` + executor, or a script.
- **Identifier translation:** module or graph facts.
- **Orthology:** module or `CrossReference`/`OrthologOf`.
- **Storage engine:** emitter + executor.
- **Scheduling:** runtime or linker.
- **Licence enforcement:** resource facts + filter module.
- **Incremental strategy:** planner and runtime reading prior artifacts.

## Rules

- A `Language` turns one declaration into one symbol; the linker transcribes each reachable declaration once, with no batch protocol, and owns roots, order and closure.
- A `Planner` declares `component_id`, `version`, `runtime_fields`; `plan` returns steps. Planners sharing a component agree on version and fields.
- A `StepExecutor` declares exact `kinds` and the `resources` it reads; `execute` returns a `StepOutcome`. Its `ResourceView` is exact; another type raises `KeyError`.
- `InstructionKind` is exact; no prefix matching, wildcard kind or family dispatch.
- A `ResourceProvider` subscribes to events, publishes resources on `PipelineStarted` and disposes on `PipelineFinished` or `PipelineHalted`.
- A custom engine implements the distribution-neutral `SqlEmitter`; core consumes the relation plan and emitter and imports no DuckDB module.
- The Python executor is not an extension point: `("python", "cpython")` carries `{module, qualname}`; no isolation, timeout or retry.
- Pass one toolchain to `compile` and `execute`; `execute` maps exact kinds from its executors.
- Do not claim a missing capability unless the kernel protocol set cannot carry it; name the extension point and cost.

## Limits

- No `Extension` class, registry, plugin entry point or discovery by name; each contribution is passed explicitly to the object that owns it.
- A new language implements the whole surface; the linker transcribes per declaration.
- No per-step timeout, retry, cancellation or memory quota; a Python target runs in the host process.
- A listener observes events and cannot change scheduling, resources or the report.
- Model rules are not extension points; every other limit names the object that replaces it, and the ladder is the map.

## Next

[Ship a build](/operate/ship)

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-005 | Make the workflow contract step-centric and instruction-based, with exact instruction kinds. | 2026-11-03 | accepted | `tests/kernel/test_kernel.py`; `docs/reference/compile.md` |
| D-007 | Emit pipeline events and let resource providers subscribe to lifecycle events. | 2026-11-04 | accepted | `tests/kernel/test_runtime_events.py`; `docs/developer/system-design.md` |
| D-030 | Consume an engine-neutral relation plan and injected `SqlEmitter`; core imports no DuckDB module. | 2026-11-05 | accepted | `tests/distribution/planners/test_core_custom_emitter.py` |
