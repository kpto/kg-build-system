# Compile, build and outputs

A build turns declarations into a `GraphBlueprint`, compiles that and a module
composition into a `WorkflowContractDTO`, executes the contract, and writes
outputs and a report.

The three steps keep separate questions separate: what the graph is made from,
what this build will do, and what actually happened. The first two do not read
data.

## The three steps

| Step | Result | Reads data? | Use it to |
| --- | --- | --- | --- |
| `create_blueprint` | a `GraphBlueprint` | no | inspect, store or test the declarations |
| `compile_blueprint` | a `WorkflowContractDTO` | no | compile one module composition against a blueprint |
| `build` | a `WorkflowReport` and files | yes | execute the plan and publish outputs |

```python
from kg_build_system import build, compile, create_blueprint
from kg_build_system.distribution import (
    FileModule,
    FileModuleConfiguration,
    MetaGraphModule,
    register_module,
)

modules = (
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    register_module(MetaGraphModule),
)

blueprint = create_blueprint()
contract = compile(blueprint=blueprint, modules=modules)
report = build(contract, output_directory="build")
```

`create_blueprint` is useful when you want to inspect or store the
declaration-level description. A normal build calls `compile` directly:

```python
contract = compile(modules=modules)
report = build(contract, output_directory="build")
```

## From declarations to a blueprint

A blueprint is a frozen description of what the build reaches. It contains the
tables and projections a binding reads, the components those bindings target and
their ancestors and endpoints, the structs those types use, and the sources those
tables need. It has stable ordering, so it is safe to store, compare or pass to
compilation.

`GraphBlueprint` has four fields:

| Field | Content |
| --- | --- |
| `graph` | nodes and edges with graph names, labels, endpoints, properties, annotations, `abstract` and `parent` |
| `data` | structs, relations, projections and sources |
| `bindings` | node and edge binding DTOs |
| `sources` | physical source bindings |

The layer DTOs are internal to the declaration packages. `GraphBlueprint` is the
public handle.

You can create one in three ways:

- **This file's namespace.** Call `create_blueprint()` with no arguments. The
  framework imports the calling file's directory and collects module-level
  bindings and source bindings.
- **An explicit namespace.** Pass `namespace_path` as an importable package name
  or a directory when the build file lives elsewhere.
- **Explicit declarations.** Pass `bindings` and `sources` together.

Only reached declarations enter the blueprint. Discovery may import a package
with many declarations, but an unread table, projection or category is not
published.

## From blueprint to a contract

`compile_blueprint` reads an existing blueprint and the module composition:

```python
from kg_build_system.pipeline.compilation import compile_blueprint

contract = compile_blueprint(blueprint, modules=modules)
```

`compile` is the shortcut. It creates the blueprint when it is not supplied and
then compiles it. It appends the core module when it is absent.

Compilation checks everything that can be checked without reading data:

- every binding targets a concrete component;
- every declared property is mapped exactly once;
- every expression names a known table or projection field;
- build keys are non-null scalars;
- edge endpoints exist, are concrete and descend from the declared categories;
- every table has a source;
- every module's compile-time configuration is valid;
- the module wiring can feed every input and read every output.

`WorkflowContractDTO` owns contributions, connections and provenance. A `StepDTO`
owns its inputs, outputs, assembly preference and one `InstructionDTO`. SQL is
one instruction kind, not a contract field. The contract DTO has no separate
public workflow-fingerprint field in this API.

## Running a build

`build` consumes the contract and writes everything the contract publishes to an
output directory:

```python
from kg_build_system import BuildRuntime, build

runtime = BuildRuntime(duckdb_storage="disk", duckdb_threads=4)
report = build(contract, runtime=runtime, output_directory="build")
```

`output_directory` is required. A relative module output path is resolved beneath
it and must not escape it.

`BuildRuntime` carries settings about how the build runs, not what the graph
means:

- `credentials` maps a credential reference to its value. A source binding stores
  the reference; secrets do not enter the contract or the report.
