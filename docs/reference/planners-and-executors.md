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
    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome: ...
```

`component_id` is the planner's identity in the plan. `version` and
`runtime_fields` are published in the planner's `Component`. `kinds` is the set
of exact tuples the executor handles. The kernel refuses a duplicate
`component_id`, a duplicate step identity, a duplicate executor kind, and a plan
instruction with no executor.

## Supplied planners

| Planner | Package | `component_id` | Configuration |
| --- | --- | --- | --- |
| `CorePlanner` | `distribution.planners.core` | `core` | none; optional `engine` SQL emitter |
| `DeduplicationPlanner` | `distribution.planners.deduplication` | `deduplication` | none |
| `MergingPlanner` | `distribution.planners.merging` | `merging` | `MergingConfiguration(components=None)` |
| `ConflictValidationPlanner` | `distribution.planners.conflict_validation` | `conflict_validation` | `ConflictValidationConfiguration(fail_on_error=True)` |
| `FilePlanner` | `distribution.executors.file` | `file` | `FileConfiguration(relative_path)` |
| `MetaGraphPlanner` | `distribution.executors.meta_graph` | `meta_graph` | `MetaGraphConfiguration(...)` |
| `Neo4jPlanner` | `distribution.executors.neo4j` | `neo4j` | `Neo4jConfiguration(...)` |

### `CorePlanner`

```python
CorePlanner(*, engine: DuckDbSqlEmitter | None = None)
```

Emits source, row-source, projection, binding and aggregate steps. Its SQL steps
use `("sql", "duckdb")`. `compile` adds it before your planners when no planner
reports `component_id == "core"`.

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

Emits one deferred step that reads `core/graph.*` and publishes `file/write_result`
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
| `DuckDbExecutor` | `distribution.executors.duckdb` | `("source_relation", "duckdb")`, `("sql", "duckdb")`, `("aggregate", "duckdb")`, `("deduplication", "duckdb")`, `("merging", "duckdb")`, `("conflict_findings", "duckdb")` |
| `DuckDbResourceProvider` | `distribution.executors.duckdb` | creates relations, working storage, temporary storage, credentials and the engine session |
| `PythonExecutor` | `distribution.executors.python` | `("python", "cpython")` |
| `FileExecutor` | `distribution.executors.file` | `("file", "default")` |
| `MetaGraphExecutor` | `distribution.executors.meta_graph` | `("meta_graph", "default")` |
| `Neo4jExecutor` | `distribution.executors.neo4j` | `("neo4j", "default")` |
| `ConflictReportExecutor` | `distribution.executors.conflict_validation` | `("conflict_report", "default")` |

A `StepExecutor` may return a `StepOutcome` with `SUCCEEDED` or `WARNING` to feed
downstream steps, or `FAILED` / `SKIPPED` to disrupt them. The default disrupted
policy is `skipped(context)`, which carries the failure forward without running
the step.

`DuckDbResourceProvider` creates the execution services every distribution
executor receives: `relations`, `output_storage`, `working_storage`,
`temporary_storage`, `credentials`, `logger` and the engine. `execute` closes the
services exactly once, including when the run raises.

`distribution.executors.runtime` exports the helpers a custom executor usually
needs: `execution_services(context)`, `instruction_payload(instruction)`,
`output_name(given)`, `succeeded(context, value)`, `skipped(context)`, the local
working and temporary storage classes, and `MappingCredentialResolver`.

## Ordering and composition

The planner tuple is the composition order. The core planner is added before the
supplied planners when it is absent.

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
`nothing reads ...`. Two planners with one `component_id` fail with
`workflow component IDs must be unique`. Two steps with one identity fail
assembly.

Several bindings may target one component. The core planner unions their records
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
plan. The top-level keys are component ids, not planner class names.

## Adding a planner or executor

A custom planner and executor are ordinary objects that satisfy the kernel
protocols. Add the planner to the toolchain and the executor to its executor
sequence:

```python
from kg_build_system.distribution import default_toolchain

toolchain = default_toolchain(planners=(MyPlanner(),))
toolchain = toolchain.with_executors((*toolchain.executors, MyExecutor()))
```

`with_planners` and `with_executors` replace the sequence. `default_toolchain`
adds the core planner and the default executors. See
[Write an extension](../how-to/custom-extensions.md) for a complete example.

## What to remember

- A build is the core planner plus the planners you compose.
- Composition order is priority order; rewriting planners come first and output
  planners last.
- Planner configuration is compile-time; runtime fields are for paths and similar
  execution settings.
- An executor owns exact instruction kinds; an unclaimed kind is refused before
  execution.
- Two bindings to one component are unioned; two planners with one
  `component_id` fail.
- Output executors publish summaries and write their own files.

Related: [Planners and executors](../concepts/planners-and-executors.md),
[Compile](compile.md),
[Compile, execute and outputs](../concepts/build-and-outputs.md),
[Bindings](bindings.md), [Reference index](index.md).
