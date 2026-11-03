# Compile and build

`create_blueprint` collects declarations into a `GraphBlueprint`.
`compile_blueprint` compiles a blueprint and a module composition into a
`WorkflowContractDTO`. `compile` is the shortcut that creates the blueprint and
compiles it. `build` executes the contract and writes its outputs.

The calls separate inspection from execution. A blueprint describes the graph
model; a contract describes the ordered work of one module composition. Neither
reads data. See [Compile, build and outputs](../concepts/build-and-outputs.md).

```python
from pathlib import Path

from kg_build_system import build, compile, create_blueprint
from kg_build_system.distribution import (
    FileModule, FileModuleConfiguration, register_module,
)
from kg_build_system.pipeline.compilation import compile_blueprint

modules = (
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
)

blueprint = create_blueprint(namespace_path=Path("graph_pipeline"))
contract = compile_blueprint(blueprint, modules=modules)

# The shortcut creates the blueprint and compiles it:
contract = compile(namespace_path=Path("graph_pipeline"), modules=modules)

report = build(contract, output_directory=Path("build"), monitor=False)
```

| Call | Inputs | Returns | Reads data | Writes files |
| --- | --- | --- | --- | --- |
| `create_blueprint` | One declaration mode and optional languages | `GraphBlueprint` | No | No |
| `compile_blueprint` | A `GraphBlueprint` and `modules` | `WorkflowContractDTO` | No | No |
| `compile` | One declaration mode or a blueprint, plus `modules` | `WorkflowContractDTO` | No | No |
| `build` | A contract and an output directory | `WorkflowReport` | Yes | Yes |

## `create_blueprint`

```python
create_blueprint(
    *,
    namespace_path=None,
    bindings=(),
    sources=(),
    languages=None,
) -> GraphBlueprint
```

`create_blueprint` takes no modules. It collects declarations through the
selected languages, assembles the layer DTOs and validates the result.

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

The layer DTOs are internal to the declaration packages. `GraphBlueprint` is the
public handle; `graph`, `data`, `bindings` and `sources` reference internal layer
DTOs.

## `compile_blueprint`

```python
compile_blueprint(
    blueprint: GraphBlueprint,
    *,
    modules,
    engine=None,
) -> WorkflowContractDTO
```

`compile_blueprint` reads the blueprint exactly as given. It never creates a
blueprint. It compiles the modules you pass; the `compile` shortcut appends the
core module when it is absent.

```python
contract = compile_blueprint(blueprint, modules=modules)
```

Compilation checks everything that does not need data:

- every binding targets a concrete component;
- every declared property is mapped exactly once;
- every expression names a known table or projection field;
- keys are non-null scalars;
- edge endpoints exist, are concrete and descend from the declared categories;
- every reached table has a source;
- each module's compile-time configuration is valid;
- the module wiring can feed every input and read every output.

`WorkflowContractDTO` owns the workflow structure:

| Field | Content |
| --- | --- |
| `contributions` | One contribution per module, with its steps |
| `connections` | Resolved connections between step openings |
| `provenance` | Opaque JSON recorded by compilation |

A `StepDTO` owns its inputs, outputs, `assembly_preference` and one
`InstructionDTO(kind, payload)`. SQL is one instruction kind, not a contract
field. The contract DTO has no separate public workflow-fingerprint field.

## `compile`

```python
compile(
    *,
    modules=(),
    namespace_path=None,
    bindings=None,
    sources=None,
    blueprint=None,
    engine=None,
) -> WorkflowContractDTO
```

`compile` accepts the same declaration modes as `create_blueprint`, or an
existing blueprint:

```python
contract = compile(blueprint=blueprint, modules=modules)
```

`blueprint` cannot be combined with `namespace_path`, `bindings` or `sources`.
When a blueprint is supplied, `modules` is the composition compiled against it.
The shortcut appends the core module when it is absent.

Compilation never opens a source or reads a row.

## `build`

```python
build(
    contract,
    *,
    output_directory: str | Path,
    working_directory: str | Path | None = None,
    temporary_directory: str | Path | None = None,
    runtime: BuildRuntime | None = None,
    monitor=None,
) -> WorkflowReport
```

| Argument | Meaning |
| --- | --- |
| `contract` | The `WorkflowContractDTO` returned by `compile_blueprint` or `compile` |
| `output_directory` | Where publications, `workflow_contract.json` and `build_report.json` land |
| `working_directory` | Working storage; a relative path resolves beneath the output directory |
| `temporary_directory` | Temporary storage; `None` uses the runtime value or the system directory |
| `runtime` | Credentials, module runtime overrides and engine settings |
| `monitor` | Progress display: automatic, forced, disabled or a custom monitor object |

`build` dispatches each step by `step.instruction.kind`. A kind the build does not
implement is refused.

```python
report = build(
    contract,
    output_directory=Path("out"),
    monitor=False,
)

if not report.succeeded:
    for failure in report.unresolved_failures:
        print(failure.module_id, failure.step_id, failure.message)
```

`workflow_contract.json` is written before execution starts. `build_report.json`
is written after execution finishes. A failure before execution raises; a
failure inside a step becomes a report entry.

## `BuildRuntime`

```python
BuildRuntime(
    credentials: dict[str, str] = {},
    module_configuration: dict[str, dict[str, Any]] = {},
    output_directory: Path = Path.cwd() / "build",
    working_directory: Path = Path("_workdir"),
    temporary_directory: Path | None = None,
    duckdb_storage: Literal["memory", "disk"] = "memory",
    duckdb_threads: int | None = None,
    duckdb_memory_limit: str | None = None,
    duckdb_compression: bool = True,
)
```

`BuildRuntime` supplies credentials, per-module runtime overrides and engine
settings. Runtime values are not part of the contract. A relative working
directory resolves beneath the output directory.

## `WorkflowReport`

| Attribute | Meaning |
| --- | --- |
| `published_artifacts` | One entry per publication, with its type and value |
| `recovered_failures` | Failures that a later step handled |
| `unresolved_failures` | Failures that blocked a publication |
| `provenance` | Contract provenance plus execution facts |
| `succeeded` | True when `unresolved_failures` is empty |

Each failure exposes `message`, `module_id`, `step_id` and `exception_type`.

## Required inputs

| Requirement | Enforced by |
| --- | --- |
| Exactly one declaration mode | `create_blueprint` / `compile` argument checks |
| A source for every reached table | `compile_blueprint` |
| Valid compile-time configuration for every module | `compile_blueprint` |
| A wireable module composition | `compile_blueprint` |
| An output directory for execution | `build` |
| Matching module `VERSION` values at execution | `build` |

## What to remember

- `create_blueprint` takes no modules and returns `GraphBlueprint`.
- `compile_blueprint` reads a blueprint and takes the module composition.
- `compile` is the shortcut: it creates the blueprint and compiles it.
- A step owns its `InstructionDTO`; SQL is one instruction kind.
- `build` executes the contract and dispatches by `step.instruction.kind`.

Related: [Compile, build and outputs](../concepts/build-and-outputs.md),
[Modules](modules.md), [Bindings](bindings.md), [Reference index](index.md).