- `module_configuration` supplies runtime values for fields a module declared.
  Unknown fields, missing required fields and values of the wrong type stop the
  build before any step runs.
- `duckdb_storage` chooses `"memory"` or `"disk"`; `duckdb_compression`,
  `duckdb_memory_limit` and `duckdb_threads` tune execution.

`build` dispatches each step by `step.instruction.kind`. A kind the build does not
implement is refused.

## Durability and module versions

A contract is durable data only in the environment that can execute it. It names
each module by import coordinates and records the implementation version that
compiled it. When `build` starts, it imports every module the contract names and
requires the module's current `VERSION` to equal the version compiled into the
contract. A mismatch stops the build.

The framework has no schema compatibility, version negotiation or migration path.
A stored contract is reproducible only where the same module implementations and
`VERSION` values are available. Changing the framework or a module means
compiling again.

## What a build writes

| Path | Written by | Contents |
| --- | --- | --- |
| `workflow_contract.json` | `build` | the contract that was executed |
| `build_report.json` | `build` | published artifacts, failures and provenance |
| the configured `FileModule` path | `FileModule` | one JSON object per graph record |
| `meta_graph.json` | `MetaGraphModule` | the effective topology with counts and example values |
| `meta_graph.html` | `MetaGraphModule` | a self-contained diagram of the same document, when enabled |
| `neo4j-import/` | `Neo4jModule` | Parquet files and a standalone import script |
| `_workdir/` | the runtime | working storage, normally empty after a build |

`workflow_contract.json` is written before execution starts, so it exists even
when the run fails. `build_report.json` is written after a completed run.

Only registered modules publish files. Core's graph records are ordinary outputs,
so a composition must include a stage that reads them; otherwise assembly fails
rather than silently writing nothing.

### The graph file

`FileModule` writes one JSON object per line. Each line contains `build_key`,
`type` (the component's logical name), `kind` (`node` or `edge`) and the
component's properties. An edge also carries `source_build_key` and
`target_build_key`. A record that has not passed through a merging stage carries
`_kg_binding_symbol`, the binding that produced it.

### The meta-graph

`MetaGraphModule` writes a document of the effective topology: every component a
binding targets, its abstract ancestors and endpoint categories, its label,
description, properties with logical types and descriptions, record counts and
example values. Counts are exact for the records that reached the module.
Examples are approximate: the module uses `approx_top_k`, bounded by
`example_limit`.

### The Neo4j bundle

`Neo4jModule` writes one Parquet file per bound node under `nodes/`, one per bound
edge under `relationships/`, and `import_neo4j.py`. The script invokes
`neo4j-admin database import` and needs neither this package nor a network at run
time.

## The report

`build` returns a `WorkflowReport`:

```python
if not report.succeeded:
    for failure in report.unresolved_failures:
        print(failure.module_id, failure.message)
```

- `succeeded` is true when `unresolved_failures` is empty.
- `unresolved_failures` lists failures that blocked a publication.
- `recovered_failures` lists failures that a later step handled.
- `published_artifacts` lists one entry per published value.
- `provenance` records the contract provenance and execution facts.

A problem inside a step becomes a failure in the report. A failure before
execution raises.

## Limits

- A contract is durable only for the exact module implementations and `VERSION`
  values that compiled it. There is no migration path.
- A contract is one module composition. Different module compositions need a
  different contract.
- The contract DTO has no public workflow-fingerprint field.
- Meta-graph counts reflect the records that reached the module.
- Only registered modules publish. There is no implicit graph file.
- Module output paths are relative to the output directory and must not escape it.
- Compilation catches declaration and composition problems; source and step
  failures appear in the report.

## Next steps

- [Modules](modules.md) explains how to choose and order the stages that produce
  these outputs.
- [Semantics and annotations](semantics.md) explains what the meta-graph
  publishes about meaning.

## Reference

- [Compile and build reference](../reference/compile.md) lists the entry points,
  contract fields, runtime settings and error messages.
- [Modules reference](../reference/modules.md) lists each supplied module, its
  configuration and the artifacts it publishes.
