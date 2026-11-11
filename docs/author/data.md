---
title: Declare data
summary: A Table names a source asset; a Field names a value type; the owner that supplies the value decides whether it may be absent.
section: author
order: 20
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/data/model/public/declarations.py
  - kg_build_system/distribution/languages/data/service/_private/descriptors.py
  - docs/author/data.md
subject: data
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Data contracts and types</span><a href="/subjects/data">Overview</a><a href="/author/data" class="active">Guide</a><a href="/spec/data">Spec</a><a href="/reference/api">API</a><a href="/philosophy/meaning-first">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> Data declarations are the schema. There is no separate mapping document: the class is the row shape, every field is a typed column, and a nested record is another class.

## What it is

| Declaration | Job | Read as |
| --- | --- | --- |
| `Table[Asset]` | Rows read from one logical asset. | `Table.row_source()` |
| `Struct` | A nested record inside a source row. | A member of a `Table`. |
| `ComputedStruct` | A nested value built from expressions. | A member of a computed read. |
| `Projection` | A named relation over one row source. | `Projection.row_source()` |
| `TableGroup` | A catalog of tables; not a row shape. | Discovery only. |
| `StructTemplate` | Annotations-only mixin for rows. | Not a source itself. |

`field()` declares a source member. `computed_field(selection)` declares a computed member on a `Projection` or `ComputedStruct`. The host decides which constructor is legal.

<figure class="kb-plate">
  <img src="/_assets/nullability.svg" alt="Source reads are nullable, computed reads follow their selection, and row effects make an explicit decision.">
  <figcaption>Absence belongs to the owner. The field annotation never writes it.</figcaption>
</figure>

## Rules

- A concrete `Table` is `Table[Asset]`. A table that omits its asset, or inherits another final table, is refused.
- A `Field[T]` declares a value type, never `T | None`. `Field[str | None]` is a static type error; the source read already returns `Selection[Nullable[str]]`.
- Source `Table` and source `Struct` reads are nullable. `Projection` outputs and `ComputedStruct` members follow their `computed_field` selection.
- Nested item absence stays in the value: `Field[Array[Nullable[str]]]` is legal; a nested owner nullable is refused.
- A graph property is a scalar or a flat, non-null array of scalars. Nested richness becomes nodes and edges.
- `TableGroup` needs at least one final table or table group member. It is not a row source.
- Custom scalars and structs are identified by `(module, qualname)` and must be top-level and importable.

## Example

```python
from kg_build_system import Array, Field, Struct, Table, field

from reference_project.assets import Estate


class ContactLocation(Struct):
    city: Field[str] = field(name="city")
    room: Field[str] = field(name="room")


class Contact(Struct):
    email: Field[str] = field(name="email")
    location: Field[ContactLocation] = field(name="location")


class Premises(Struct):
    contact_name: Field[str] = field(name="contact_name")
    contact: Field[Contact] = field(name="contact")


class SitesTable(Table[Estate]):
    site_id: Field[str] = field(name="site_id")
    site_name: Field[str] = field(name="site_name")
    premises: Field[Premises] = field(name="premises")
    priority_scores: Field[Array[int | None]] = field(name="priority_scores")
```

Read `SitesTable.site_name` and the type is `Selection[Nullable[str]]`. Read `DefectProjection.title` and the type is whatever its `computed_field` selection says.

## Limits

- Exact numeric and temporal behaviour is canonical: eight unit scalars, `Array[T]`, structs and custom scalars. `Date`, `Time`, `Timestamp` and `Uuid` are aliases, not second types.
- `Table` and `Projection` are not legal field value types. A relation is read through `row_source()`.
- A computed field annotation is not a second schema: it follows its selection.
- Generated source uses `Field[T]`; observed nullability is provenance for notes and statistics, never `| None` in the declaration.
- A table group is a catalog, not a union. It does not produce rows.

## Next

[Select values](/author/values) — what a field read gives you and how to narrow it.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-003 | Treat canonical types as a kernel assumption and keep default implementations in the distribution. | 2026-11-03 | accepted | `tests/kernel/test_kernel.py` |
| D-014 | Unify authoring around `Selection[T]` with owner-derived nullability. | 2026-11-05 | accepted | `tests/test_authoring_api.py` |
| D-025 | Treat observation as provenance: every generated source field renders `Field[T]`, never an optional annotation. | 2026-11-05 | accepted | `tests/test_codegen_discovery.py` |
| D-029 | Restrict graph properties to scalars or flat arrays of non-null scalars, and type SQL output by the property type. | 2026-10-22 | accepted | `docs/reference/types.md#graph-property-shape` |
