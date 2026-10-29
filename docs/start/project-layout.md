# Project layout

A kg-build-system project separates four questions: what the data looks like,
what the graph means, how rows become records, and which outputs a build
produces. The layout below keeps each answer in its own layer so a change to a
feed does not force a change to the graph model, and a change to an edge does
not require editing a build script.

Use an importable package for the project. The examples in this guide call the
package `people_graph`; the reference monitored-estate project calls its package
`reference_project`. The conventions are the same.

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
      __init__.py                 # generation requests, when used
      people/
        __init__.py               # generated PeopleTable
      knows/
        __init__.py               # generated KnowsTable
      projections/
        __init__.py
        introductions.py          # reusable derived grain
    topology/
      common.py                   # templates and categories
      person/
        __init__.py               # PersonNode
        knows__person.py          # KnowsEdge
    bindings/
      common.py                   # shared property values
      person/
        __init__.py               # PersonNode binding
        knows__person.py          # KnowsEdge binding
    build/
      graph.jsonl
      build_report.json
```

The `table/`, `topology/`, `bindings/` and `data/` directories are siblings
inside the package, not inside each other. `sources.py` and `build.py` sit at the
package root. `compile()` treats the directory containing `build.py` as the
namespace to scan, so every declaration module is reachable from that package.

## `table/` — data contracts

This layer answers "what columns exist and what do they mean?" It contains
[`Table`, `Struct` and `ComputedStruct`](../concepts/data-contracts.md)
declarations and reusable `Projection` classes; it knows nothing about nodes,
edges or graph properties.

A generated package lives at `table/<request_id>/`, with the author-owned
generation request in `table/__init__.py`. The reference project uses that form
for every source: `table/sites/`, `table/equipment/`, `table/surveys/` and a
nested `table/readings/` generated table group. Generated contracts make the
physical schema visible and consistent, but they are not the only option;
handwritten tables are ordinary declarations and use the same public API;
one can also be a single module such as `table/people.py`.

`table/projections/` holds hand-written derived grains. A projection is a named
row product: expansions, selected struct members and columns fixed into one
reusable row shape ([projections](../concepts/projections.md)). Keep it here when
more than one binding needs that grain.

The reference project's `defects.py` flattens a survey document to one row per
defect, and `observations.py` then expands the observations inside that grain.
They are separate projections because each expansion changes the row count and
a projection has one row plan.

Do not put graph labels or property names in this layer. A column named
`unit_ref` is data; that it identifies a `UnitNode` is a binding decision.

## `topology/` — graph meaning

This layer answers "what kinds of thing and relationship exist?" A node package
is a directory directly under `topology/`. Its `__init__.py` declares the node;
its other public modules declare edges that start at that node.

```text
topology/person/
  __init__.py             # PersonNode
  knows__person.py        # KnowsEdge: Person -> Person
```

An edge module is named
`<relationship_predicate>__<destination_node>.py`. Both parts are snake case and
the double underscore separates them. The source node is implied by the
containing package, but the declaration still states both endpoints:

```python
class KnowsEdge(Edge[PersonNode, PersonNode]):
    """Relates two people."""

    options = EdgeOptions(annotations=(EdgeLabel("KNOWS"),))
    since: PropertySlot[int] = property()
```

The filename is a convention for navigation. It has no effect on discovery or
graph semantics, and the graph label remains declaration metadata. Do not re-export public
edge modules from the node package's `__init__.py`; imports should point from an
edge module toward its endpoint packages, which keeps the import graph acyclic.
Underscore-prefixed modules such as `_shared.py` are for private helpers, not
edges.

`topology/common.py` is the place for templates and categories shared across
nodes or edges. The reference project's `ProvenancedNodeTemplate` supplies a
provenance property to every node, and its `AbstractNode` categories provide
shared labels and properties. These are ordinary topology declarations, not
binding targets, so they have no mirror under `bindings/`.

## `sources.py` — physical locations

This file contains one `bind_source()` per physical source. It chooses the
location, format, version and, for a table group, the layout that maps each
member table to a file.

```python
people_source = bind_source(
    target=PeopleTable,
    config=DataSourceConfig(
        str(DATA / "people.csv"),
        format=InputFormat.CSV,
        version="people-2026-08",
    ),
)
```

A single group source uses one config for the family:

```python
readings_source = bind_source(
    target=ReadingsTableGroup,
    config=DataSourceConfig(
        str(DATA / "readings"),
        format=InputFormat.JSON,
        layout="{group_path}/{table_name}.json",
        version="telemetry-2026-08",
    ),
)
```

Keep provenance here: the source version belongs to the physical feed, not to a
node or edge. An author reading `sources.py` should be able to answer "which
file produced this build?" without opening a binding.

## `bindings/` — the mapping

This layer answers "which rows produce which records, and what does each
property receive?" It mirrors the topology layout:

```text
bindings/person/
  __init__.py             # PersonNode binding
  knows__person.py        # KnowsEdge binding
