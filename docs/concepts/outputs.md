# Outputs

A build has three public calls, and each stops at a different point: `compile`
freezes the declaration into a contract, `create_blueprint` stops one step
earlier and hands back the validated declarations, and `build` executes a
contract and writes files. The split exists so an author can inspect or test the
plan without touching data, ship the same plan to several targets, and tell a
consumer which build produced an artifact.

```python
from kg_build_system import build, compile, create_blueprint
from kg_build_system.modules import (
    FileModule, FileModuleConfiguration, MetaGraphModule, register_module,
)

modules = (
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    register_module(MetaGraphModule),
)

blueprint = create_blueprint(modules=modules)
contract = compile(modules=modules)
report = build(contract, output_directory="build")
```

The bare calls read the calling file's package namespace: every module-level
binding and source object declared there is discovered. Pass
`namespace_path="path/to/package"` to discover another namespace, or pass
explicit `bindings=` and `sources=` instead. `compile` additionally accepts
`blueprint=` to freeze a blueprint you made earlier.

Every call also takes `modules=`. That sequence is the complete module
composition. Its order sets the priority of each stage: a reader takes the
freshest rewriting result available, and output modules belong last. Two
*bindings* to one component are not competing producers: the core module unions
their records into one stream. Two *modules* producing the same artifact type
would make the wiring ambiguous and fail compilation. The core module is
appended automatically and is not something you register.

## `compile` versus `create_blueprint`

| | `create_blueprint` | `compile` | `build` |
| --- | --- | --- | --- |
| Reads declarations | Yes | Yes | No |
| Returns | a frozen blueprint | a frozen contract | `WorkflowReport` |
| Runs steps | No | No | Yes |
| Writes files | No | No | Yes |
| Safe to store and inspect | Yes | Yes | Result only |

`create_blueprint` validates the declarations and returns a frozen description
of the reached tables, projections, topology, bindings, sources and configured
modules. It requires at least one graph component and one binding. It is for
inspection, tooling and tests. `compile` goes further: it turns those
declarations into the executable contract that `build` consumes. Normal builds
call `compile` directly.

Discovery may import declarations the build never uses. The blueprint contains
only what a binding reaches: its row source and expressions, projection
dependencies, target components and their ancestors and endpoints, used structs,
and the sources those tables require.

!!! note "The contract is the build input"

    A contract is immutable and self-contained data. Building it again does not
    re-read your Python declarations, so a stored contract can be executed later
    without recompiling. It records module references and configuration as data,
    not live Python module objects.

    Its durability is tied to those implementations: `build` requires each
    module's current `VERSION` to match the version compiled into the contract,
    and the framework has no schema compatibility, negotiation or migration
    path. Keep the contract with the code and module versions that produced it;
    recompile when either changes.

## What a build writes

`build(contract, output_directory="build")` resolves the output directory,
creates it, and writes the contract before execution starts:

| Path | Written by | Contents |
| --- | --- | --- |
| `workflow_contract.json` | `build` | The frozen contract, including the workflow fingerprint |
| `build_report.json` | `build` | Published artifacts, failures and provenance |
| `graph.jsonl` (configured path) | `FileModule` | One JSON object per graph record |
| `meta_graph.json` | `MetaGraphModule` | Effective topology with counts and example values |
| `meta_graph.html` | `MetaGraphModule` | Self-contained diagram of that document |
| `neo4j-import/` | `Neo4jModule` | Parquet files and a standalone import script |
| `_workdir/` | Build runtime | Working directory; normally empty after a build |

`workflow_contract.json` is always written. `build_report.json` is written when
execution finishes; if the build raises before that, the contract is on disk
but the report is not.

Relative paths passed to modules are resolved beneath the output directory.
`working_directory` defaults to `_workdir` beneath it; a relative
`working_directory` argument is resolved there too.

## The output modules

### `FileModule`

Writes one JSON Lines file. Each line is one node or edge record, with
`build_key`, `type` (the component's logical name), `kind` (`"node"` or
`"edge"`) and its properties. Edge records also carry `source_build_key` and
`target_build_key`. A record that has not passed through a merging stage also
carries `_kg_binding_symbol`, the binding that produced it. Property values are
written in canonical form: booleans, numbers and strings unchanged; dates,
times, timestamps and UUIDs as their canonical text; `null` as JSON `null`. Keys
are sorted, so the file is stable across runs.

The module publishes a summary artifact with `nodes`, `edges` and `location`.
The output path is the registration configuration's `relative_path`, which can
be replaced at runtime.

### `MetaGraphModule`

Writes `meta_graph.json`, a document of the effective topology: each node and
edge component a binding targets, its abstract ancestors, its label,
description, properties with logical types and descriptions, record counts, and
example property values. Counts are exact for the records that reached the
module. Example values are approximate: they are the most common values reported
by `approx_top_k`, bounded by `example_limit`, and the document names that
method. Abstract categories carry summed exact counts and pooled inherited
examples because they emit no rows of their own. With `include_html=True` it
also writes a self-contained `meta_graph.html` drawing the same topology.

