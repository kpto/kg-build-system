# Build your first graph

Build a small people graph from two CSV files, then compile it, run the build, and inspect the JSON Lines output.

## Before you begin

[Install kg-build-system](install.md) and confirm that the import check succeeds. You also need a terminal and a directory for the project.

Create the project package and its directories:

```bash
mkdir -p people-graph/people_graph/{data,table,topology/person,bindings/person}
cd people-graph
touch people_graph/__init__.py \
      people_graph/table/__init__.py \
      people_graph/topology/__init__.py \
      people_graph/topology/person/__init__.py \
      people_graph/bindings/__init__.py \
      people_graph/bindings/person/__init__.py
```

Run all later commands from `people-graph/`. The package has this structure:

```text
people-graph/
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
    topology/
      __init__.py
      person/
        __init__.py
        knows__person.py
    bindings/
      __init__.py
      person/
        __init__.py
        knows__person.py
```

Add the two input files.

`people_graph/data/people.csv`:

```csv
person_id,name,city
p1,Ada,London
p2,Grace,New York
p3,Alan,London
```

`people_graph/data/knows.csv`:

```csv
source_id,target_id,since
p1,p2,2020
p2,p3,2021
```

The finished graph has three people and two `KNOWS` relationships:

```text
Ada ──KNOWS──> Grace ──KNOWS──> Alan
```

## Steps

### 1. Declare the tables

Start with the shape of the rows. A table is a typed Python class, and each member is a `Field[T]` that names the value type. A table is logical: it says what a row holds, not where the row lives.

Create `people_graph/table/people.py`:

```python
from kg_build_system import Field, Table, TableOptions, field


class PeopleTable(Table):
    """One row per person in the directory."""

    options = TableOptions(name="people")
    person_id: Field[str] = field(description="Stable person identifier.")
    name: Field[str] = field()
    city: Field[str] = field()
```

Create `people_graph/table/knows.py`:

```python
from kg_build_system import Field, Table, TableOptions, field


class KnowsTable(Table):
    """One row per professional introduction."""

    options = TableOptions(name="knows")
    source_id: Field[str] = field()
    target_id: Field[str] = field()
    since: Field[int] = field()
```

`PeopleTable` is both a shape and a row source. The source binding in the next step supplies the file location. For more about declarations, see [data contracts](../concepts/data-contracts.md) and the [declarations reference](../reference/declarations.md).

### 2. Bind a source

A source binding supplies the physical location for a table. `bind_source()` connects the table to a `DataSourceConfig`; `InputFormat.CSV` selects the CSV reader.

Create `people_graph/sources.py`:

```python
from pathlib import Path

from kg_build_system import DataSourceConfig, InputFormat, bind_source

from people_graph.table.knows import KnowsTable
from people_graph.table.people import PeopleTable

DATA = Path(__file__).parent / "data"

people_source = bind_source(
    target=PeopleTable,
    config=DataSourceConfig(str(DATA / "people.csv"), format=InputFormat.CSV),
)

knows_source = bind_source(
    target=KnowsTable,
    config=DataSourceConfig(str(DATA / "knows.csv"), format=InputFormat.CSV),
)
```

Keep source bindings at module level. `compile()` discovers them when it scans the package. The source binding is the only place the file path appears, so you can move a feed without changing a table, a node, or an edge. See [sources](../concepts/sources.md).

### 3. Declare the topology

Topology uses graph names, not file columns. A node declares a kind of thing; an edge declares a relationship and its direction. These declarations do not import the tables or the CSV files.

Create `people_graph/topology/person/__init__.py`:

```python
from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class PersonNode(Node):
    """Someone recorded in the directory."""

    options = NodeOptions(annotations=(NodeLabel("Person"),))
    name: PropertySlot[str] = property()
    city: PropertySlot[str] = property()
```

Create `people_graph/topology/person/knows__person.py`:

```python
from kg_build_system import Edge, EdgeLabel, EdgeOptions, PropertySlot, property

from people_graph.topology.person import PersonNode


class KnowsEdge(Edge[PersonNode, PersonNode]):
    """Relates two people."""

    options = EdgeOptions(annotations=(EdgeLabel("KNOWS"),))
    since: PropertySlot[int] = property()
```

`PropertySlot[T]` is the graph-side counterpart of `Field[T]`: a binding must supply an expression of that type. `NodeLabel` and `EdgeLabel` are annotations, not properties; the compiled model preserves them.

The type arguments on `Edge[PersonNode, PersonNode]` state both endpoints. The file name `knows__person.py` is a convention for navigation; the declaration is the graph meaning. See [topology](../concepts/topology.md), [semantics and annotations](../concepts/semantics.md), and the [topology reference](../reference/topology.md).

### 4. Bind the node

A binding says which rows produce which records. The `rows=` argument takes a row
source value; a `Table` class is accepted as a compatibility shorthand and
converted with `row_source()`, but the explicit value states the plan. The `bind`
callable receives a symbolic instance of that row shape; `row.name` is a typed
selection, not a value read from a file.

Create `people_graph/bindings/person/__init__.py`:

```python
from kg_build_system import NodeValues, node_binding

from people_graph.table.people import PeopleTable
from people_graph.topology.person import PersonNode

person_binding = node_binding(
    target=PersonNode,
    rows=PeopleTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.person_id.alter_rows().drop_null(),
        properties=PersonNode(
            name=row.name.default_to("Unnamed person"),
            city=row.city.default_to("Unknown"),
        ),
    ),
)
```

The build key is the non-null scalar that identifies a node. A `Field[T | None]` reads as nullable; `Field[T]` reads non-null, so the key narrows with `alter_rows().drop_null()`. A property uses `default_to(...)` when an absent value has a meaningful fallback.

!!! note "Null values and rows"
    `drop_null()` removes the row when a nullable value is null; on a present value it is a no-op. `default_to(value)` keeps the row and replaces a null; it is a no-op on a present value. Use `drop_null()` for a nullable key that cannot name anything, and `default_to()` for a property whose absence has a fallback. See [types and nullability](../concepts/types.md) and the [type vocabulary](../reference/types.md).

### 5. Bind the edge

An edge binding supplies its own key and the keys of both endpoints. The build key must identify the relationship; the endpoint keys must identify the nodes it connects.

Create `people_graph/bindings/person/knows__person.py`:

```python
from kg_build_system import EdgeValues, edge_binding

from people_graph.table.knows import KnowsTable
from people_graph.topology.person.knows__person import KnowsEdge

knows_binding = edge_binding(
    target=KnowsEdge,
    rows=KnowsTable.row_source(),
    bind=lambda row: EdgeValues(
        build_key=(
            row.source_id.alter_rows().drop_null().expression
            .append("->")
            .append(row.target_id.alter_rows().drop_null().expression)
        ),
        source_build_key=row.source_id.alter_rows().drop_null(),
        target_build_key=row.target_id.alter_rows().drop_null(),
        properties=KnowsEdge(since=row.since.alter_rows().drop_null()),
    ),
)
```

The edge key combines the two endpoint keys, so each introduction is identifiable. `since` is declared as a required property on `KnowsEdge`, so the binding narrows it with `drop_null()`; a row without a year does not become an edge.

Every declared property must receive exactly one value. The framework reports a missing or mistyped property before any data is read. See [bindings](../concepts/bindings.md) and the [bindings reference](../reference/bindings.md).

### 6. Compile the contract

`compile()` reads the package around the calling module, checks the bindings against their declarations, and returns an immutable contract. It does not read the CSV files.

Create `people_graph/build.py`:

```python
from pathlib import Path

from kg_build_system import build, compile
from kg_build_system.distribution import FileModule, FileModuleConfiguration, register_module


def main() -> None:
    contract = compile(modules=[
        register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    ])
    report = build(contract, output_directory=Path(__file__).parent / "build")
    for artifact in report.published_artifacts:
        print(artifact.value)


if __name__ == "__main__":
    main()
```

