# Modelling patterns

Most graph-building mistakes are modelling decisions, not framework mistakes.
This page collects the decisions that come up repeatedly.

## Identity and keys

A build key is the identity of one graph record. It must be:

- **non-null** — a null key is refused when the binding is written;
- **stable** — the same fact gets the same key on every run;
- **content-derived** — never a row number, file offset, or iteration counter;
- **unique within its component** — two facts that share a key become one
  component's records unless you act.

The simplest key is a source identifier that is already unique:

```python
build_key=row.site_id.alter_rows().drop_null()
```

`drop_null()` both narrows a nullable value and filters the row when it is null;
it is a row effect, so it is reached through `alter_rows()`. If a missing
identifier should still produce a record, use `default_to(...)` instead and
accept the placeholder as identity. Do not use a value that changes between
builds, such as a timestamp of ingestion.

When no single field identifies the record, compose one deterministically. Add a
namespace when identifiers from different systems could collide:

```python
build_key=(
    row.unit_ref.alter_rows().drop_null().expression.prepend("unit::")
    .append("::")
    .append(row.reading_uid.alter_rows().drop_null().expression)
)
```

A composite key made from several columns is still one scalar string. Edge
endpoint keys must use exactly the same expression as the corresponding node
binding; otherwise the edge points at a key no node emitted.

## One row grain per binding

A binding reads rows at one grain and emits one graph record per row. The grain
is decided by expansions and filters before the binding sees it.

```python
class DefectProjection(Projection(SurveysTable.row_source())):
    survey_id = computed_field(SurveysTable.survey_id.alter_rows().drop_null())
    defect_id = computed_field(
        SurveysTable.areas.alter_rows().expand()
        .extract(lambda value: value.elements).alter_rows().expand()
        .extract(lambda value: value.defects).alter_rows().expand()
        .extract(lambda value: value.defect_id)
    )
    # ... other defect properties ...
```

