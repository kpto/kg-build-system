---
title: "18. The kernel and the extension surface"
summary: "The kernel is six protocols and a handful of composition values; an extension is an ordinary object placed in a toolchain or a runtime."
section: book
perspective: book
part: IV
chapter: 18
order: 41
status: normative
verified: 2026-11-11
sources:
  - kg_build_system/kernel/service/public/pipeline.py
  - kg_build_system/kernel/model/public/language.py
  - kg_build_system/distribution/service/internal/emission.py
  - tests/kernel/test_toolchain_flow.py
---

## The question behind an extension

A project imports interaction assertions from three sources. Each row says that one molecule interacts with another, and each source has its own evidence. The project wants one edge when more than half of the sources agree, and no edge when the sources tie. The author reaches for the row algebra and finds `group_by`. It collects rows into groups. It does not vote.

The first sentence of the diagnosis is easy: "the framework cannot do consensus." The sentence is also wrong in a way that matters. The default distribution does not ship a consensus planner, and the shipped row algebra has no majority operation. Those are facts about one composition. The kernel still defines the objects that can carry a vote: a planner can emit a step for it, an executor can compute it, and a toolchain can compose both with the rest of the build. The correct diagnosis is not a missing feature but a missing object.

That distinction is the argument of Part IV. An extension starts with a capability the shipped system lacks and ends with a named object that carries it. The kernel is the small, domain-agnostic vocabulary in which that object is described. The distribution is one set of implementations of that vocabulary. Review is the discipline of keeping the two apart.

The question to ask is therefore not "can the framework do X?" but "which job is X?" The kernel answers with six jobs.

## Six protocols, six jobs

The extension surface is six protocols. A protocol here is structural: an object satisfies it by having the named members, not by inheriting a base class or registering a name. The kernel checks the object by using it.

| Protocol | Job | Shape |
| --- | --- | --- |
| `Language` | Own one declaration syntax. | `discover_declarations`, `compute_key`, `get_kind`, `get_identity`, `get_references`, `transcribe`, `render` |
| `Linker` | Select roots, order languages, walk the reference closure and assemble one model. | `link(languages, namespace) -> ModelT` |
| `Planner` | Turn a linked model into steps. | `component_id`, `version`, `runtime_fields`, `plan(model, context) -> Sequence[Step]` |
| `StepExecutor` | Execute one exact instruction kind and declare the resources it reads. | `kinds`, `resources`, `execute(context, instruction) -> StepOutcome` |
| `ResourceProvider` | Open and dispose live resources over the pipeline lifecycle. | `on_event(event)` |
| `Runtime` | Schedule a plan, dispatch steps and produce a report. | `execute(plan, executors, *, configuration, listeners=())` |

A `Language` is the frontend of a build. `discover_declarations` receives a `Namespace` and yields the declarations the language recognises. `compute_key` derives a qualified name from one declaration. `get_kind` states the symbol's role in the language's own vocabulary. `get_identity` resolves an authoring value to the symbol it denotes, and `get_references` reports the direct references from that value. `transcribe` turns one declaration into one `Symbol`, and `render` is the reverse direction: it turns a symbol value back into authoring source. The language's `name` is written into every `SymbolRef` it produces.

The linker owns what the kernel cannot. It decides which languages participate and in what order, which declarations are roots, how the reference closure is walked and how the resulting symbols become one model. The kernel never inspects that model. `ModelT` is opaque: it may be a graph blueprint, a different semantic model or a test fixture. A custom language and a custom linker can therefore run without the graph distribution.

A `Planner` emits steps; it does not execute them. Its `component_id` names the group that owns the steps, `version` names the implementation, and `runtime_fields` names the configuration fields the runtime may pass to that component. Planners that share a component must agree on version and runtime fields. The component is published once, and every step in the group takes its id. `plan` returns a sequence of `Step` values: typed inputs, typed outputs, one instruction and an assembly preference.

A `StepExecutor` owns one exact instruction kind. `Executor` is the pair `kinds` and `execute`; `StepExecutor` adds `resources`, the exact types the executor reads from its `ResourceView`. The executor receives an `ExecutionContext` or a `DisruptedExecutionContext` and returns a `StepOutcome`. It owns the engine bookkeeping: a connection, a file handle, a query. The planner owns none of it. Splitting planning from execution is what lets a plan be inspected before any side effect occurs.

A `ResourceProvider` is an event subscriber. It adds resources to `PipelineStarted.resources` and disposes them on `PipelineFinished` or `PipelineHalted`. A provider that never saw a start does nothing. The runtime owns the providers; the toolchain has no `resources` field. This is a deliberate separation: a composition value describes the build, while a runtime owns the live capabilities of one run.

