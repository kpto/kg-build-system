# System design

The framework has a domain-agnostic **kernel** and one **distribution**. The
kernel is a toolchain: it links language declarations into an opaque model,
compiles that model into a workflow plan and executes the plan through exact
instruction-kind executors. The distribution supplies the graph domain: the
blueprint, the modules that plan and execute it, and the resources those
executors use.

The kernel vocabulary is toolchain vocabulary:

| Kernel name | Meaning |
| --- | --- |
| `Language` | frontend: discovers declarations, keys them, transcribes symbols and renders source |
| `Declaration` | one authoring object a language offers; it has no key |
| `Symbol` | one linked unit: key, kind, value and references |
| `SymbolRef` | a typed reference to a symbol by language and key |
| `Key` | a hierarchical symbol identifier made of string segments |
| `Linker` | root policy, reference closure, symbol order and model assembly |
| `Planner` | emits workflow `Step`s for one component |
| `WorkflowPlan` | one assembled instruction DAG |
| `Step` | one scheduled instruction with typed inputs and outputs |
| `StepExecutor` | executes one exact instruction kind |
| `Runtime` | emits pipeline events, schedules steps and dispatches instructions |
| `Resource` | a live capability with a lifecycle, owned by a provider |
| `ResourceProvider` | subscribes to pipeline events and owns the resources it publishes |
| `ResourceRegistry` | the live resources one run publishes by exact type |
| `PipelineEvent` | one lifecycle, step or log event emitted by a run |
| `EventBus` | delivers every event to the providers and listeners of one run |
| `ResourceView` | the exact resources one executor declared |
| `Toolchain` | languages + linker + planners + executors + runtime |

The distribution vocabulary is domain vocabulary: graph, blueprint, node, edge,
binding, projection, table, core, meta-graph, Neo4j, DuckDB and Python.

## The package tree

```text
kg_build_system/
  kernel/
    model/
      public/
        key.py           Key
        language.py      Declaration, Key, Language, Namespace,
                         ReferenceResolver, RenderContext, SourceFragment,
                         Symbol, SymbolContext, SymbolRef
        symbol.py        Declaration, Symbol, SymbolContext, SymbolRef
        workflow.py      OpeningDirection, StepId, OpeningId, ArtifactType,
                         ArtifactPattern, InstructionKind, Instruction,
                         Input, Output, Publication, Step, Connection,
                         Component, RuntimeField, WorkflowPlan
        runtime.py       StepStatus, Failure, Artifact, StepOutcome,
                         ContinuableInput, DisruptingInput, PublishedArtifact,
                         ResourceView, WorkflowReport, ExecutionContext,
                         DisruptedExecutionContext, RuntimeConfiguration
        events.py        ResourceRegistry, PipelineEvent, EventBus, Listener,
                         PipelineStarted, StepStarted, StepFinished,
                         StepLogged, PipelineFinished, PipelineHalted
        types/           canonical types
      internal/
        json.py
        types/dto.py
      _private/
        types/
    service/
      public/
        pipeline.py      Linker, Planner, StepExecutor, Runtime, Resource,
                         ResourceProvider, Toolchain, PlanContext
        runtime.py       WorkflowRuntime
      internal/
        pipeline.py      thin wrappers only
        types/functions.py
        workflow_codec.py
      _private/
        pipeline.py      build -> compile -> execute
        assembly.py      step and connection assembly
        runtime.py       event dispatch, scheduler and step lifecycle
        workflow_codec.py
        report_codec.py  WorkflowReport document
  distribution/
    model/
      public/
        refs.py          NodeRef, EdgeRef, RelationRef, FieldRef, PropertyRef,
                         AssetRef, OperationRef, Ref
        artifacts.py     CoreArtifactTypes, graph-record vocabulary
        runtime.py       BuildRuntime
        paths.py         relative-path rule
      _private/
        refs.py          reference document codec
    languages/
      annotations/
      expressions/
      asset/
      data/
      topology/
      binding/
    interpreter/
      model/public/graph_blueprint.py
      service/public/create.py
      service/internal/adapters/kernel_linker.py
      service/_private/{create,link,assembly,validation,codec,source,discovery}.py
    modules/
      core/
        row_source/
          service/public/planner.py   RowSourcePlanner
          service/_private/           row-source steps and SQL
        projection/
          service/public/planner.py   ProjectionPlanner
          service/_private/           projection steps and SQL
        binding/
          service/public/planner.py   BindingPlanner
          service/_private/           binding steps, SQL and guards
        records/
          service/public/planner.py   RecordsPlanner
          service/_private/           aggregation steps
        service/
          public/{__init__,functions}.py  core_planners facade
          _private/planning/          shared CorePlan, relations and emission
      deduplication/
      merging/
      conflict_validation/
      file/
      meta_graph/
      neo4j/
      duckdb/
      python/
      runtime/
    service/             the distribution leaf's service zone
      public/create.py
      internal/{emission,execution,relations,rendering}.py
      _private/{execution,rendering}.py
    implementations.py   language and linker implementations
  generation/
    code_generation/
  frontend/
    monitor.py           Monitor, NullMonitor, ConsoleMonitor, resolve_monitor
  __init__.py            top-level lazy export table; literal __all__
  api.py                 default_toolchain, DEFAULT_TOOLCHAIN,
                         create_blueprint, compile, execute
  cli/
```

