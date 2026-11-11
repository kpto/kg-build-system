---
title: System design
summary: The kernel protocols, linker closure, blueprint, plan, runtime, zones and dependency spine.
section: developer
perspective: developer
order: 30
status: normative
verified: 2026-11-10
sources:
  - docs/developer/system-design.md
  - ARCHITECTURE.md
  - kg_build_system/kernel/service/public/pipeline.py
  - kg_build_system/kernel/model/public/events.py
  - kg_build_system/api.py
---

## Interface

The framework has a domain-agnostic kernel and one distribution. The kernel is a toolchain: it links language declarations into an opaque model, compiles that model into a workflow plan and executes the plan through exact instruction-kind executors. The distribution supplies the graph domain: the blueprint, its planning and execution modules, and their resources.

The canonical extension surface is [/kernel/protocols](/kernel/protocols).

The kernel model is opaque `ModelT`; it never reads an instruction payload or artifact value.

### Package tree

```text
kg_build_system/
  kernel/
    model/public/{key,language,symbol,workflow,runtime,events}.py, types/
    model/internal/{json.py,types/dto.py}, model/_private/types/
    service/public/{pipeline,runtime}.py
    service/internal/{pipeline,types/functions,workflow_codec}.py
    service/_private/{pipeline,assembly,runtime,workflow_codec,report_codec}.py
  distribution/
    model/public/{refs,artifacts,runtime,paths}.py
    languages/{annotations,expressions,semantics,graph,asset,data,topology,binding}/
    interpreter/
      model/public/graph_blueprint.py
      service/public/create.py
      service/internal/adapters/kernel_linker.py
      service/_private/{create,link,assembly,validation,codec,source,discovery}.py
    modules/
      core/{row_source,projection,binding,records}/service/public/planner.py
      core/service/_private/planning/
      {deduplication,merging,conflict_validation,file,meta_graph,neo4j,duckdb,python,runtime}/
    service/{public,internal,_private}/
    implementations.py
  generation/code_generation/
  frontend/monitor.py
  __init__.py
  api.py
  cli/
```

A **module** is a feature package under `distribution/modules/` grouping one feature's planners, executors, resources and configuration; it is not a protocol or registry entry.

### Kernel interface

| Name | Kind | Contract |
| --- | --- | --- |
| `Namespace` | supporting protocol | `values() -> Sequence[object]`; the authoring objects a build may collect declarations from. |
| `ReferenceResolver` | supporting protocol | `get_identity(value: Any) -> SymbolRef \| None`; resolves an authoring value to the symbol it denotes. |
| `RenderContext` | supporting protocol | Opaque render context; a language passes it to dependency renderers and does not inspect it. |
| `Language` | protocol | `discover_declarations`, `compute_key`, `get_kind`, `get_identity`, `get_references`, `transcribe` and `render`; the full signature is below. |
| `Linker` | protocol | `link(languages, namespace) -> LinkerModelT`; owns roots, language order, the closure and model assembly. |
| `Planner` | protocol | `component_id`, `version`, `runtime_fields` and `plan(model, context) -> Sequence[Step]`. |
| `Resource` | protocol | `close() -> None`; a live capability with a lifecycle. |
| `ResourceProvider` | protocol | `on_event(event: PipelineEvent) -> None`; publishes resources on `PipelineStarted` and disposes them on finish or halt. |
| `Executor` | protocol | `kinds: tuple[InstructionKind, ...]` and `execute(context, instruction) -> StepOutcome`. |
| `StepExecutor` | protocol | `Executor` plus `resources: tuple[type, ...] = ()`; the exact resource types it reads. |
| `Runtime` | protocol | `execute(plan, executors, *, configuration, listeners=()) -> WorkflowReport`. |
| `Toolchain` | composition value | Frozen composition of languages, linker, runtime, planners and executors; not a protocol. |

`SqlEmitter` is a neutral distribution service protocol under `distribution/service/internal`, not a kernel protocol. Core planners consume it; the kernel never imports it.

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

class Linker(Protocol[LinkerModelT]):
    def link(
        self, languages: Sequence[Language], namespace: Namespace,
    ) -> LinkerModelT: ...

@dataclass(frozen=True, slots=True)
class PlanContext:
    runtime_configuration: Mapping[str, Mapping[str, Any]] = ...
    shared: MutableMapping[str, Any] = ...

class Planner(Protocol[PlannerModelT]):
    component_id: str
    version: str
    runtime_fields: tuple[RuntimeField, ...]
    def plan(
        self, model: PlannerModelT, context: PlanContext,
    ) -> Sequence[Step]: ...