```

The mirror is deliberate. Given an edge declaration, the corresponding binding
is at the same relative path, so a change to `knows__person.py` has an obvious
counterpart. The source node is still implicit from the package, and the
binding still names its target and supplies both endpoint keys.

```python
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

Every source field reads as nullable, so the key narrows and the properties
choose a fallback. `row` is a symbolic shape instance, not the table class.

`bindings/common.py` holds values that many bindings stamp identically, such as
a provenance stage or source version. The reference project expresses those as
typed bundles so a missing or mistyped shared property is a static error at
every unpacking site. They are still ordinary values passed into the binding,
not a second declaration system.

Bindings are the only layer that imports both a table and a topology component.
That is why they are separate: a feed can be reshaped without touching graph
meaning, and a node can be reused across feeds without copying bindings.

## `build.py` — composition

The build entry point names the modules whose outputs this build produces and
the directory to write; it contains no declarations.

```python
def main() -> None:
    contract = compile(modules=[
        register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    ])
    build(contract, output_directory="build")
```

`compile()` scans the package around `build.py`, so the declarations and
bindings are found without an import list. `build()` executes the resulting
contract and writes the selected outputs. Keep the `if __name__ == "__main__":`
guard so importing `build.py` during discovery does not run a build.

Choose modules here, not in the layers below: a file-only build, a
deduplication pass, a meta-graph, or a Neo4j import are composition choices. See
[modules](../concepts/modules.md) and [outputs](../concepts/outputs.md).

## `data/` and `build/`

Put input files under `data/` and generated artifacts under `build/`. The
reference project keeps both inside its package so paths resolve relative to the
project and the whole example is self-contained.

Build artifacts are inspectable development material: the graph records, the
build report, the frozen workflow contract and any module-specific output. Do
not edit them by hand. Rebuild instead. They are not source declarations and
should not be imported by the project.

## Why the layers stay separate

| Layer | Owns | Changes when |
| --- | --- | --- |
| `data/` | bytes on disk | a feed is refreshed |
| `table/` | field names, types, nullability | a source schema changes |
| `topology/` | node and edge types, properties | the graph model changes |
| `sources.py` | location, format, version | a feed moves or changes format |
| `bindings/` | which rows make which records | a mapping decision changes |
| `build.py` | module composition and output path | a build target changes |

The dependency direction is one-way:

```text
data ──> table ──┐
                 ├──> bindings ──> build
topology ────────┘
```

Tables do not import topology. Topology does not import tables. Sources do not
know graph meaning. A binding is the meeting point, and the build composes the
result. This is what makes it possible to test a contract on its own, reuse a
node type, or replace one output module without rewriting declarations.

## What to remember

- `table/` owns shape, `topology/` owns meaning, `sources.py` owns location,
  and `bindings/` is the only layer that imports both sides.
- Dependencies point from bindings toward declarations. Tables never import
  topology; topology never imports tables.
- Keep one module per node and mirror that tree under `bindings/`; discovery
  needs no registry.
- `build.py` at the package root is the entry point and needs a `__main__`
  guard.

For a complete runnable version of this layout, continue to
[your first graph](first-graph.md). For the mapping rules in detail, see
[topology](../concepts/topology.md) and [bindings](../concepts/bindings.md).