A **module** is a feature package under `distribution/modules/`. It is not a
protocol and not a registry entry. It groups one feature's planners, executors,
resources and configuration. Core is a module with four planners; DuckDB is a
module with a source planner, an executor, a resource provider, a service and an
SQL emitter.

## Module layout

Every leaf uses the zones it needs:

```text
pkg/
  __init__.py          docstring, imports and __all__ only
  model/
    public/            authoring models, returned values, public DTOs
    internal/          cross-package data: dto/, model/
    _private/          private plans, render models, SQL types
  service/
    public/            author-facing methods; thin wrappers
    internal/          service interfaces, codec/assembly wrappers, adapters/
    _private/          codecs, transcription, rendering, validation, assembly,
                       planning, engines, runtime
```

- A leaf contains only the zones it uses. An empty zone is deleted; it is not a
  marker.
- `__init__.py` is a facade: a docstring, imports, a literal `__all__` and
  import/re-export machinery (`__getattr__`, `__dir__`, a lazy group table).
  It contains no business logic: no service, planner, codec, validation,
  feature registry or default instance.
- The package root keeps the lazy export table, `__getattr__`, `__dir__` and a
  literal `__all__` in `kg_build_system/__init__.py`. The literal export list
  and the lazy group table are checked for parity by `tests/test_facades.py`.
- `tests/test_facades.py` enforces the facade shape, and the relaxed layout test
  enforces that an existing zone is not empty and a facade imports an existing
  public zone.
- `distribution/modules/core` is the parent of the four core feature planners:
  `row_source`, `projection`, `binding` and `records`. Each feature is a layout
  leaf whose definition site is `service/public/planner.py` and whose
  implementation is under `service/_private/`. The feature leaves are grouped
  under the core module for private-import checks, so private imports stay
  inside `core`. The shared `CorePlan` and emission helpers remain in
  `core/service/_private/planning/`; `core/__init__.py` and
  `core/service/public/functions.py` re-export the planners from the feature
  public sites.

## The three verbs

`kg_build_system.kernel.service.public.pipeline.Toolchain` is the kernel's
composition surface. It has three verbs and they do not overlap.

### `build(namespace) -> ModelT`

1. Hand the language sequence and the namespace to `linker.link`.
2. Let the linker discover each language's declarations and compute a key with
   `language.compute_key`.
3. Let the linker select roots, resolve the reference closure from the authoring
   declaration values with `language.get_references`, order the reachable
   declarations and transcribe each one with `language.transcribe`.
4. Refuse a duplicate language name, a duplicate declaration key, an unknown
   reference or a reference cycle. Only reachable declarations become symbols.
5. Order symbols dependencies-first and assemble the opaque model.

`build` is the only verb that reads declarations. It does not plan or execute.
The kernel does not order languages itself: ordering is part of the linker's
root and closure policy.

### `compile(model) -> WorkflowPlan`

1. Call every planner in order with the same linked model and one
   `PlanContext`.
2. Group planners by `component_id`. Planners in one group must agree on
   `version` and `runtime_fields`.
3. Publish one `Component` per group, assign its `component_id` to every step
   the group produced, and refuse a duplicate `StepId(component, name)`.
   `compile_model` does not run its own duplicate check; assembly resolves empty
   names first and is the single authority.
4. Assemble open inputs to outputs, publications to the report, and return one
   `WorkflowPlan`. A wiring with no producer or with a cycle is refused.

`compile` does not call `build` and does not read data. The composition root
(`api.compile`) may call `create_blueprint` and then `compile`; the kernel
method never does.

### `execute(plan, *, output_directory, configuration=None, listeners=()) -> WorkflowReport`

1. Build an exact-kind map from every executor's `kinds`. A duplicate kind
   raises `ValueError`.
2. Refuse an instruction kind in the plan that has no executor, before any step
   runs.
3. Build a `RuntimeConfiguration` when none is supplied.
4. Call `runtime.execute(plan, executors, configuration=..., listeners=...)`.
5. The runtime creates a fresh `EventBus` and `ResourceRegistry`, subscribes the
   providers and the frontend listeners, emits `PipelineStarted` and reads the
   resources the providers published. It validates every executor declaration,
   builds one view per executor, emits the step and log events and finally
   emits `PipelineFinished` or `PipelineHalted`.

The scheduler classifies each upstream result as continuable (`SUCCEEDED`,
`WARNING`) or disrupting (`FAILED`, `SKIPPED`). A normal step receives an
`ExecutionContext`; a disrupted step receives a `DisruptedExecutionContext` and
normally returns a `SKIPPED` outcome. An executor owns any engine bookkeeping.

