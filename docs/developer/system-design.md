# System design

The framework has a domain-agnostic **kernel** and one **distribution**. The
kernel is a toolchain: it orders languages, links their layers into an opaque
model, compiles that model into a workflow plan and executes the plan through
exact instruction-kind executors. The distribution supplies the graph domain:
the blueprint, the planners and the executors that know what a node, an edge,
DuckDB or Neo4j means.

The kernel vocabulary is toolchain vocabulary:

| Kernel name | Meaning |
| --- | --- |
| `Language` | frontend library: declarations -> `Layer` |
| `Layer` | object file: one language's value plus named `Definition`s |
| `Definition` | symbol: a named unit another language may reference |
| `Linker[ModelT]` | links ordered layers into one opaque model |
| `Planner[ModelT]` | compiles the model into workflow `Step`s |
| `WorkflowPlan` | one assembled instruction DAG |
| `Step` | one scheduled instruction with typed inputs and outputs |
| `StepExecutor` | executes one exact instruction kind |
| `Runtime` | schedules steps and dispatches instructions |
| `ResourceProvider` | creates and closes execution services |
| `Toolchain` | languages + linker + planners + executors + resources + runtime |
| `Extension` | a named bundle of languages, planners and executors |

The distribution vocabulary is domain vocabulary: graph, blueprint, node, edge,
binding, projection, table, core, meta-graph, Neo4j, DuckDB, Python.

## The package tree

```text
kg_build_system/
  kernel/
    model/
      public/
        language.py      Definition, Layer, Language, Namespace,
                         LanguageContext, RenderContext, SourceFragment
        workflow.py      InstructionKind, Instruction, ArtifactType, Input,
                         Output, Publication, Step, Connection, Component,
                         RuntimeField, WorkflowPlan
        runtime.py       StepStatus, Failure, Artifact, StepOutcome,
                         ContinuableInput, DisruptingInput, PublishedArtifact,
                         WorkflowReport, ExecutionContext,
                         DisruptedExecutionContext, RuntimeConfiguration
        types/           canonical types
      internal/
        json.py
        types/dto.py
      _private/
        types/
    service/
      public/
        pipeline.py      Linker, Planner, StepExecutor, Runtime,
                         ResourceProvider, Toolchain, Extension, PlanContext
        runtime.py       WorkflowRuntime
      internal/
        pipeline.py      thin wrappers only
        workflow_codec.py
      _private/
        ordering.py      language ordering
        pipeline.py      transcribe -> link -> plan -> run
        assembly.py      step and connection assembly
        runtime.py       scheduler and step lifecycle
        workflow_codec.py
  distribution/
    model/
      public/
        paths.py         relative-path rule
        runtime.py       BuildRuntime
      internal/
    languages/
      annotations/
      expressions/
      data/
      topology/
      binding/
    interpreter/
      model/public/graph_blueprint.py
      service/public/create.py
      service/internal/adapters/kernel_linker.py
      service/_private/{create,assembly,validation,codec,source,discovery}.py
    planners/
      core/
      deduplication/
      merging/
      conflict_validation/
    executors/
      model/
        public/      no author-facing model
        internal/
      service/
        public/
        internal/
        _private/
      runtime/
      duckdb/
      python/
      file/
      meta_graph/
      neo4j/
      conflict_validation/
    service/             the distribution leaf's service zone
      public/create.py
      internal/rendering.py
      _private/rendering.py
    default.py           DEFAULT_TOOLCHAIN / default_toolchain
  generation/
    code_generation/
  api.py                 create_blueprint, compile, execute
  cli/
```

Every leaf keeps the same layout, including the leaf under `planners/` and
`executors/`:

