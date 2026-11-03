# Compile and execute

`create_blueprint` collects declarations into a `GraphBlueprint`. `compile`
compiles a blueprint with a planner composition into a `WorkflowPlan`. `execute`
runs the plan and writes its outputs.

The calls separate inspection from execution. A blueprint describes the graph
model; a workflow plan describes the ordered work of one planner composition.
Neither reads data. See
[Compile, execute and outputs](../concepts/build-and-outputs.md).

```python
from pathlib import Path

from kg_build_system import compile, create_blueprint, execute
from kg_build_system.distribution import FileConfiguration, FilePlanner

planners = (FilePlanner(FileConfiguration("graph.jsonl")),)

blueprint = create_blueprint(namespace_path=Path("graph_pipeline"))
plan = compile(blueprint=blueprint, planners=planners)

# The shortcut creates the blueprint and compiles it:
plan = compile(namespace_path=Path("graph_pipeline"), planners=planners)

report = execute(plan, output_directory=Path("build"))
```

| Call | Inputs | Returns | Reads data | Writes files |
| --- | --- | --- | --- | --- |
| `create_blueprint` | One declaration mode and optional languages | `GraphBlueprint` | No | No |
| `compile` | One declaration mode or a blueprint, plus planners or a toolchain | `WorkflowPlan` | No | No |
| `execute` | A plan, an output directory and an optional runtime or toolchain | `WorkflowReport` | Yes | Yes |

## `create_blueprint`

```python
create_blueprint(
    *,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] = (),
    sources: Sequence[BoundSource] = (),
    languages: Sequence[Language] | None = None,
) -> GraphBlueprint
```

`create_blueprint` takes no planners. It collects declarations through the
selected languages, links the layers and validates the result.

| Argument | Meaning |
| --- | --- |
| `namespace_path` | An importable package name or directory to discover |
| `bindings` | Explicit bindings; supply together with `sources` |
| `sources` | Explicit source bindings; supply together with `bindings` |
| `languages` | Language composition; defaults to table, topology and binding |

There are three declaration modes:

| Mode | Arguments | Discovery |
| --- | --- | --- |
| Calling file | none | Imports the calling file's directory recursively and collects module-level binding and source values |
| Explicit namespace | `namespace_path=...` | Imports that package or directory |
| Explicit declarations | `bindings=(...), sources=(...)` | Uses exactly the supplied values |

`namespace_path` cannot be combined with `bindings` or `sources`. `bindings` and
`sources` must be supplied together.

```python
blueprint = create_blueprint(
    namespace_path=Path("graph_pipeline"),
)
```

Only reached declarations enter the blueprint: the tables and projections a
binding reads, the components it targets and their ancestors and endpoints, the
structs those types use, and the sources those tables need.

`GraphBlueprint` has four fields:

| Field | Content |
| --- | --- |
| `graph` | `GraphPartDTO`: nodes and edges with graph names, labels, endpoints, properties, annotations, `abstract` and `parent` |
| `data` | `DataPartDTO`: structs, relations, projections and sources |
| `bindings` | `NodeBindingDTO` and `EdgeBindingDTO` values |
| `sources` | `SourceDTO` values for physical source bindings |

The layer DTOs are internal to the language packages. `GraphBlueprint` is the
public handle; `graph`, `data`, `bindings` and `sources` reference internal layer
DTOs.

## `compile`

```python
compile(
    *,
    blueprint: GraphBlueprint | None = None,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] | None = None,
    sources: Sequence[BoundSource] | None = None,
    planners: Sequence[Planner] = (),
    toolchain: Toolchain[GraphBlueprint] | None = None,
    engine: DuckDbSqlEmitter | None = None,
) -> WorkflowPlan
```

`compile` reads the blueprint exactly as given, or creates one from the
declaration mode. It never reads data.

When `toolchain` is omitted, `compile` uses `default_toolchain`, adding the core
planner unless a supplied planner already reports `component_id == "core"`, then
appends the planners you pass. When `toolchain` is supplied, it appends the
`planners` argument to that toolchain's planners.

```python
plan = compile(blueprint=blueprint, planners=planners)
```

Compilation checks everything that does not need data:

