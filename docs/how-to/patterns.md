# Apply recurring modelling patterns

Choose identity, grain and graph shape deliberately so each source row produces
exactly the record it describes.

## Before you begin

- Know the difference between a table, a projection and a binding. See
  [Bindings](../concepts/bindings.md) and
  [Projections](../concepts/projections.md).
- Know how nullability and row effects work. See
  [Expressions](../concepts/expressions.md).
- Decide what one row means before writing a key. The grain is the first
  modelling decision, not the last.

The examples use these declarations:

```python
from kg_build_system import (
    Edge, EdgeValues, Field, Node, NodeValues, Projection, PropertySlot, Table,
    computed_field, edge_binding, endpoint, field, node_binding, property,
)
from kg_build_system.types import Array


class SiteTable(Table):
    site_id: Field[str] = field()
    name: Field[str] = field()
    closed_on: Field[str] = field()


class UnitTable(Table):
    unit_ref: Field[str] = field()
    site_id: Field[str] = field()
    label: Field[str] = field()
    tags: Field[Array[str | None]] = field()


class SiteNode(Node):
    name: PropertySlot[str] = property()
    closed_on: PropertySlot[str | None] = property()


class UnitNode(Node):
    label: PropertySlot[str] = property()


class TagNode(Node):
    label: PropertySlot[str] = property()


class HasUnitEdge(Edge[SiteNode, UnitNode]):
    pass
```

## Steps

### Step 1: Choose an identity that survives the build

A build key is the identity of one graph record. It must be:

- **non-null** — a null key is refused when the binding is written;
- **stable** — the same fact gets the same key on every run;
- **content-derived** — never a row number, file offset or iteration counter;
- **unique within its component** — two facts that share a key have the same
  identity; fix the key or merge them deliberately.

The simplest key is a source identifier that is already unique:

```python
site_binding = node_binding(
    target=SiteNode,
    rows=SiteTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=row.name.default_to("Unnamed site"),
            closed_on=row.closed_on,
        ),
    ),
)
```

When the identifier is declared `Field[str | None]`, `alter_rows().drop_null()`
both narrows the key and drops rows whose identifier is absent. A `Field[str]`
key is already present, so the same call is a no-op. Use `default_to(...)` only
when a shared placeholder identity is genuinely correct; every absent identifier
then becomes the same record.

When no single field identifies the record, compose one deterministically. Add a
namespace when identifiers from different systems could collide. Inside a
`bind` callable:

```python
key = (
    row.site_id.alter_rows().drop_null().expression.prepend("site::")
    .append("::unit::")
    .append(row.unit_ref.alter_rows().drop_null().expression)
)
```

Use that scalar as the binding's `build_key`. A composite key is still one
scalar string. An edge endpoint key must use the same expression as the node
binding; otherwise the edge points at a key no node emitted.

### Step 2: Keep one grain per binding

A binding reads rows at one grain and emits one record per row. The grain is
decided by expansions, filters, joins and groups before the binding sees it.

Write one binding per component and row context. A node and an edge are separate
components, even when both read the same rows:

```python
unit_binding = node_binding(
    target=UnitNode,
    rows=UnitTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        properties=UnitNode(label=row.label.default_to("Unnamed unit")),
    ),
)

has_unit_binding = edge_binding(
    target=HasUnitEdge,
    source_node=endpoint(SiteNode),
    target_node=endpoint(UnitNode),
    rows=UnitTable.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        source_build_key=row.site_id.alter_rows().drop_null(),
        target_build_key=row.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(),
    ),
)
```

Both bindings read one row per unit. The node binding emits the unit; the edge
binding emits the relationship from its site. Do not put both records in one
binding, and do not join a relation merely to reach an endpoint that the row
already carries.

If a binding needs two grains, it needs two bindings or a projection between
them. A grouped source is already one row per group, so a binding over it emits
one record per group, not one per member.

