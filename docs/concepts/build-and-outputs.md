# Compile, execute and outputs

A build turns declarations into a `GraphBlueprint`, compiles that with a planner
composition into a `WorkflowPlan`, executes the plan, and writes outputs and a
report.

The three steps keep separate questions separate: what the graph is made from,
what this build will do, and what actually happened. The first two do not read
data.

## The three steps

| Step | Result | Reads data? | Use it to |
| --- | --- | --- | --- |
| `create_blueprint` | a `GraphBlueprint` | no | inspect, store or test the declarations |
| `compile` | a `WorkflowPlan` | no | plan one planner composition against a blueprint |
| `execute` | a `WorkflowReport` and files | yes | execute the plan and publish outputs |

```python
from kg_build_system import compile, create_blueprint, execute
from kg_build_system.distribution import (
    FileConfiguration,
    FilePlanner,
    MetaGraphPlanner,
)

planners = (
    FilePlanner(FileConfiguration("graph.jsonl")),
    MetaGraphPlanner(),
)

blueprint = create_blueprint()
plan = compile(blueprint=blueprint, planners=planners)
report = execute(plan, output_directory="build")
```

`create_blueprint` is useful when you want to inspect or store the
declaration-level description. A normal build calls `compile` directly:

```python
plan = compile(planners=planners)
report = execute(plan, output_directory="build")
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

The language DTOs are internal to the language packages. `GraphBlueprint` is the
public handle. Cross-symbol fields are role-typed references such as `NodeRef`,
`FieldRef` and `OperationRef`, not bare names.

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

## From blueprint to a workflow plan

`compile` reads an existing blueprint and a planner composition:

```python
from kg_build_system import compile
from kg_build_system.distribution import (
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
)

plan = compile(
    blueprint=blueprint,
    planners=(
        DeduplicationPlanner(),
        FilePlanner(FileConfiguration("graph.jsonl")),
    ),
)
```

`compile` is also the shortcut. It creates the blueprint when it is not supplied,
adds the five core planners when no supplied planner has `component_id == "core"`,
and appends the planners you pass. It returns a `WorkflowPlan`.

Compilation checks everything that can be checked without reading data:

- every binding targets a concrete component;
- every declared property is mapped exactly once;
- every expression names a known table or projection field;
- build keys are non-null scalars;
- edge endpoints exist, are concrete and descend from the declared categories;
- every table has a source;
- every planner's compile-time configuration is valid;
- the step wiring can feed every input and read every ordinary output.

`WorkflowPlan` owns the workflow structure:

| Field | Content |
| --- | --- |
| `components` | One component per distinct component id, with its id, version and runtime fields |
| `steps` | The scheduled instructions with typed inputs and outputs |
| `connections` | Resolved connections between step openings |
| `provenance` | Opaque JSON recorded by compilation |

A `Step` owns its inputs, outputs, `assembly_preference` and one
`Instruction(kind, payload)`. SQL is one instruction kind, not a plan field. The
step's identity is derived from its facts as `StepId(component, name)`; an
opening is `OpeningId(step, direction, name)`, so an input and an output named
`value` are different openings. An input declares an `ArtifactPattern`; an output
and a publication name a concrete `ArtifactType`.

## Running a build

`execute` consumes the plan and writes everything the plan publishes to an output
directory:

```python
from kg_build_system import BuildRuntime, execute