## Kernel interfaces

```python
# kernel/model/public/key.py
@dataclass(frozen=True, slots=True)
class Key:
    segments: tuple[str, ...]
    def child(self, *segments: str) -> Key: ...
    def starts_with(self, other: Key) -> bool: ...
    def matches(self, pattern: Key) -> bool: ...
    def to_document(self) -> list[str]: ...
```

```python
# kernel/model/public/symbol.py
@dataclass(frozen=True, slots=True)
class SymbolRef:
    language: str
    key: Key

@dataclass(frozen=True, slots=True)
class Declaration:
    value: Any

@dataclass(frozen=True, slots=True)
class Symbol:
    key: Key
    kind: str
    value: Any
    references: tuple[SymbolRef, ...] = ()

@dataclass(frozen=True, slots=True)
class SymbolContext:
    symbols: Mapping[SymbolRef, Symbol]
    def get_symbol(self, reference: SymbolRef) -> Symbol: ...
    def get_value(self, reference: SymbolRef) -> Any: ...
```

`Symbol` carries its key. `Declaration` does not: the language derives the key
with `compute_key`. `SymbolContext` exposes the symbols transcribed before the
current declaration in dependency order.

```python
# kernel/model/public/language.py
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

Declarations are candidates, not symbols. The linker indexes every declaration,
selects the root declarations, walks the reference closure before transcription
and transcribes only the reachable ones. A declaration that no root reaches
contributes no symbol.

`get_identity` answers for an authoring value and lets the resolver name the
symbol a typed value denotes. `get_references` receives the **authoring
declaration value**, not a transcribed DTO, and returns its direct dependencies;
the linker follows those edges recursively. An expression is an inline fragment,
so its leaves are typed references rather than separately keyed expressions.

`transcribe` is the required per-declaration path. `context` holds the symbols
already transcribed, dependencies first. A language may keep a batch
implementation internally, but the linker calls `transcribe` once per reachable
declaration and no language exposes a batch method as its contract.

Some languages publish child declarations. The data language publishes each
field as a declaration keyed by its owner and column name; the topology language
publishes each property keyed by its component and property name. The owner
references its child declarations, so the same closure walk reaches them.

```python
# kernel/service/public/pipeline.py
class Linker(Protocol[ModelT]):
    def link(
        self, languages: Sequence[Language], namespace: Namespace,
    ) -> ModelT: ...

@dataclass(frozen=True, slots=True)
class PlanContext:
    runtime_configuration: Mapping[str, Mapping[str, Any]] = ...
    shared: MutableMapping[str, Any] = ...   # per compile

class Planner(Protocol[ModelT]):
    component_id: str
    version: str
    runtime_fields: tuple[RuntimeField, ...]
    def plan(self, model: ModelT, context: PlanContext) -> Sequence[Step]: ...
