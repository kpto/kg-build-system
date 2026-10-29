# Compile and build

`create_blueprint` validates declarations, `compile` freezes them into an executable contract, and `build` runs that contract and writes its outputs.

The three calls separate inspection from execution. A blueprint describes what the graph is made from; a contract adds the ordered work of one module composition. Neither reads data. See [Compile, build and outputs](../concepts/build-and-outputs.md).

```python
from pathlib import Path

from kg_build_system import build, compile, create_blueprint
from kg_build_system.modules import (
    FileModule, FileModuleConfiguration, register_module,
)

modules = (
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
)

blueprint = create_blueprint(modules=modules)
contract = compile(modules=modules)
report = build(contract, output_directory=Path("build"), monitor=False)
```

| Call | Inputs | Returns | Reads data | Writes files |
| --- | --- | --- | --- | --- |
| `create_blueprint` | `modules` and one declaration mode | Frozen blueprint | No | No |
| `compile` | `modules` and one declaration mode, or a blueprint | Frozen contract | No | No |
| `build` | A contract and an optional `BuildRuntime` | `WorkflowReport` | Yes | Yes |

## `create_blueprint`

```python
create_blueprint(
    *,
    modules,
    namespace_path=None,
    bindings=None,
    sources=None,
)
```

| Argument | Meaning |
| --- | --- |
| `modules` | The module composition, as `ModuleRegistration` values; required |
| `namespace_path` | An importable package name or directory to discover |
| `bindings` | Explicit bindings; supply together with `sources` |
| `sources` | Explicit source bindings; supply together with `bindings` |

There are three declaration modes:

| Mode | Arguments | Discovery |
| --- | --- | --- |
| Calling file | `modules` only | Imports the calling file's directory recursively and collects module-level binding and source values |
| Explicit namespace | `namespace_path=...` | Imports that package or directory |
| Explicit declarations | `bindings=(...), sources=(...)` | Uses exactly the supplied values |

`namespace_path` cannot be combined with `bindings` or `sources`. `bindings` and `sources` must be supplied together.

```python
blueprint = create_blueprint(
    namespace_path=Path("graph_pipeline"),
    modules=modules,
)
```

Only reached declarations enter the blueprint: the tables and projections a binding reads, the components it targets and their ancestors and endpoints, the structs those types use, and the sources those tables need. A declaration outside that reach is not published.

The result is frozen and stably ordered. Its inspection attributes are:

| Attribute | Content |
| --- | --- |
| `components` | Reached node and edge declarations; each exposes `kind`, `name`, `abstract` and `properties` |
| `bindings` | Reached bindings; each exposes `component`, `debug_name`, `build_key`, `properties` and, for an edge, both endpoint keys |
| `tables` / `projections` | Reached logical sources and their fields |
| `structs` | Reached nested record declarations |
| `sources` | One physical source per reached table |
| `modules` | The configured module composition |

```python
for component in blueprint.components:
    print(component.kind, component.name, component.abstract)

for binding in blueprint.bindings:
    print(binding.component, binding.debug_name, binding.build_key)
```

A blueprint is a build artifact, not a hand-edited configuration file. The environment that compiles or runs it must still provide the module implementations it names.

### Errors

| Condition | Error |
| --- | --- |
| `namespace_path` is combined with explicit declarations | `ValueError: namespace_path cannot be combined with bindings or sources` |
| Only one of `bindings` and `sources` is supplied | `ValueError: bindings and sources must be supplied together` |
| The result has no component | `ValueError: blueprints require at least one graph component` |
| The result has no binding | `ValueError: blueprints require at least one graph binding` |
| The calling code has no filesystem path, such as a REPL | `RuntimeError: the calling code does not have a filesystem namespace` |
| A binding is malformed | `TypeError` naming the argument or property |
| Declarations disagree across classes | `ValueError` such as an unknown field or an incompatible target |
| A module class has no usable ID | `TypeError: workflow module classes must declare a non-empty string ID` |
| A module class is defined inside a function | `ValueError: workflow modules must be importable top-level classes` |

## `compile`

```python
compile(
    *,
    modules,
    namespace_path=None,
    bindings=None,
    sources=None,
    blueprint=None,
)
```

`compile` accepts the same three declaration modes as `create_blueprint`, or one already-built blueprint:

```python
contract = compile(blueprint=blueprint, modules=modules)
```

| Argument | Meaning |
| --- | --- |
| `modules` | The complete module composition; required in every mode |
| `namespace_path` | Discover one package or directory |
| `bindings` / `sources` | Supply both explicitly |
| `blueprint` | Compile an existing blueprint; replaces its module composition |

