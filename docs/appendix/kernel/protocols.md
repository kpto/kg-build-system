---
title: Kernel protocols
summary: The six kernel protocols, their supporting composition values and the cost of each extension.
section: kernel
perspective: developer
order: 10
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/kernel/service/public/pipeline.py
  - kg_build_system/kernel/model/public/language.py
  - kg_build_system/kernel/model/public/runtime.py
  - kg_build_system/distribution/service/internal/emission.py
  - kg_build_system/api.py
---

## Interface

The kernel exposes six composition protocols and a set of supporting interface values. The protocols and values named here are re-exported from `kg_build_system.kernel`; an implementation is an ordinary object, checked structurally, passed explicitly to a `Toolchain`.

| Protocol | Contract | Default composition |
| --- | --- | --- |
| `Language` | Discover, key, transcribe and render one declaration syntax. | One per distribution language. |
| `Linker[ModelT]` | `link(languages, namespace) -> ModelT`; owns roots, order, closure and assembly. | `BlueprintLinker` for the graph model. |
| `Planner[ModelT]` | `component_id`, `version`, `runtime_fields`, `plan(model, context)`. | Four core planners, `DuckDbSourcePlanner` and feature-module planners. |
| `StepExecutor` | Exact `kinds`, declared `resources`, `execute(context, instruction)`. | Module executors such as file and meta-graph writers. |
| `ResourceProvider` | `on_event(event)`; opens on start, disposes on finish or halt. | DuckDB and module providers. |
| `Runtime` | `execute(plan, executors, *, configuration, listeners=())`. | `WorkflowRuntime`. |

### Language

A language owns one part of a build. The linker calls `transcribe` once per reachable declaration; a language may batch internally, but the batch path is not a protocol.

```python
class Language(Protocol):
    name: str
    def discover_declarations(
        self, namespace: Namespace,
    ) -> Iterable[Declaration]: ...
    def compute_key(self, declaration: Declaration) -> Key: ...
    def get_kind(self, declaration: Declaration) -> str: ...
    def get_identity(self, value: Any) -> SymbolRef | None: ...
    def get_references(
        self, value: Any, resolver: ReferenceResolver,
    ) -> tuple[SymbolRef, ...]: ...
    def transcribe(
        self, declaration: Declaration, context: SymbolContext,
    ) -> Symbol: ...
    def render(self, symbol: Symbol, context: RenderContext) -> SourceFragment: ...
```

`name` is written into every `SymbolRef` the language produces. `get_references` returns direct edges only; the linker walks the closure. `render` is the reverse direction and returns a `SourceFragment`.

### Linker

The linker owns what the kernel cannot: language order, roots, the reference walk and model assembly. The kernel never inspects the returned `ModelT`.

```python
class Linker(Protocol[LinkerModelT]):
    def link(
        self, languages: Sequence[Language], namespace: Namespace,
    ) -> LinkerModelT: ...
```

### Planner

A planner emits steps; it does not execute them. Planners that share one `component_id` must agree on `version` and `runtime_fields`; the component is published once and every step in the group takes its id.

```python
class Planner(Protocol[PlannerModelT]):
    component_id: str
    version: str
    runtime_fields: tuple[RuntimeField, ...]
    def plan(
        self, model: PlannerModelT, context: PlanContext,
    ) -> Sequence[Step]: ...
```

### StepExecutor

An executor executes one exact instruction kind and declares the resource types it reads. `StepExecutor` is `Executor` plus `resources`; the executor owns engine bookkeeping, the planner owns none.

```python
class Executor(Protocol):
    kinds: tuple[InstructionKind, ...]
    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome: ...

class StepExecutor(Executor, Protocol):
    resources: tuple[type, ...] = ()
```

### ResourceProvider

A provider is an event subscriber. It adds resources to `PipelineStarted.resources` and disposes them on `PipelineFinished` or `PipelineHalted`; a provider that never saw `PipelineStarted` does nothing.

```python
class ResourceProvider(Protocol):
    def on_event(self, event: PipelineEvent) -> None: ...
```

### Runtime

The runtime opens resources, schedules a plan and dispatches each step to the executor that claims its exact kind. `executors` is an exact-kind map built by the toolchain before the run.

```python
class Runtime(Protocol):
    def execute(
        self,
        plan: WorkflowPlan,
        executors: Mapping[InstructionKind, StepExecutor],
        *,
        configuration: RuntimeConfiguration,
        listeners: Sequence[Listener] = (),
    ) -> WorkflowReport: ...
```

### Supporting interface values