```

`PlanContext.shared` is mutable scratch space for one compile. It lets several
planners that share a component publish and read the same planning state. Core
uses it for `"core.plan"`; the plan is computed once and read by the four core
planners.

## Declarations, symbols and the linker

A language is a frontend. It discovers the authoring objects it recognises,
keys them, reports the direct references an authoring value declares,
transcribes one declaration into a symbol and renders symbol values back to
authoring source.

- A **declaration** is an authoring object a language offers. It carries only
  the value the language recognised.
- A **key** is a tuple of string segments chosen by the language. The empty key
  is the root of a language's key space.
- A **symbol** is a linked unit. It has a key unique within its language, a
  kind, a value and the references the linker must resolve.
- A **reference** is a `SymbolRef(language, key)`. There is no bare
  cross-symbol string.

The linker owns the part the kernel cannot: which declarations are roots, how
the language order constrains indexing, how the reference closure is walked and
what model the distribution assembles. The distribution's `BlueprintLinker`
indexes languages in the fixed order `expressions`, `asset`, `data`, `topology`,
`binding`, then orders the reachable declarations by their authoring references:
data reads asset declarations and expression operations, and bindings read both.

The symbol graph is **linker IR**. It exists to key declarations, resolve
references and order transcription. It is not the delivered model.

## Blueprint versus symbol graph

A blueprint is the semantic model of the graph, not a symbol table.

```python
GraphBlueprint(
    graph=GraphPartDTO(nodes=..., edges=...),
    data=DataPartDTO(structs=..., relations=..., projections=...),
    assets=AssetPartDTO(assets=...),
    bindings=...,
)
```

- The blueprint names nodes, edges, relations, fields, properties, assets and
  operations as semantic roles. A relation names its asset with an `AssetRef`. It carries no Python path, declaration object or
  symbol-table entry.
- The symbol graph is the linker's working representation. It may carry keys,
  kinds and references; it does not appear in the delivered artifact.
- The interpreter assembles the language DTOs into one blueprint. The blueprint
  codec composes the language codecs; the source service delegates to each
  language's renderer.

A language DTO knows only the DTOs of the languages it depends on. It does not
know the blueprint.

`GraphBlueprint` is the public handle. Its fields reference language DTOs, but
those DTOs are not exported public names. `BindingDTO` is the shared binding DTO
used by the blueprint and the core planners; it is not exported from the
interpreter facade.

## The authoring model

The distribution has one authoring value for a typed position in a row:
`Selection[T]`. `NullableSelection[T]` is the alias `Selection[Nullable[T]]`.
There is no expression-family authoring type, no accessor that unwraps the
compiler tree, and no separately named expression object. The compiler
expression tree is private; every operation is a method on the selection.

- A `Field[T]` declares a value type, never `T | None`. A source `Table` or
  source `Struct` read yields `NullableSelection[T]` because the source may omit
  the value. A `Projection` output and a `ComputedStruct` member yield the type
  of their `computed_field` selection, composed with the carrier's presence.
- Nested array-item nullability belongs to the value and is allowed:
  `Field[Array[Nullable[str]]]` reads as
  `Selection[Nullable[Array[Nullable[str]]]]`.
- `Table` and `Projection` are `RowSourceProvider`s. A relation is read through
  `Table.row_source()` or `Projection.row_source()`. There is no table-class
  shorthand for rows and no unpinned `class P(Projection)`; `Projection(source)`
  pins one row-source value at class creation.
- There is one `Field` class with two constructors: `field()` for a source
  `Table` or `Struct`, and `computed_field(selection)` for a `Projection` or
  `ComputedStruct`. The host decides which constructor is legal.
- A binding lambda receives a typed row proxy `S`; `rows=Table.row_source()` is
  the only form.
- `Selection.alter_rows()` is the only row-effect gate. It returns a one-shot
  handle exposing only the effects valid for the selection: `drop_null` on a
  nullable selection, `drop_if` on every selection, and `expand` on an array.
  An invalid effect is absent from the handle type. Each effect returns a
  selection, so a second effect needs a second `alter_rows()`.
- Navigation is `extract`, `at` and `slice`; value operations include `lookup`,
  `zip`, `unique`, `sort`, `concat`, `transform_items` and `drop_null_items`.
- `lookup` is ungated: it returns a nullable array of target records. The caller
  composes the grain: left keeps the value, inner adds
  `alter_rows().drop_null()`, and one row per match adds
  `alter_rows().expand()`.
- `zip` pairs two arrays by position at value level and refuses unequal lengths.
  `RowSource.unnest` expands one array member while preserving the source row;
  it is the row-source spelling of an array grain.

The languages implement the linker path per declaration: `get_references`
reports direct references from the authoring value, the linker resolves the
closure and orders reachable declarations, and `transcribe` converts one
declaration into one `Symbol`. A batch helper may stay internal, but
`transcribe_many` is not the protocol path.

Generation observes a source and renders declarations. Observation is
provenance: a generated source-backed field always renders `Field[T]`, and the
observed nullability tier changes the manifest, statistics and notes, never the
rendered annotation. Value-type nullability, such as an array item, stays in the
value type.

## Assets

An asset is one logical unit of source data, like a package. One asset may back
many tables. A table names its asset with `Table[Asset]`, and a relation carries
that identity as an `AssetRef`. `AssetOptions` carries `website`, optional
`layout`, `semantics` and `governance`; it has no adapter or code-generation
field.

`AssetLayout` is optional descriptive metadata, not an access contract. There is
no adapter concept and no adapter registry. A module contributes ordinary
relation-producing steps; `DuckDbSourcePlanner` resolves compatible `parquet`,
`json` and `csv` layouts. `@asset_contract(AssetContractOptions(...))` is an
inert generation-frontend decorator on an `Asset` subclass and is outside
`AssetOptions` and the blueprint.

## Typed references and expression fragments

Every cross-symbol field in a blueprint is a role-typed reference from
`distribution/model/public/refs.py`:

| Role | Names | Used by |
| --- | --- | --- |
| `NodeRef` | one topology node | node parents, edge endpoints, binding targets |
| `EdgeRef` | one topology edge | edge parents, edge binding targets |
| `RelationRef` | one relation or projection | row scans |
| `FieldRef` | one declared field | columns and field reads |
| `PropertyRef` | one graph property | topology properties |
| `AssetRef` | one logical asset | `RelationDTO.asset` |
| `OperationRef` | one operation specification | operation expressions |

Each wraps a `SymbolRef` and exposes `.symbol`, `.key`, `.language` and `.name`.
Equality and hashing use the wrapped reference. A reference document is
`[language, role, *key segments]`:

```json
["data", "field", "sites.site_name"]
["expressions", "operation", "default_to"]
```

Fields and properties are symbols. A relation stores `FieldRef`s; a node stores
`PropertyRef`s. `FieldReferenceDTO` stores a `FieldRef` plus an optional nested
`path`. `OperationExpressionDTO` stores an `OperationRef`.

An expression is an inline fragment, not a symbol. Its leaves are typed
references: a field read names a `FieldRef`, an operation names an
`OperationRef`, and a literal is a canonical value. A shared or named expression
is a computed field or a projection output, not a separately keyed expression
symbol. The expressions language publishes operation symbols so those leaves
resolve; it does not publish one symbol per expression tree.

## Identity

- A key is a qualified name: `Key` segments chosen by the language. Distribution
  keys use graph names such as `site`, `sites.site_name` and `site.name`.
- A symbol reference is `SymbolRef(language, key)`.
- A binding without a debug name uses a stable content digest as its key
  segment; a debug name is prefixed to that digest. This is the distribution's
  binding identity, not the kernel's general rule.
- Fingerprints and digests may be recorded beside a value, as generation does
  for ownership. They are not the blueprint's primary key, and the framework does
  not content-address symbols by default.
- Pipeline identity is not symbol identity. `StepId(component, name)` and
  `OpeningId(step, direction, name)` are role types over `Key`; they carry no
  language and are not `SymbolRef`. Direction is part of an opening key because
  an input and an output may share a name.
- `ArtifactType` is a concrete `Key`; an input declares an `ArtifactPattern`.
  `*` matches one segment and a final `**` matches the rest. `ArtifactType.name`
  is display only and is never parsed.
- `InstructionKind(operation, engine)` is a two-segment role type. Executor maps
  are keyed by it, and the document form stays `["sql", "duckdb"]`.

## Planning and multiple planners per component

`compile_model` groups planners by `component_id`. Several planners may share a
component when their `version` and `runtime_fields` agree. The component is
published once; every step the group emits is assigned that component id;
assembly refuses a duplicate `StepId`.

This is how core is split:

| Planner | Responsibility |
| --- | --- |
| `RowSourcePlanner` | row-source steps |
| `ProjectionPlanner` | projection steps |
| `BindingPlanner` | binding steps |
| `RecordsPlanner` | aggregate record steps |

All four report `component_id="core"` and the same version and runtime fields.
`core_planners(engine=...)` returns them in assembled order; the engine is the
distribution's neutral `SqlEmitter` protocol. They share one `CorePlan` in
`PlanContext.shared["core.plan"]`.

The generic `DuckDbSourcePlanner` is a separate planner with
`component_id="duckdb"`. It reads each relation's asset layout and emits one
`source.<relation>` step with instruction kind
`("source_relation", "duckdb")`. One asset may produce many source steps; the
planner is not an adapter.

A planner emits steps; it does not execute them. An executor executes one exact
instruction kind; it does not plan. A component that needs both is two objects.

## Execution resources and the runtime

```python
# kernel/model/public/events.py
class ResourceRegistry:
    def add(self, resource_type: type, value: Any) -> None: ...
    def get(self, resource_type: type) -> Any: ...
    def snapshot(self) -> Mapping[type, Any]: ...

