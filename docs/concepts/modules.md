# Modules

A module is one reusable stage of a build: it reads records produced by earlier stages, does one job across the whole graph, and either passes the records on or publishes them.

Bindings answer what one row becomes. A module answers what happens to all records together: removing duplicates, validating conflicts, merging parallel facts, or writing a target. That is why a module is chosen when you compose the build, not when you write a binding.

## Where a module fits

A build has one pipeline:

```text
sources → bindings → core graph records → rewriting modules → output modules
```

The core module turns your declarations into the first graph records. Rewriting modules consume those records and produce records again. Output modules consume the final records and publish files or artifacts.

## Composing a build

You compose modules as a tuple and pass it to `compile`:

```python
from kg_build_system import compile
from kg_build_system.modules import (
    CollapseExactDuplicatesModule,
    FileModule,
    FileModuleConfiguration,
    MetaGraphModule,
    register_module,
)

modules = (
    register_module(CollapseExactDuplicatesModule),
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    register_module(MetaGraphModule),
)

contract = compile(modules=modules)
```

This survey build removes exact duplicate records, writes JSON Lines, and describes the effective topology. The tuple is the whole composition. The same tuple can create a blueprint, and `build` later receives the compiled contract rather than the tuple. The bindings and sources are discovered from the calling file, so the example shows only the module tuple.

`register_module` chooses a module class and, when needed, its frozen configuration. A module with defaults can be registered without one. `FileModule` has no default path, so it requires a path.

## The core module

The core module is always present. It is appended after the modules you register, and you do not register it yourself. It reads sources, evaluates projections and bindings, and assembles each component's records.

Several bindings may target one component. Core unions their records into that component's single record stream, so one node type can be built from several sources or grains. This is a normal composition, not two producers competing for the same record. Abstract categories are not record producers, so they get no records of their own.

## Rewriting modules

A rewriting module consumes graph records and produces graph records. It changes which records survive or what values they carry. It does not write a target.

### `CollapseExactDuplicatesModule`

This module removes rows that are identical in every column, including the build key and all properties. A repeated key whose values differ is left alone; use merging or fix the binding. It has no configuration.

### `MergeCompatibleFactsModule`

This module groups records by build key and keeps the minimum value for every property. That is sound only when the parallel rows really are one fact expressed more than once, such as the same identifier arriving from two source partitions.

By default it applies to every bound component. Restrict it to the components whose parallel rows are compatible. In the survey example that is `SiteNode`:

```python
from kg_build_system.modules import (
    MergeCompatibleFactsModule,
    MergeCompatibleFactsModuleConfiguration,
    register_module,
)

merge_sites = register_module(
    MergeCompatibleFactsModule,
    MergeCompatibleFactsModuleConfiguration(components=(SiteNode,)),
)
```

Components you do not name keep every row.

!!! warning "Merging is not aggregation"

    The module keeps a minimum value; it does not sum, choose the latest value, or apply a domain rule. If parallel edge facts are deliberately distinct, keep that family out of scope and build the reduction into the binding or a projection instead.

### `RejectConflictingNonNullValuesModule`

This module looks at every property of every bound component. It groups by build key and reports a finding when one property has more than one distinct non-null value. Nulls never create a conflict: one non-null value beside any number of nulls is fine.

With `fail_on_error=True`, the default, a finding fails the run. With `fail_on_error=False`, the module continues, publishes a report artifact, and passes the records on so later output modules still see them.

Each finding names the component, build key, property and number of distinct values.

!!! warning "Validate before you merge"

    Merging has already chosen one value per key. A conflict check placed after merging finds nothing. Register conflict validation before the merging stage when you want to discover conflicts.

## Output modules

An output module consumes final graph records and publishes them in a target format. The supplied targets cover the common destinations.

### `FileModule`

`FileModule` writes one JSON object per line. Each line carries `build_key`, `type`, `kind` and the component's properties. An edge also carries its endpoint keys. A record that has not passed through a merging stage also carries `_kg_binding_symbol`. Keys are sorted, and temporal and UUID values use their canonical text, so the file is readable and stable.

The path is relative to the build's output directory and must not escape it. The module publishes a summary with the node count, edge count and location.

### `MetaGraphModule`