runtime = BuildRuntime(duckdb_storage="disk", duckdb_threads=4)
report = execute(plan, runtime=runtime, output_directory="build")
```

`output_directory` is required. A relative planner output path is resolved
beneath it and must not escape it.

`BuildRuntime` carries settings about how the build runs, not what the graph
means:

- `credentials` maps a credential reference to its value. A source binding stores
  the reference; secrets do not enter the plan or the report.
- `component_configuration` supplies runtime values for fields a component
  declared. Its keys must name plan components. Unknown fields, missing required
  fields and values of the wrong type stop the run before any step executes.
- `provider_configuration` holds resource-provider settings. `duckdb_storage`
  chooses `"memory"` or `"disk"`; `duckdb_compression`,
  `duckdb_memory_limit` and `duckdb_threads` tune execution.

`execute` dispatches each step by the exact `InstructionKind` in
`step.instruction.kind`. A kind the toolchain does not register is refused before
any step runs. The runtime
opens the registered resource providers, gives each executor only the resource
types it declared, and closes the providers in reverse order when the run ends.

## Durability and implementation versions

A workflow plan is durable data only in the environment that has executors for
every instruction kind it contains. A plan names each component id and version,
and each step carries an exact instruction kind. When `execute` starts, it builds
the kind map and refuses an unregistered kind.

The framework has no schema compatibility, version negotiation or migration path.
A stored plan is reproducible only where the same executors and instruction
payload readers are available. Changing a planner, an executor or the framework
means compiling again.

## What a build writes

| Path | Written by | Contents |
| --- | --- | --- |
| `workflow_plan.json` | `execute` | the plan that was executed |
| `build_report.json` | `execute` | published artifacts, failures and provenance |
| the configured `FilePlanner` path | `FileExecutor` | one JSON object per graph record |
| `meta_graph.json` | `MetaGraphExecutor` | the effective topology with counts and example values |
| `meta_graph.html` | `MetaGraphExecutor` | a self-contained diagram of the same document, when enabled |
| `neo4j-import/` | `Neo4jExecutor` | Parquet files and a standalone import script |
| `_workdir/` | the runtime | working storage, normally empty after a build |

`workflow_plan.json` is written before execution starts, so it exists even when
the run fails. `build_report.json` is written after a completed run.

Only the planners you compose publish files. Core's graph records are ordinary
outputs, so a composition must include a planner that reads them; otherwise
assembly fails rather than silently writing nothing.

### The graph file

`FileExecutor` writes one JSON object per line. Each line contains `build_key`,
`type` (the component's logical name), `kind` (`node` or `edge`) and the
component's properties. An edge also carries `source_build_key` and
`target_build_key`. A record that has not passed through a merging step carries
`_kg_binding_symbol`, the binding that produced it.

### The meta-graph

`MetaGraphExecutor` writes a document of the effective topology: every component
a binding targets, its abstract ancestors and endpoint categories, its label,
description, properties with logical types and descriptions, record counts and
example values. Counts are exact for the records that reached the executor.
Examples are approximate: the executor uses `approx_top_k`, bounded by
`example_limit`.

### The Neo4j bundle

`Neo4jExecutor` writes one Parquet file per bound node under `nodes/`, one per
bound edge under `relationships/`, and `import_neo4j.py`. The script invokes
`neo4j-admin database import` and needs neither this package nor a network at run
time.

## The report

`execute` returns a `WorkflowReport`:

```python
if not report.succeeded:
    for failure in report.unresolved_failures:
        print(failure.step_id, failure.message)
```

- `succeeded` is true when `unresolved_failures` is empty.
- `unresolved_failures` lists failures that blocked a publication.
- `recovered_failures` lists failures that a later step handled.
- `published_artifacts` lists one entry per published value.
- `provenance` records the plan provenance.

Each failure exposes `message`, a typed `step_id` and `exception_type`. A problem inside
a step becomes a failure in the report. A failure before execution raises.

## Limits

- A plan is durable only for the exact instruction kinds and executors it names.
  There is no migration path.
- A plan is one planner composition. A different composition needs a different
  plan.
- Meta-graph counts reflect the records that reached the executor.
- Only composed output planners publish. There is no implicit graph file.
- Planner output paths are relative to the output directory and must not escape
  it.
- Compilation catches declaration and composition problems; source and step
  failures appear in the report.

## Next steps

- [Planners and executors](planners-and-executors.md) explains how to choose and order the stages
  that produce these outputs.
- [Semantics and annotations](semantics.md) explains what the meta-graph
  publishes about meaning.

## Reference

- [Compile and execution reference](../reference/compile.md) lists the entry
  points, plan fields, runtime settings and error messages.
- [Planners and executors reference](../reference/planners-and-executors.md) lists each supplied
  planner and executor, its configuration and the artifacts it publishes.