```text
pkg/
  __init__.py          imports only model.public and service.public
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

`distribution/executors` is also a leaf. Its `model/public` package is empty: it
states that the leaf has no author-facing model of its own rather than inventing
a facade. `distribution/executors/python` states the same absence and exports
only `PythonExecutor` from `service.public`. `distribution/service` is not a
leaf: it is the `distribution` leaf's service zone, holding the shared blueprint
creator and rendering interface.

## The three verbs

`kg_build_system.kernel.service.public.pipeline.Toolchain` is the kernel's
composition surface. It has three verbs and they do not overlap.

### `build(namespace) -> ModelT`

1. Order languages by `requires`. A duplicate name, an unknown dependency or a
   cycle raises `ValueError`.
2. Call `language.collect(namespace)` for each language in order.
3. Call `language.transcribe(declarations, context)`. The context exposes only
   the layers already transcribed. A language that returns a non-`Layer`, or a
   layer whose `language` differs from the language's `name`, is refused.
4. Call `language.validate(layer)`.
5. Call `linker.link(layers)`. The linker's `requires` must name layers that
   exist; the kernel never inspects the returned model.

`build` is the only verb that reads declarations. It does not plan or execute.

### `compile(model) -> WorkflowPlan`

1. Call every planner in order with the same linked model and one
   `PlanContext`.
2. Assign each returned step the planner's `component_id`, overriding whatever
   component the planner wrote on the step.
3. Refuse a duplicate component id or duplicate step id
   `f"{component}.{name}"`.
4. Assemble open inputs to outputs, publications to the report, and return one
   `WorkflowPlan`. A wiring with no producer or with a cycle is refused.

`compile` does not call `build` and does not read data. The composition root
(`api.compile`) may call `create_blueprint` and then `compile`; the kernel
method never does.

### `execute(plan, *, output_directory, configuration=None, monitor=None) -> WorkflowReport`

1. Build an exact-kind map from every `executor.kinds`. A duplicate kind raises
   `ValueError`.
2. Refuse an instruction kind in the plan that has no executor, before any step
   runs.
3. Build a `RuntimeConfiguration` when none is supplied.
4. Call `resources.services(plan, configuration)`.
5. Call `runtime.execute(plan, executors, services=..., configuration=..., monitor=...)`.
6. Call `resources.close(services)` exactly once, including when execution
   raises.

The scheduler classifies each upstream result as continuable (`SUCCEEDED`,
`WARNING`) or disrupting (`FAILED`, `SKIPPED`). A normal step receives an
`ExecutionContext`; a disrupted step receives a `DisruptedExecutionContext` and
normally returns a `SKIPPED` outcome. An executor owns any engine bookkeeping.

## Kernel interfaces

```python
# kernel/model/public/language.py
@dataclass(frozen=True, slots=True)
class Definition:
    id: str
    kind: str
    value: Any

@dataclass(frozen=True, slots=True)
class Layer:
    language: str
    value: Any
    definitions: Mapping[str, Definition] = field(default_factory=dict)

class Language(Protocol):
    name: str
    requires: tuple[str, ...]
    def collect(self, namespace: Namespace) -> Sequence[object]: ...
    def transcribe(
        self, declarations: Sequence[object], context: LanguageContext,
    ) -> Layer: ...
    def validate(self, layer: Layer) -> None: ...
    def render(self, layer: Layer, context: RenderContext) -> SourceFragment: ...

class LanguageContext(Protocol):
    def layer(self, name: str) -> Layer: ...

class Namespace(Protocol):
    def values(self) -> Sequence[object]: ...
```

`Layer.value` is the language's own frozen DTO. `Layer.definitions` is the
symbol index other languages may read; `Layer.__post_init__` copies it and wraps
it in a read-only proxy. A language may publish one definition per declaration;
publishing only the layer value is allowed and is recorded as a limit.

```python
# kernel/model/public/workflow.py
type InstructionKind = tuple[str, ...]

@dataclass(frozen=True, slots=True)
class Instruction:
    kind: InstructionKind
    payload: JsonValue

@dataclass(frozen=True, slots=True)
class ArtifactType:
    namespace: str
    name: str

@dataclass(frozen=True, slots=True)
class Input:
    type: ArtifactType
    name: str | None
    input_name: str

@dataclass(frozen=True, slots=True)
class Output:
    type: ArtifactType
    name: str | None = None

@dataclass(frozen=True, slots=True)
class Publication:
    type: ArtifactType
    name: str | None = None

@dataclass(frozen=True, slots=True)
class Step:
    component: str
    name: str
    inputs: tuple[Input, ...]
    outputs: tuple[Output | Publication, ...]
    instruction: Instruction
    assembly_preference: Literal["eager", "deferred"] = "eager"

@dataclass(frozen=True, slots=True)
class Connection:
    input_id: str
    output_id: str

@dataclass(frozen=True, slots=True)
class RuntimeField:
    key: str
    description: str
    required: bool = True
    value_type: Literal["string", "integer", "number", "boolean", "json"] = "string"
    secret: bool = False

@dataclass(frozen=True, slots=True)
class Component:
    id: str
    version: str
    runtime_fields: tuple[RuntimeField, ...] = ()

@dataclass(frozen=True, slots=True)
class WorkflowPlan:
    components: tuple[Component, ...]
    steps: tuple[Step, ...]
    connections: tuple[Connection, ...] = ()
    provenance: JsonValue | None = None
