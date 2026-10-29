# Bindings

Topology says what a node or edge *means*. A binding says which rows produce
those records and what each property receives. It is the only place where data
shape and graph meaning meet.

A node binding emits one node per input row; an edge binding emits one edge per
row. There is no separate mapping document and no SQL: you write typed Python,
and every value is checked against the declaration at binding creation.

Every binding names a concrete `target`, the rows it reads, its keys, and a
value for every declared property. It may carry endpoint tokens, `debug_name`,
and `options`. Only row-derived values live inside `bind`; the rest stay outside.

## The two current forms

The `rows=` + `bind=` form evaluates a callable against the row shape and
returns `NodeValues` or `EdgeValues`. The direct form assigns expressions to
`build_key`, endpoint keys where needed, and `properties`. Both forms are
current; neither is deprecated, and they may not be mixed in one call.

These declarations are used throughout the page:

```python
from kg_build_system import Edge, Field, Node, PropertySlot, Table, field, property

class EquipmentTable(Table):
    site_id: Field[str] = field()
    unit_ref: Field[str] = field()
    unit_name: Field[str] = field()
    in_service: Field[bool] = field()
    survey_period: Field[str] = field()
    status: Field[str] = field()

class SiteNode(Node):
    name: PropertySlot[str] = property()

class UnitNode(Node):
    name: PropertySlot[str] = property()
    in_service: PropertySlot[bool] = property()

class HasUnitEdge(Edge[SiteNode, UnitNode]):
    as_at: PropertySlot[str] = property()
```

Every column reads as a nullable selection, even though the fields name plain
value types. A binding therefore narrows keys and defaults or narrows properties
before it assigns them.

A node binding in the `rows=` form:

```python
from kg_build_system import NodeValues, node_binding

unit_binding = node_binding(
    target=UnitNode,
    rows=EquipmentTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        properties=UnitNode(
            name=row.unit_name.default_to("Unnamed unit"),
            in_service=row.in_service.default_to(False),
        ),
    ),
)
```

The same binding in the direct form:

```python
direct_unit_binding = node_binding(
    target=UnitNode,
    build_key=EquipmentTable.unit_ref.alter_rows().drop_null(),
    properties=UnitNode(
        name=EquipmentTable.unit_name.default_to("Unnamed unit"),
        in_service=EquipmentTable.in_service.default_to(False),
    ),
)
```

An edge binding in the `rows=` form:

```python
from kg_build_system import EdgeValues, edge_binding

has_unit_binding = edge_binding(
    target=HasUnitEdge,
    rows=EquipmentTable.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        source_build_key=row.site_id.alter_rows().drop_null(),
        target_build_key=row.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(
            as_at=row.survey_period.default_to("Unrecorded period"),
        ),
    ),
)
```

The direct edge form supplies the same keys and properties. A site binding,
not shown, produces the source nodes; the register gives one row per unit, so
the unit reference also keys the relation.

```python
direct_has_unit_binding = edge_binding(
    target=HasUnitEdge,
    build_key=EquipmentTable.unit_ref.alter_rows().drop_null(),
    source_build_key=EquipmentTable.site_id.alter_rows().drop_null(),
    target_build_key=EquipmentTable.unit_ref.alter_rows().drop_null(),
    properties=HasUnitEdge(
        as_at=EquipmentTable.survey_period.default_to("Unrecorded period"),
    ),
)
```

The `bind` callable receives a row *shape instance* — a symbolic proxy, not data
and not a dictionary. Access fields as attributes. A named helper takes the
shape instance and returns `NodeValues[UnitNode, str]` or the matching
`EdgeValues`.

## Rows: tables, projections and filters

`rows` accepts a row-source value: `Table.row_source()`, `Projection.row_source()`,
or a derived source such as `source.where(...)`, `source.join(...)` or
`source.group_by(...)`. A declaration class is not accepted; write
`Table.row_source()`. A `Struct` is a shape, not a row source.

A **table** gives the grain of the source contract; a **projection** gives a
named grain several bindings can share; a **derived row source** filters,
joins, groups, unions, deduplicates or orders either. Every one of those
operations returns a row source, and a projection relation accepts the same
algebra. The predicate receives a symbolic shape instance and returns a Boolean
expression:

```python
active_units = EquipmentTable.row_source().where(
    lambda row: row.status.alter_rows().drop_null().expression.equals("active")
)
```

Use `rows=active_units` for a one-off filter; a binding has no separate
predicate. `EquipmentTable.where(...)` is shorthand for the same filter. When
several bindings need the same filtered grain, publish a projection over it:

```python
class ActiveUnitsProjection(active_units.projection_base()):
    """The active units, under a name bindings can share."""
```

The projection base carries the filter and the source's inherited outputs in its
plan; the named class is what other declarations reference. See
[projections](projections.md).

Each binding owns its row context: a filter or expansion in one binding never
changes another, even when both read the same source.

## Keys

The build key is graph identity. It must be a non-null scalar expression;
nullable, array, and struct expressions are rejected. A Python literal is not
an expression: wrap a constant in `value_expression(...)`.

A node key identifies one node within its component; an edge key identifies one
relationship record. `source_build_key` and `target_build_key` name the
endpoint nodes by their build keys. Keys may use any scalar type.

Every source field reads as nullable, so a key written from a source column
needs `alter_rows().drop_null()` (or `default_to(...)`). `drop_null()` makes the
key present and drops rows that cannot be identified. Because it is a row
effect, it is reached through `alter_rows()`. `default_to` is legal on a key, but
it gives every missing identifier the same identity; use it only when a shared
sentinel node is genuinely correct. If a relation is unique per ordered pair,
derive its key from the endpoints; if several assertions can occur, derive the
key from whatever distinguishes them.

Two producers may emit the same key. Their records are independent, so an
overlapping key can appear more than once; compose a deduplication module when
exact duplicates are not wanted. See [modules](modules.md).

## Assigning properties

Assign every declared property exactly once, including inherited properties:

```python
UnitNode(
    name=row.unit_name.default_to("Unnamed unit"),
    in_service=row.in_service.default_to(False),
)
```

Values are expressions evaluated per row. A constant uses
`value_expression("degC")`. The expression type must match the declaration; a
non-null value may satisfy a nullable property, but a nullable value may not
satisfy a required one. Missing and unknown properties both fail.

A binding never aggregates: one input row produces one record. Reshape rows in a
projection. The rule is about the rows the binding receives, not the source's
original rows: `group_by` has already collapsed each key tuple to one row, so a
binding over `{by, members}` emits one record per group. Use `members` to carry
the collected rows into an array property; there is no SQL aggregate, count,
sum or `having` in the algebra.

```python
from kg_build_system import Node, PropertySlot, property

class StatusNode(Node):
    members: PropertySlot[str] = property()

by_status = EquipmentTable.row_source().group_by(
    by=lambda row: {"status": row.status},
)

status_binding = node_binding(
    target=StatusNode,
    rows=by_status,
    bind=lambda row: NodeValues(
        build_key=row.by.extract(lambda key: key.status),
        properties=StatusNode(
            members=row.members
            .transform_items(lambda member: member.extract(lambda item: item.unit_ref))
            .drop_null_items()
            .concat("|"),
        ),
    ),
)
```

## Null handling

| Operation | Effect | Row |
| --- | --- | --- |
| `default_to(value)` | Replaces null with a value | Kept |
| `alter_rows().drop_null()` | Narrows the type by dropping nulls | Dropped |

`drop_null()` is a row filter, not a per-property mask. If it appears in any
property or key expression, rows where that value is null disappear from the
whole binding. It is the right choice for keys and often wrong for a
descriptive property. Use `default_to` when the row is meaningful without the
value; use `drop_null()` when it cannot ground the record at all.

A required property is a claim the build enforces. If a statically non-null
expression turns out to be null, the build stops with a message naming the
component and value; a property message also names the row's build key. A
nullable property accepts null and stores no value. Because every source field
reads as nullable, a nullable property can take a source field directly, while a
required property needs `default_to(...)` or `alter_rows().drop_null()`.