Every `alter_rows().expand()` multiplies the rows. If a binding reads a table
with an array and expands inside one of its property expressions, the record
repeats once per item. That is fan-out: the same build key appears many times,
often with the same values. See
[Fan-out and deduplication](#fan-out-and-deduplication).

Choose the grain first, then write the binding. A node binding should read one
row per node; an edge binding should read one row per edge. If a binding needs
two grains, it needs two bindings or a projection between them.

## Edge, property, or reified node

A fact can often be modelled in more than one way. Use the question the graph
must answer.

| Model it as | When |
| --- | --- |
| a property | the value describes the node or edge itself and has no identity |
| an edge | the fact is a relationship between two things |
| a node | the fact has its own properties, identity, or relationships |

A measurement's numeric value is a property of the reading node. The fact that a
unit produced the reading is an edge. If the measurement itself must be linked
to a laboratory, an instrument, or a calibration event, it deserves a node — even
if today it only carries one number.

!!! tip
    A property cannot be shared by two components or carry its own edges. When
    either becomes necessary, promote it to a node rather than duplicating it on
    both sides.

## Abstract categories for shared meaning

Use `AbstractNode` and `AbstractEdge` when several components share meaning:

- a shared property that every member must have;
- a shared label or annotation;
- an endpoint that may be any member of a family.

```python
class DocumentedAbstractNode(AbstractNode):
    summary: PropertySlot[str] = property()

class SiteNode(DocumentedAbstractNode, Node):
    name: PropertySlot[str] = property()

class DefectNode(DocumentedAbstractNode, Node):
    title: PropertySlot[str] = property()
```

The category is graph-visible but never a binding target. It produces no records
of its own; the meta-graph rolls descendant counts into it. Concrete members are
bound normally.

An edge may declare a category endpoint:

```python
class DocumentedEdge(
    AbstractEdge[DocumentedAbstractNode, DocumentedAbstractNode]
): ...

class ObservedDuringEdge(DocumentedEdge, Edge[DefectNode, SiteNode]): ...

edge_binding(
    target=ObservedDuringEdge,
    source_node=endpoint(DefectNode),
    target_node=endpoint(SiteNode),
    rows=DefectProjection.row_source(),
    bind=lambda row: EdgeValues(...),
)
```

The `endpoint(...)` tokens name the concrete components used by this binding.
They are required for an abstract declared side and must descend from the
category.

!!! warning
    Not every output target accepts category endpoints. The Neo4j target needs
    both declared endpoints to be concrete node components, so declare concrete
    endpoints for edges you intend to export there.

## Fan-out and deduplication

Fan-out is repeated rows for the same identity. It usually comes from an
`alter_rows().expand()` in the row source, several bindings targeting one
component, or repeated records in the source itself.

Diagnose it by counting records by build key in the output. If the count is
greater than one, decide what the duplicates mean:

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

## Optional facts

Property nullability belongs to the property, not to the row. A nullable
property means "this record may not have this value"; the node or edge still
exists.

```python
class SiteNode(Node):
    name: PropertySlot[str] = property()
    closed_on: PropertySlot[Date | None] = property()
```

A nullable property accepts a null expression directly. Every source field reads
as nullable, so a nullable property can take one unchanged. If the property is
non-null, choose explicitly:

```python
city=row.city.default_to("Unlisted")                 # keep the row
build_key=row.identifier.alter_rows().drop_null()    # drop rows without a key
```

`default_to` preserves the record; `drop_null` adds a filter to that binding's
row source. The choice is visible in the record count, so make it deliberately.
Never use `drop_null` merely to satisfy a type: it can silently remove nodes and
the edges that depended on them.

## Nested arrays and structs

Graph properties are scalars or flat, homogeneous arrays of non-null scalars. A
nested array or an array of structs is row material, not a property value.

Flatten one level at a time, with one grain per projection:

```python
area = SurveysTable.areas.alter_rows().expand()
element = area.extract(lambda value: value.elements).alter_rows().expand()
defect = element.extract(lambda value: value.defects).alter_rows().expand()
```

Each step is a new row grain. Publish the grain when more than one binding needs
it; a further expansion needs a further projection. Arrays with null items can be
cleaned with `drop_null_items()` when the null item carries no meaning; narrow the
array to a present selection first:

```python
codes = row.codes.alter_rows().drop_null().drop_null_items()
key = codes.sort().unique().concat(":")
```

## Naming

Names are graph vocabulary, not Python plumbing.

- Name topology classes with their tier: `SiteNode`, `DocumentedAbstractNode`,
  `ProvenancedNodeTemplate`. Concrete and abstract Node/Edge components strip
  the matching suffix from their logical name; templates carry no logical name.
- Use `NodeOptions(name=...)` or `EdgeOptions(name=...)` when the class name
  would produce a misleading or duplicate logical name.
- Name properties for what they mean in the graph, not how they are derived.
- Name edge modules `<relationship_predicate>__<destination_node>.py`, both in
  snake case, as in `has_unit__unit.py`.

## When to add a projection

Add a projection when more than one binding needs the grain, reaching it needs
several expansions, or the grain deserves a shared name. Do not add one for a
single expression on an existing grain: use a shared selection or write it in the
binding. A projection is a named row product with one row plan, so a further
expansion needs a further projection.

## Splitting a large graph

Use a node-first layout:

```text
graph_pipeline/
  build.py
  table/projections/
  topology/site/{__init__.py, has_unit__unit.py}
  bindings/site/{__init__.py, has_unit__unit.py}
```

- One package per node under `topology/`; the node class lives in its
  `__init__.py`.
- Edges that originate from that node live in sibling modules.
- `bindings/` mirrors `topology/`.
- Shared templates and categories live in a plain module such as
  `topology/common.py`.

Namespace discovery finds module-level bindings and sources recursively, so the
layout is enough; no registry list is needed. Keep `build.py` at the package root
and pass only `modules` to `compile`.

## What to remember

- Start from the grain: one row per node or per edge, with a key that matches
  it.
- Use an edge for a relationship, a property for a fact about one thing, and a
  node when the relationship itself carries identity or facts.
- Categories share meaning; they do not replace bindings.
- Fan-out is explicit. `alter_rows().expand()` multiplies rows, so key on the
  item.
- Add a projection when a grain is reused or genuinely new, not to tidy one
  expression.

Related pages: [Projections](../concepts/projections.md),
[Topology](../concepts/topology.md), [Bindings](../concepts/bindings.md),
[Modules](../concepts/modules.md), and [Debugging](debugging.md).
