---
title: "9. Binding as implementation detail"
summary: "A binding is the one place where a row source becomes a concrete node or edge record."
section: book
perspective: book
part: II
chapter: 9
order: 26
status: normative
verified: 2026-11-11
sources:
  - docs/book/part-2/06-binding.md
  - docs/appendix/reference/bindings.md
  - docs/appendix/spec/binding.md
---

A node or edge declaration states what a record is. A row source states what rows exist. A binding is the only place where the second becomes the first. It is deliberately an implementation object: the design can be reviewed without it, and the data can change without rewriting the design.

## The binding is the only place a row becomes a record

A topology declaration never reads data. A table declaration never names a node or an edge. The binding is the only declaration that imports both sides, and that is why it is the seam.

`node_binding` and `edge_binding` accept two forms. The direct form names a key and a properties instance. The row-derived form names a row source and a callable. The callable receives a typed row proxy, not a dictionary and not data, and returns `NodeValues` or `EdgeValues`:

```python
from kg_build_system import (
    EdgeValues, Field, NodeValues, Table, edge_binding, field, node_binding,
)

from reference_project.assets import Estate
from reference_project.table.sites import SitesTable


class EquipmentTable(Table[Estate]):
    site_id: Field[str] = field()
    unit_ref: Field[str] = field()
    unit_name: Field[str] = field()
    in_service: Field[bool] = field()
    survey_period: Field[str] = field()


site_binding = node_binding(
    target=SiteNode,
    rows=SitesTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=row.site_name.default_to("Unnamed site"),
            summary=row.site_name.default_to("Unnamed site"),
        ),
    ),
)

unit_binding = node_binding(
    target=UnitNode,
    rows=EquipmentTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        properties=UnitNode(
            name=row.unit_name.default_to("Unnamed unit"),
            in_service=row.in_service.default_to(False),
            survey_period=row.survey_period,
            summary=row.unit_name.default_to("Unnamed unit"),
        ),
    ),
)

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

`SitesTable` is the site relation declared for the estate feed; `EquipmentTable` reads the equipment register.

`rows` takes a row-source value, never a `Table` or `Projection` class. A filter or a reshape belongs in the row source or in a projection. The row source has already decided the grain; the binding maps one row of that grain to one record.

The two forms are exclusive. Supplying `build_key` and `rows` together, or only half of either form, is refused. The direct form is not a shortcut around rows: a class-level selection still evaluates per row. A selection names a field symbolically; it is not a constant.

Why insist that the binding is the only place a row becomes a record? Because every other answer puts the mapping in a place that cannot be reviewed as a mapping. If topology read a table, the design would depend on a source schema. If a table named a node, the data language would need graph vocabulary and the graph language would need data vocabulary. If a planner invented records, the mapping would be a runtime behaviour rather than a declaration. The seam keeps the design above it and the plumbing below it.

## A key is a present scalar, and an edge has three

Every binding supplies a build key. The key identifies one record within its component. It is a present scalar selection. A nullable selection is refused; an array or struct selection is refused; a Python literal is refused unless it is wrapped in `value_expression(...)`.

A key read from a source field is nullable, because source access is nullable regardless of what the file claims. The author narrows it:

```python
build_key=row.site_id.alter_rows().drop_null()
```

`drop_null()` drops the row when the value is absent. That is usually the right answer for an identifier: a record without a key cannot be identified. `default_to()` is legal on a key, but every missing identifier then shares one identity. Use it only when a shared sentinel is genuinely correct, never to keep a row alive.

An edge supplies three keys: its own `build_key`, a `source_build_key` and a `target_build_key`. The endpoint keys name the nodes the relation grounds. A null endpoint key cannot ground a relation, so the row is dropped rather than given an invented endpoint. The relation's own key is separate from the endpoint keys because a relation is its own record; two edges may connect the same pair of nodes with different meanings or different `as_at` values.

Keys may overlap between producers. Two bindings can emit the same key independently, and the graph will hold both records until a deduplication or merge planner runs. The key states identity within a component; it does not enforce uniqueness across the whole build. Uniqueness is a planner decision, and making it a binding refusal would force every producer to know about every other producer.

## Every property once, and null is a topology decision

A binding assigns every declared property exactly once, including properties inherited from a template or a category. A missing property is refused. An extra property is refused. A bare value is refused; a property value is a selection or an expression.

The null rule is the subtle part:

- A required property needs a present selection. A nullable source read must be narrowed with `default_to(...)` or `drop_null()`.
- An optional property accepts a nullable selection, because the topology already says absence is meaningful.

`alter_rows().drop_null()` inside a property assignment is a row filter for the whole binding, not a per-property mask. If a unit has no name and the binding writes `name=row.unit_name.alter_rows().drop_null()`, the entire unit record disappears, not just the name. Use `default_to(...)` when the row remains meaningful without the value, and use a nullable property when absence is part of the design.

This is why the topology decision comes first. A property declared required is a promise that every record has a value. A property declared optional is a promise that a reader must handle absence. A binding cannot change either promise; it can only satisfy it or fail.

The same rule applies to arrays. A property declared `Array[str]` requires a present array with non-null items. A property declared `Array[str] | None` accepts an absent array, but not an array containing nulls. The framework refuses an array whose items are nullable; flatten the value or drop the row.

## Endpoints are named only where the design is abstract

An edge binding resolves its endpoints from the declared edge. When the declared side is concrete, the endpoint is already fixed. When the declared side is an abstract category, the binding must name the concrete node the row grounds:

```python
source_node=endpoint(SiteNode)
target_node=endpoint(UnitNode)
```

An `endpoint(...)` token is required exactly when the declared side is abstract. It must name a concrete node that equals or descends from that category. A token cannot widen the category, name a template, or point at another edge. Supplying a token for a concrete side is allowed and documents the component used, but it is not required.

The asymmetry is deliberate. A concrete endpoint is a design decision already made. An abstract endpoint deliberately leaves the choice open so that several concrete kinds can share one relation family; the binding is where that choice becomes concrete for a set of rows. Requiring a token there makes the choice visible instead of letting a default decide it.

## Identity is the content, not the label

Two bindings that map the same rows to the same component with the same keys, properties, endpoints and row plan, and with no distinguishing `debug_name`, are the same binding. The framework enforces that by deriving a content identity: the SHA-256 digest of the canonical binding document, truncated to sixteen hexadecimal characters, with `debug_name` and `python_ref` removed.

The digest covers the target and kind, the build key, the edge endpoint keys, every property selection, the resolved endpoint components, the row-source plan, the binding annotations and the optional semantics fragment. Change any of those and the identity changes. Rename a producer and it does not.

`debug_name` is the human handle. It prefixes the identity string for display and appears in the meta-graph's binding entries, but it does not enter the digest. This is the right split: the name helps a reader find a producer, while the content decides whether two producers are the same mapping. A `debug_name` distinguishes producers without changing the content they produce, and it cannot carry design.

Two bindings on one component with the same content and no distinguishing `debug_name` are refused as a duplicate blueprint symbol. That refusal is a feature. A silent second producer would make the graph's record count depend on import order or on which binding the planner happened to see first. The refusal says the model has one mapping stated twice, and the author should keep one or change the other.

## What the seam refuses to do

A binding does not aggregate, join, expand, deduplicate, merge or rewrite rows. One input row produces one record. A binding reads a row source whose grain already matches the record. If a defect grain is three expansions below a survey document, those expansions belong to a projection named for the grain, and the binding reads that projection. If a site and a unit need a join, the join belongs in a row source or a projection, not in a loop inside `bind`.

The refusals are not limitations of the factory. They protect the review surface. A binding that could join would be a second planner. A binding that could emit several records per row would hide grain. A binding that could merge would make the record count a runtime fact. Keeping the seam thin is what makes "which rows become which record" answerable by reading one declaration.

Python mode does not escape the model. It carries a `{module, qualname}` reference, not a live callable body. It is an execution mode for a mapping that needs imperative code, not a place to put a design that the declarative surface cannot express.

## Next

[10. Generating declarations](/book/part-2/07-generation) — turn an observed source schema into ordinary declarations without making generation part of the build.
