# Project layout

A kg-build-system project is one importable Python package with a separate place for each decision in the build.

## Before you begin

[Install kg-build-system](install.md) and complete [build your first graph](first-graph.md), or use this page as a reference while creating a new project. The examples use the `people_graph` package from that walkthrough; apply the same pattern to any project.

## Recommended layout

```text
people-graph/
  pyproject.toml
  people_graph/
    __init__.py
    build.py
    sources.py
    data/
      people.csv
      knows.csv
    table/
      __init__.py
      people.py
      knows.py
      projections/
        __init__.py
        introductions.py
    topology/
      common.py
      person/
        __init__.py
        knows__person.py
    bindings/
      common.py
      person/
        __init__.py
        knows__person.py
    build/
      graph.jsonl
      build_report.json
      workflow_contract.json
```

The `table/`, `topology/`, `bindings/`, and `data/` directories are siblings inside the package, not inside each other. `sources.py` and `build.py` sit at the package root. Every directory that holds Python modules needs an `__init__.py` file; `data/` and `build/` do not.

`pyproject.toml` is optional for the walkthrough but recommended for a real project.

`compile()` treats the package that contains `build.py` as the namespace to scan. The package name is part of every import: the walkthrough imports `people_graph.table.people`, and `compile()` discovers module-level bindings and sources from the same package.

## Steps

### 1. Create the package root

Put `build.py` and `sources.py` beside the `data/`, `table/`, `topology/`, and `bindings/` directories. Do not put declarations in `build.py`; it is the composition entry point.

Run project commands from the directory that contains `people_graph/`, not from inside the package. That keeps `python -m people_graph.build` resolving the package you are editing.

### 2. Add data contracts in `table/`

`table/` owns the shape of the rows: field names, value types, nested records, and the source's declared structure. It knows nothing about nodes, edges, or graph properties.

Use one module per handwritten table, such as `table/people.py`, or a generated package under `table/<request_id>/`. A reusable derived grain belongs in `table/projections/`. A projection names a row product that more than one binding can read.

Generated contracts are owned by the generator. The author-owned request lives in `table/__init__.py`; change the request and regenerate rather than editing a generated package. See [data contracts](../concepts/data-contracts.md), the [declarations reference](../reference/declarations.md), and [projections](../concepts/projections.md).

Keep graph labels and property names out of this layer. A column named `unit_ref` is data; that it identifies a `UnitNode` is a binding decision.

### 3. Declare graph meaning in `topology/`

`topology/` owns node and edge types, their properties, their hierarchy, and the direction of an edge. It does not import a table, a source, or an output target.

A node package is a directory directly under `topology/`. Its `__init__.py` declares the node. Other public modules in that package declare edges that start at that node:

```text
topology/person/
  __init__.py             # PersonNode
  knows__person.py        # KnowsEdge: Person -> Person
```

An edge module is named `<relationship_predicate>__<destination_node>.py`. Both parts are snake case, and the double underscore separates them. The source node is implied by the containing package, but the declaration still states both endpoints in its type arguments. The file name is a convention for navigation; it has no effect on discovery or graph semantics.

Use `topology/common.py` for templates and categories shared across nodes or edges. Do not re-export public edge modules from a node package's `__init__.py`; imports should point from an edge module toward its endpoint packages, which keeps the import graph acyclic.

See [topology](../concepts/topology.md) and the [topology reference](../reference/topology.md) for categories, templates, properties, and endpoint rules.

### 4. Put the mapping in `bindings/`

`bindings/` owns the answer to "which rows produce which records, and what does each property receive?" It mirrors the topology layout, so an edge declaration and its binding have the same relative path:

```text
bindings/person/
  __init__.py             # PersonNode binding
  knows__person.py        # KnowsEdge binding
```

A node binding lives in the package `__init__.py`; an edge binding lives in the module named after the edge. This is a convention for navigation, not a second declaration system.

Bindings are the only layer that imports both a table and a topology component. That is what lets a feed be reshaped without touching graph meaning, and a node be reused across feeds without copying bindings. Keep shared property values, such as a provenance stage or source version, in `bindings/common.py` and pass them into the binding as ordinary values.

See [bindings](../concepts/bindings.md) and the [bindings reference](../reference/bindings.md).

### 5. Bind physical locations in `sources.py`

`sources.py` owns the location, format, and version of each physical source. It contains one `bind_source()` per source and no graph declarations:

