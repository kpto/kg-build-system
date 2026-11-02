# Bindings

A binding maps one row source onto one node or edge: it names graph identity, gives every declared property a value, and produces one record per row it receives.

Topology says what a site, unit or defect means. Rows supply the values. A binding is where the two meet. It is the only declaration that imports both the data shape and the graph meaning, so it is also the only place where a mismatch between them can appear.

## The problem: a row is not a record

An input row has columns. A graph record needs an identity and a value for every declared property.

The row may lack a usable identifier, carry a null where the graph requires a value, or describe a relation rather than a thing. The binding makes those decisions explicit: which expression is the build key, which rows survive, and what each property receives.

## The model

A **node binding** targets one concrete node. An **edge binding** targets one concrete edge and also supplies its source and target keys.

Every binding names:

- the concrete `target`;
- the rows it reads;
- a present scalar build key;
- a value for every declared property, including inherited ones.

In the `rows=` form, the `bind` callable receives a **shape instance** for the row source. That is a symbolic object, not data and not a dictionary. Read its fields as attributes and return `NodeValues` or `EdgeValues` with the row-derived values.

```python
from kg_build_system import (
    Edge, Field, Node, PropertySlot, Table, field, property,
)


class SiteTable(Table):
    site_id: Field[str] = field()
    name: Field[str] = field()
    region: Field[str] = field()


class UnitTable(Table):
    site_id: Field[str] = field()
    unit_ref: Field[str] = field()
    unit_name: Field[str] = field()
    in_service: Field[bool] = field()
    status: Field[str] = field()
    survey_period: Field[str] = field()


class SiteNode(Node):
    name: PropertySlot[str] = property()
    region: PropertySlot[str | None] = property()


class UnitNode(Node):
    name: PropertySlot[str] = property()
    in_service: PropertySlot[bool] = property()


class HasUnitEdge(Edge[SiteNode, UnitNode]):
    as_at: PropertySlot[str | None] = property()
```

Create a node binding for the site grain:

```python
from kg_build_system import NodeValues, node_binding

site_binding = node_binding(
    target=SiteNode,
    rows=SiteTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=row.name.default_to("Unnamed site"),
            region=row.region,
        ),
    ),
)
```

The unit grain produces the target nodes for the edge. It uses the same pattern:

```python
def build_unit(row: UnitTable) -> NodeValues[UnitNode, str]:
    return NodeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        properties=UnitNode(
            name=row.unit_name.default_to("Unnamed unit"),
            in_service=row.in_service.default_to(False),
        ),
    )


unit_binding = node_binding(
    target=UnitNode,
    rows=UnitTable.row_source(),
    bind=build_unit,
)
```

Create an edge binding for the site-to-unit relation:

```python
from kg_build_system import EdgeValues, edge_binding

has_unit_binding = edge_binding(
    target=HasUnitEdge,
    rows=UnitTable.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        source_build_key=row.site_id.alter_rows().drop_null(),
        target_build_key=row.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(as_at=row.survey_period),
    ),
)
```

The edge's source key is the site's build key and its target key is the unit's. The register has one row per unit, so the unit reference also identifies the relationship.

### Two equivalent spellings

`rows=` with `bind=` is the form this page uses. You can also pass `build_key` and `properties` directly to `node_binding`, or the three keys and `properties` to `edge_binding`. Both spellings create the same binding. Do not mix them in one call.

## Rows: the value you hand the binding

`rows` accepts a row-source value: a table relation, a projection relation, or a derived source such as `source.where(...)`, `source.join(...)` or `source.group_by(...)`.

`rows=UnitTable` is accepted as a compatibility shorthand and converted to
`UnitTable.row_source()`. Prefer the explicit value; a `Struct` is a shape, not a
row source.

A binding has no separate predicate. Filter the row source you pass:

```python
active_units = UnitTable.row_source().where(
    lambda unit: unit.status.alter_rows().drop_null().expression.equals("active")
)
```

Use the filtered source directly for a one-off binding. Publish a projection when several bindings need the same filtered grain; see [projections](projections.md). Each binding owns its row context: a filter or expansion in one binding never changes another, even when both read the same source.

## Keys: graph identity

A node key identifies one node within its component. An edge key identifies one relationship record, and its source and target keys name the endpoint nodes by their build keys.

A build key must be a present scalar expression. Nullable, array and struct
expressions are rejected. A key written from a source column needs
`alter_rows().drop_null()` or `default_to(...)` when the field is declared
`Field[T | None]`; a `Field[T]` key is already present.

On a nullable value, `drop_null()` makes the key present and drops rows that
cannot be identified. `default_to()` keeps the row but gives every missing
identifier the same identity; use it only when a shared sentinel node is
genuinely correct. On a present value both calls are no-ops.

A constant is not an expression: wrap it in `value_expression(...)`.

