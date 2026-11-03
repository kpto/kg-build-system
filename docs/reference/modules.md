# Modules

`register_module` adds one reusable build stage to a composition; the supplied modules deduplicate, merge, validate, or write graph records.

Modules do whole-graph work. They do not describe graph meaning and do not own a binding. The core module always reads sources and assembles records; registered modules consume or publish what it produced. See [Modules](../concepts/modules.md).

```python
from kg_build_system.distribution import (
    CollapseExactDuplicatesModule, FileModule, FileModuleConfiguration,
    MetaGraphModule, MetaGraphModuleConfiguration, register_module,
)

modules = (
    register_module(CollapseExactDuplicatesModule),
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    register_module(MetaGraphModule, MetaGraphModuleConfiguration(example_limit=5)),
)
```

## `register_module`

```python
register_module(
    module_class: type[Module],
    configuration: ModuleRegistrationConfiguration | None = None,
) -> ModuleRegistration
```

| Argument | Meaning |
| --- | --- |
| `module_class` | A module class with an `ID`, a `VERSION` and a `CONFIGURATION_TYPE` |
| `configuration` | An instance of that configuration type; omitted, the class is called with no arguments |

```python
from kg_build_system.distribution import (
    FileModule, FileModuleConfiguration, register_module,
)

file_module = register_module(
    FileModule,
    FileModuleConfiguration("graph.jsonl"),
)
```

Registration returns a frozen `ModuleRegistration` with two fields:

| Field | Meaning |
| --- | --- |
| `module_class` | The registered module class |
| `configuration` | The frozen configuration value |

A module class must be importable at top level. Its `ID` must be a non-empty lowercase identifier. The same module ID may appear only once in a composition.

The last two errors below are reported when the composition is validated, not when `register_module` returns.

### Errors

| Condition | Error |
| --- | --- |
| `configuration` is not the module's `CONFIGURATION_TYPE` | `TypeError: <Module> requires <Configuration> configuration` |
| No configuration is given and the type has required fields | The configuration constructor's `TypeError` |
| The module has no usable ID | `TypeError: workflow module classes must declare a non-empty string ID` |
| The module class is defined inside a function | `ValueError: workflow modules must be importable top-level classes` |

## Registration values

### `ModuleRegistrationConfiguration`

A frozen dataclass base for serialisable, non-secret module configuration:

```python
from dataclasses import dataclass

from kg_build_system.distribution import ModuleRegistrationConfiguration

@dataclass(frozen=True)
class ExportConfiguration(ModuleRegistrationConfiguration):
    relative_path: str = "graph.jsonl"
```

`to_json()` returns the JSON-compatible form carried in module provenance. Configuration is compile-time: changing it changes the contract. Do not put credentials in it.

### `Module`

The module protocol names the identity and the two factories:

| Member | Meaning |
| --- | --- |
| `ID` | Stable module identifier; unique in a composition |
| `VERSION` | Implementation version recorded in the contract |
| `CONFIGURATION_TYPE` | The class `register_module` validates against |
| `compiler(configuration)` | Classmethod factory for the compile-time compiler |
| `executor(context)` | Classmethod factory for the runtime executor |

Custom module authoring is framework-internal in this release. `Module` is
importable and `register_module` composes a supplied module. A supplied module
implements `compiler(configuration)` and `executor(context)`; the compiler
receives the validated configuration, and the executor receives an
`ExecutorFactoryContext`. Those factories and their return types are not part of
the public authoring surface. Write modules inside the framework, not in a graph
project; a project composes the supplied modules.

## Supplied modules

| Module | ID | Configuration | Effect | Publication |
| --- | --- | --- | --- | --- |
| `CollapseExactDuplicatesModule` | `collapse_exact_duplicates` | None | Removes rows identical in every column | None; rewrites records |
| `MergeCompatibleFactsModule` | `merge_compatible_facts` | `MergeCompatibleFactsModuleConfiguration(components=None)` | Folds same-key rows, keeping the minimum value per property | None; rewrites records |
| `RejectConflictingNonNullValuesModule` | `reject_conflicting_non_null_values` | `RejectConflictingNonNullValuesConfiguration(fail_on_error=True)` | Reports more than one distinct non-null value per key and property | `reject_conflicting_non_null_values/report` when findings are reported without failing |
| `FileModule` | `file` | `FileModuleConfiguration(relative_path)` | Writes JSON Lines | `file/write_result` |
| `MetaGraphModule` | `meta_graph` | `MetaGraphModuleConfiguration(...)` | Writes the topology document and optional HTML page | `meta_graph/meta_graph_document` |
| `Neo4jModule` | `neo4j` | `Neo4jModuleConfiguration(...)` | Writes a Neo4j import bundle | `neo4j/import_bundle` |

