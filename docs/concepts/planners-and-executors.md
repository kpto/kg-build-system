# Planners and executors

A planner decides what work the whole graph needs. An executor performs one
exact kind of instruction. Together they are the two extension points of a
build: the core module turns declarations into rows and records, and the other
modules rewrite or publish those records.

Bindings answer what one row becomes. A planner answers what happens to all
records together: removing duplicates, validating conflicts, merging parallel
facts, or writing a target. That is why a planner is chosen when you compose the
build, not when you write a binding.

## Where a planner and executor fit

A build has one plan:

```text
sources -> bindings -> core graph records -> rewriting planners -> output planners
```

The core module turns your declarations into the first graph records.
Rewriting planners consume those records and produce records again. Output
planners consume the final records and publish files or artifacts.

Every planner emits `Step` values with typed inputs and outputs. The kernel
assembles the steps into one `WorkflowPlan`. An executor is selected by the exact
instruction kind in a step.

## Composing a build

You compose planners as a tuple and pass it to `compile`:

```python
from kg_build_system import compile, execute
from kg_build_system.distribution import (
    DeduplicationPlanner,
    FileConfiguration,
    FilePlanner,
    MetaGraphPlanner,
)

plan = compile(planners=(
    DeduplicationPlanner(),
    FilePlanner(FileConfiguration("graph.jsonl")),
    MetaGraphPlanner(),
))
report = execute(plan, output_directory="build")
```

The tuple is the whole planner composition. `compile` creates the blueprint
internally, appends the five core planners when no planner claims `component_id
== "core"`, and returns a `WorkflowPlan`. `execute` later receives that plan
rather than the tuple. The bindings and sources are discovered from the calling
file, so the example shows only the planner tuple.

Planner configuration is compile-time and carried in the instruction payload.
Changing it changes the plan.

## The core planners

The core module is always present. Its five planners are added before the
planners you supply, and you do not pass them yourself. Together they read
sources, evaluate projections and bindings, and assemble each component's
records.

Several bindings may target one component. Core unions their records into that
component's single record stream, so one node type can be built from several
sources or grains. This is a normal composition, not two producers competing for
the same record. Abstract categories are not record producers, so they get no
records of their own.

The core module has five planners — `InputPlanner`, `RowSourcePlanner`,
`ProjectionPlanner`, `BindingPlanner` and `RecordsPlanner` — all with
`component_id="core"` and the same `version` and `runtime_fields`.
`core_planners()` returns them in assembled order; they share one `CorePlan` in
`PlanContext.shared["core.plan"]`. Together they emit source, row-source,
projection, binding and aggregate steps. Their SQL steps use `("sql", "duckdb")`;
the DuckDB module's `DuckDbExecutor` runs them.

## Modules

A module is a feature package under `distribution/modules/`. It groups the
planners, executors, resource providers and configuration for one feature; it is
not a protocol or a registry entry. `core`, `deduplication`, `merging`,
`conflict_validation`, `file`, `meta_graph`, `neo4j`, `duckdb`, `python` and
`runtime` are modules.

The DuckDB module is more than an executor. It supplies `DuckDbExecutor` for the
SQL kinds, `DuckDbResourceProvider` for the live engine, `DuckDbService` as the
engine resource, and `DuckDbSqlEmitter` for SQL text. The core planners use the
emitter; the executor uses the service.

## Rewriting planners

A rewriting planner consumes graph records and produces graph records. It
changes which records survive or what values they carry. It does not write a
target.

### `DeduplicationPlanner`

This planner removes rows that are identical in every column, including the
build key and all properties. A repeated key whose values differ is left alone;
use merging or fix the binding. It has no configuration and applies to every
bound record component.

### `MergingPlanner`

This planner groups records by build key and keeps the minimum value for every
property. That is sound only when the parallel rows really are one fact expressed
more than once, such as the same identifier arriving from two source partitions.