A `Runtime` opens the resources, schedules the plan and dispatches each step to the executor that claims its exact kind. `WorkflowRuntime` is the kernel's default implementation: transport-agnostic, resource-agnostic and free of graph vocabulary. A different runtime carries different scheduling, cancellation or isolation rules without changing the protocol set.

## Values that hold a composition together

The six protocols do not float free. They exchange a small set of supporting values, and those values explain why the composition is explicit.

`Namespace` is a protocol with one method, `values()`, returning the authoring objects a build may collect declarations from. `ReferenceResolver` resolves an authoring value to the `SymbolRef` it denotes, or to `None`. `RenderContext` is opaque: a language passes it to dependency renderers and does not inspect it. `SymbolContext` is a frozen value holding the symbols transcribed before the current declaration, dependencies first; `get_symbol` and `get_value` raise `KeyError` for an unknown reference. `PlanContext` is a frozen value holding runtime configuration keyed by component id plus a `shared` scratch mapping for one compile. `Resource` is the lifecycle protocol: `close() -> None`.

Two names need more care because they are easy to mistake for protocols.

`Toolchain` is a frozen composition value, not a protocol. It holds `languages`, `linker`, `runtime`, `planners` and `executors` and exposes the three verbs `build`, `compile` and `execute`. It is the object a caller constructs. A language, linker, planner or executor is a value placed inside it; a provider is placed in the runtime. Calling `Toolchain` a protocol suggests that another object could implement a toolchain while keeping the same members, which misses the point. The toolchain is the composition itself.

`SqlEmitter` is a neutral distribution service protocol, not a kernel protocol. It lives under `kg_build_system/distribution/service/internal/emission.py`. Core planners consume it and import no DuckDB module; the kernel never sees SQL or an engine object. A second storage engine supplies another emitter and an executor; the kernel protocol set does not change. The distinction matters for review: adding an engine is a distribution composition, while adding an emitter protocol to the kernel would be a model change.

The same care applies to providers. A provider is passed to the runtime, not to `Toolchain`. A toolchain with a `resources` field would make one run's live capabilities part of the build description, and the same plan could no longer be executed twice with different resources. The runtime owns that lifecycle because the lifecycle belongs to an execution, not to a plan.

## An extension is an ordinary object

There is no `Extension` class, no registry, no plugin entry point, no discovery by name, no schema version and no compatibility negotiation. An extension is an ordinary object passed explicitly to the composition that owns it. A language, linker, planner or executor goes to `Toolchain(...)` or `default_toolchain(...)`; a provider goes to the runtime.

This is a design choice with a visible cost and a visible benefit. The cost is that a project must write the composition down. The benefit is that a build reads as the list of objects the project actually supplies. A reader can see which language produces which declarations, which planner owns which component and which executor claims which instruction kind, without tracing a registration call or a naming convention.

Explicitness also makes replacement local. A project that wants another source planner passes one. A project that wants another core planner passes a planner that claims `core`, and `default_toolchain` does not add the four defaults. A project that wants another executor appends it to the executor list. The rest of the composition stays intact.

The kernel does not promise that every composition is a graph build. A custom language, linker, planner, executor and runtime can compile and execute without the graph distribution. A graph build, by contrast, cannot run on the kernel alone: nodes, edges, bindings and the blueprint are distribution concepts. Both statements are true because the kernel and the distribution answer different questions.

Project-local extension is expected before a kernel change. A project adds a value operation in `expression/`, a relation operation, source adapter or planner/executor module in `modules/`, and composes them in `manifest.py`. The kernel protocols are for a different toolchain or a different distribution. The exact project surfaces, the blueprint operation declarations and the current limits are in the [Extension reference](/appendix/reference/extension).

## The extension ladder

The ladder turns a capability question into an object question. Each rung names the smallest object that can carry the new behaviour and the cost of adding it.

| Question | Extend | Cost |
| --- | --- | --- |
| Does the source need new I/O or decoding? | A source planner and executor, or a module. | Planner, executor, exact kind and a contract test. |
| Is it a new declaration syntax or authoring value? | `Language`. | Seven methods, a renderer and a round-trip test. |
| Is it a new derived relation over existing records? | `Planner` and `StepExecutor` as a module. | Component identity, exact kind, plan and provenance tests. |
| Is it a new storage engine or query backend? | `SqlEmitter` and an executor. | Emitter, type mapping, executor and resource provider. |
| Is it a new lifecycle resource? | `ResourceProvider`. | Provider, exact resource type and a disposal test. |
| Is it a different scheduling or assembly rule? | `Linker` or `Runtime`. | A new model or state machine. |
| Does it change what a graph means? | A model change. | Developer review and a specification change. |

