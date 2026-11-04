# Planners and executors

A planner emits workflow steps; an executor owns one exact instruction kind. The
supplied planners deduplicate, merge, validate, or produce graph records; the
supplied executors run DuckDB, Python, file, meta-graph and Neo4j instructions.
See [Planners and executors](../concepts/planners-and-executors.md).

```python
from kg_build_system import compile, execute
from kg_build_system.distribution import (
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
    MetaGraphConfiguration,
    MetaGraphPlanner,
)

planners = (
    DeduplicationPlanner(),
    FilePlanner(FileConfiguration("graph.jsonl")),
    MetaGraphPlanner(MetaGraphConfiguration(example_limit=5)),
)
plan = compile(planners=planners)
report = execute(plan, output_directory="build")
```

## Kernel protocols

A planner implements:

```python
class Planner(Protocol[ModelT]):
    component_id: str
    version: str
    runtime_fields: tuple[RuntimeField, ...]
    def plan(self, model: ModelT, context: PlanContext) -> Sequence[Step]: ...
```

An executor implements:

```python
class StepExecutor(Protocol):
    kinds: tuple[InstructionKind, ...]
    resources: tuple[type, ...]
    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome: ...
```

`component_id` is the planner's identity in the plan. Several planners may share
one `component_id`; they must agree on `version` and `runtime_fields`, which are
published once in the component's `Component`. `kinds` is the set of exact
`InstructionKind` values the executor handles, and `resources` names the exact
resource types it reads from its `ResourceView`. The kernel refuses disagreeing
planner versions or runtime fields, a duplicate `StepId`, a duplicate executor
kind, a missing declared resource and a plan instruction with no executor.

## Supplied planners

| Planner | Package | `component_id` | Configuration |
| --- | --- | --- | --- |
| `DuckDbSourcePlanner` | `distribution.modules.duckdb` | `duckdb` | `formats`, `union_by_name` |
| `RowSourcePlanner` | `distribution.modules.core` | `core` | none; optional `engine` SQL emitter |
| `ProjectionPlanner` | `distribution.modules.core` | `core` | none; optional `engine` SQL emitter |
| `BindingPlanner` | `distribution.modules.core` | `core` | none; optional `engine` SQL emitter |
| `RecordsPlanner` | `distribution.modules.core` | `core` | none; optional `engine` SQL emitter |
| `DeduplicationPlanner` | `distribution.modules.deduplication` | `deduplication` | none |
| `MergingPlanner` | `distribution.modules.merging` | `merging` | `MergingConfiguration(components=None)` |
| `ConflictValidationPlanner` | `distribution.modules.conflict_validation` | `conflict_validation` | `ConflictValidationConfiguration(fail_on_error=True)` |
| `FilePlanner` | `distribution.modules.file` | `file` | `FileConfiguration(relative_path)` |
| `MetaGraphPlanner` | `distribution.modules.meta_graph` | `meta_graph` | `MetaGraphConfiguration(...)` |
| `Neo4jPlanner` | `distribution.modules.neo4j` | `neo4j` | `Neo4jConfiguration(...)` |

### Core planners

```python
core_planners(*, engine: DuckDbSqlEmitter | None = None)
RowSourcePlanner(*, engine: DuckDbSqlEmitter | None = None)
ProjectionPlanner(*, engine: DuckDbSqlEmitter | None = None)
BindingPlanner(*, engine: DuckDbSqlEmitter | None = None)
RecordsPlanner(*, engine: DuckDbSqlEmitter | None = None)
```

The core module owns four planners that share `component_id="core"` and one
`CorePlan` in `PlanContext.shared["core.plan"]`. `core_planners()` returns them in
assembled order: row-source, projection, binding and records. Together they emit
row-source, projection, binding and aggregate steps. SQL steps use
`("sql", "duckdb")`. `compile` adds the four before your planners when no planner
reports `component_id == "core"`.

### `DuckDbSourcePlanner`

```python
DuckDbSourcePlanner(
    *,
    formats: Sequence[str] = ("parquet", "json", "csv"),
    union_by_name: bool = False,
)
```

Emits one `source.<relation>` step for each asset-backed relation the graph
reads whose `AssetLayout` resolves to `parquet`, `json` or `csv`. The step
produces `CoreArtifactTypes.table(relation)` with instruction kind
`("source_relation", "duckdb")`.