```

An `ArtifactType` on an `Input` is a pattern matched with `fnmatchcase`; an
`ArtifactType` on an output or publication is one concrete type. Step identity is
`f"{component}.{name}"`; an opening identity is
`f"{step_id}.{opening_name}"`. `assembly_preference="deferred"` tells the
assembler to keep the step as one unit when it shares or reorganises work.

```python
# kernel/model/public/runtime.py
class StepStatus(StrEnum):
    SUCCEEDED = "succeeded"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass(frozen=True, slots=True)
class Failure:
    message: str
    step_id: str
    exception_type: str | None = None

@dataclass(frozen=True, slots=True)
class Artifact:
    output_name: str
    type: ArtifactType
    value: Any

@dataclass(frozen=True, slots=True)
class StepOutcome:
    step_id: str
    status: StepStatus
    artifacts: tuple[Artifact, ...] = ()
    failure: Failure | None = None

@dataclass(frozen=True, slots=True)
class ContinuableInput:
    output_id: str
    status: Literal[StepStatus.SUCCEEDED, StepStatus.WARNING]
    artifact: Artifact | None

@dataclass(frozen=True, slots=True)
class DisruptingInput:
    output_id: str
    status: Literal[StepStatus.FAILED, StepStatus.SKIPPED]
    artifact: Artifact | None
    failure: Failure | None

@dataclass(frozen=True, slots=True)
class ExecutionContext:
    step: Step
    step_id: str
    component: str
    runtime_configuration: Mapping[str, Any]
    inputs: Mapping[str, tuple[ContinuableInput, ...]]
    services: Any

@dataclass(frozen=True, slots=True)
class DisruptedExecutionContext:
    step: Step
    step_id: str
    component: str
    runtime_configuration: Mapping[str, Any]
    inputs: Mapping[str, tuple[ContinuableInput | DisruptingInput, ...]]
    disruptions: tuple[DisruptingInput, ...]
    services: Any

@dataclass(frozen=True, slots=True)
class PublishedArtifact:
    type: ArtifactType
    value: Any

@dataclass(frozen=True, slots=True)
class WorkflowReport:
    published_artifacts: tuple[PublishedArtifact, ...]
    recovered_failures: tuple[Failure, ...]
    unresolved_failures: tuple[Failure, ...]
    provenance: dict[str, Any]

    @property
    def succeeded(self) -> bool: ...

@dataclass(frozen=True, slots=True)
class RuntimeConfiguration:
    output_directory: Path
    working_directory: Path
    temporary_directory: Path | None = None
    credentials: Mapping[str, str] = field(default_factory=dict)
    component_configuration: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict,
    )
```

`RuntimeConfiguration.component_configuration` is keyed by component id.
`BuildRuntime` in the distribution is a public authoring value that converts to
this kernel value with `to_configuration()`.

```python
# kernel/service/public/pipeline.py
class Linker(Protocol[ModelT]):
    requires: tuple[str, ...]
    def link(self, layers: Mapping[str, Layer]) -> ModelT: ...

@dataclass(frozen=True, slots=True)
class PlanContext:
    runtime_configuration: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict,
    )

class Planner(Protocol[ModelT]):
    component_id: str
    version: str
    runtime_fields: tuple[RuntimeField, ...]
    def plan(self, model: ModelT, context: PlanContext) -> Sequence[Step]: ...

class StepExecutor(Protocol):
    kinds: tuple[InstructionKind, ...]
    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome: ...

class ResourceProvider(Protocol):
    def services(
        self, plan: WorkflowPlan, configuration: RuntimeConfiguration,
    ) -> Any: ...
    def close(self, services: Any) -> None: ...

class Runtime(Protocol):
    def execute(
        self,
        plan: WorkflowPlan,
        executors: Mapping[InstructionKind, StepExecutor],
        *,
        services: Any,
        configuration: RuntimeConfiguration,
        monitor: Any = None,
    ) -> WorkflowReport: ...

@dataclass(frozen=True, slots=True)
class Extension:
    name: str
    languages: tuple[Language, ...] = ()
    planners: tuple[Any, ...] = ()
    executors: tuple[StepExecutor, ...] = ()

