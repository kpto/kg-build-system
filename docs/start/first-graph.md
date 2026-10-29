# Your first graph

This walkthrough builds a complete graph from two CSV files: two tables, two
graph components, two bindings and one build entry point.

```text
Ada ──KNOWS──> Grace ──KNOWS──> Alan
```

## Before you start

[Install kg-build-system](install.md) and create this package. The
[project layout](project-layout.md) page explains the directories.

```text
people-graph/people_graph/
  build.py  sources.py  data/
  table/{__init__.py,people.py,knows.py}
  topology/person/{__init__.py,knows__person.py}
  bindings/person/{__init__.py,knows__person.py}
```

Create `__init__.py` in each package, then run commands from `people-graph/`.

## Add the data

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

## Declare the tables

A table is both a typed shape and a row source; every member uses `Field[T]`.

`people_graph/table/` contains one module per table:

```python
# people_graph/table/people.py
from kg_build_system import Field, Table, TableOptions, field


class PeopleTable(Table):
    """One row per person in the directory."""

    options = TableOptions(name="people")
    person_id: Field[str] = field(description="Stable person identifier.")
    name: Field[str] = field()
    city: Field[str] = field()
# people_graph/table/knows.py
from kg_build_system import Field, Table, TableOptions, field


class KnowsTable(Table):
    """One row per professional introduction."""

    options = TableOptions(name="knows")
    source_id: Field[str] = field()
    target_id: Field[str] = field()
    since: Field[int] = field()
```

Each annotation names the value the column holds. It does not make the column
non-null on access: `row.person_id` is a nullable selection even though the
declaration is `Field[str]`. Narrow it with `alter_rows().drop_null()` for a key,
or replace an absence with `default_to(...)` for a property. See
[data contracts](../concepts/data-contracts.md) and
[types and nullability](../concepts/types.md).

## Declare the topology

Topology uses graph names, not file columns. A node package holds its node.

`people_graph/topology/person/__init__.py` declares the node, and the edge
module's name says where it starts and ends:

```python
# people_graph/topology/person/__init__.py
from kg_build_system import Node, NodeLabel, NodeOptions, PropertySlot, property


class PersonNode(Node):
    """Someone recorded in the directory."""

    options = NodeOptions(annotations=(NodeLabel("Person"),))
    name: PropertySlot[str] = property()
    city: PropertySlot[str] = property()

# people_graph/topology/person/knows__person.py
from kg_build_system import Edge, EdgeLabel, EdgeOptions, PropertySlot, property

from people_graph.topology.person import PersonNode


class KnowsEdge(Edge[PersonNode, PersonNode]):
    """Relates two people."""

    options = EdgeOptions(annotations=(EdgeLabel("KNOWS"),))
    since: PropertySlot[int] = property()
```

The declaration states both endpoints in its type arguments; the filename is for
navigation, not graph semantics. `PropertySlot[T]` is the graph-side counterpart
of `Field[T]`: the binding supplies an expression of that type.

## Bind rows to records

A binding names a target component and a row source. The `bind` callable receives
a symbolic instance of the row source's shape, not a materialised Python row and
not the class; `row.name` is a typed selection.
`people_graph/bindings/person/` holds both bindings:

```python
# people_graph/bindings/person/__init__.py
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


# An edge binding declares both endpoint keys and the edge key. This key
# combines the endpoints so each introduction is identifiable.
# people_graph/bindings/person/knows__person.py
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

`rows=` accepts a row-source value: `Table.row_source()`, a filtered or derived
source, or a joined/grouped source. A declaration class is not accepted. The
`bind` callable always receives that source's shape instance. See
[bindings](../concepts/bindings.md).

!!! note "Null values and rows"
    Every source field reads as nullable, including a `Field[str]` column, so
    each binding decides what absence means. `alter_rows().drop_null()` filters
    the row out and returns a non-null selection. `default_to(value)` keeps the
    row and replaces the null. Use `drop_null()` for a key that cannot name
    anything, and `default_to()` for a property whose absence has a meaningful
    fallback.

## Point at the data

`people_graph/sources.py`:

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

## Compile and build

`compile()` reads the package around the calling module, checks the bindings
against their declarations, and returns an immutable contract. `build()` executes
it.

`people_graph/build.py`:

```python
from pathlib import Path

from kg_build_system import build, compile
from kg_build_system.modules import FileModule, FileModuleConfiguration, register_module

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

`FileModule` writes the graph records as JSON Lines; the core module is supplied
automatically. Run:

```bash
python -m people_graph.build
```

The `__main__` guard stops discovery's import of `build.py` from running it.

## The result

```text
{'nodes': 3, 'edges': 2, 'location': '.../people_graph/build/graph.jsonl'}
```

`people_graph/build/graph.jsonl` contains one record per line. Each record names
its build key (and endpoint keys for an edge), its binding, kind and type,
followed by the properties the binding supplied:

```json
{"_kg_binding_symbol": "binding:edge:knows:...", "build_key": "p1->p2", "kind": "edge", "since": 2020, "source_build_key": "p1", "target_build_key": "p2", "type": "knows"}
{"_kg_binding_symbol": "binding:node:person:...", "build_key": "p1", "city": "London", "kind": "node", "name": "Ada", "type": "person"}
```

The file also has the other edge and two more `Person` records. The report
records published summaries, failures and provenance; the frozen contract is
written to `build/workflow_contract.json`.

## What to remember

- The order is always shape, meaning, connection: declare the table, declare the
  node or edge, then bind one to the other.
- The `bind` callable receives a symbolic shape instance; `row.name` is a typed
  selection, not a Python value.
- Every source field reads as nullable. A key must be a present scalar, so filter
  with `alter_rows().drop_null()` rather than inventing an identity.
- `compile()` checks the declarations; `build()` reads data and writes outputs.
- Read the JSON Lines output and confirm the counts before adding components.

## Next

Read [data contracts](../concepts/data-contracts.md) for nested structs and table
groups, and [topology](../concepts/topology.md) and
[bindings](../concepts/bindings.md) for inheritance and endpoints.