```python
from pathlib import Path

from kg_build_system import DataSourceConfig, InputFormat, bind_source

from people_graph.table.people import PeopleTable

DATA = Path(__file__).parent / "data"

people_source = bind_source(
    target=PeopleTable,
    config=DataSourceConfig(
        location=str(DATA / "people.csv"),
        format=InputFormat.CSV,
        version="people-2026-08",
    ),
)
```

Bind at module level so discovery can find the source. A table may be bound once. Keep source provenance here: the version belongs to the physical feed, not to a node or edge. See [sources](../concepts/sources.md) and the [sources and ingest reference](../reference/ingest.md).

### 6. Compose the build in `build.py`

`build.py` chooses the modules whose outputs this build produces and the directory to write. It contains no declarations.

```python
from pathlib import Path

from kg_build_system import build, compile
from kg_build_system.modules import FileModule, FileModuleConfiguration, register_module


def main() -> None:
    contract = compile(modules=[
        register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    ])
    build(contract, output_directory=Path(__file__).parent / "build")


if __name__ == "__main__":
    main()
```

`compile()` scans the package around `build.py`, so the declarations and bindings do not need an import list. Keep the `if __name__ == "__main__":` guard so discovery's import of `build.py` does not run a build.

Choose modules here, not in the layers below. A file-only build, a deduplication pass, a meta-graph, or a Neo4j import are composition choices. See [modules](../concepts/modules.md), the [modules reference](../reference/modules.md), and [compile, build and outputs](../concepts/build-and-outputs.md).

### 7. Keep inputs in `data/` and outputs in `build/`

Put input files under `data/` and generated artifacts under `build/`. Keeping both inside the package makes paths resolve relative to the project and the example self-contained.

Build artifacts are inspectable development material: the graph records, the build report, the frozen workflow contract, and any module-specific output. Do not edit them by hand and do not import them from the project. Rebuild instead.

| Artifact | Written by | Contents |
| --- | --- | --- |
| `workflow_contract.json` | `build()` | The frozen contract and its workflow fingerprint |
| `build_report.json` | `build()` | Published artifacts, failures, and provenance |
| `graph.jsonl` | `FileModule` | One JSON object per graph record |

## Where each layer lives

| Layer | Owns | Changes when |
| --- | --- | --- |
| `data/` | Bytes on disk | A feed is refreshed |
| `table/` | Field names and value types | A source schema changes |
| `topology/` | Node and edge types, properties | The graph model changes |
| `sources.py` | Location, format, version | A feed moves or changes format |
| `bindings/` | Which rows make which records | A mapping decision changes |
| `build.py` | Module composition and output path | A build target changes |

## Dependency direction

The dependencies point one way:

```text
data ──> table ──┐
                 ├──> bindings ──> build
topology ────────┘
```

Tables do not import topology. Topology does not import tables. Sources do not know graph meaning. A binding is the meeting point, and the build composes the result.

!!! warning "Keep the direction one-way"
    If a table imports a node, or a topology module imports a table, the layers become impossible to change or test separately. If a mapping needs data from both sides, it belongs in `bindings/`.

## Verify

Check that the package imports without running a build:

```bash
python -c "import people_graph.build; print('layout ok')"
```

You should see `layout ok`. This confirms the package path and the `__main__` guard. It does not validate the bindings; run the build or call `compile()` for that.

To verify the whole example, run `python -m people_graph.build` and check the node and edge counts as described in [build your first graph](first-graph.md#verify).

## What to remember

- `table/` owns shape, `topology/` owns meaning, `sources.py` owns location, and `bindings/` is the only layer that imports both sides.
- Keep one module per table and one package per node; mirror the topology tree under `bindings/`.
- `build.py` at the package root is the entry point and needs a `__main__` guard.
- Inputs go in `data/`; generated artifacts go in `build/` and are never edited by hand.

## Next steps

- [Build your first graph](first-graph.md) for the complete runnable version of this layout.
- [Data contracts](../concepts/data-contracts.md) and [topology](../concepts/topology.md) for the declarations in each layer.
- [Bindings](../concepts/bindings.md) and [sources](../concepts/sources.md) for the mapping and physical location.
- [Compile, build and outputs](../concepts/build-and-outputs.md) for the contract and artifacts.
- [Authoring API reference](../reference/index.md) for the public names used in these files.
