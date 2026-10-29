# Data contracts

A data contract is a Python class that describes one row of input: its fields,
their types and the records nested inside it.

Data contracts are the first layer of a build. Source data is not under your
control. Columns are renamed, a number arrives as text, a nested object is absent.
A contract puts the shape you expect into the code that builds the graph, so a
mismatch is a declaration error rather than a surprise halfway through a build.
The class is the schema; there is no separate mapping document to keep in step
with it.

## Why contracts come first

Every later layer reads the same shape. An expression reads a field, a row source
returns rows of that shape, and a binding maps those rows onto node and edge
properties. If the shape is only a convention, each layer can interpret it
differently and the build discovers the disagreement late.

A contract fixes the vocabulary before any of that happens. Compilation can then
check that a field exists, that a value has the right type, and that a graph
property can hold what the binding supplies. No row is read to find a typing
mistake.

## The model

Three declarations cover the data side of a build:

- A `Table` describes a relation: one class, one row shape. It is also a row
  source, so a binding can pass `SiteTable.row_source()` as its rows.
- A `Struct` describes a record nested inside a row or inside another struct. It
  is a shape only and is never a row source.
- A `Field[T]` declares one member. `T` is the value type, such as `str`, `Date`,
  a nested `Struct`, or an `Array` of those.

`Table` and source `Struct` members are source-backed and use `field()`.
Projection outputs and `ComputedStruct` members are expression-backed and use
`computed_field(expression)`. The host decides which constructor is legal; mixing
them is refused when the class is created.

The declaration names the value type, not whether a row supplies it. Every source
field reads as nullable, including a declared `Field[str]`. Presence is decided
in the binding with `alter_rows().drop_null()` or `default_to(...)`. That rule is
covered on [types and nullability](types.md#nullability-belongs-to-access).

## Example: one row per site

The survey project reads sites, units and defects. Each table is one grain of the
data, and each field names the value the source holds:

```python
from kg_build_system import Field, Struct, Table, field
from kg_build_system.types import Array, Date


class ContactStruct(Struct):
    """How a site can be reached."""

    email: Field[str] = field()
    phone: Field[str] = field()


class SiteTable(Table):
    """One surveyed site."""

    site_id: Field[str] = field()
    name: Field[str] = field()
    surveyed_on: Field[Date] = field()
    contact: Field[ContactStruct] = field()
    aliases: Field[Array[str | None]] = field()


class UnitTable(Table):
    """One asset at a site."""

    unit_id: Field[str] = field()
    site_id: Field[str] = field()
    label: Field[str] = field()


class DefectTable(Table):
    """One defect found on a unit."""

    defect_id: Field[str] = field()
    unit_id: Field[str] = field()
    title: Field[str] = field()
    status: Field[str] = field()
    severity: Field[int] = field()
    tags: Field[Array[str]] = field()
```

The names are inferred: `SiteTable` becomes `site`, `UnitTable` becomes `unit`,
and so on. Set `TableOptions(name=..., description=...)` when the external name or
the description should differ from the defaults.

The repeated `site_id` and `unit_id` are deliberate. A row source can join the
tables on those fields later, and a binding can build keys from them. The
contract does not decide the grain; it only states what each row holds. Grain and
joins are on [row sources](row-sources.md).

## Nested records

A nested JSON object becomes a `Struct`. Every step into it stays nullable: the
`contact` field may be absent, and when it is present a source member such as
`email` may still be absent in its own right. Use `extract` to read a member:

```python
email = SiteTable.contact.extract(lambda contact: contact.email)
# NullableSelection[str]
```

A `Struct` is never bound, placed in a table group or passed as `rows=`. It only
describes the value of a field. A nested record is also not a graph property;
bind its scalar members to separate property slots.

## Computed values and type witnesses

`computed_field(expression)` declares a value that comes from an expression rather
than from a source column. A projection uses it for its typed outputs; a
`ComputedStruct` uses it for a record that a row already carries:

```python
from kg_build_system import ComputedStruct, Field, Table, computed_field, field


class SiteSummaryStruct(ComputedStruct):
    """The member types a summary record carries."""

    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())
    name = computed_field(SiteTable.name)


class SummaryTable(Table):
    site_id: Field[str] = field()
    summary: Field[SiteSummaryStruct] = field()
```

When `SiteSummaryStruct` is used as a field type, its member expressions are
**type witnesses**. They fix each member's type and nullability but are not
evaluated and do not create a row plan. Under a present carrier, reading
`summary.site_id` through `extract` returns the nested data from the carrier row,
typed as a present string; reading `name` returns a nullable string. A witness
only describes the record. To calculate a value from another relation, declare a
projection output instead. See
[computed structs](projections.md#computed-structs).

## Decisions you make

### Name the value, not its presence

Write `Field[str]`, not `Field[str | None]`. A top-level `| None` is accepted and
stripped because source access is nullable either way; the binding owns presence.
See [nullability on access](types.md#nullability-belongs-to-access).

### Declare an array at two levels

`Field[Array[str]]` names a list of non-null strings. `Field[Array[str | None]]`
names a list whose items may be null. That item union stays in the declaration
because a null item inside a present list is a fact about the value. Array
presence belongs to access, so do not write `Field[Array[str] | None]`.

### Describe names and meaning

The Python attribute and the external field name are usually the same in snake
case. Use `field(name="...")` when the source spells a column differently. Write
a documentation string below a field, or pass `description=`, to explain what the
value means rather than how it is derived. A table's class docstring is its
description unless `TableOptions` overrides it.

### Share fields with a template

A `StructTemplate` shares fields and annotations with `Table`, `Struct` and
`ComputedStruct` hosts. Put the template first in the base list and give it
`StructOptionsTemplate`; it never becomes a declaration of its own and never
enters the compiled blueprint. A `ComputedStruct` host accepts the template's
annotations, but its members still need `computed_field`. Templates are the way
to carry common provenance columns without copying members.

### Let a group describe a family

A `TableGroup` is a catalog of concrete tables and nested groups, not a shape and
not a union. It lets one source binding describe a family whose files follow one
layout. Each member keeps its own rows and its own shape. See
[sources](sources.md#when-a-family-shares-a-layout).

### Generate a contract from a source

`kbs generate` writes ordinary `Table`, `Struct` and `TableGroup` classes from a
physical source. The generated field names the value type only. If the source
declares nullability, the generator records that claim in the file header and the
generation manifest, not in the field type: every source field still reads as
nullable. A nullability `override` can assert or decline a claim for the
generator's diagnostics, but it does not change the rendered field or make access
non-null. Change the request and regenerate; generated files are not hand-edited.

## Limits

- A field type must be a value record: a scalar, an array, a `Struct`,
  `ComputedStruct` or custom scalar. A table or projection cannot be a field
  type; bind that relation separately.
- A `Struct` has no location, no row source and no group membership.
- `Table`, `TableGroup` and `Projection` are final. Share members through a
  `StructTemplate` instead of inheriting from another final declaration. A
  data-domain template belongs on a table, struct or computed struct, not on a
  projection or table group.
- `options` is reserved for declaration metadata. If the data has a column named
  `options`, declare the attribute as `options_`.
- Two members of one declaration cannot share an external name.
- A graph property is a scalar or a flat array of non-null scalars. Nested
  structures are expanded or reified before binding; see
  [types](types.md#what-a-value-may-become).

## Next steps

Continue with [types and nullability](types.md) to see how these annotations
become checked logical types.

## Reference

For the complete declaration surface, including options, field constructors,
templates and generated contracts, see the
[declarations reference](../reference/declarations.md).