class Executor(Protocol):
    kinds: tuple[InstructionKind, ...]
    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome: ...

class StepExecutor(Executor, Protocol):
    resources: tuple[type, ...] = ()

class Resource(Protocol):
    def close(self) -> None: ...

class ResourceProvider(Protocol):
    def on_event(self, event: PipelineEvent) -> None: ...

class Runtime(Protocol):
    def execute(
        self,
        plan: WorkflowPlan,
        executors: Mapping[InstructionKind, StepExecutor],
        *,
        configuration: RuntimeConfiguration,
        listeners: Sequence[Listener] = (),
    ) -> WorkflowReport: ...

@dataclass(frozen=True, slots=True)
class Toolchain(Generic[ModelT]):
    languages: Sequence[Language]
    linker: Linker[ModelT]
    runtime: Runtime | None = None
    planners: Sequence[Planner[ModelT]] = ()
    executors: Sequence[StepExecutor] = ()
    def build(self, namespace: Namespace) -> ModelT: ...
    def compile(self, model: ModelT) -> WorkflowPlan: ...
    def execute(
        self,
        plan: WorkflowPlan,
        *,
        output_directory: Path,
        configuration: RuntimeConfiguration | None = None,
        listeners: Sequence[Listener] = (),
    ) -> WorkflowReport: ...
