# Compile, build and outputs

A build turns your declarations into a frozen blueprint, compiles that into an immutable contract, executes the contract, and writes outputs and a report.

The three steps keep separate questions separate: what the graph is made from, what this build will do, and what actually happened. You can inspect and test the first two without reading data, and a consumer can tell which plan produced an output.

## The three steps

| Step | Result | Reads data? | Use it to |
| --- | --- | --- | --- |
| `create_blueprint` | a frozen blueprint | no | inspect, store or test the declarations |
| `compile` | a frozen contract | no | freeze the work for one module composition |
| `build` | a `WorkflowReport` and files | yes | execute the plan and publish outputs |

```python
from kg_build_system import build, compile, create_blueprint
from kg_build_system.modules import (
    FileModule,
    FileModuleConfiguration,
    MetaGraphModule,
    register_module,
)

modules = (
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    register_module(MetaGraphModule),
)

blueprint = create_blueprint(modules=modules)
contract = compile(blueprint=blueprint, modules=modules)
report = build(contract, output_directory="build")
```

`create_blueprint` is useful when you want to inspect or store the declaration-level description. A normal build calls `compile` directly:

```python
contract = compile(modules=modules)
report = build(contract, output_directory="build")
```

## From declarations to a blueprint

A blueprint is a frozen description of what the build reaches. It contains the tables and projections a binding reads, the components those bindings target and their ancestors and endpoints, the structs those types use, the sources those tables need, and the configured modules. It has stable ordering, so it is safe to store, compare or pass to `compile`.

A blueprint must contain at least one graph component and at least one binding. An empty blueprint is refused.

You can create one in three ways:

- **This file's namespace.** With only `modules`, the framework imports the calling file's directory and collects module-level bindings and source bindings. Put the call beside the packages it describes. Discovery does not call factories, so a binding must exist as a module-level value.
- **An explicit namespace.** Pass `namespace_path` as an importable package name or a directory when the build file lives elsewhere.
- **Explicit declarations.** Pass `bindings` and `sources` together.

Only reached declarations enter the blueprint. Discovery may import a package with many declarations, but an unread table, projection or category is not published.

## From blueprint to a contract

`compile` creates a blueprint from the same three modes, or accepts one you already built. When you pass a blueprint, `modules` replaces the blueprint's module composition. This lets you describe the graph once and compile different output sets from it.

Compilation checks everything that can be checked without reading data:

- every binding targets a concrete component;
- every declared property is mapped exactly once;
- every expression names a known table or projection field;
- build keys are non-null scalars;
- edge endpoints exist, are concrete, and descend from the declared categories;
- every table has a source;
- every module's compile-time configuration is valid.

The contract is immutable and self-contained as data. It records the ordered work each module contributed and the module references needed to execute it. It contains no resolved credentials. `build` takes the contract and an optional runtime; it takes no module list.

Compilation also gives the plan an identity:

```python
print(contract.workflow_fingerprint)
```

## Running a build

`build` consumes the contract and writes everything the contract publishes to an output directory:

```python
from kg_build_system import BuildRuntime, build

runtime = BuildRuntime(duckdb_storage="disk", duckdb_threads=4)
report = build(contract, runtime=runtime, output_directory="build")
```

The output directory defaults to `build` beneath the current directory. The working directory defaults to `_workdir` beneath the output directory, and temporary storage defaults to the system temporary directory. A relative module output path is resolved beneath the output directory and must not escape it.

`BuildRuntime` carries settings about how the build runs, not what the graph means:

- `credentials` maps a credential reference to its value. A source binding stores the reference; secrets do not enter the contract or the report.
- `module_configuration` supplies runtime values for fields a module declared. Unknown fields, missing required fields and values of the wrong type stop the build before any step runs.
- `duckdb_storage` chooses `"memory"` or `"disk"`; `duckdb_compression`, `duckdb_memory_limit` and `duckdb_threads` tune execution.

`build`'s `output_directory` and `working_directory` decide where the run writes and override the same-named runtime values. Runtime settings do not change the contract or its fingerprint.

## Durability and module versions

A contract is durable data only in the environment that can execute it. It names each module by import coordinates and records the implementation version that compiled it. When `build` starts, it imports every module the contract names and requires the module's current `VERSION` to equal the version compiled into the contract. A mismatch stops the build.

The framework has no schema compatibility, version negotiation or migration path. A stored contract is reproducible only where the same module implementations and `VERSION` values are available. Changing the framework or a module means compiling again.

This is deliberate: a contract describes one exact workflow, not a family of compatible workflows.

## What a build writes

| Path | Written by | Contents |
| --- | --- | --- |
| `workflow_contract.json` | `build` | the contract that was executed, including its workflow fingerprint |
| `build_report.json` | `build` | published artifacts, failures and provenance |
| the configured `FileModule` path | `FileModule` | one JSON object per graph record |
| `meta_graph.json` | `MetaGraphModule` | the effective topology with counts and example values |
| `meta_graph.html` | `MetaGraphModule` | a self-contained diagram of the same document, when enabled |
| `neo4j-import/` | `Neo4jModule` | Parquet files and a standalone import script |
| `_workdir/` | the runtime | working storage, normally empty after a build |