- every binding targets a concrete component;
- every declared property is mapped exactly once;
- every expression names a known table or projection field;
- keys are non-null scalars;
- edge endpoints exist, are concrete and descend from the declared categories;
- every reached table has a source;
- each planner's compile-time configuration is valid;
- the step wiring can feed every input and read every ordinary output.

`WorkflowPlan` owns the workflow structure:

| Field | Content |
| --- | --- |
| `components` | One component per planner, with its id, version and runtime fields |
| `steps` | The scheduled instructions with typed inputs and outputs |
| `connections` | Resolved connections between step openings |
| `provenance` | Opaque JSON recorded by compilation |

A `Step` owns its inputs, outputs, `assembly_preference` and one
`Instruction(kind, payload)`. Step identity is `f"{component}.{name}"`; an
opening identity is `f"{step_id}.{opening_name}"`. SQL is one instruction kind,
not a plan field.

## `execute`

```python
execute(
    plan: WorkflowPlan,
    *,
    output_directory: str | Path,
    runtime: BuildRuntime | None = None,
    toolchain: Toolchain[GraphBlueprint] | None = None,
) -> WorkflowReport
```

| Argument | Meaning |
| --- | --- |
| `plan` | The `WorkflowPlan` returned by `compile` |
| `output_directory` | Where publications, `workflow_plan.json` and `build_report.json` land |
| `runtime` | Credentials, component runtime overrides and engine settings |
| `toolchain` | The executors, resources and runtime; defaults to `DEFAULT_TOOLCHAIN` |

`execute` writes the plan before execution starts and the report after it
finishes. It dispatches each step by the exact tuple `step.instruction.kind`. A
kind the toolchain does not implement is refused before any step runs.

```python
report = execute(
    plan,
    output_directory=Path("out"),
)

if not report.succeeded:
    for failure in report.unresolved_failures:
        print(failure.step_id, failure.message)
```

A failure before execution raises. A failure inside a step becomes a report
entry.

## `BuildRuntime`

```python
BuildRuntime(
    credentials: dict[str, str] = {},
    component_configuration: dict[str, dict[str, Any]] = {},
    output_directory: Path = Path.cwd() / "build",
    working_directory: Path = Path("_workdir"),
    temporary_directory: Path | None = None,
    duckdb_storage: Literal["memory", "disk"] = "memory",
    duckdb_threads: int | None = None,
    duckdb_memory_limit: str | None = None,
    duckdb_compression: bool = True,
)
```

`BuildRuntime` supplies credentials, per-component runtime overrides and engine
settings. Runtime values are not part of the plan. A relative working directory
resolves beneath the output directory. `to_configuration()` returns the kernel
`RuntimeConfiguration` that execution reads.

The engine settings are published under the `duckdb` component id, so an
executor reads them from the same per-component map as every other component's
values.

## `WorkflowReport`

| Attribute | Meaning |
| --- | --- |
| `published_artifacts` | One entry per publication, with its type and value |
| `recovered_failures` | Failures that a later step handled |
| `unresolved_failures` | Failures that blocked a publication |
| `provenance` | The plan provenance |
| `succeeded` | True when `unresolved_failures` is empty |

Each failure exposes `message`, `step_id` and `exception_type`.

## Required inputs

| Requirement | Enforced by |
| --- | --- |
| Exactly one declaration mode | `create_blueprint` / `compile` argument checks |
| A source for every reached table | the blueprint validation inside `compile` |
| Valid compile-time configuration for every planner | each planner's `plan` |
| A wireable planner composition | kernel assembly |
| An output directory for execution | `execute` |
| An executor for every instruction kind | `Toolchain.execute` |
| Matching plans and executors at execution | `execute` |

## What to remember

- `create_blueprint` takes no planners and returns `GraphBlueprint`.
- `compile` reads a blueprint and takes planners or a toolchain; it returns a
  `WorkflowPlan`.
- `execute` runs the plan, dispatches by `step.instruction.kind` and returns a
  `WorkflowReport`.
- A step owns its `Instruction`; SQL is one instruction kind.
- `execute` writes `workflow_plan.json` before the run and `build_report.json`
  after it.

Related: [Compile, execute and outputs](../concepts/build-and-outputs.md),
[Planners and executors](planners-and-executors.md), [Bindings](bindings.md),
[Reference index](index.md).