If a relation is unique per ordered pair, derive its key from the endpoints. If several assertions can occur, derive the key from whatever distinguishes them. Two producers may emit the same key; their records are independent, so an overlapping key can appear more than once. Compose a deduplication module when exact duplicates are not wanted; see [modules](modules.md).

## Properties: a value for every declaration

Assign every declared property exactly once, including inherited ones; `build_unit` above does this for `UnitNode`.

Values are expressions evaluated per row. They may be selections or expressions,
and a constant uses `value_expression(...)`. A non-null value satisfies either a
nullable or a required property. A nullable value satisfies a nullable property
directly; for a required property, narrow or default it so the value carries the
non-null claim. A nullable expression is accepted for compatibility, but it does
not by itself guarantee presence.

A required property is a claim the build enforces. If an expression typed non-null turns out to be null, the build stops and names the component and the failing value; a property message also names the row's build key. A nullable property accepts null and stores an absent graph value.

A binding never aggregates. One row the binding receives produces one record. Reshape rows in a projection instead.

The rule follows the rows the binding receives, not the original file. A grouped source has already collapsed each key tuple to one row, so a binding over `{by, members}` emits one record per group. Use `members` to carry the collected rows into an array property. The algebra has no `count`, `sum` or `having`.

## Null handling

A nullable declaration or expression needs a null decision. The two operations
have different row behaviour:

| Goal | Use | Row |
| --- | --- | --- |
| Replace null and keep the row | `default_to(value)` | Kept |
| Drop rows whose value is null | `alter_rows().drop_null()` | Dropped |

On a present value both are no-ops. `drop_null()` is a row filter, not a
per-property mask. If it appears in any property or key expression, rows where
that nullable value is null disappear from the whole binding. Use it for keys and
for records that cannot exist without the value. Use `default_to()` for a
descriptive property when the row is still meaningful without it.

A field declared `Field[T | None]` can be passed directly to a nullable
property; a required property needs `default_to(...)` or
`alter_rows().drop_null()` to narrow it.

For arrays, a property declared `Array[T]` cannot accept `Array[T | None]`. Narrow the array first, then remove null items: `row.labels.alter_rows().drop_null().drop_null_items()`.

Use `row.labels.default_to([]).drop_null_items()` when an absent array should be stored as an empty list instead. Null and empty arrays are different values.

## Endpoint tokens

An edge binding may name an endpoint explicitly with `endpoint(...)`. Pass the token as `source_node` or `target_node`. For example, an edge whose source is an abstract category would use `source_node=endpoint(SiteNode)`.

`source_node` names the declared source side and `target_node` the declared target. A token must name a concrete node that equals or descends from the declared endpoint.

A token is required exactly when the declared side is an abstract category. An edge declared `Edge[AssetNode, DocumentedAbstractNode]` needs `target_node=endpoint(PlaceNode)`. A concrete side needs no token, though one still documents the component used. Endpoint identity is the component, not a producer, so two bindings may name different concrete endpoints.

## One target, one row context

A binding maps one row context onto one component. If one context feeds two components, or two sources feed one component, write one binding per pair.

Give each producer a distinct `debug_name` when a component has more than one. The name is reported by the meta-graph output and keeps the producers distinct in binding identity. Two bindings targeting the same component from the same row context with the same values and no distinguishing name describe the same binding and collide on identity.

Bindings are ordinary module-level values. The default `compile(modules=...)` discovers them by importing the calling file's namespace recursively. Re-exported objects are deduplicated by identity. Bindings created inside functions or stored in a container are not discovered. You can also pass bindings and sources explicitly to `compile`; see [compile and build](build-and-outputs.md).

Use `BindingOptions(annotations=...)` to carry portable metadata; see [semantics and annotations](semantics.md).

## Limits

- One received row produces one record. A binding does not itself aggregate, join or expand; those belong to the row source.
- A build key must be a present scalar. Keys, including endpoint keys, cannot be nullable, arrays or structs.
- `rows` takes a row-source value. A `Table` or `Projection` class is accepted as
  a compatibility shorthand; a `Struct` is not.
- Every declared property must be assigned exactly once.
- `alter_rows().drop_null()` removes the whole row; it does not write a null property.
- A token is required for an abstract endpoint and must name a concrete descendant.
- A namespace-discovered binding must be a module-level value.

## What to remember

- A binding is the only place where data shape and graph meaning meet.
- Name the target, the rows, a present scalar key and a value for every property.
- A `Field[T | None]` reads as nullable; `Field[T]` reads non-null; narrow keys and default or narrow properties.
- `drop_null()` drops the row from the whole binding; `default_to()` keeps it.
- Write one binding per target and row context, and use `debug_name` when one component has several producers.

## Next steps

- [Semantics and annotations](semantics.md) make these records explainable to consumers.
- [Modules](modules.md) add whole-graph stages after the bindings.

## Reference

[Bindings reference](../reference/bindings.md) lists the factory arguments, key and property rules, endpoint tokens and errors.