`AssetLayout` resolution is `members[relation]`, then
`selector.format(table=relation, table_path=relation.replace(".", "/"))`, then
`locator`; a relative result is joined to `locator`. One asset may produce many
steps. A relation with no layout, an unsupported format or no location produces
no step, which leaves an unresolved opening when the graph reads it. `formats`
restricts the accepted layouts. The planner is not an adapter; another module
contributes another ordinary planner for another format.

### `DeduplicationPlanner`

```python
DeduplicationPlanner()
```

Emits one distinct step per bound record component. It removes rows identical in
every column, including the build key and all properties. A repeated key whose
values differ is left alone. It applies to every bound component and has no
configuration.

### `MergingPlanner`

```python
MergingPlanner(configuration: MergingConfiguration)
MergingConfiguration(components: tuple[type[Node] | type[Edge[Any, Any]], ...] | None = None)
```

Emits one merge step per component in scope. It groups by build key and keeps the
minimum value for every property. `components=None` applies it to every bound
component; a tuple restricts it to those concrete `Node` and `Edge` classes.

Merging is not aggregation: `min()` is not a sum, a latest-value rule or a domain
choice. Keep deliberately distinct edge families out of scope.

| Condition | Error |
| --- | --- |
| A component is abstract, a template or not a class | `TypeError: components must be concrete Node or Edge classes` |

### `ConflictValidationPlanner`

```python
ConflictValidationPlanner(configuration: ConflictValidationConfiguration)
ConflictValidationConfiguration(fail_on_error: bool = True)
```

Emits one findings step per property and one deferred report step. For every
property of every bound component it groups by build key and looks for more than
one distinct non-null value. Nulls never create a conflict; one non-null value
beside any number of nulls is fine.

With `fail_on_error=True` (the default), any finding fails the run. With
`fail_on_error=False`, the build continues, forwards the records to later
planners, and publishes a report:

```python
from kg_build_system import execute

report = execute(plan, output_directory="build")
for artifact in report.published_artifacts:
    if artifact.type.namespace == "conflict_validation":
        print(artifact.value.findings)
```

The published value is `ConflictingNonNullValuesReport`, whose `findings` tuple
contains `ConflictingNonNullValueFinding(component, build_key, property_name,
distinct_values)`. No report is published when there are no findings.

### `FilePlanner`

```python
FilePlanner(FileConfiguration(relative_path: str))
```

Emits one deferred step that reads `ArtifactPattern.of("core", "graph", "**")` and
publishes `file/write_result`
with `nodes`, `edges` and `location`. The executor writes one JSON object per
line to `relative_path`, resolved beneath the output directory. The path must be
non-empty, relative, and must not contain `..`.