`blueprint` cannot be combined with `namespace_path`, `bindings` or `sources`. When a blueprint is supplied, `modules` replaces the blueprint's module composition, so one declaration snapshot can compile different output sets.

Compilation checks everything that does not need data:

- every binding targets a concrete component;
- every declared property is mapped exactly once;
- every expression names a known table or projection field;
- keys are non-null scalars;
- edge endpoints exist, are concrete, and descend from the declared categories;
- every reached table has a source;
- each module's compile-time configuration is valid;
- the module wiring can feed every input and read every output.

The contract always contains the core module and every module you registered. `build` takes no module list.

### Errors

| Condition | Error |
| --- | --- |
| `blueprint` is combined with another declaration mode | `ValueError: blueprint cannot be combined with namespace_path, bindings, or sources` |
| `namespace_path` is combined with explicit declarations | `ValueError: namespace_path cannot be combined with bindings or sources` |
| Only one of `bindings` and `sources` is supplied | `ValueError: bindings and sources must be supplied together` |
| A reached table has no source | `ValueError: no source bound for: <table>` |
| Two declarations share a name or identity | `ValueError` naming the namespace, such as `component names must be unique` |
| A binding targets a category | `ValueError: <kind> binding '<id>' may not target abstract component '<name>'` |
| The module composition cannot be wired | An assembly error naming each input or output it could not settle |

Compilation never opens a source or reads a row.

## `build`

```python
build(
    contract,
    runtime: BuildRuntime | None = None,
    *,
    output_directory: str | Path = Path("build"),
    working_directory: str | Path = Path("_workdir"),
    temporary_directory: str | Path | None = None,
    monitor: WorkflowExecutionMonitor | bool | None = None,
) -> WorkflowReport
```

| Argument | Meaning | Default |
| --- | --- | --- |
| `contract` | The frozen contract returned by `compile` | Required |
| `runtime` | Credentials, module runtime overrides and engine settings | `BuildRuntime()` |
| `output_directory` | Where publications, `workflow_contract.json` and `build_report.json` land | `build` under the current directory |
| `working_directory` | Working storage for the run | `_workdir` under the output directory |
| `temporary_directory` | Temporary storage | The runtime value, or the system temporary directory |
| `monitor` | Progress display: automatic, forced, disabled, or a custom `WorkflowExecutionMonitor` from `kg_build_system.workflow` | Automatic on a terminal |

`output_directory` and `working_directory` override the same-named `BuildRuntime` fields. A relative working directory resolves beneath the output directory.

`monitor=False` disables progress output. `monitor=True` forces it when output is redirected. An object implementing `WorkflowExecutionMonitor` receives the same lifecycle events.

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

`workflow_contract.json` is written before execution starts, so it exists even when the run fails. `build_report.json` is written after execution finishes.

### Errors

| Condition | Error |
| --- | --- |
| A module implementation version differs from the compiled one | `RuntimeError: module '<id>' implementation version '<current>' does not match compiled version '<compiled>'` |
| A module import no longer provides the compiled ID | `RuntimeError: module import does not provide '<id>'` |
| A runtime field is unknown | `ValueError: unknown runtime configuration for <id>: ...` |
| A required runtime field is missing | `ValueError: missing runtime configuration for <id>: ...` |
| A runtime field has the wrong type | `TypeError: invalid runtime configuration for <id>: ...` |
| A step fails | The failure is returned in `report.unresolved_failures` or `report.recovered_failures`; `build` does not raise for a step failure |

A failure before execution, such as an invalid runtime configuration or a module mismatch, raises. A failure inside a step becomes a report entry.

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

| Field | Meaning | Default |
| --- | --- | --- |
| `credentials` | Resolved credential values by reference | Empty |
| `module_configuration` | Per-module runtime overrides by module ID | Empty |
| `output_directory` | Default output directory; replaced by the `build` argument | Current directory plus `build` |
| `working_directory` | Working storage; a relative path resolves beneath the output directory | `_workdir` |
| `temporary_directory` | Temporary storage; `None` uses the system directory | `None` |
| `duckdb_storage` | `"memory"` or `"disk"` | `"memory"` |
| `duckdb_threads` | Query parallelism | Platform default |
| `duckdb_memory_limit` | A size such as `"4GiB"` | Platform default |
| `duckdb_compression` | Column compression | `True` |