`compile()` scans the package that contains `build.py`, so the declarations and bindings do not need an import list. `FileModule` writes the graph records as JSON Lines, and its configured path is relative to the output directory. The core module, which materialises the records, is supplied automatically.

The `__main__` guard matters: discovery imports `build.py`, and without the guard that import would run the build.

### 7. Build the graph

Run the entry point from the project root:

```bash
python -m people_graph.build
```

`build()` executes the frozen contract. The configured `FileModule` writes the graph and publishes a summary, which the loop prints:

```text
{'nodes': 3, 'edges': 2, 'location': '.../people-graph/people_graph/build/graph.jsonl'}
```

Your absolute location will differ. The build also writes `workflow_contract.json` before execution and `build_report.json` after it finishes.

### 8. Inspect the output

Open `people_graph/build/graph.jsonl`. Each line is one graph record. A run of this example produces two edge records and three node records:

```json
{"_kg_binding_symbol": "binding:edge:knows:f60786089df46529c00a7a81", "build_key": "p1->p2", "kind": "edge", "since": 2020, "source_build_key": "p1", "target_build_key": "p2", "type": "knows"}
{"_kg_binding_symbol": "binding:edge:knows:f60786089df46529c00a7a81", "build_key": "p2->p3", "kind": "edge", "since": 2021, "source_build_key": "p2", "target_build_key": "p3", "type": "knows"}
{"_kg_binding_symbol": "binding:node:person:81ad7a0b90659a7c83d7c4d1", "build_key": "p1", "city": "London", "kind": "node", "name": "Ada", "type": "person"}
{"_kg_binding_symbol": "binding:node:person:81ad7a0b90659a7c83d7c4d1", "build_key": "p2", "city": "New York", "kind": "node", "name": "Grace", "type": "person"}
{"_kg_binding_symbol": "binding:node:person:81ad7a0b90659a7c83d7c4d1", "build_key": "p3", "city": "London", "kind": "node", "name": "Alan", "type": "person"}
```

Each record carries:

- `build_key`: the record's identity.
- `type` and `kind`: the graph component and whether it is a node or an edge.
- The properties the binding supplied.
- `source_build_key` and `target_build_key` on an edge.
- `_kg_binding_symbol`: the binding that produced the record.

The contract in `workflow_contract.json` is the frozen plan. `build_report.json` records the published artifacts, any failures, and provenance. Both are build artifacts; do not edit them by hand. See [compile, build and outputs](../concepts/build-and-outputs.md) and the [compile reference](../reference/compile.md).

## Verify

Confirm that the node and edge counts match the input:

```bash
grep -c '"kind": "node"' people_graph/build/graph.jsonl
grep -c '"kind": "edge"' people_graph/build/graph.jsonl
```

The first command prints `3`, and the second prints `2`. Also check that `people_graph/build/workflow_contract.json` and `people_graph/build/build_report.json` exist.

If the counts differ, inspect the input keys and the `drop_null()` calls first. A missing or null key removes a row from the graph.

## What to remember

- The order is shape, source, meaning, binding: declare the table, bind its source, declare the node or edge, then bind the rows.
- The `bind` callable receives a symbolic row instance; `row.name` is a typed selection, not a Python value.
- A `Field[T | None]` reads as nullable; `Field[T]` reads non-null. A key must be a present scalar, so narrow it with `alter_rows().drop_null()` rather than inventing an identity.
- `compile()` checks the declarations; `build()` reads data and writes outputs.
- Read the JSON Lines file and confirm the counts before adding more components.

## Next steps

- [Project layout](project-layout.md) explains where to put a larger project.
- [Data contracts](../concepts/data-contracts.md) covers nested structs, table groups, and generated contracts.
- [Topology](../concepts/topology.md) and [bindings](../concepts/bindings.md) cover categories, endpoints, and inheritance.
- [Compile, build and outputs](../concepts/build-and-outputs.md) covers the contract and the build report in detail.
- [Authoring API reference](../reference/index.md) lists the names used in this walkthrough.