Each record contains `build_key`, `type` (the component's logical name), `kind`
(`"node"` or `"edge"`) and the component's properties. An edge also carries
`source_build_key` and `target_build_key`. A record that has not passed through a
merging step also carries `_kg_binding_symbol`. Property keys are sorted.

The planner declares one optional runtime field, `relative_path`. Replace it
without replanning:

```python
from kg_build_system import BuildRuntime

runtime = BuildRuntime(
    component_configuration={
        "file": {"relative_path": "graph/current.jsonl"},
    },
)
```

| Condition | Error |
| --- | --- |
| The path is empty | `ValueError: file output path must be a non-empty relative path` |
| The path is absolute or contains `..` | `ValueError: file output path must be relative to the build output directory` |

### `MetaGraphPlanner`

```python
MetaGraphPlanner(MetaGraphConfiguration(
    relative_path: str = "meta_graph.json",
    example_limit: int = 3,
    include_html: bool = True,
    html_relative_path: str = "meta_graph.html",
))
```

Emits one deferred step that writes a JSON description of the effective
topology: each bound component, its abstract ancestors and endpoint categories,
its label, description, properties with logical types and descriptions, and its
record count. Counts are exact for the records that reached the executor. A
category's record count is the sum of its own and its descendants' records.

Examples are approximate: the executor reports the most common values with
`approx_top_k`, bounded by `example_limit`, and the document names that method.
`example_limit=0` omits examples. With `include_html=True`, it also writes a
self-contained HTML page drawing the same document.

Both paths are relative to the output directory and must not escape it. The
executor publishes `meta_graph/meta_graph_document` with component counts, total
nodes and edges, the document location, and the HTML location when enabled. The
configuration is compile-time; this planner has no runtime path override.

| Condition | Error |
| --- | --- |
| An output path is empty | `ValueError: <context> must be a non-empty relative path` |
| An output path is absolute or contains `..` | `ValueError: <context> must be relative to the build output directory` |
| `example_limit < 0` | `ValueError: meta-graph example limit may not be negative` |

### `Neo4jPlanner`

```python
Neo4jPlanner(Neo4jConfiguration(
    relative_directory: str = "neo4j-import",
    script_name: str = "import_neo4j.py",
    default_database: str = "neo4j",
))
```

Emits one export step per bound node and edge component and one deferred script
step. The executor writes one Parquet file per bound node component under
`nodes/`, one per bound edge component under `relationships/`, a standalone
`import_neo4j.py`, and a summary. The script invokes
`neo4j-admin database import` and needs neither this package nor a network at
run time.

The planner checks property types. It exports `bool`, `int`, `float`, `str`,
`date`, `time` and `timestamp`, plus arrays of `bool`, `int`, `float` and `str`.
It refuses `uuid` and custom-scalar properties, arrays of temporal, `uuid` or
custom-scalar items, and reserved import-field names. Every edge needs both
endpoint node components bound and exported; an edge whose declared endpoints are
abstract categories cannot be exported.

`relative_directory` may be replaced at runtime through
`component_configuration={"neo4j": {"relative_directory": ...}}`. The executor
publishes `neo4j/import_bundle` with the directory, script path, node and edge
counts, and the file lists.

| Condition | Error |
| --- | --- |
| A path is empty, absolute or contains `..` | `ValueError` naming the Neo4j output directory or script name |
| `script_name` is not a single Python filename | `ValueError: Neo4j script name must be a Python filename` |
| `default_database` is empty | `ValueError: Neo4j default database must be non-empty` |
| A property type cannot be exported | A plan-time `ValueError` naming the component and property |

## Supplied executors

| Executor | Package | Kinds |
| --- | --- | --- |
| `DuckDbExecutor` | `distribution.modules.duckdb` | `("source_relation", "duckdb")`, `("sql", "duckdb")`, `("aggregate", "duckdb")`, `("deduplication", "duckdb")`, `("merging", "duckdb")`, `("conflict_findings", "duckdb")` |
| `DuckDbResourceProvider` | `distribution.modules.duckdb` | event subscriber: opens the engine on `PipelineStarted` and provides `DuckDbService` and its `RelationService` |
| `RuntimeResources` | `distribution.modules.runtime` | event subscriber: provides output, working and temporary storage and the credential resolver |
| `PythonExecutor` | `distribution.modules.python` | `("python", "cpython")` |
| `FileExecutor` | `distribution.modules.file` | `("file", "default")` |
| `MetaGraphExecutor` | `distribution.modules.meta_graph` | `("meta_graph", "default")` |
| `Neo4jExecutor` | `distribution.modules.neo4j` | `("neo4j", "default")` |
| `ConflictReportExecutor` | `distribution.modules.conflict_validation` | `("conflict_report", "default")` |

A `StepExecutor` may return a `StepOutcome` with `SUCCEEDED` or `WARNING` to feed
downstream steps, or `FAILED` / `SKIPPED` to disrupt them. The default disrupted
policy is `skipped(context)`, which carries the failure forward without running
the step.

The runtime owns the resource providers. Each run creates a fresh `EventBus`
and `ResourceRegistry`, subscribes the providers and the frontend listeners, and
emits `PipelineStarted`. Providers publish resources into the registry while
they handle that event; the runtime refuses a duplicate exact type, validates
every executor's declared `resources`, builds one view per executor and emits
`PipelineFinished` or `PipelineHalted` so the providers dispose their resources.
An executor reads a resource with `context.resources.get(SomeResource)` and an
undeclared type raises `KeyError`. `DuckDbResourceProvider` supplies
`DuckDbService` and `RelationService`; `RuntimeResources` supplies
`OutputStorage`, `WorkingStorage`, `TemporaryStorage` and `CredentialResolver`.

`distribution.modules.runtime` exports the helpers a custom executor usually
needs: `instruction_payload(instruction)`, `output_name(given)` (an output
opening name as a `Key`), `succeeded(context, value)`, `skipped(context)`,
`RuntimeResources`, the
`OutputStorage`, `WorkingStorage` and `TemporaryStorage` protocols, and
`MappingCredentialResolver`.

## Ordering and composition

The planner tuple is the composition order. The DuckDB source planner is added
first, then the four core planners. Core is added when no supplied planner has
`component_id == "core"`; the source planner is added when no supplied planner
has `component_id == "duckdb"`.

| Rule | Result |
| --- | --- |
| Rewriting planners before output planners | Outputs publish the records the last rewriting planner produced |
| Validation before merging | Conflict validation sees parallel values before merging collapses them |
| Deduplication anywhere among rewriting planners | It only removes exact duplicates |
| Output planners last | They consume the final rewriting result |

```python
from kg_build_system.distribution import (
    ConflictValidationPlanner,
    ConflictValidationConfiguration,
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
)

planners = (
    ConflictValidationPlanner(ConflictValidationConfiguration()),
    DeduplicationPlanner(),
    FilePlanner(FileConfiguration("graph.jsonl")),
)
```

A rewriting planner after an output planner may leave the two seeing different
records. If an ordinary output has no reader, assembly fails with
`nothing reads ...`. Two steps with one identity fail assembly. Several planners
may share one `component_id` when their `version` and `runtime_fields` agree;
the component is published once.

Several bindings may target one component. The core planners union their records
into that component's single stream; this is not two competing producers.

## Artifacts and publications

A publication is a value handed to the build itself rather than to another step.
It appears in `WorkflowReport.published_artifacts` as an entry with `type`
(namespace and name) and `value`. The supplied publications are:

| Publication | Value |
| --- | --- |
| `file/write_result` | `nodes`, `edges`, `location` |
| `meta_graph/meta_graph_document` | Component counts, totals, document location, optional HTML location |
| `neo4j/import_bundle` | Directory, script, node and edge counts, node and relationship file lists |
| `conflict_validation/report` | `ConflictingNonNullValuesReport` whose `findings` tuple names each conflict |

Output executors publish summaries, not the graph itself. A composition may
include more than one output planner; each writes its own artifact from the
records it receives.

## Runtime configuration

A planner may declare runtime fields. `BuildRuntime.component_configuration`
supplies them by component id:

```python
from kg_build_system import BuildRuntime

runtime = BuildRuntime(
    component_configuration={
        "file": {"relative_path": "graph/current.jsonl"},
        "neo4j": {"relative_directory": "neo4j/current"},
    },
)
```

Runtime configuration is validated before any step runs. It is not part of the
plan. The top-level keys are plan component ids, not planner class names.
Resource-provider settings live in `BuildRuntime.provider_configuration`; the
`duckdb` engine settings are a provider entry, not a component entry.

## Adding a planner or executor

A custom planner and executor are ordinary objects that satisfy the kernel
protocols. Add the planner to the toolchain and the executor to its executor
sequence:

```python
from kg_build_system import default_toolchain

toolchain = default_toolchain(planners=(MyPlanner(),))
toolchain = toolchain.with_executors((*toolchain.executors, MyExecutor()))
```

`with_planners` and `with_executors` replace the sequence. `default_toolchain`
adds the generic DuckDB source planner, the four core planners and the default
executors. Register any new
`ResourceProvider` on the runtime that executes the plan. See
[Write an extension](../how-to/custom-extensions.md) for a complete example.

## What to remember

- A build is the generic DuckDB source planner plus the four core planners plus
the planners you compose.
- Composition order is priority order; rewriting planners come first and output
  planners last.
- Planner configuration is compile-time; runtime fields are for paths and similar
  execution settings.
- An executor owns exact instruction kinds and declares the resources it reads;
  an unclaimed kind is refused before execution.
- Two bindings to one component are unioned; planners sharing a `component_id`
  must agree on version and runtime fields.
- Output executors publish summaries and write their own files.

Related: [Planners and executors](../concepts/planners-and-executors.md),
[Compile](compile.md),
[Compile, execute and outputs](../concepts/build-and-outputs.md),
[Bindings](bindings.md), [Reference index](index.md).