```

### Capability ledger

| Need | Default distribution | Extension point | Cost |
| --- | --- | --- | --- |
| Majority vote over assertions | Not in the row algebra | `Planner` + `StepExecutor` | Module + tests |
| Semicolon-delimited source lists | Not in the row algebra | Source planner or executor, or a language operation | Decoding |
| ID translation / orthology | Not built in | A module or graph facts | Mapping input + module |
| Another SQL engine | DuckDB only | `SqlEmitter` + executor | Adapter |
| Another source format | parquet, json, csv | Another planner | Module |
| A new declaration syntax | The graph languages | `Language` | Language work |
| A new lifecycle resource | The runtime providers | `ResourceProvider` | Provider |
| Incremental update | Whole-plan rebuild | A runtime or planner extension | Runtime work |

### What the framework does not decide

The kernel defines protocols; a composition chooses acquisition, identifier translation, orthology, the storage engine, scheduling policy, licence enforcement and incremental strategy. Acquisition is a `ResourceProvider` plus an executor, or a frontend script kept outside for reproducibility. Identifier translation and orthology are modules or graph facts. The storage engine is a `SqlEmitter` plus an executor; scheduling policy is a `Runtime` or `Linker`; licence enforcement is a filter module over `Resource` facts; incremental strategy is a runtime or planner extension. None is a kernel decision.

### Declarations, symbols and references

A **declaration** is an authoring object a language offers. It carries only the value the language recognised and has no key. A **key** is a tuple of string segments chosen by the language. A **symbol** is a linked unit with a language-unique key, kind, value and references. A **reference** is a `SymbolRef(language, key)`; there is no bare cross-symbol string.

`Symbol` carries its key; `Declaration` does not. `Language.compute_key` derives the key, and `get_kind` states the symbol kind. `SymbolContext` exposes the symbols transcribed before the current declaration, dependencies first. Some languages publish child declarations: fields and properties keyed by owner.

## Rules

### Three verbs

| Verb | Input | Output | Contract |
| --- | --- | --- | --- |
| `build` | `Namespace` through `Linker` | opaque model | Discovers, keys, selects roots, resolves the closure, transcribes reachable declarations and assembles. It does not plan or execute. |
| `compile` | linked model | `WorkflowPlan` | Calls planners in order, groups by `component_id`, publishes one `Component` per group, assigns ids, assembles wiring. It does not build or read data. |
| `execute` | plan and output directory | `WorkflowReport` | Builds the exact-kind map, refuses a missing or duplicate kind before any step, opens resources and dispatches. |

`compile` does not call `build`; the composition root `api.compile` may create a blueprint first, but the kernel method does not. A serialised plan is self-contained because `api.compile` encodes the source blueprint document under `plan.provenance["blueprint"]`. [Plan specification](/spec/plan) states the assembly contract.

### Linker closure

The linker owns what the kernel cannot: roots, language order, the reference walk and model assembly. `BlueprintLinker` indexes languages in the fixed order `expressions`, `asset`, `data`, `topology`, `binding`, `graph`; the first five are required and `graph` is optional.

The linker indexes every declaration before roots apply, refuses a duplicate language name or key, selects roots by language, and walks the closure from authoring declaration values through `get_references`. Only reachable declarations become symbols; `transcribe` runs once per reachable declaration, dependencies first, and its key must equal the indexed key. An unknown reference or a reference cycle is refused. `get_identity` lets the resolver name the symbol an authoring value denotes. The symbol graph is assembled dependencies-first. [Linking specification](/spec/linking) owns the per-requirement contract.

### Blueprint and symbol graph

A blueprint is the semantic model of the graph, not a symbol table:

```python
GraphBlueprint(
    graph=GraphPartDTO(nodes=..., edges=...),
    data=DataPartDTO(structs=..., relations=..., projections=...),
    assets=AssetPartDTO(assets=...),
    bindings=...,
    graph_declaration=... | None,
)
```

The blueprint names nodes, edges, relations, fields, properties, assets and operations as semantic roles. A relation names its asset with an `AssetRef`; it carries no Python path, declaration object or symbol-table entry. The symbol graph is the linker's working representation: it may carry keys, kinds and references, and it does not appear in the delivered artifact.

| Role type | Names |
| --- | --- |
| `NodeRef` | one topology node |
| `EdgeRef` | one topology edge |
| `RelationRef` | one relation or projection |
| `FieldRef` | one declared field |
| `PropertyRef` | one graph property |
| `AssetRef` | one logical asset |
| `OperationRef` | one operation specification |

Each wraps a `SymbolRef` and exposes `.symbol`, `.key`, `.language` and `.name`; its document is `[language, role, *key segments]`. A language DTO knows only the DTOs of the languages it depends on; the interpreter assembles the language DTOs into one blueprint. The blueprint codec composes the language codecs, and the source service delegates to each language's renderer. [Identity specification](/spec/identity) and [document shapes](/reference/documents) own the exact forms.

### Plan, planners, executors and resources

`compile` calls every planner with the same linked model and one `PlanContext`. Planners in one `component_id` group must agree on `version` and `runtime_fields`; the component is published once and every step the group emits is assigned its id. Assembly refuses a duplicate `StepId(component, name)` and a wiring with no producer or with a cycle. `PlanContext.shared` is per-compile scratch space; the four core planners share `"core.plan"`.

| Planner | Component | Responsibility |
| --- | --- | --- |
| `RowSourcePlanner` | `core` | row-source steps |
| `ProjectionPlanner` | `core` | projection steps |
| `BindingPlanner` | `core` | binding steps |
| `RecordsPlanner` | `core` | aggregate record steps |
| `DuckDbSourcePlanner` | `duckdb` | one `source.<relation>` step per relation |

All four core planners report `component_id="core"` and share one `CorePlan`. `core_planners(engine=...)` returns them with the injected neutral `SqlEmitter`; core imports the relation plan and the protocol, never the DuckDB module. The source planner emits one step per relation from its asset layout.

A planner emits steps; an executor executes one exact instruction kind; neither does the other's job. `InstructionKind(operation, engine)` is a two-segment role type with no prefix matching; a `Step` owns exactly one `Instruction`. Planning and side effect are two objects.

The runtime owns the providers and `Toolchain` has no `resources` field. Every run creates a fresh `EventBus` and `ResourceRegistry`; providers publish on `PipelineStarted` and dispose on `PipelineFinished` or `PipelineHalted`. The runtime validates each executor declaration against the registry, refuses a missing or duplicate exact type, and builds one `ResourceView` containing only that executor's declared `resources`. Asking for an undeclared type raises `KeyError`.

### Runtime events

The event type is `PipelineStarted | StepStarted | StepFinished | StepLogged | PipelineFinished | PipelineHalted`, delivered by `EventBus` to providers and frontend listeners. Lifecycle order is `PipelineStarted`, one `StepStarted` and `StepFinished` pair per step with any `StepLogged` between them, then `PipelineFinished` on success or `PipelineHalted` on failure. `PipelineHalted` is emitted before the original error is re-raised.

The scheduler classifies each upstream result as continuable (`SUCCEEDED`, `WARNING`) or disrupting (`FAILED`, `SKIPPED`). A normal step receives an `ExecutionContext`; a disrupted step receives a `DisruptedExecutionContext` and normally returns `SKIPPED`. A listener error propagates through the bus and is treated as a pipeline failure. [Execution specification](/spec/execution) owns the report and lifecycle requirements.

### Zones and import matrix

Every leaf uses the zones it needs; an empty zone is deleted.

| Zone | Reader | May be imported by | Holds |
| --- | --- | --- | --- |
| `pkg` | graph author | any package | facade over `model.public` and `service.public` |
| `pkg.model.public` | graph author | any package, for authoring names and frozen type vocabulary | authoring models, returned values, public DTOs |
| `pkg.model.internal` | framework code | any package, for cross-package data | `dto/` and `model/` data |
| `pkg.model._private` | its own package | no other package | private plans, render models, SQL types |
| `pkg.service.public` | graph author | any package, for service interfaces | authoring methods and thin wrappers |
| `pkg.service.internal` | framework code | any package, for service interfaces | codec and assembly wrappers, adapters |
| `pkg.service._private` | its own package | no other package | codecs, transcription, rendering, validation, assembly, planning, engines, runtime |

| Source | May import | Must not import |
| --- | --- | --- |
| `model.public` | model data | any service or `_private` |
| `model.internal` | model data | any service or `_private` |
| `model._private` | `model.public`, `model.internal` | service |
| `service.public` | `model.public`, `service.internal` | `_private` |
| `service.internal` | model data; `service._private` with function-local imports | `service.public` |
| `service._private` | model data and other private service code | `service.public` |

Another package imports `public` or `internal`, never `_private`. A protocol implementation is a separate file under `service/internal/adapters/<protocol>.py`; it names the protocol and delegates to `service._private`. `BlueprintLinker` is implemented this way for the kernel `Linker` protocol.

### Dependency spine

| Package | May import |
| --- | --- |
| `kernel` | no framework package |
| `languages/annotations` | `kernel` |
| `languages/expressions` | `kernel` |
| `languages/semantics` | `kernel` |
| `languages/graph` | `kernel`, semantics |
| `languages/asset` | `kernel`, annotations, semantics |
| `languages/data` | `kernel`, annotations, expressions, asset, semantics |
| `languages/topology` | `kernel`, annotations, expressions, semantics |
| `languages/binding` | `kernel`, annotations, data, topology, semantics |
| `interpreter` | `kernel`, every graph language, semantics |
| `modules/<name>` | `kernel`, `interpreter` where it reads a blueprint, languages, `distribution.model`, `distribution.service`; core uses the neutral relation plan and `SqlEmitter` protocol, not the DuckDB module |
| `implementations.py` | `kernel`, interpreter, languages |
| `generation/code_generation` | `kernel`, `languages/asset`; observation is read-only |
| `api.py` | `kernel`, distribution |
| `cli` | generation, `api.py` |

Two rules apply to every row: the kernel imports no graph, data, topology, binding, SQL, DuckDB, Python or generation package; no package imports another package's private zones. The spine is a tree for reading, not a complete graph, and the dependency tests enforce the exact edge set. A new edge is a model decision proposed with its reason.

### Generation

`generation/code_generation/` is the edit-time lane. It observes a source, runs a provider and renders declarations. `@asset_contract(AssetContractOptions(...))` is an inert decorator on an `Asset` subclass and is outside `AssetOptions` and the blueprint.

Generation and the toolchain are separate lanes. `build` imports the resulting declarations and never invokes generation; `compile` and `execute` never invoke generation. Generated and handwritten declarations enter the same language, blueprint, plan and execution path; there is no generation-specific path. Observation is provenance: a generated source-backed field renders `Field[T]`; observed nullability changes the manifest, statistics and notes, not the annotation. Nullability that belongs to the value, such as an array item, stays in the value type.

## Limits

- A toolchain is the composition unit: languages, planners and executors are explicit values, and providers are owned by the runtime.
- `SqlEmitter` is a distribution-neutral service protocol, not a kernel protocol. DuckDB is the default emitter; `DuckDbSqlEmitter` implements that protocol, and another engine supplies another emitter and executor. [Extend the toolchain](/operate/extend) names the composition.
- A Python instruction is a reference: `("python", "cpython")` carries `{module, qualname}`, not a live callable.
- Public `GraphBlueprint` fields reference internal language DTOs that are not exported public names.
- A repeated struct graph name takes its qualified Python name as an extra key segment.
- A module contributes an ordinary relation-producing planner; `DuckDbSourcePlanner` resolves parquet, json and csv. No adapter registry is needed.
- [Limits](/review/limits) records the consumer-facing boundary and [Contracts](/review/contracts) the invariants that guard it.

## Next

[Plan specification](/spec/plan) — the plan, component and assembly contract in requirement form.
