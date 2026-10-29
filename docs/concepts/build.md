# Compile and build

A build has three separate steps:

| Call | Result | Runs anything? |
| --- | --- | --- |
| `create_blueprint` | a frozen blueprint | no |
| `compile` | a frozen contract | no |
| `build` | a `WorkflowReport` and files | yes |

The separation is useful. A blueprint is the complete description of what the
graph is made from; a contract adds the ordered work that a particular module
composition will do. You can compile once, inspect the contract, and run it many
times.

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
report = build(contract, output_directory=Path("build"))
```

`create_blueprint` is for inspection, storage, or passing an already-built
blueprint back to `compile`.

## Creating a blueprint

`create_blueprint` needs `modules` and one declaration source. There are three
modes.

**This file's namespace.** When only `modules` is given, the framework imports
the calling file's directory and discovers module-level binding and source
objects. Put the call in the project's `build.py`, beside the packages it
describes:

```python
def make_blueprint():
    return create_blueprint(modules=modules)
```

**An explicit namespace.** Pass an importable package name or directory when the
build file lives elsewhere:

```python
blueprint = create_blueprint(
    namespace_path=Path("graph_pipeline"),
    modules=modules,
)
```

Discovery imports Python modules recursively and collects bindings and source
bindings. It does not call factories, so a binding must exist as a module-level
value, not only inside a function.

**Explicit declarations.** Pass both `bindings` and `sources`:

```python
blueprint = create_blueprint(
    bindings=(site_binding,),
    sources=(site_source,),
    modules=modules,
)
```

`bindings` and `sources` must be supplied together. Every table the bindings read
must have exactly one physical source by the time you compile.

The result is a frozen, portable description with stable ordering. Its
attributes expose the tables, projections, components, bindings and sources; see
[Debugging](../guides/debugging.md#inspecting-a-blueprint) for how to read them.
The environment that later compiles or runs a build must still provide the
module implementations the description names. It is a build artifact, not a
hand-edited configuration file.

## Compiling a contract

`compile` creates the blueprint from the same three modes, or accepts one you
already built:

```python
contract = compile(
    blueprint=blueprint,
    modules=modules,
)
```

When a blueprint is supplied, `modules` replaces the blueprint's module
composition. This lets you describe the graph once and compile different output
sets from it. The contract always contains the core module and every module you
registered; `build` takes no module list.

Compilation does everything that can be checked without reading data:

- every binding targets a concrete component;
- every declared property is mapped exactly once;
- every expression names a known table or projection field;
- keys are non-null scalars;
- edge endpoints exist, are concrete, and descend from the declared categories;
- every table has a source;
- every module's compile-time configuration is valid.

The contract is immutable and self-contained, with no resolved credentials. It
records the frozen work each module contributed and identifies itself by
fingerprint:

```python
print(contract.workflow_fingerprint)
```

## Running a build

`build` consumes only the contract and, optionally, a `BuildRuntime`:

```python
from kg_build_system import build

report = build(
    contract,
    output_directory=Path("build"),
    monitor=False,
)
```

`monitor=False` disables the progress display. On a terminal it is enabled
automatically; `monitor=True` forces it even when output is redirected.

The output directory receives everything the contract publishes. It defaults to
`build` beneath the current working directory:

```text
build/
  workflow_contract.json   # the contract that was executed
  build_report.json        # artifacts and failures after the run
  graph.jsonl              # written by FileModule
  meta_graph.json          # written by MetaGraphModule
  neo4j-import/            # written by Neo4jModule
```

Not every file appears in every build; only registered modules publish anything.
`workflow_contract.json` is written before execution, so it exists even when the
run fails; `build_report.json` is written after a completed run.

The working directory defaults to `_workdir` beneath the output directory.
Relative working paths resolve there. Temporary storage defaults to the system
temporary directory. `build` also accepts `working_directory` and
`temporary_directory` explicitly.

## Runtime configuration

`BuildRuntime` carries settings that describe how the build runs, not what the
graph means.

| Field | Default | Meaning |
| --- | --- | --- |
| `credentials` | `{}` | resolved credential values by reference |
| `module_configuration` | `{}` | per-module runtime overrides |
| `duckdb_storage` | `"memory"` | `"memory"` or `"disk"` |
| `duckdb_compression` | `True` | column compression |
| `duckdb_memory_limit` | platform default | a size such as `"4GiB"` |
| `duckdb_threads` | platform default | query parallelism |

```python
from kg_build_system import BuildRuntime

runtime = BuildRuntime(
    duckdb_storage="disk",
    duckdb_memory_limit="4GiB",
    duckdb_threads=4,
    module_configuration={"file": {"relative_path": "graph/current.jsonl"}},
)
report = build(contract, runtime, output_directory=Path("out"))
```

Use `duckdb_storage="disk"` for a graph too large to keep comfortably in memory.
`build`'s `output_directory` and `working_directory` arguments decide where a
run writes, and override the same-named `BuildRuntime` fields. When
`temporary_directory` is omitted, the runtime's value is used. The defaults are
`build`, `_workdir` beneath it, and the system temporary directory.

Credentials named by a source binding are resolved through `runtime.credentials`.
The contract contains only the reference, never the value. A missing credential
fails the step that needs it.

## Reproducibility and fingerprints

Two compilations of the same declarations and module configuration produce the
same `workflow_fingerprint`:

```python
first = compile(modules=modules)
second = compile(modules=modules)
assert first.workflow_fingerprint == second.workflow_fingerprint
```

The fingerprint covers the executable plan: the bindings and expressions, the
module composition and each module's configuration. It does not cover the
physical row order of an output. Treat it as an identity for the plan, not as a
checksum of the bytes in `graph.jsonl`.

The compile-time blueprint has its own fingerprint at
`contract.provenance["compile"]["blueprint_fingerprint"]`, covering the
declarations themselves, including descriptions and annotations.

After a build, `report.provenance["workflow_fingerprint"]` records which plan
produced the report, alongside the blueprint fingerprint and the DuckDB settings
that were in force. `build_report.json` contains the same information.

Changes that alter the plan produce a different fingerprint: a new binding, a
changed expression, a different module or module configuration, or a different
module order. Credentials and runtime-only overrides do not, because they are not
part of the contract.

## Errors and diagnostics

`create_blueprint` and `compile` raise before anything is read: `TypeError` for
a malformed binding such as a nullable key, `ValueError` for cross-declaration
problems such as an unknown field or unbound table, and an assembly error when the
module composition has no consistent wiring.

`build` raises when the contract cannot be executed at all: an incompatible
module version or invalid runtime configuration. Problems inside a step, such as
a source that cannot be opened as its declared format, become failures in the
returned report:

```python
if not report.succeeded:
    for failure in report.unresolved_failures:
        print(failure.module_id, failure.message)
```

`report.recovered_failures` lists failures that a later step handled.
`report.published_artifacts` lists what the modules published, such as record
counts and report documents. A validation finding with `fail_on_error=True` is a
step failure, so the build returns an unsuccessful report rather than raising.

## What to remember

- `create_blueprint` validates declarations, `compile` freezes the work, and
  `build` executes it.
- Compilation checks everything that does not need data.
- Module composition belongs to compile, not build.
- Runtime configuration supplies credentials and resources; it does not change
  the contract.
- A failed step yields a report; a failure before execution raises.

The debugging guide covers the common messages and how to inspect a blueprint or
contract: [Debugging](../guides/debugging.md).

Related pages: [Modules](modules.md), [Outputs](outputs.md), and the
[public API](../reference/api.md).