```python
from kg_build_system import BuildRuntime, build

runtime = BuildRuntime(
    duckdb_storage="disk",
    duckdb_memory_limit="4GiB",
    duckdb_threads=4,
    module_configuration={
        "file": {"relative_path": "graph/current.jsonl"},
    },
)

report = build(contract, runtime, output_directory=Path("out"))
```

A source's credential reference is resolved through `runtime.credentials`. The contract contains only the reference, never the value. Runtime overrides do not change the contract or its fingerprint.

Unknown module runtime fields, missing required fields and values of the wrong type stop the build before any step runs.

## `WorkflowReport`

| Attribute | Type | Meaning |
| --- | --- | --- |
| `published_artifacts` | Tuple of published values | One entry per publication; each has `type` with `namespace` and `name`, and `value` |
| `recovered_failures` | Tuple of failures | Failures that a later step handled |
| `unresolved_failures` | Tuple of failures | Failures that blocked a publication |
| `provenance` | `dict` | Workflow fingerprint, compile provenance and the pinned time zone |
| `succeeded` | `bool` property | True when `unresolved_failures` is empty |

Each failure exposes `message`, `module_id`, `step_id` and `exception_type`.

```python
for artifact in report.published_artifacts:
    print(artifact.type.namespace, artifact.type.name, artifact.value)
```

A validation finding with `fail_on_error=True` is a step failure, so the build returns an unsuccessful report rather than raising.

## Contract and blueprint facts

A blueprint is frozen declaration data. A contract is frozen executable data: it contains no authoring classes and no resolved credentials. The contract identifies itself by fingerprint; the blueprint's fingerprint is derived from its declarations and recorded in the contract.

| Fact | Blueprint | Contract |
| --- | --- | --- |
| Read by | `compile` or inspection | `build` |
| Module composition | Recorded | Compiled and ordered |
| Declarations | Reached tables, projections, structs, components, bindings and sources | Recorded in provenance |
| Fingerprint | Not stored on the blueprint; carried into the contract as `provenance["compile"]["blueprint_fingerprint"]` | `contract.workflow_fingerprint` |
| Credentials | References only | References only |
| Reusable | Yes, for inspection or a later compile | Yes, while module implementations and versions match |

The workflow fingerprint covers the executable plan: the compiled binding work, expressions, module composition, each module's configuration and the module order. The blueprint fingerprint covers the declarations and the configured module composition, including descriptions and annotations. Credentials and runtime-only overrides are outside both.

Two compilations of the same declarations and module configuration produce the same workflow fingerprint:

```python
first = compile(modules=modules)
second = compile(modules=modules)
assert first.workflow_fingerprint == second.workflow_fingerprint
```

The fingerprints describe the plan, not the input data or the physical row order of an output. Matching fingerprints do not prove matching source files.

After a build, the report records both identities:

```python
print(report.provenance["workflow_fingerprint"])
print(report.provenance["compile"]["blueprint_fingerprint"])
```

`report.provenance["duckdb"]["TimeZone"]` records the build's pinned time zone. `build_report.json` contains the same information.

### Durability

A stored contract is reproducible only in an environment that supplies the same module implementations and versions. `build` imports each module the contract names and compares the running `VERSION` with the compiled one:

```text
module '<id>' implementation version '<current>' does not match compiled version '<compiled>'
```

A module whose class no longer provides its compiled ID fails with `module import does not provide '<id>'`. Changing the framework or a module means compiling again.

There is no compatibility negotiation or migration path for contracts. Keep a contract with the code and module versions that produced it.

## Required inputs

| Requirement | Enforced by |
| --- | --- |
| A `modules` sequence in every mode | A missing argument or a registration error |
| Exactly one declaration mode | `create_blueprint` / `compile` argument checks |
| At least one graph component | `create_blueprint` / `compile` |
| At least one binding | `create_blueprint` / `compile` |
| A source for every reached table | `compile` |
| Valid compile-time configuration for every module | `create_blueprint` / `compile` |
| A wireable module composition | `compile` |
| Matching module `VERSION` values at execution | `build` |

## What to remember

- `create_blueprint` validates declarations; `compile` freezes module work; `build` executes.
- A blueprint needs one component and one binding, and contains only reached declarations.
- Compilation checks everything that does not need data.
- Module composition belongs to `compile`, not `build`.
- Runtime supplies credentials and engine settings; it does not change the contract.
- A contract is durable only with the same module implementations and `VERSION` values.
- A failed step yields a report; a failure before execution raises.

Related: [Compile, build and outputs](../concepts/build-and-outputs.md), [Modules](modules.md), [Bindings](bindings.md), [Reference index](index.md).