For arrays, a property declared `Array[T]` cannot accept `Array[T | None]`. The
source array is nullable as a whole, so narrow it first, then drop null items
when the declared item type is non-null:
`row.labels.alter_rows().drop_null().drop_null_items()` removes absent arrays
and null items together. Use `row.labels.default_to([]).drop_null_items()` when
an absent array should be stored as an empty list instead. Null and empty arrays
are different values.

## Endpoint tokens

An edge binding may name an endpoint explicitly with `endpoint(...)`. Pass the
tokens as `source_node` and `target_node` to either form:

```python
from kg_build_system import endpoint

site_endpoint = endpoint(SiteNode)
unit_endpoint = endpoint(UnitNode)
```

Pass them as `source_node=site_endpoint` and `target_node=unit_endpoint`.
`source_node` names the declared source side, `target_node` the declared target.
A token must name a concrete node that equals or descends from the declared
endpoint. When a declared side is an abstract category its token is required:
an edge declared `Edge[AssetNode, DocumentedAbstractNode]` needs
`target_node=endpoint(PlaceNode)`. Concrete sides need no token, though one
still documents the component used. Endpoint identity is the component, not a
producer, so two bindings may name different concrete endpoints.

## One target, one row context

A binding maps one row context onto one component: if one context feeds two
components, or two sources feed one component, write one binding per pair.

Give each producer a distinct `debug_name` when a component has more than one.
The name is reported by the meta-graph output and keeps the producers distinct
in binding identity. Two bindings targeting the same component from the same row
context with the same values and no distinguishing `debug_name` are not two
producers; they describe the same binding and collide on identity.

## Annotations and debug names

Attach portable metadata with `BindingOptions`:

```python
from dataclasses import dataclass
from kg_build_system import Annotation, BindingOptions

@dataclass(frozen=True)
class Tracked(Annotation):
    namespace = "example_project"
    annotation_id = "tracked"
    stage: str

binding_options = BindingOptions(annotations=(Tracked(stage="derived"),))
```

Pass it as `options=binding_options`. Annotations are preserved for modules
that understand their namespace and ID; see [annotations and
descriptions](annotations.md).

A binding has no description field; use a module docstring or comment above it.
`debug_name` is the human handle carried into the meta-graph. It does not appear
in failure messages, which name the component and the failing value.

## Finding bindings in a project

Bindings are ordinary module-level values, and a typical project mirrors the
topology layout:

```text
graph_pipeline/
  build.py
  topology/site/__init__.py             # SiteNode
  topology/site/has_unit__unit.py       # HasUnitEdge
  bindings/site/__init__.py             # site binding
  bindings/site/has_unit__unit.py       # edge binding
```

`compile(modules=...)` discovers `NodeBinding`, `EdgeBinding`, and `BoundSource`
values by importing the calling file's namespace recursively. Re-exported
objects are deduplicated by identity. Bindings created inside functions or
stored in a container are not discovered.

The other modes are `compile(namespace_path="graph_pipeline", modules=...)` to
name the namespace explicitly, and `compile(bindings=(...), sources=(...),
modules=...)` to supply both declarations and sources.

A normal entry point is a module at the project root:

```python
from kg_build_system import compile
from kg_build_system.modules import (
    FileModule, FileModuleConfiguration, register_module,
)

contract = compile(
    modules=(register_module(FileModule, FileModuleConfiguration("graph.jsonl")),),
)
```

`create_blueprint(modules=...)` performs the same discovery for inspection
before building. Every table read by a binding needs a source binding; see
[sources](sources.md) and [compile and build](build.md).

!!! warning "Row values are not row filters"
    `alter_rows().drop_null()` in a property expression drops the row from that
    binding. It does not replace the property value with null. Use
    `default_to()` when the row must survive.

## What to remember

- A binding is the only place data shape and graph meaning meet.
- Every binding names a target, a row source, a present scalar key and a value
  for every declared property.
- Every source field reads as nullable. Narrow keys with
  `alter_rows().drop_null()`; default or narrow properties.
- Write one binding per target and row context; use `debug_name` when one
  component has several producers.
- `alter_rows().drop_null()` removes a row. Use it for keys instead of
  defaulting them.
- Bindings are discovered at module level, so keep each one small and named.

Next: [Annotations and descriptions](annotations.md) documents what these
records mean, and [Modules](modules.md) adds whole-graph stages.