### Step 3: Make fan-out explicit

Fan-out is repeated rows for the same identity. It usually comes from an
`alter_rows().expand()` in the row source, several bindings targeting one
component, or repeated records in the source itself.

An expansion changes the grain. Publish the new grain in its own projection and
key the record by the item, not by its parent:

```python
unit_tag = UnitTable.tags.alter_rows().drop_null().alter_rows().expand()


class TagProjection(Projection(UnitTable.row_source())):
    """One row per tag on a unit."""

    unit_ref = computed_field(UnitTable.unit_ref.alter_rows().drop_null())
    tag = computed_field(unit_tag.alter_rows().drop_null())


tag_binding = node_binding(
    target=TagNode,
    rows=TagProjection.row_source(),
    bind=lambda row: NodeValues(
        build_key=(
            row.unit_ref.expression.prepend("unit::")
            .append("::tag::")
            .append(row.tag.expression)
        ),
        properties=TagNode(label=row.tag),
    ),
)
```

If a tag is a property of the unit rather than a record with its own identity,
keep it as a property and do not expand. The expansion is correct only when one
row per tag is the intended grain.

Diagnose fan-out by counting records by build key. If the count is greater than
one, decide what the duplicates mean:

- **Exact duplicates.** Add `CollapseExactDuplicatesModule`. It removes rows
  where every column matches.
- **Compatible facts with one correct value.** Add
  `MergeCompatibleFactsModule` with the affected components in scope. It folds
  same-key rows and keeps the minimum per property.
- **Different facts that need separate identity.** Fix the key so each fact gets
  its own. Do not hide the problem with deduplication.
- **The wrong grain.** Move the expansion into a separate projection and bind
  each grain separately.

Deduplication is not a substitute for identity design.

### Step 4: Decide what an absent value means

Property nullability belongs to the property, not to the row. A nullable
property means "this record may not have this value"; the node or edge still
exists. A required property is a claim the build enforces.

`SiteNode` above declares `name` required and `closed_on` nullable. A nullable
property accepts a nullable expression directly. A field declared
`Field[str | None]` can be passed unchanged; a `Field[str]` is already present.
For a required property, choose explicitly:

```python
name = row.name.default_to("Unnamed site")        # keep the row
build_key = row.site_id.alter_rows().drop_null()  # drop rows without a key
```

On a nullable value, `default_to` preserves the record and
`alter_rows().drop_null()` adds a filter to the binding's row source. The choice
is visible in the record count, so make it deliberately. Both calls are no-ops on
a present value. Never use `drop_null` merely as a ritual: when the value is
nullable it can silently remove nodes and the edges that depended on them.

An empty array and an absent array are different values. Narrow the array before
assigning a non-null array property, and drop null items when the declared item
type is non-null:

```python
labels = row.tags.alter_rows().drop_null().drop_null_items()
```

### Step 5: Choose edge endpoints and direction

An edge is a directed assertion. `Edge[SiteNode, UnitNode]` reads "site has
unit"; the source is the first argument and the target is the second. If the
reverse is a different assertion, declare a second edge type with the endpoints
swapped.

The source and target keys name existing node records. Use the same expressions
as the node bindings. The `has_unit_binding` in Step 2 shows the shape: its
source key is the site identifier, its target key is the unit reference, and its
edge key is the unit reference because this source has one row per unit.

The `endpoint(...)` tokens name the concrete components used by this binding.
They are required when the edge declares an abstract category on that side, and
they still document a concrete side. A token must name a concrete node that
equals or descends from the declared endpoint.

An edge key identifies the relationship record. One row per ordered pair gives
one edge per pair. If several assertions can occur between the same pair, derive
the key from whatever distinguishes them.

### Step 6: Choose a category for shared meaning, not for records

Use `AbstractNode` and `AbstractEdge` when several components share meaning: a
common property, a common label, or an endpoint that may be any member of a
family.