### `CollapseExactDuplicatesModule`

Removes rows that are identical in every column, including the build key and all properties. A repeated key whose values differ is left alone. There is no configuration.

### `MergeCompatibleFactsModule`

```python
MergeCompatibleFactsModuleConfiguration(
    components: tuple[type[Node] | type[Edge[Any, Any]], ...] | None = None,
)
```

Folds rows with the same build key into one row, keeping the minimum value for every property. It is only sound when parallel same-key rows are one fact expressed more than once. `components=None` applies it to every bound component; a tuple restricts it to those concrete `Node` and `Edge` classes.

```python
from kg_build_system import Node
from kg_build_system.distribution import (
    MergeCompatibleFactsModule, MergeCompatibleFactsModuleConfiguration,
    register_module,
)

class SiteNode(Node):
    pass

modules = (
    register_module(
        MergeCompatibleFactsModule,
        MergeCompatibleFactsModuleConfiguration(components=(SiteNode,)),
    ),
)
```

Merging is not aggregation: `min()` is not a sum, a latest-value rule or a domain choice. Keep deliberately distinct edge families out of scope.

| Condition | Error |
| --- | --- |
| A component is abstract, a template or not a class | `TypeError: components must be concrete Node or Edge classes` |

### `RejectConflictingNonNullValuesModule`

```python
RejectConflictingNonNullValuesConfiguration(fail_on_error: bool = True)
```

For every property of every bound component, groups by build key and looks for more than one distinct non-null value. Nulls never create a conflict; one non-null value beside any number of nulls is fine.

With `fail_on_error=True` (the default), any finding fails the run. With `fail_on_error=False`, the build continues, forwards the records to later modules, and publishes a report:

```python
from kg_build_system import build

report = build(contract)
for artifact in report.published_artifacts:
    if artifact.type.namespace == "reject_conflicting_non_null_values":
        print(artifact.value.findings)
```

The published value has a `findings` tuple. Each finding names the component, build key, property and number of distinct values. No report is published when there are no findings.

### `FileModule`

```python
FileModuleConfiguration(relative_path: str)
```

Writes one JSON object per line to `relative_path`, resolved beneath the build's output directory. The path must be non-empty, relative, and must not contain `..`.

