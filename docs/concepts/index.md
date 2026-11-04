# How a build works

A build has one story: a row of source data becomes a record in a graph, and the
meaning of that record is stated before the build runs.

This guide follows a small environmental survey. A JSON file holds sites,
surveyed units and defects. The graph has `SiteNode`, `UnitNode` and
`DefectNode`, and edges such as `HAS_UNIT` and `HAS_DEFECT`. The same shape
appears in every concept page, so you can see where each idea fits.

## 1. Describe the rows

Start with the data you read. A [data contract](data-contracts.md) is a Python
class whose fields are the columns you expect. A `Table` describes a row of
input; a `Struct` describes a nested record inside it.

```python
class SiteTable(Table):
    site_id: Field[str] = field()
    name: Field[str | None] = field()
    surveyed_on: Field[Date] = field()
```

The declaration is the schema. There is no separate mapping document. Every
field also carries a [type](types.md), so compilation can check what a value
may become.

## 2. Give the rows a source

A [source](sources.md) attaches the table to a file or URI. The table says what a
row looks like; the source says where the rows live. Keeping them separate means
a feed can move without changing the graph.

```python
source = bind_source(
    target=SiteTable,
    config=DataSourceConfig("data/sites.json", format=InputFormat.JSON),
)
```

## 3. Work with values

[Expressions](expressions.md) read a field, walk into a nested record, expand a
list, or compute a new value. A selection knows its type and nullability. Row
effects such as expanding an array or dropping a null row are explicit.

```python
site_name = SiteTable.name.alter_rows().drop_null()
```

A source field reads the presence its declaration names. `Field[T]` is present;
`Field[T | None]` is nullable. The author decides whether to drop the row,
default the value, or keep it nullable.

## 4. Choose the grain

A [row source](row-sources.md) is the relation a binding reads. `where`,
`union`, `join`, `group_by`, `distinct` and `order_by` derive one. The grain is
the answer to "what is one row?" — one site, one unit, or one site-and-unit pair.

```python
unit_rows = SiteTable.row_source().join(
    UnitTable.row_source(),
    on=lambda site, unit: (site.site_id, unit.site_id),
)
```

When a grain is reused or deserves a name, a [projection](projections.md) pins
it to a relation and publishes typed outputs. A projection is the named contract
between the rows and every binding that reads them.

## 5. Declare the graph's meaning

[Topology](topology.md) knows nothing about files. It declares the node and edge
types, their properties, their hierarchy and their direction.

```python
class SiteNode(Node):
    site_id: PropertySlot[str] = property()
    name: PropertySlot[str | None] = property()


class HasUnit(Edge[SiteNode, UnitNode]):
    pass
```

The declaration is the meaning of the record: what it is, what identifies it,
which properties it carries, and what an edge asserts.

## 6. Connect rows to records

A [binding](bindings.md) maps one row context onto one node or edge. It names
the rows, the build key, and a value for every property.

```python
node_binding(
    target=SiteNode,
    rows=SiteTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(name=row.name),
    ),
)
```

The binding is the only part that imports both the data shape and the graph
meaning. The build key identifies the record; the properties carry the values;
the row source carries the grain.

## 7. Make the meaning part of the graph

[Semantics and annotations](semantics.md) turn descriptions and annotations into
data. A description explains a component to a human; an annotation is a typed
payload a tool can read. Both survive compilation and can be published with the
graph, so a consumer does not have to read the pipeline.

## 8. Compose the planners and executors

[Planners and executors](planners-and-executors.md) are the stages applied to the whole graph
after the bindings. The core module's five planners materialise rows and records;
file, meta-graph and Neo4j planners publish the result; deduplication, merging and
validation planners change which records survive.

## 9. Compile and run

[Compile, execute and outputs](build-and-outputs.md) turns the declarations and
planners into a `WorkflowPlan`, executes it, and writes the selected outputs. The
plan and report make the build inspectable.

```python
plan = compile(planners=planners)
report = execute(plan, output_directory="build")
```

## The whole pipeline

```text
source files
    │
    ▼
data contracts ──► expressions ──► row sources ──► projections
    │                                                │
    └──────────────► topology ◄── bindings ◄─────────┘
                           │
                           ▼
                  compile ──► WorkflowPlan ──► execute ──► graph and reports
```

Each part has one job. The next page takes the first step:
[data contracts](data-contracts.md).