| Name | Kind | Contract |
| --- | --- | --- |
| `Namespace` | protocol | `values() -> Sequence[object]`; the authoring values a build may collect declarations from. |
| `ReferenceResolver` | protocol | `get_identity(value) -> SymbolRef \| None`; resolves an authoring value to the symbol it denotes. |
| `RenderContext` | protocol | Opaque; a language passes it to dependency renderers and does not inspect it. |
| `SymbolContext` | frozen value | Symbols transcribed before the current declaration, dependencies first; `get_symbol` and `get_value` raise `KeyError` for an unknown reference. |
| `PlanContext` | frozen value | `runtime_configuration` keyed by component id, plus `shared`, a per-compile scratch mapping. |
| `Resource` | protocol | `close() -> None`; a live capability with a lifecycle. |
| `Toolchain` | frozen composition value | `languages`, `linker`, `runtime`, `planners` and `executors` in one value; `build`, `compile` and `execute`. |
| `WorkflowRuntime` | default runtime class | The kernel's `Runtime` implementation; transport-agnostic and resource-agnostic. |

`Toolchain` is a composition value, not a protocol: it is the object a caller constructs, and a language, linker, planner or executor is a value placed in it. A provider is placed in the runtime. `default_toolchain` in `kg_build_system.api` is one composition of that value for the graph distribution; it adds the generic source planner unless a supplied planner claims `duckdb`, and the four core planners unless one claims `core`.

`SqlEmitter` is not a kernel protocol. It is a neutral distribution service protocol under `kg_build_system/distribution/service/internal` (`emission.py`). Core planners consume it and import no DuckDB module; another storage engine supplies another emitter and executor. The kernel never sees SQL or an engine object.

### Instruction kinds and resources

- `InstructionKind(operation, engine)` is an exact two-segment role type: `("sql", "duckdb")`, `("python", "cpython")`. Dispatch compares it exactly; there is no prefix matching, wildcard kind or family dispatch.
- `StepExecutor.resources` names exact types. The runtime validates each declaration against the run's `ResourceRegistry` and builds a `ResourceView` containing only those types. Asking for an undeclared type, even one opened for another executor, raises `KeyError`.
- A duplicate resource type from two providers, a missing executor kind or a duplicate kind is refused before any step runs.

### Extension ladder

| Question | If yes, extend | Cost |
| --- | --- | --- |
| Does the source need new I/O or decoding? | A source planner and executor, or a module. | Planner, executor, exact kind and a contract test. |
| Is it a new declaration syntax or authoring value? | `Language`. | Seven methods, a renderer and a round-trip test. |
| Is it a new derived relation over existing records? | `Planner` and `StepExecutor` as a module. | Component identity, exact kind, plan and provenance tests. |
| Is it a new storage engine or query backend? | `SqlEmitter` and an executor. | Emitter, type mapping, executor and resource provider. |
| Is it a new lifecycle resource? | `ResourceProvider`. | Provider, exact resource type and a disposal test. |
| Is it a different scheduling or assembly rule? | `Linker` or `Runtime`. | A new model or state machine. |
| Does it change what a graph means? | A model change. | Developer review and a specification change. |

The full task guide, including a worked semantic module, is [Extend the toolchain](/book/part-4/01-the-kernel-and-extension#the-extension-ladder).

## Rules

- One object owns one job. A planner emits steps; an executor executes one exact kind; a provider owns a lifecycle; the runtime schedules and dispatches.
- A protocol is implemented structurally. There is no base class to inherit, no registration call and no discovery by name.
- A language, linker, planner or executor is a value passed to `Toolchain` or `default_toolchain`; a provider is passed to the runtime. There is no extension class, extension registry, plugin entry point, schema version or compatibility promise.
- A custom language, linker, planner, executor and runtime compile and execute without the default distribution.
- The runtime owns providers; `Toolchain` has no `resources` field.
- A listener observes events and cannot change scheduling, resources or the report. A listener error is a pipeline failure.
- Instruction kinds and resource types are exact identities. A new executor claims a new exact kind; it does not extend an existing family.
- A new engine implements the neutral distribution emitter and is composed with its executor; the kernel protocol set does not change.

## Limits

- The kernel does not standardise acquisition, identifier translation, orthology, storage engine, scheduling policy, licence enforcement or incremental strategy. Each belongs to a composition.
- `Language` has no batch protocol. The linker calls `transcribe` once per reachable declaration.
- The default runtime has no per-step timeout, retry, cancellation or memory quota. A different `Runtime` carries them.
- Resource lookup is by exact type. A subclass does not satisfy a declared base type.
- Protocol conformance is checked by use. There is no runtime conformance registry.
- `SqlEmitter` sits below the kernel, in the distribution. A custom distribution supplies its own neutral emission boundary.

## Next

[Kernel model](/appendix/kernel/model) — the canonical types and workflow values the protocols exchange.