The first six rungs are composition. The seventh is not. A model change alters what the framework is allowed to mean, so it is proposed as an interface change before it is implemented and reviewed through the developer documentation. The ladder is therefore also a warning: a capability that seems to need a kernel change usually needs a distribution object instead, and a capability that genuinely changes graph meaning should not be smuggled in as a module.

The ladder changes the answer to "the framework cannot do X." If X is a new source format, the answer is a planner and an executor. If X is a new syntax, the answer is a language. If X is a new engine, the answer is an emitter and an executor. If X is a new lifecycle resource, the answer is a provider. Only when the protocol set cannot carry the concept is the kernel the right place to change.

There is a second class of answer, developed in Chapter 21: a model rule. A graph property is scalar, so a nested object is reified as nodes and edges. An edge is directed. An instruction kind is exact. These are not rungs on the ladder because no composition should carry them. A reviewer who treats a model rule as a missing extension asks for a second meaning of the graph, not for another implementation.

## A consensus module, composed

The consensus module sits on the third rung. It is a derived relation over existing records, so it is a planner and an executor. The planner states what to compute and which artifact it reads; the executor computes it and owns the instruction kind.

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

The planner claims `component_id="consensus"` and version `"1"`. It has no runtime fields because the threshold is in the instruction payload, not in runtime configuration. Its input is the pattern `core/graph/**`, declared under the executor's input name `records`; that pattern accepts node and edge artifacts from the core component. Its output is a `Publication`, so the assertion is both an output and a final workflow artifact. The instruction kind is the exact pair `("consensus", "default")`.

The executor claims that same exact kind and declares no resources. A disrupted context becomes `SKIPPED`, because a step whose upstream failed has nothing to vote on. Otherwise the executor collects the artifact values under `records`, calls `majority`, and returns one of three outcomes: an assertion under the declared output opening, `WARNING` for a tie, or `SUCCEEDED` with no artifact when there are no rows. `majority` is module-local and deliberately absent from the sketch; it is ordinary code that groups by `(subject, object, relation)` and returns an assertion only when the supporting count crosses the threshold.

Composition is one call. `default_toolchain` adds the generic DuckDB source planner unless a supplied planner claims `duckdb`, and the four core planners unless a supplied planner claims `core`. The consensus planner claims neither, so both defaults stay. The executor is appended to the default executor list, because a new kind needs a new claimant and the existing executors keep their own kinds.

```python
from kg_build_system import DEFAULT_TOOLCHAIN, default_toolchain

toolchain = default_toolchain(
    planners=(ConsensusPlanner(),),
    executors=(*DEFAULT_TOOLCHAIN.executors, ConsensusExecutor()),
)
```

A SQL-backed variant would claim `("consensus", "duckdb")`, take a `SqlEmitter` in its planner and declare the DuckDB resource type in its executor. That variant is a second module, not an edit to the core planners. It changes the engine boundary and the resource declaration, but not the graph model, the plan vocabulary or the kernel protocols.

The module is not shipped. The default distribution has no `ConsensusPlanner`, no `("consensus", "default")` kind and no voting code. The sketch is a composition a reader writes, and the rest of Part IV uses it as a test case: Chapter 19 asks why the shipped composition stops where it does, Chapter 20 asks what tests guard the module's interface, and Chapter 21 asks which kind of limit its absence represents.

## The contract tests belong to the module

A module is not finished when it returns an edge on one happy path. The planner and executor are an interface, and the interface is what the tests must pin. The consensus module needs tests for at least five claims.

- A supported object wins. When the supporting count crosses the threshold, the executor returns `SUCCEEDED` with one assertion under `consensus/assertion`.
- A tie returns `WARNING`. The step does not invent an assertion and does not fail the pipeline.
- Provenance survives. Every assertion carries the sources that supported it, so a consumer can say why the edge exists.
- The resource declaration is exact. A SQL variant asks for the DuckDB type and receives it; asking for an undeclared type raises `KeyError`.
- The kind is unique. Two executors claiming `("consensus", "default")` are refused before any step runs, and a plan with that kind and no executor is refused as well.

These are contract tests because each names a refusal or a guarantee at the module boundary, not an internal branch. They do not prove that the majority rule is the right rule for the domain. They prove that the module honours the kernel vocabulary it claims to implement: one component, one exact kind, one declared resource set, one outcome per step.

A green module therefore says something narrow and useful: the composition loads, the plan assembles, the executor is dispatched and the declared outputs are published. The design question remains separate. A reviewer still asks whether a vote belongs in a planner at all, whether the threshold is configuration or payload, and whether a tie should warn or fail. Those answers belong to the module's author and its consumers, not to the kernel.

## Next

[19. The default distribution](/book/part-4/02-the-default-distribution) — read the shipped graph system as one composition of these protocols.