Each record contains `build_key`, `type` (the component's logical name), `kind` (`"node"` or `"edge"`) and the component's properties. An edge also carries `source_build_key` and `target_build_key`. A record that has not passed through a merging stage also carries `_kg_binding_symbol`. Property keys are sorted.

The module publishes `file/write_result` with `nodes`, `edges` and `location`.

`relative_path` may be replaced at runtime without recompiling:

```python
from kg_build_system import BuildRuntime

runtime = BuildRuntime(
    module_configuration={
        "file": {"relative_path": "graph/current.jsonl"},
    },
)
```

| Condition | Error |
| --- | --- |
| The path is empty | `ValueError: file output path must be a non-empty relative path` |
| The path is absolute or contains `..` | `ValueError: file output path must be relative to the build output directory` |

### `MetaGraphModule`

```python
MetaGraphModuleConfiguration(
    relative_path: str = "meta_graph.json",
    example_limit: int = 3,
    include_html: bool = True,
    html_relative_path: str = "meta_graph.html",
)
```

Writes a JSON description of the effective topology: each bound component, its abstract ancestors and endpoint categories, its label, description, properties with logical types and descriptions, and its record count. Counts are exact for the records that reached the module. A category's record count is the sum of its own and its descendants' records.

Examples are approximate: the module reports the most common values with `approx_top_k`, bounded by `example_limit`, and the document names that method. `example_limit=0` omits examples. With `include_html=True`, it also writes a self-contained HTML page drawing the same document.

Both paths are relative to the output directory and must not escape it. The configuration is compile-time; the module has no runtime path override.

The module publishes `meta_graph/meta_graph_document` with the document summary: component counts, total nodes and edges, the document location, and the HTML location when enabled.

| Condition | Error |
| --- | --- |
| An output path is empty | `ValueError: <context> must be a non-empty relative path` |
| An output path is absolute or contains `..` | `ValueError: <context> must be relative to the build output directory` |
| `example_limit < 0` | `ValueError: meta-graph example limit may not be negative` |

### `Neo4jModule`

```python
Neo4jModuleConfiguration(
    relative_directory: str = "neo4j-import",
    script_name: str = "import_neo4j.py",
    default_database: str = "neo4j",
)
```

Writes one Parquet file per bound node component under `nodes/`, one per bound edge component under `relationships/`, a standalone `import_neo4j.py`, and a summary. The script invokes `neo4j-admin database import` and needs neither this package nor a network at run time.

The target checks property types at compile time. It exports `bool`, `int`, `float`, `str`, `date`, `time` and `timestamp`, plus arrays of `bool`, `int`, `float` and `str`. It refuses `uuid` and custom-scalar properties, arrays of temporal, `uuid` or custom-scalar items, and reserved import-field names. Every edge needs both endpoint node components bound and exported; an edge whose declared endpoints are abstract categories cannot be exported.

`relative_directory` may be replaced at runtime through `module_configuration={"neo4j": {"relative_directory": ...}}`. The module publishes `neo4j/import_bundle` with the directory, script path, node and edge counts, and the file lists.

| Condition | Error |
| --- | --- |
| A path is empty, absolute or contains `..` | `ValueError` naming the Neo4j output directory or script name |
| `script_name` is not a single Python filename | `ValueError: Neo4j script name must be a Python filename` |
| `default_database` is empty | `ValueError: Neo4j default database must be non-empty` |
| A property type cannot be exported | A compile-time `ValueError` naming the component and property |

## Ordering and composition

The registration tuple is the composition order. The core module is appended after every registered module.

| Rule | Result |
| --- | --- |
| Record-rewriting modules before output modules | Outputs publish the records the last rewriting stage produced |
| Validation before merging | Conflict validation sees parallel values before merging collapses them |
| Collapse anywhere among rewriting stages | It only removes exact duplicates |
| Output modules last | They consume the final rewriting result |

```python
from kg_build_system.distribution import (
    CollapseExactDuplicatesModule, FileModule, FileModuleConfiguration,
    RejectConflictingNonNullValuesModule, register_module,
)

modules = (
    register_module(RejectConflictingNonNullValuesModule),
    register_module(CollapseExactDuplicatesModule),
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
)
```

A rewriting module registered after an output module may leave the two seeing different records. If nothing consumes a module's output, compilation fails with `nothing reads ...`. Two modules with the same ID fail with `module IDs must be unique`. Two modules producing the same artifact type make the wiring ambiguous and fail compilation rather than choosing one.

Several bindings may target one component. The core module unions their records into that component's single stream; this is not two competing producers. Only two modules writing the same artifact type are ambiguous.

## Artifacts and publications

A publication is a value handed to the build itself rather than to another step. It appears in `WorkflowReport.published_artifacts` as an entry with `type` (namespace and name) and `value`. The supplied publications are:

| Publication | Value |
| --- | --- |
| `file/write_result` | `nodes`, `edges`, `location` |
| `meta_graph/meta_graph_document` | Component counts, totals, document location, optional HTML location |
| `neo4j/import_bundle` | Directory, script, node and edge counts, node and relationship file lists |
| `reject_conflicting_non_null_values/report` | A report value whose `findings` tuple names each conflict |

Output modules publish summaries, not the graph itself. A contract may register more than one output module; each writes its own artifact from the records it receives.

## Runtime configuration

A module may declare runtime fields. `BuildRuntime.module_configuration` supplies them by module ID:

```python
from kg_build_system import BuildRuntime

runtime = BuildRuntime(
    module_configuration={
        "file": {"relative_path": "graph/current.jsonl"},
        "neo4j": {"relative_directory": "neo4j/current"},
    },
)
```

| Condition | Error |
| --- | --- |
| An unknown field is supplied | `ValueError: unknown runtime configuration for <id>: ...` |
| A required field is missing | `ValueError: missing runtime configuration for <id>: ...` |
| A value has the wrong type | `TypeError: invalid runtime configuration for <id>: ...` |
| The module implementation version differs from the compiled one | `RuntimeError: module '<id>' implementation version ... does not match compiled version ...` |

Runtime configuration is validated before any step runs. It is not part of the contract.

## What to remember

- A build is the core pipeline plus the modules you register.
- Registration order is composition order; rewriting modules come first and output modules last.
- Configuration is compile-time; runtime fields are for paths and similar execution settings.
- Two bindings to one component are unioned; two modules publishing one artifact type make wiring ambiguous.
- Output modules publish summaries and write their own files.
- Custom module authoring is framework-internal; projects compose the supplied modules.

Related: [Modules](../concepts/modules.md), [Compile](compile.md), [Compile, build and outputs](../concepts/build-and-outputs.md), [Bindings](bindings.md), [Reference index](index.md).