Configuration covers `relative_path`, `example_limit`, `include_html` and
`html_relative_path`. Setting `example_limit=0` disables the value queries and
leaves counts only. The module publishes the document summary as an artifact.
The descriptions and labels it shows are the ones described in
[Annotations and descriptions](annotations.md).

### `Neo4jModule`

Writes an administrative-import bundle: one Parquet file per bound node
component under `nodes/`, one per bound edge component under `relationships/`,
and `import_neo4j.py`, a standalone script that invokes `neo4j-admin database
import` and needs neither this package nor a network at run time. Node files
carry stable per-component ID spaces and `:LABEL`; relationship files carry
`:START_ID`, `:END_ID` and `:TYPE`.

```python
from kg_build_system.modules import Neo4jModule, Neo4jModuleConfiguration, register_module

neo4j = register_module(
    Neo4jModule,
    Neo4jModuleConfiguration(relative_directory="neo4j-import"),
)
```

A null property is exported as a null column value, which Neo4j imports as an
absent property. Property types the target cannot represent fail compilation
rather than being coerced. Configuration covers `relative_directory`,
`script_name` and `default_database`; the directory can be replaced at runtime.
The module publishes a bundle summary with the directory, script path, node and
edge counts and the file lists.

## Runtime configuration

Execution settings live in `BuildRuntime`, separate from the contract:

```python
from kg_build_system import BuildRuntime, build

runtime = BuildRuntime(
    module_configuration={"file": {"relative_path": "output/estate.jsonl"}},
    duckdb_storage="disk",
    duckdb_threads=4,
    duckdb_memory_limit="8GiB",
)

report = build(contract, runtime=runtime, output_directory="build")
```

- `module_configuration` maps a module ID to that module's runtime fields.
  Unknown keys, missing required keys and values of the wrong type are rejected
  before any step runs.
- `credentials` maps a credential reference to its secret value. A source
  binding stores the reference, never the secret; secrets do not enter the
  contract or the report.
- `duckdb_storage` is `"memory"` by default; `"disk"` uses an ephemeral
  database and the working directory for large builds.
- `duckdb_threads`, `duckdb_memory_limit` and `duckdb_compression` tune the
  execution engine.

Set the output directory through `build(..., output_directory=...)`. `build`
resolves that argument (default `build` under the current directory) and uses
it for the runtime, so a value placed in `BuildRuntime.output_directory` is
replaced when the build runs.

`build(..., monitor=...)` also accepts a custom `WorkflowExecutionMonitor`
object, in addition to `True`, `False` and the automatic terminal default. Use
it to stream step progress into your own CI or desktop surface.

## Reading the report

`build` returns a `WorkflowReport`:

```python
report = build(contract, output_directory="build")

if not report.succeeded:
    for failure in report.unresolved_failures:
        print(failure.module_id, failure.step_id, failure.message)
```

- `succeeded` is true when no failure affected a published artifact. A failure
  in a step that nothing published depends on is recorded in
  `recovered_failures`; one that blocks a publication is recorded in
  `unresolved_failures`.
- `published_artifacts` holds one entry per published value, with its
  `ArtifactType` and the value. The output modules publish small summaries
  rather than the graph itself.
- `provenance` records the contract fingerprints and the blueprint, plus the
  pinned time zone. The blueprint is the declaration-level record of what was
  built.

The same report is written to `build_report.json`, so a CI job can archive the
result without keeping Python objects.

## Reproducibility

The contract carries a `workflow_fingerprint`. It is derived from the frozen
workflow: the modules and their configuration, the steps and connections, and
the work each module will do. Recompiling the same declarations produces the
same fingerprint. It changes when a change alters that workflow: compiled
work, module configuration, module references or module order.

The report's provenance also carries `provenance["compile"]["blueprint_fingerprint"]`,
which covers the declarations themselves. A new annotation or description
changes the blueprint fingerprint even when the executable steps do not change.

The build pins its session time zone to UTC. Values are canonicalised wherever
a target writes text, and the meta-graph document orders components and examples
canonically. With the same input files, the same declarations and the same
module configuration, repeated builds produce the same records and the same
meta-graph document.

The fingerprints cover the build, not the data. A source file can change
without any declaration changing, so matching fingerprints do not prove
matching input data. Use them to state what was built, and your own data
versioning to state what it was built from.

## What to remember

- The contract is the self-contained build artifact; output modules decide what
  is published, and module versions bound its durability.
- `FileModule` writes JSON Lines, `MetaGraphModule` describes the graph, and
  `Neo4jModule` produces an import bundle.
- Runtime holds credentials and resources, not graph meaning.
- Fingerprints describe the build, not the input data.
- The same contract can be built repeatedly and to several targets.

Next: [Modules](modules.md) explains how build stages are composed, and
[Compile and build](build.md) follows the lifecycle in detail.