```python
from kg_build_system import AbstractNode


class DocumentedAbstractNode(AbstractNode):
    summary: PropertySlot[str] = property()


class PlaceNode(DocumentedAbstractNode, Node):
    name: PropertySlot[str] = property()


class AssetNode(DocumentedAbstractNode, Node):
    name: PropertySlot[str] = property()
```

A category is graph-visible but never a binding target. It produces no records of
its own; only `PlaceNode` and `AssetNode` are bound. The meta-graph rolls
descendant counts into the category.

Use a template such as `NodeTemplate` when you only need to share fields without
creating a graph-visible parent. Use a category when the graph itself should
expose the shared type or an edge should accept a whole family.

An edge may declare a category endpoint, but some targets need a concrete pair.
The Neo4j target requires both declared endpoints to be concrete node
components, so declare concrete endpoints for edges you intend to export there.

## Verify

Compile and run a smoke build, then check counts and endpoints:

```python
import json
from collections import Counter
from pathlib import Path

from kg_build_system import build, compile
from kg_build_system.modules import (
    FileModule, FileModuleConfiguration, register_module,
)

modules = (
    register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
)
report = build(compile(modules=modules), output_directory=Path("build"))
print(report.succeeded, report.unresolved_failures)

rows = [
    json.loads(line)
    for line in Path("build/graph.jsonl").read_text().splitlines()
]
print(Counter((row["kind"], row["type"]) for row in rows))

keys = Counter(
    row["build_key"] for row in rows if row["type"] == "unit"
)
print({key: count for key, count in keys.items() if count > 1})

node_keys = {row["build_key"] for row in rows if row["kind"] == "node"}
missing = [
    row for row in rows
    if row["kind"] == "edge"
    and (
        row["source_build_key"] not in node_keys
        or row["target_build_key"] not in node_keys
    )
]
# Presence check; compare with the named component when keys can collide.
print(missing[:3])
```

Check that:

- Each component has the expected number of records for its grain.
- No build key repeats more often than its grain allows.
- Required properties are present; nullable properties are absent only where the
  data is absent.
- Every edge endpoint key is present in the node records, in the component the
  edge names.
- A category has no records of its own; its descendants carry them.

Add `MetaGraphModule` when you want exact counts per component and category. See
[Compile, build and outputs](../concepts/build-and-outputs.md).

## Troubleshoot

| Symptom | What to change |
| --- | --- |
| `build_key must not be nullable` | Narrow with `alter_rows().drop_null()`, or default deliberately. |
| A component has duplicate build keys | The grain is wrong or the key is not unique. Fix the key, split the grain into a projection, or add a deduplication or merge module. |
| A node is missing and an edge points nowhere | The node row was dropped by a `drop_null`, or the endpoint key expression differs from the node key. |
| A required property is null at run time | Default it, make the property nullable, or drop the row deliberately. |
| `may not target abstract component` | Bind a concrete descendant, not the category. |
| `join keys must be scalar expressions` | Use a scalar key, or compose one scalar key from several fields. |
| A row count is an exact multiple | An expansion or many-side join multiplied the rows. Move the repeated grain into its own projection. |
| An edge has the wrong direction | Swap the `Edge[Source, Target]` type arguments or declare the reverse edge as a separate type. |
| `... share external name` | Rename the field or property with its `name=` argument. |
| A category endpoint fails export | Declare concrete endpoints for the edge; the Neo4j target needs both sides concrete. |

## Next steps

- [Join, group and union](relations.md) covers combined grains and named
  projections.
- [Debug a build](debug.md) covers report reading and record counts.
- [Topology](../concepts/topology.md) explains categories, templates and edge
  direction.
- [Bindings](../concepts/bindings.md) explains keys, property values and
  endpoint tokens.
- The [bindings reference](../reference/bindings.md) and
  [topology reference](../reference/topology.md) list the declaration surface.