By default it applies to every bound component. Restrict it to the components
whose parallel rows are compatible:

```python
from kg_build_system.distribution import (
    MergingConfiguration,
    MergingPlanner,
)

merge_sites = MergingPlanner(MergingConfiguration(components=(SiteNode,)))
```

Components you do not name keep every row.

!!! warning "Merging is not aggregation"

    The planner keeps a minimum value; it does not sum, choose the latest value,
    or apply a domain rule. If parallel edge facts are deliberately distinct,
    keep that family out of scope and build the reduction into the binding or a
    projection instead.

### `ConflictValidationPlanner`

This planner looks at every property of every bound component. It groups by
build key and reports a finding when one property has more than one distinct
non-null value. Nulls never create a conflict: one non-null value beside any
number of nulls is fine.

With `fail_on_error=True`, the default, a finding fails the run. With
`fail_on_error=False`, the run continues, publishes a report artifact, and passes
the records on so later output planners still see them.

Each finding names the component, build key, property and number of distinct
values.

!!! warning "Validate before you merge"

    Merging has already chosen one value per key. A conflict check placed after
    merging finds nothing. Compose conflict validation before the merging
    planner when you want to discover conflicts.

## Output planners and executors

An output planner consumes final graph records and its executor publishes them
in a target format. The supplied targets cover the common destinations.

### File

`FilePlanner(FileConfiguration(relative_path))` writes one JSON object per line.
Each line carries `build_key`, `type`, `kind` and the component's properties. An
edge also carries its endpoint keys. A record that has not passed through a
merging step also carries `_kg_binding_symbol`. Keys are sorted, and temporal and
UUID values use their canonical text, so the file is readable and stable.

The path is relative to the build's output directory and must not escape it. The
executor publishes a summary with the node count, edge count and location.
`relative_path` may be replaced at runtime through
`BuildRuntime(component_configuration={"file": {"relative_path": ...}})`.

### Meta-graph

`MetaGraphPlanner(MetaGraphConfiguration(...))` writes `meta_graph.json`, a
description of the effective topology. It covers every component a binding
targets, its abstract ancestors and endpoint categories, its label and
description, its properties with logical types and descriptions, record counts
and example values.

Counts are exact for the records that reached the executor. Examples are
illustrative rather than a distribution: the executor uses `approx_top_k`,
bounded by `example_limit`. A category carries inclusive counts and pooled
examples from its descendants because it emits no records itself. With
`include_html=True`, the executor also writes a self-contained HTML diagram of
the same document.

### Neo4j

`Neo4jPlanner(Neo4jConfiguration(...))` writes one Parquet file per bound node
and edge component, a standalone `import_neo4j.py`, and a summary. The column
headers are the `neo4j-admin database import` headers, so the bundle does not
need this package at import time.

The planner checks types while it plans. It exports `bool`, `int`, `float`,
`str`, `date`, `time` and `timestamp`, plus arrays of `bool`, `int`, `float` and
`str`. It refuses `uuid` and custom-scalar properties, arrays of temporal,
`uuid` or custom-scalar items, and reserved import-field names.

!!! warning "Concrete endpoints for Neo4j"

    Every edge needs both endpoint node components bound and exported. An edge
    whose declared endpoints are abstract categories cannot be exported. Declare
    concrete endpoints for edges you intend to import.

## Ordering and composition

The planner tuple is composition order, and core is added before it. That order
is your priority order: when an output can read more than one producer of the
same record type, the last rewriting step before the output supplies the records.

For predictable results:

- pass every rewriting planner first and output planners last;
- put validation before merging;
- place `DeduplicationPlanner` anywhere among the rewriting planners;
- let the last rewriting planner before the outputs decide what they publish;
- remember that a rewriting planner after an output planner can make the two see
  different records.

Every ordinary output of a step must be read by another step; only a publication
is exempt. If a step's output has no reader, assembly fails. That is a
composition mistake, not a declaration mistake.