@dataclass(frozen=True, slots=True)
class PipelineStarted:
    plan: WorkflowPlan
    configuration: RuntimeConfiguration
    resources: ResourceRegistry

@dataclass(frozen=True, slots=True)
class StepStarted:
    step_id: StepId
    detail: str = ""

@dataclass(frozen=True, slots=True)
class StepFinished:
    outcome: StepOutcome
    detail: str = ""

@dataclass(frozen=True, slots=True)
class StepLogged:
    step_id: StepId
    level: str
    message: str

@dataclass(frozen=True, slots=True)
class PipelineFinished:
    report: WorkflowReport

@dataclass(frozen=True, slots=True)
class PipelineHalted:
    error: BaseException

type PipelineEvent = (
    PipelineStarted | StepStarted | StepFinished | StepLogged
    | PipelineFinished | PipelineHalted
)

type Listener = Callable[[PipelineEvent], None]

class EventBus:
    def subscribe(self, listener: Listener) -> None: ...
    def emit(self, event: PipelineEvent) -> None: ...

class ResourceProvider(Protocol):
    def on_event(self, event: PipelineEvent) -> None: ...

class ResourceView:
    resources: Mapping[type, Any]
    def get[T](self, resource: type[T]) -> T: ...

class StepExecutor(Protocol):
    kinds: tuple[InstructionKind, ...]
    resources: tuple[type, ...]
    def execute(self, context, instruction) -> StepOutcome: ...

class Runtime(Protocol):
    def execute(
        self, plan, executors, *, configuration, listeners=()
    ) -> WorkflowReport: ...