@dataclass(frozen=True, slots=True)
class Toolchain(Generic[ModelT]):
    languages: Sequence[Language]
    linker: Linker[ModelT]
    planners: Sequence[Planner[ModelT]] = ()
    executors: Sequence[StepExecutor] = ()
    resources: ResourceProvider | None = None
    runtime: Runtime | None = None

    def build(self, namespace: Namespace) -> ModelT: ...
    def compile(self, model: ModelT) -> WorkflowPlan: ...
    def execute(
        self,
        plan: WorkflowPlan,
        *,
        output_directory: Path,
        configuration: RuntimeConfiguration | None = None,
        monitor: Any = None,
    ) -> WorkflowReport: ...
    def with_planners(
        self, planners: Sequence[Planner[ModelT]],
    ) -> Toolchain[ModelT]: ...
    def with_executors(
        self, executors: Sequence[StepExecutor],
    ) -> Toolchain[ModelT]: ...
```

`Toolchain.execute` raises `RuntimeError` when `resources` or `runtime` is
`None`. `with_planners` and `with_executors` replace the sequence; they do not
append. The distribution's `default_toolchain` is what adds the core planner and
the supplied executors.

An extension contributes a language, a planner and/or an executor. A language
that introduces a new model also supplies its linker when the caller composes
the `Toolchain`; `Extension` itself bundles languages, planners and executors.

`WorkflowRuntime` in `kernel.service.public.runtime` is the kernel's default
scheduler. It is transport-agnostic: services and instruction payloads are
opaque to it.

## Providers and engines

`ResourceProvider` and `Runtime` are the only kernel interfaces a distribution
must supply to execute. Planners and executors are opt-in: a toolchain with no
planner produces an empty plan, and a toolchain with no executor refuses a plan
instruction whose kind is not registered.

A `StepExecutor` is selected by an exact instruction-kind tuple. There is no
prefix matching, no dispatcher table inside the kernel and no engine import in
the kernel. `kinds` is the executor's declaration of every kind it owns; the
toolchain builds the map before the first step runs.

## Instruction kinds

Kinds are exact tuples. A custom planner may emit a new kind and register its
own executor.

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

`("source_relation", "duckdb")`, `("sql", "duckdb")` and `("aggregate",
"duckdb")` are emitted by the core planner and owned by the DuckDB executor.
`DeduplicationPlanner`, `MergingPlanner` and `ConflictValidationPlanner` emit the
other DuckDB kinds.

## Planner and executor ownership

Planner classes are public names under
`kg_build_system.distribution.planners.<name>`. A target that needs both a
planning decision and a side effect owns a planner and an executor under
`kg_build_system.distribution.executors.<name>`.

| Component | Class | Package | Responsibility |
| --- | --- | --- | --- |
| `core` | `CorePlanner` | `planners.core` | source, row-source, projection, binding and aggregate steps |
| `deduplication` | `DeduplicationPlanner` | `planners.deduplication` | one distinct step per bound record component |
| `merging` | `MergingPlanner` | `planners.merging` | one merge step per component in the configured scope |
| `conflict_validation` | `ConflictValidationPlanner` | `planners.conflict_validation` | findings steps and one deferred report step |
| `file` | `FilePlanner` / `FileExecutor` | `executors.file` | JSON Lines target |
| `meta_graph` | `MetaGraphPlanner` / `MetaGraphExecutor` | `executors.meta_graph` | topology document and optional HTML |
| `neo4j` | `Neo4jPlanner` / `Neo4jExecutor` | `executors.neo4j` | component exports and import script |
| `conflict_validation` | `ConflictReportExecutor` | `executors.conflict_validation` | report publication |
| — | `DuckDbExecutor` | `executors.duckdb` | `source_relation`, `sql`, `aggregate`, `deduplication`, `merging`, `conflict_findings` |
| — | `DuckDbResourceProvider` | `executors.duckdb` | relations, working storage, temporary storage, credentials, engine session |
| — | `PythonExecutor` | `executors.python` | `("python", "cpython")` |

A target planner declares its input as an artifact pattern such as
`ArtifactType("core", "graph.*")` and its side effect as a kind its executor
owns. The planner never writes a file; the executor never changes the plan.

Planner configuration is compile-time and carried in the instruction payload.
Runtime fields describe values an operator may replace at execution time, keyed
by component id in `RuntimeConfiguration.component_configuration`. The supplied
`FilePlanner` and `Neo4jPlanner` each expose one optional runtime field.

## Distribution

`distribution/` is one system and one toolchain. Its primary edges are:

| Package | Contents |
| --- | --- |
| `languages/{annotations,expressions,data,topology,binding}` | the graph declaration languages and their DTOs |
| `interpreter` | `GraphBlueprint`, `BlueprintLinker`, `create_blueprint`, validation and source rendering |
| `planners/*` | graph-aware planners that emit steps |
| `executors/*` | instruction executors and execution services |
| `model/public` | `BuildRuntime`, path validation |
| `service/public` | the shared `create_blueprint` shortcut |
| `default.py` | `DEFAULT_TOOLCHAIN` and `default_toolchain` |

`interpreter/service/internal/adapters/kernel_linker.py` is the adapter that
implements the kernel `Linker` protocol for `BlueprintLinker`. The adapter file
names the protocol, delegates to `service._private` and is not buried in the
blueprint model.

`api.py` is the composition root. `create_blueprint` uses the default
languages and `BlueprintLinker`. `compile` creates a blueprint unless one is
supplied, then uses `DEFAULT_TOOLCHAIN` or the supplied toolchain; it appends
the core planner unless a planner already reports `component_id == "core"`, then
appends the caller's planners. `execute` writes `workflow_plan.json` before the
run and `build_report.json` after it.

## Generation

`generation/code_generation/` is the edit-time lane. It turns typed requests
into declarations before the blueprint runs. It is upstream of the blueprint.

| Surface | Contents |
| --- | --- |
| `model/public` | generation requests and result models |
| `model/internal` | provider contract and discovery models |
| `model/_private` | generated render model |
| `service/public` | `generation`, `generate`, `discover`, `watch` |
| `service/internal` | provider loading and provider adapters |
| `service/_private` | discovery, rendering, ownership, watcher and engine |

Generation and the toolchain are separate lanes:

- generation observes a source, runs a provider and renders declarations;
- `build` imports the resulting declarations and never invokes generation;
- `compile` and `execute` never invoke generation.

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
| `distribution/languages/data` | `kernel`, annotations, expressions |
| `distribution/languages/topology` | `kernel`, annotations, expressions |
| `distribution/languages/binding` | `kernel`, annotations, data, topology |
| `distribution/interpreter` | `kernel`, every graph language |
| `distribution/planners/*` | `kernel`, `distribution/interpreter`, distribution languages; the core planner also uses the DuckDB SQL emitter |
| `distribution/executors/*` | `kernel`, distribution model, distribution languages; the conflict-report executor reuses the planner's report values |
| `distribution/default.py` | `kernel`, interpreters, planners, executors |
| `distribution/service` | `kernel`, distribution languages and interpreter |
| `generation/code_generation` | `kernel`; engine observation is read-only |
| `api.py` | `kernel`, `distribution` |
| `cli` | `generation`, `api.py` |

Two rules apply to every row:

- the kernel imports no graph, data, topology, binding, SQL, DuckDB or Python
  package;
- no package imports another package's private zones.

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
- `distribution.planners.*` and `distribution.executors.*`;
- `duckdb`, `pyarrow` or another engine client;
- SQL text or a SQL AST;
- `generation`.

The kernel also must not read an instruction payload or an artifact value. The
executor registered for a kind reads the payload; the distribution owns the
value.

## Current state and limits

The tree above is the implementation.

- 115 tests passed, 604 subtests.
- Pyright: 0 errors.
- Open Targets: the migrated project builds against the new API; 7 tests pass.

The remaining limits are:

| Limit | Current choice |
| --- | --- |
| A toolchain is the only composition unit. | There is no registry. A caller composes a `Toolchain` or uses `default_toolchain`. |
| DuckDB is the default SQL emitter. | `DuckDbSqlEmitter` is the core planner's SQL library; another engine supplies another emitter. |
| A Python instruction is a reference. | `("python", "cpython")` carries `{module, qualname}`, not a live callable. |
| Public `GraphBlueprint` fields reference internal layer DTOs. | `GraphBlueprint` is public; its `graph`, `data`, `bindings` and `sources` fields are typed by layer DTOs that are not exported public names. |
| A language may publish only its layer value. | Publishing one `Definition` per declaration is allowed; publishing only the value is recorded as a limit. |

See [data and expressions](data-and-expressions.md) for the DTO shapes and the
source round trip.

## What to remember

- The kernel is domain-agnostic and owns the toolchain vocabulary.
- `build` reads declarations, `compile` plans, `execute` runs.
- A planner emits steps; an executor owns one exact instruction kind.
- The distribution supplies the graph blueprint, planners and executors.
- A service adapter is an explicit file under `service/internal/adapters`.
- A step owns its instruction; SQL is one instruction kind.

Next: [Data and expressions](data-and-expressions.md).