Two steps cannot share the identity `f"{component}.{name}"`. Several planners
may share a `component_id`; they must agree on `version` and `runtime_fields`,
and the component is published once. If several producers write one artifact
type and the composition cannot tell which one a consumer means, assembly fails
rather than choosing one.

Two *bindings* to one component are different: core unions them. They are not
two producers of a record type.

## Configuration and runtime

Planner configuration is compile-time. It is carried in the instruction
payload, so changing it changes what is planned. Credentials are not planner
configuration.

A planner may also declare runtime fields that a later run can replace without
replanning. The supplied file and Neo4j planners expose their output path this
way. Runtime values are supplied through
`BuildRuntime(component_configuration=...)`. An unknown field, a missing required
field, or a value of the wrong type stops the run before any step executes.

## What a planner and executor may do

A planner works on the whole graph, not on one row. At plan time it may inspect
the blueprint and its own configuration and emit steps with typed ports. A planner
does not execute, read data or write a file.

An executor works on one step. It receives the step's inputs, the component's
resolved runtime configuration, its own `ResourceView` and a step-scoped logger.
It may rewrite records, publish an artifact, warn, fail, or recover from an
upstream failure. It does not schedule another step and does not change the
plan.

An executor declares the exact resource types it reads in `resources`. The
runtime opens every provider, merges the declared resources, builds one view per
executor and closes the providers in reverse order. An executor asks for a
resource with `context.resources.get(SomeResource)`; asking for a type it did
not declare raises `KeyError`. The runtime owns the providers, not the
toolchain.

A planner may not make binding-level choices. Reading a nested value, choosing a
key, or turning an array into rows belongs to [expressions](expressions.md) and
[projections](projections.md); choosing which rows become which records belongs
to [bindings](bindings.md). An executor also does not carry credentials or
receive the raw database connection.

## Adding a planner or executor

Add one when the whole graph needs a stage the supplied planners do not provide:
a new output format, a validation rule that spans components, or a rewrite that
is not a row-source operation.

1. Choose a `component_id`, a `version` and the runtime fields the stage needs.
   Several planners may share the component when these agree.
2. Declare the inputs as artifact types. A target that accepts every graph
   record uses the pattern `ArtifactType("core", "graph.*")`.
3. Emit one instruction per decision, with an exact kind tuple.
4. Implement an executor whose `kinds` contains that tuple and whose
   `resources` names every resource it reads.
5. Add both to the toolchain, or pass the planner to `compile` and append the
   executor to the default toolchain. Register any new resource provider on the
   runtime that executes the plan.

A planner can emit a new kind and register its own executor; the kernel does not
maintain a list of allowed kinds. See [Write an extension](../how-to/custom-extensions.md)
for a complete one-file example.

## Limits

- A planner changes the whole build. Keep row-level work in expressions,
  projections and bindings.
- Order is part of the result. Moving an output before a rewriting planner
  changes what that output publishes.
- Every ordinary output needs a reader, and every step identity must be unique.
  Planners sharing a component must agree on its version and runtime fields.
- A target may narrow what it can store. Neo4j rejects unsupported property
  types and edges with unbound or abstract endpoints while planning.
- The meta-graph counts the records that reached it. An earlier position reports
  earlier records, and its examples remain approximate.
- A stored `WorkflowPlan` names an exact instruction kind; it runs only where an
  executor for that kind is registered.

## Next steps

- [Semantics and annotations](semantics.md) explains what a planner can read from
  a declaration.
- [Compile, execute and outputs](build-and-outputs.md) follows the plan, the run and
  the published files.

## Reference

- [Planners and executors reference](../reference/planners-and-executors.md) lists every
  supplied planner and executor, its configuration, runtime fields and artifact
  types.
- [Compile and execution reference](../reference/compile.md) specifies the public
  calls, the plan fields and the report.
