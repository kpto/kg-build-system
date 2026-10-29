# Modules

A module is one reusable stage of a build. It is not part of a binding and does
not describe graph meaning. It reads what earlier stages produced, does one job
across the whole graph, and hands the result on. Output modules publish that
result; validation and clean-up modules rewrite it.

The core module is always present: it reads sources, evaluates projections and
bindings, and assembles each component's records. Registering a module is a
choice about the build as a whole — which checks run, which records survive, and
where the result is written.

Modules are supplied when the build is composed, not when a binding is written:

```python
from kg_build_system import compile
from kg_build_system.modules import (
    FileModule, FileModuleConfiguration, register_module,
)

modules = (
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
)
contract = compile(modules=modules)
```

The same tuple is used for `create_blueprint`, `compile` and later
recompilations. See [Compile and build](build.md) for the three entry points.

## Registering a module

`register_module` chooses a module class and, optionally, its frozen
configuration dataclass:

```python
from kg_build_system.modules import (
    FileModule, FileModuleConfiguration, MetaGraphModule,
    MetaGraphModuleConfiguration, register_module,
)

modules = (
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    register_module(
        MetaGraphModule, MetaGraphModuleConfiguration(example_limit=5),
    ),
)
```

Without a configuration, a module whose configuration dataclass has defaults
uses that default. `FileModule` has no default for its path, so it needs
`FileModuleConfiguration(relative_path)`.

Configuration is compile-time: it is carried in the contract, so changing it
changes what is compiled and fingerprinted.

A module may also declare runtime fields that a later build can override without
recompiling. The supplied modules expose the output paths of `FileModule` and
`Neo4jModule` this way, supplied through `BuildRuntime.module_configuration`:

```python
from kg_build_system import BuildRuntime

runtime = BuildRuntime(module_configuration={
    "file": {"relative_path": "graph/current.jsonl"},
})
```

Unknown runtime fields, or a value of the wrong type, stop the build before any
step runs.

!!! note
    Module configuration is not a place for credentials. Credentials are
    resolved at build time and never enter the contract.

## The built-in modules

### `CollapseExactDuplicatesModule`

This module removes rows that are identical in every column, including the build
key and all properties. A repeated key whose values differ is left alone; use
merging or fix the binding. No configuration.

### `MergeCompatibleFactsModule`

`MergeCompatibleFactsModule` folds rows with the same build key into one row,
keeping the minimum value for every property. That is only sound when the
parallel rows really are one fact expressed more than once — for example, the
same identifier arriving from two source partitions.

By default it applies to every bound component. Restrict it to the concrete
components whose parallel rows are compatible:

```python
from kg_build_system.modules import (
    MergeCompatibleFactsModule, MergeCompatibleFactsModuleConfiguration,
    register_module,
)

modules = (
    register_module(
        MergeCompatibleFactsModule,
        MergeCompatibleFactsModuleConfiguration(components=(SiteNode,)),
    ),
)
```

The tuple may contain concrete `Node` and `Edge` classes only; components not
named keep every row.

!!! warning "Merging is not aggregation"
    `min()` is not a sum, a latest-value rule, or a domain choice. If parallel
    edge facts are deliberately distinct, keep that family out of scope. Build
    the reduction into the binding or a projection instead.

### `RejectConflictingNonNullValuesModule`

For every property of every bound component, this module groups by build key and
looks for more than one distinct non-null value. Nulls never create a conflict;
one non-null value beside any number of nulls is fine.

```python
from kg_build_system.modules import (
    RejectConflictingNonNullValuesConfiguration,
    RejectConflictingNonNullValuesModule, register_module,
)

modules = (register_module(
    RejectConflictingNonNullValuesModule,
    RejectConflictingNonNullValuesConfiguration(fail_on_error=False)),)
```

The default `fail_on_error=True` fails the run on any finding.
`fail_on_error=False` continues; if there are findings, it publishes a
`ConflictingNonNullValuesReport` as `reject_conflicting_non_null_values/report`:

```python
from kg_build_system import build

report = build(contract)
for artifact in report.published_artifacts:
    if artifact.type.namespace == "reject_conflicting_non_null_values":
        print(artifact.value.findings)
```

Each finding names the component, build key, property, and count of distinct
values. When the module does not fail the run, it passes the records on, so later
output modules see them.

### `FileModule`