`MetaGraphModule` writes `meta_graph.json`, a description of the effective topology. It covers every component a binding targets, its abstract ancestors and endpoint categories, its label and description, its properties with logical types and descriptions, record counts and example values.

Counts are exact for the records that reached the module. Examples are illustrative rather than a distribution: the module uses `approx_top_k`, bounded by `example_limit`. A category carries inclusive counts and pooled examples from its descendants because it emits no records itself. With `include_html=True`, the module also writes a self-contained HTML diagram of the same document.

### `Neo4jModule`

`Neo4jModule` writes one Parquet file per bound node and edge component, a standalone `import_neo4j.py`, and a summary. The column headers are the `neo4j-admin database import` headers, so the bundle does not need this package at import time.

The target checks types at compile time. It exports `bool`, `int`, `float`, `str`, `date`, `time` and `timestamp`, plus arrays of `bool`, `int`, `float` and `str`. It refuses `uuid` and custom-scalar properties, arrays of temporal, `uuid` or custom-scalar items, and reserved import-field names.

!!! warning "Concrete endpoints for Neo4j"

    Every edge needs both endpoint node components bound and exported. An edge whose declared endpoints are abstract categories cannot be exported. Declare concrete endpoints for edges you intend to import.

## Ordering and composition

Modules are composed in the order you register them, and core is appended after them. That order is your priority order: when an output can read more than one producer of the same record type, the last rewriting stage before the output supplies the records.

For predictable results:

- register every rewriting module first and output modules last;
- put validation before merging;
- place `CollapseExactDuplicatesModule` anywhere among the rewriting modules;
- let the last rewriting module before the outputs decide what they publish;
- remember that a rewriting module registered after an output module can make the two see different records.

Every ordinary output must be read by another step; only a publication is exempt. If nothing consumes an output, compilation fails with a `nothing reads ...` message. That is a composition mistake, not a declaration mistake.

Two configured instances of one module ID cannot be composed. Blueprint validation reports `module IDs must be unique`. If several producers write one artifact type and the composition cannot tell which one a consumer means, compilation fails rather than choosing one.

Two *bindings* to one component are different: core unions them. They are not two producers of a record type.

## Configuration and runtime

Module configuration is compile-time. It is carried in the contract, so changing it changes what is compiled and fingerprinted. Credentials are not module configuration.

A module may also declare runtime fields that a later build can replace without recompiling. The supplied modules expose the output path of `FileModule` and the output directory of `Neo4jModule` this way. Runtime values are supplied through `BuildRuntime.module_configuration`. An unknown field, a missing required field, or a value of the wrong type stops the build before any step runs.

## What a module may do

A module works on the whole graph, not on one row. At compile time it may inspect the blueprint and its own configuration. At run time it receives the records its steps consume, its resolved configuration and the execution services, and it may rewrite records, publish an artifact, warn, fail, or recover from an upstream failure.

A module may not make binding-level choices. Reading a nested value, choosing a key, or turning an array into rows belongs to [expressions](expressions.md) and [projections](projections.md); choosing which rows become which records belongs to [bindings](bindings.md). A module also does not carry credentials or receive the raw database connection.

Module authoring is framework work in this release. The `Module` protocol is importable and `register_module` composes a supplied module, but a project's job is composition: use the supplied modules and keep the tuple small.

## Limits

- A module changes the whole build. Keep row-level work in expressions, projections and bindings.
- Order is part of the result. Moving an output before a rewriting stage changes what that output publishes.
- Every output needs a reader, and every module ID must be unique.
- A target may narrow what it can store. Neo4j rejects unsupported property types and edges with unbound or abstract endpoints at compile time.
- The meta-graph counts the records that reached it. An earlier position reports earlier records, and its examples remain approximate.
- A contract requires the exact module implementations and `VERSION` values that compiled it. See [Compile, build and outputs](build-and-outputs.md).

## Next steps

- [Semantics and annotations](semantics.md) explains what a module can read from a declaration.
- [Compile, build and outputs](build-and-outputs.md) follows the contract, the build and the published files.

## Reference

- [Modules reference](../reference/modules.md) lists every supplied module, its configuration, runtime fields and artifact types.
- [Compile and build reference](../reference/compile.md) specifies registration, composition and module references.