`workflow_contract.json` is written before execution starts, so it exists even when the run fails. `build_report.json` is written after a completed run. If the build raises before it can write the report, the contract is on disk but the report is not.

Only registered modules publish files. Core's graph records are ordinary outputs, so a composition must include a stage that reads them; otherwise assembly fails rather than silently writing nothing.

### The graph file

`FileModule` writes one JSON object per line. Each line contains `build_key`, `type` (the component's logical name), `kind` (`node` or `edge`) and the component's properties. An edge also carries `source_build_key` and `target_build_key`. A record that has not passed through a merging stage carries `_kg_binding_symbol`, the binding that produced it.

Property keys are sorted. Booleans, numbers and strings are written unchanged; dates, times, timestamps and UUIDs use canonical text; `null` is JSON `null`. The module publishes a summary with the node count, edge count and location.

### The meta-graph

`MetaGraphModule` writes a document of the effective topology: every component a binding targets, its abstract ancestors and endpoint categories, its label, description, properties with logical types and descriptions, record counts and example values. Counts are exact for the records that reached the module. Examples are approximate: the module uses `approx_top_k`, bounded by `example_limit`, and the document names that method.

An abstract category carries inclusive counts and pooled examples from its descendants because it emits no records itself. `example_limit=0` omits examples and leaves counts only. With `include_html=True`, the module also writes a self-contained HTML page drawing the same document.

The descriptions and labels it shows are the ones described in [Semantics and annotations](semantics.md).

### The Neo4j bundle

`Neo4jModule` writes one Parquet file per bound node under `nodes/`, one per bound edge under `relationships/`, and `import_neo4j.py`. The script invokes `neo4j-admin database import` and needs neither this package nor a network at run time. Node files carry a stable component ID space and `:LABEL`; relationship files carry `:START_ID`, `:END_ID` and `:TYPE`.

A null property is exported as a null column value, which Neo4j imports as an absent property. Property types the target cannot represent fail compilation rather than being coerced. A bundle summary records the directory, script path, node and edge counts and file lists.

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
- `published_artifacts` lists one entry per published value, with its artifact type and value. Output modules publish small summaries rather than the graph itself.
- `provenance` records the contract fingerprints, the blueprint and the pinned time zone.

A problem inside a step becomes a failure in the report. A validation finding with `fail_on_error=True` is a step failure, so the build returns an unsuccessful report rather than raising. A failure before execution, such as an incompatible module version or invalid runtime configuration, raises.

The same report is written to `build_report.json`, so a CI job can archive it without keeping Python objects.

## Reproducibility

The contract's `workflow_fingerprint` identifies the executable plan. Two compilations of the same declarations and module configuration produce the same fingerprint. A new binding, a changed expression, a different module or module configuration, or a different module order changes it.

The contract records a blueprint fingerprint that covers the declarations, bindings, sources, descriptions, annotations and module registrations. A new annotation on a reached declaration changes the blueprint fingerprint even when it does not change the executable steps. The report records both fingerprints.

The build pins its session time zone to UTC and writes text values in canonical form. With the same input files, declarations and module configuration, repeated builds produce the same records and the same meta-graph document.

Fingerprints describe the build, not the data. A source file can change without any declaration changing. Matching fingerprints do not prove matching input data; use your own data versioning to state what the build read.

## Errors and diagnostics

`create_blueprint` and `compile` raise before anything is read: `TypeError` for a malformed binding, `ValueError` for a cross-declaration problem such as an unknown field or unbound table, and an assembly error when the module composition has no consistent wiring.

`build` raises when the contract cannot be executed at all, such as an incompatible module version or invalid runtime configuration. Problems inside a step become failures in the returned report instead.

## Limits

- A contract is durable only for the exact module implementations and `VERSION` values that compiled it. There is no migration path; recompile when the framework or a module changes.
- A contract is one module composition. Different module compositions need a different contract, even when the blueprint is the same.
- Fingerprints cover the plan, not the input data or the physical row order of an output.
- Meta-graph counts reflect the records that reached the module, and example values are illustrative rather than a distribution.
- Only registered modules publish. There is no implicit graph file.
- Runtime configuration can replace declared module fields and supply credentials and resources; it cannot change graph meaning or add a step.
- Module output paths are relative to the output directory and must not escape it.
- Compilation catches declaration and composition problems; source and step failures appear in the report.

## Next steps

- [Modules](modules.md) explains how to choose and order the stages that produce these outputs.
- [Semantics and annotations](semantics.md) explains what the meta-graph publishes about meaning.

## Reference

- [Compile and build reference](../reference/compile.md) lists the entry points, validation rules, contract fields, runtime settings and error messages.
- [Modules reference](../reference/modules.md) lists each supplied module, its configuration and the artifacts it publishes.