`FileModule` writes one JSON object per line. Each line contains `build_key`,
`type` (the component's logical name), `kind` (`node` or `edge`), the
component's properties, and the endpoint keys for an edge. A record that has not
passed through a merging stage also carries `_kg_binding_symbol`. Property keys
are sorted, so the file is readable and diff-friendly.

```python
from kg_build_system.modules import (
    FileModule, FileModuleConfiguration, register_module,
)

modules = (register_module(FileModule, FileModuleConfiguration("graph.jsonl")),)
```

The path is relative to the build's output directory and must not escape it. The
module publishes `file/write_result` with `nodes`, `edges`, and `location`.

### `MetaGraphModule`

`MetaGraphModule` writes a JSON description of the effective topology: every
component a binding targets, its abstract ancestors and endpoint categories, its
properties and logical types, and its record count. Counts are exact for the
records that reached the module, so they reflect whatever stage last owned them.
A category's `inclusive_records` is the exact sum of its own and its descendants'
records.

Example values are approximate: the module reads the most common values with
`approx_top_k`, bounded by `example_limit`, rather than scanning a sorted sample.
The document names that method. Inherited category examples are pooled from the
descendants and ordered canonically; they are illustrative, not a precise
distribution.

```python
from kg_build_system.modules import (
    MetaGraphModule, MetaGraphModuleConfiguration, register_module,
)

modules = (register_module(MetaGraphModule, MetaGraphModuleConfiguration(
    relative_path="meta_graph.json", example_limit=3,
    include_html=True, html_relative_path="meta_graph.html")),)
```

`example_limit=0` omits examples. The HTML page is self-contained and draws the
same document. Both paths are relative to the output directory.

### `Neo4jModule`

`Neo4jModule` writes one Parquet file per bound node and edge component, a
standalone `import_neo4j.py`, and a summary. Column headers are the
`neo4j-admin database import` headers, so the bundle does not need this package
at import time.

```python
from kg_build_system.modules import (
    Neo4jModule, Neo4jModuleConfiguration, register_module,
)

modules = (register_module(Neo4jModule, Neo4jModuleConfiguration(
    relative_directory="neo4j-import", default_database="neo4j")),)
```

The target checks types at compile time. It exports `bool`, `int`, `float`,
`str`, `date`, `time` and `timestamp`, plus arrays of `bool`, `int`, `float` and
`str`. It refuses `uuid` and custom-scalar (`CustomDataType`) properties, arrays
of temporal, `uuid` or custom-scalar items, and reserved import-field names.

!!! warning "Concrete endpoints for Neo4j"
    Every edge needs both endpoint node components bound and exported. An edge
    whose declared endpoints are abstract categories cannot be exported; declare
    concrete endpoints for edges you intend to import.

## Ordering and composition

Modules are composed in the order registered; the core module is appended after
them. Record-rewriting modules — collapse, merge, validation — consume graph
records and produce graph records again. Output modules consume them.

Several bindings may target one component. The core module unions their records
into that component's single record stream, so this is an ordinary way to build
one node type from several sources or grains; it is not two producers of a
record type. Two *modules* writing the same artifact type are different: the
wiring becomes ambiguous and compilation fails rather than choosing one.

For predictable results, register every rewriting module first and output
modules last. The last rewriting module before the outputs supplies the records
those outputs publish. Put validation before merging: merging has already chosen
one value per key, so conflict validation afterwards finds nothing. Collapse can
sit anywhere among the rewriting stages.

If a rewriting module is registered after an output module, the two may see
different records. If nothing consumes its output, compilation fails with
`nothing reads ...`. Both are composition mistakes, not declaration mistakes.
Two modules with the same module ID cannot be composed: blueprint validation
reports `module IDs must be unique`.

## When to add a module

Add one when the job concerns the whole build rather than one binding: publishing
a new format, validating a rule that spans components, cleaning records across
many components, or describing the build itself.

Do not add a module for work belonging to one binding. Reading a nested value,
choosing a key, or turning an array into rows is a job for
[expressions](expressions.md) and [projections](projections.md). Choosing which
rows become which records is a job for [bindings](bindings.md).

Custom module authoring is framework-internal in this release. The `Module`
protocol is importable and `register_module` composes a supplied module, but a
module's `create_compiler` and `create_executor` return types are not part of the
public authoring surface (`compile.interfaces` and `workflow.interfaces` are
private today). Write a module only inside the framework, not in a graph project;
a project composes the supplied modules and keeps composition small.

## What to remember

- A build is the core pipeline plus the modules you register.
- Module order sets stage priority; output modules belong last.
- Two bindings to one component are unioned. Two *modules* producing the same
  artifact type make the wiring ambiguous and fail compilation.
- Add a module for whole-graph work such as deduplication, merging, validation
  or writing.
- Keep row-level choices in expressions and bindings, where the grain is known.
- Custom module authoring is framework-internal; projects compose supplied
  modules.
- Output modules decide where results land; the same contract can feed several.

Related pages: [Compile and build](build.md), [Outputs](outputs.md),
[Modelling patterns](../guides/patterns.md), and
[Debugging](../guides/debugging.md).