```

- The runtime owns the providers. `Toolchain` has no `resources` field.
- Each run creates a fresh `EventBus` and `ResourceRegistry` and subscribes the
  providers before the frontend listeners. Nothing carries from one run to the
  next.
- Lifecycle order: `PipelineStarted`, then one `StepStarted` / `StepFinished`
  pair per step with any `StepLogged` between them, then `PipelineFinished` on
  success or `PipelineHalted` on failure. `PipelineHalted` is emitted before the
  original error is re-raised.
- Providers publish resources on `PipelineStarted` and dispose them on
  `PipelineFinished` or `PipelineHalted`. A provider that never saw
  `PipelineStarted` does nothing.
- The runtime validates every executor declaration against the registry, refuses
  a missing type and builds a view containing only that executor's declared
  `resources`. A duplicate exact type is refused by `ResourceRegistry.add`.
- `ExecutionContext` and `DisruptedExecutionContext` expose `resources:
  ResourceView` and a per-step `logger`; every log method emits `StepLogged`.
- A resource type is exact. Asking for a type the executor did not declare
  raises `KeyError`, even when another executor received that resource.
- `DuckDbService` owns the engine and its relation service; it is a resource.
  `DuckDbResourceProvider` is in `modules/duckdb`. `RuntimeResources` in
  `modules/runtime` provides output, working and temporary storage and the
  credential resolver.
- A listener error propagates through the bus and is treated as a pipeline
  failure: the runtime emits `PipelineHalted` and re-raises the listener error.

## Composition root and the distribution

`api.py` is the composition root. It owns `default_toolchain`,
`DEFAULT_TOOLCHAIN`, `create_blueprint`, `compile` and `execute`.

- `default_toolchain` composes the default languages, `BlueprintLinker`, the
  generic `DuckDbSourcePlanner` when no supplied planner reports
  `component_id == "duckdb"`, the four core planners when no supplied planner
  reports `component_id == "core"`, the supplied planners, the default executors
  and a `WorkflowRuntime` with `RuntimeResources` and `DuckDbResourceProvider`.
- `default_toolchain` injects `DuckDbSqlEmitter()` into the core planners unless
  the caller supplies another `SqlEmitter`. The core planners import only the
  neutral plan and protocol, never the DuckDB module.
- `DEFAULT_TOOLCHAIN` is the default composition.
- `create_blueprint` discovers declarations, links them and validates the
  blueprint.
- `compile` creates a blueprint when one is not supplied, then compiles it.
- `execute` writes `workflow_plan.json` before the run and `build_report.json`
  after it. Its `monitor` argument is a frontend listener: `None` and `False`
  subscribe nothing, `True` selects `ConsoleMonitor`, and a monitor is used
  unchanged.

`distribution` supplies implementations only. It does not own the composition
root.

`frontend/monitor.py` owns presentation. `Monitor` is the listener protocol,
`NullMonitor` presents nothing, `ConsoleMonitor` writes simple text and imports
`rich` lazily, and `resolve_monitor` maps the public argument to a listener or
`None`. The kernel imports no frontend module and no `rich`.

## Distribution modules

| Module | Contents |
| --- | --- |
| `core` | four planners and one shared `CorePlan`; imports the neutral plan and emitter protocol |
| `deduplication` | `DeduplicationPlanner` |
| `merging` | `MergingPlanner` and its configuration |
| `conflict_validation` | planner, report values and `ConflictReportExecutor` |
| `file` | `FilePlanner` and `FileExecutor` |
| `meta_graph` | `MetaGraphPlanner` and `MetaGraphExecutor` |
| `neo4j` | `Neo4jPlanner` and `Neo4jExecutor` |
| `duckdb` | `DuckDbSourcePlanner`, `DuckDbExecutor`, `DuckDbResourceProvider`, `DuckDbService`, `DuckDbSqlEmitter` implementing the neutral protocol |
| `python` | `PythonExecutor` |
| `runtime` | `RuntimeResources` and executor helpers |

`distribution/languages/{annotations,expressions,asset,data,topology,binding}`
own the language frontends. `distribution/interpreter` owns `GraphBlueprint`,
`BlueprintLinker`, `create_blueprint`, validation, the blueprint codec and source
rendering. `distribution/implementations.py` supplies the language and linker
implementations.

## Instruction kinds

`InstructionKind(operation, engine)` is an exact two-segment role type. A custom
planner may emit a new kind and register its own executor.

| Kind | Payload |
| --- | --- |
| `("source_relation", "duckdb")` | `{relation, location, format, credential_reference, declaration, declared_columns, declared_paths}` |
| `("sql", "duckdb")` | `{relation, sql}` |
| `("aggregate", "duckdb")` | `{relation}` |
| `("deduplication", "duckdb")` | `{relation}` |
| `("merging", "duckdb")` | `{relation, select}` |
| `("conflict_findings", "duckdb")` | `{component, field}` |
| `("conflict_report", "default")` | `{fail_on_error}` |
| `("python", "cpython")` | `{module, qualname}` |
| `("file", "default")` | `{relative_path}` |
| `("meta_graph", "default")` | `{relative_path, example_limit, include_html, html_relative_path, components}` |
| `("neo4j", "default")` | `{kind: "export_component" | "write_script", ...}` |

`DuckDbSourcePlanner` emits `InstructionKind("source_relation", "duckdb")`. The
four core planners emit the injected emitter's kind, which is
`InstructionKind("sql", "duckdb")` for `DuckDbSqlEmitter`, and
`InstructionKind("aggregate", "duckdb")`. `DuckDbExecutor` owns all three. `DeduplicationPlanner`, `MergingPlanner` and
`ConflictValidationPlanner` emit the other DuckDB kinds.

## Planner and executor ownership

Planner classes are public names under
`kg_build_system.distribution.modules.<name>`. A target that needs both a
planning decision and a side effect owns a planner and an executor under the
same module.

| Component | Class | Module | Responsibility |
| --- | --- | --- | --- |
| `core` | `core_planners(engine=...)` (`RowSourcePlanner`, `ProjectionPlanner`, `BindingPlanner`, `RecordsPlanner`) | `modules.core` | row-source, projection, binding and aggregate steps |
| `deduplication` | `DeduplicationPlanner` | `modules.deduplication` | one distinct step per bound record component |
| `merging` | `MergingPlanner` | `modules.merging` | one merge step per component in scope |
| `conflict_validation` | `ConflictValidationPlanner` / `ConflictReportExecutor` | `modules.conflict_validation` | findings steps and one deferred report step |
| `file` | `FilePlanner` / `FileExecutor` | `modules.file` | JSON Lines target |
| `meta_graph` | `MetaGraphPlanner` / `MetaGraphExecutor` | `modules.meta_graph` | topology document and optional HTML |
| `neo4j` | `Neo4jPlanner` / `Neo4jExecutor` | `modules.neo4j` | component exports and import script |
| `duckdb` | `DuckDbSourcePlanner` / `DuckDbExecutor` / `DuckDbResourceProvider` | `modules.duckdb` | source and SQL kinds and the DuckDB resource |
| — | `PythonExecutor` | `modules.python` | `InstructionKind("python", "cpython")` |
| — | `RuntimeResources` | `modules.runtime` | storage and credential resources |

A target planner declares its input as an artifact pattern such as
`ArtifactPattern.of("core", "graph", "**")` and its side effect as an
`InstructionKind` its executor owns. The planner never writes a file; the
executor never changes the plan.

Planner configuration is compile-time and carried in the instruction payload.
Runtime fields describe values an operator may replace at execution time, keyed
by component id in `RuntimeConfiguration.component_configuration`. Resource
providers read `RuntimeConfiguration.provider_configuration`; `duckdb` is a
provider id, not a plan component.

## Generation

`generation/code_generation/` is the edit-time lane. It turns an inert
`@asset_contract(AssetContractOptions(...))` on an asset into declarations before
the blueprint runs. It is upstream of the blueprint.

| Surface | Contents |
| --- | --- |
| `model/public` | asset contract options, generation requests and result models |
| `model/internal` | provider contract and discovery models |
| `model/_private` | generated render model |
| `service/public` | `asset_contract`, `generate`, `discover`, `watch` |
| `service/internal` | provider loading and provider adapters |
| `service/_private` | discovery, rendering, ownership, watcher and engine |

Generation and the toolchain are separate lanes:

- generation observes a source, runs a provider and renders declarations;
- `build` imports the resulting declarations and never invokes generation;
- `compile` and `execute` never invoke generation.

A generated field renders its value type. Observed source nullability is
provenance for the manifest, statistics and semantics notes; it never adds
`| None` to a source-backed field. Nullability that belongs to the value — an
array item or an explicitly nullable computed result — stays in the value type.

A generated declaration and a handwritten declaration enter the same language,
blueprint, plan and execution path. There is no generation-specific plan path.

## Dependency spine

The tree shows the primary dependency spine. A tree cannot encode every edge;
the dependency tests enforce the rest.

| Package | May import |
| --- | --- |
| `kernel` | no framework package |
| `distribution/languages/annotations` | `kernel` |
| `distribution/languages/expressions` | `kernel` |
| `distribution/languages/asset` | `kernel`, annotations |
| `distribution/languages/data` | `kernel`, annotations, expressions, asset |
| `distribution/languages/topology` | `kernel`, annotations, expressions |
| `distribution/languages/binding` | `kernel`, annotations, data, topology |
| `distribution/interpreter` | `kernel`, every graph language |
| `distribution/modules/<name>` | `kernel`, `distribution/interpreter` where it reads a blueprint, distribution languages, `distribution.model` and `distribution.service` |
| `distribution/implementations.py` | `kernel`, interpreter, languages |
| `distribution/service` | `kernel`, distribution languages, interpreter |
| `generation/code_generation` | `kernel` and `distribution.languages.asset`; engine observation is read-only |
| `api.py` | `kernel`, `distribution` |
| `cli` | `generation`, `api.py` |

Two rules apply to every row:

- the kernel imports no graph, data, topology, binding, SQL, DuckDB or Python
  package;
- no package imports another package's private zones.

The core module is one engine consumer, not the engine. It imports the neutral
relation plan and `SqlEmitter` protocol from `distribution/service/internal`; it
does not import `distribution/modules/duckdb`. A dependency test enforces that
edge.

The exact edge set is a model decision. A new edge is proposed with its reason,
not added because a call site needs it.

## Leaf layout and import matrix

| Zone | Reader | May be imported by | Holds |
| --- | --- | --- | --- |
| `pkg` | graph author | any package | facade over `model.public` and `service.public` |
| `pkg.model.public` | graph author | any package for authoring names and frozen type vocabulary | authoring models, returned values and public DTOs |
| `pkg.model.internal` | framework code | any package for cross-package data | `dto/` and `model/` data |
| `pkg.model._private` | its own package | no other package | private plans, render models and SQL types |
| `pkg.service.public` | graph author | any package for service interfaces | authoring methods and thin wrappers |
| `pkg.service.internal` | framework code | any package for service interfaces | codec and assembly wrappers, adapters |
| `pkg.service._private` | its own package | no other package | codecs, transcription, rendering, validation, assembly, planning, engines and runtime |

The import matrix is part of the layout:

| Source | May import | Must not import |
| --- | --- | --- |
| `model.public` | model data | any service or `_private` |
| `model.internal` | model data | any service or `_private` |
| `model._private` | `model.public`, `model.internal` | service |
| `service.public` | `model.public`, `service.internal` | `_private` |
| `service.internal` | model data; `service._private` with function-local imports | `service.public` |
| `service._private` | `model.public`, `model.internal`, `model._private`, `service._private` | `service.public` |

Another package imports `pkg.model.public`, `pkg.model.internal`,
`pkg.service.public` or `pkg.service.internal`. It never imports
`pkg.model._private` or `pkg.service._private`. `_private` may use public model
data but not public service behaviour.

A public function or method is a thin wrapper over `service.internal` or
`service._private`, with a user-facing docstring and a runnable `Example:`. The
mechanism is not in `service.public`. Internal and private functions carry
developer docstrings and need no example.

A protocol implementation is a separate file under
`service/internal/adapters/<protocol>.py`. The file names the protocol, imports
the foreign protocol and delegates to `service._private`. It is not buried in a
model or factory. `BlueprintLinker` is implemented this way for the kernel
`Linker` protocol.

No `model.public`, `model.internal`, `service.public` or `service.internal`
module defines a single-underscore helper; dunder protocol methods remain. A
codec is a service: interface in `service.internal`, implementation in
`service._private`. A DTO is a model: `model.internal/dto`, or `model.public` for
a public artifact.

## What the kernel must never import

The kernel is domain-agnostic. Its dependency tests refuse an import of:

- `distribution.languages.*` (graph, data, topology, binding, annotations,
  expressions);
- `distribution.interpreter` (blueprint);
- `distribution.modules.*`;
- `duckdb`, `pyarrow` or another engine client;
- SQL text or a SQL AST;
- `generation`.

The kernel also must not read an instruction payload or an artifact value. The
executor registered for a kind reads the payload; the distribution owns the
value.

## Current state and limits

The tree above is the implementation.

- 259 tests passed, 1858 subtests.
- Pyright: 0 errors.
- mkdocs strict build: passes.
- The reference build passes.
- Open Targets: the migrated project builds against the API; 7 tests pass.

The remaining limits are:

| Limit | Current choice |
| --- | --- |
| A toolchain is the only composition unit. | There is no registry. A caller composes a `Toolchain` or uses `default_toolchain` in `api.py`. |
| DuckDB is the default SQL emitter. | `DuckDbSqlEmitter` implements the neutral `SqlEmitter` protocol; `api.default_toolchain` injects it into the core planners. Another engine supplies another emitter and executor. |
| A Python instruction is a reference. | `("python", "cpython")` carries `{module, qualname}`, not a live callable. |
| Public `GraphBlueprint` fields reference internal language DTOs. | `GraphBlueprint` is public; its `graph`, `data`, `assets` and `bindings` fields are typed by language DTOs that are not exported public names. |
| A language may share a struct graph name. | A repeated struct name takes its qualified Python name as an extra key segment; the blueprint still names the struct by its graph role. |

See [data and expressions](data-and-expressions.md) for the DTO shapes and the
source round trip.

## What to remember

- The kernel is domain-agnostic and owns the toolchain vocabulary.
- `Selection[T]` is the single authoring type; the owner supplies nullability.
- `build` links declarations into symbols and a model, `compile` plans,
  `execute` runs.
- A declaration has no key; `compute_key` derives it. A symbol carries its key,
  kind, value and references.
- The symbol graph is linker IR; the blueprint is the semantic model.
- A planner emits steps; an executor owns one exact instruction kind and
  declares the resources it reads.
- The runtime owns resource providers; a toolchain has no `resources` field.
- The distribution supplies implementations; `api.py` composes the default.
- A step owns its instruction; SQL is one instruction kind.

Next: [Data and expressions](data-and-expressions.md).
