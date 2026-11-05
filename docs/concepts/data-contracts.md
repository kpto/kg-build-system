# Data contracts

A data contract is a Python class that describes one row of input: its fields,
their types and the records nested inside it.

Data contracts are the first stage of a build. Source data is not under your
control. Columns are renamed, a number arrives as text, a nested object is absent.
A contract puts the shape you expect into the code that builds the graph, so a
mismatch is a declaration error rather than a surprise halfway through a build.
The class is the schema; there is no separate mapping document to keep in step
with it.

## Why contracts come first

Every later stage reads the same shape. A selection reads a field, a row source
returns rows of that shape, and a binding maps those rows onto node and edge
properties. If the shape is only a convention, each stage can interpret it
differently and the build discovers the disagreement late.

A contract fixes the vocabulary before any of that happens. Compilation can then
check that a field exists, that a value has the right type, and that a graph
property can hold what the binding supplies. No row is read to find a typing
mistake.

## The model

Three declarations cover the data side of a build:

- A `Table` describes a relation: one class, one row shape read from one
  [asset](assets.md). It is also a row source provider, so a binding can pass
  `SiteTable.row_source()` as its rows.
- A `Struct` describes a record nested inside a row or inside another struct. It
  is a shape only and is never a row source.
- A `Field[T]` declares one member. `T` is the value type, such as `str`, `Date`,
  a nested `Struct`, or an `Array` of those.

`Table` and source `Struct` members are source-backed and use `field()`.
Projection outputs and `ComputedStruct` members are selection-backed and use
`computed_field(selection)`. The host decides which constructor is legal; mixing
them is refused when the class is created.

A field declares a value type, never `T | None`. A source row may omit a value,
so every source field read is a `NullableSelection[T]`; the binding decides
whether to drop the row, default the value, or carry the absence into a nullable
property. Null handling is covered on
[types and nullability](types.md#a-field-declares-a-value-type).

## Example: one row per site

The survey project reads sites, units and defects. Each table is one grain of the
data, and each field names the value the source holds:

```python
from kg_build_system import Field, Struct, Table, field
from kg_build_system import Array, Date, Nullable

from estate.assets import Estate


class ContactStruct(Struct):
    """How a site can be reached."""

    email: Field[str] = field()
    phone: Field[str] = field()


class SiteTable(Table[Estate]):
    """One surveyed site."""

    site_id: Field[str] = field()
    name: Field[str] = field()
    surveyed_on: Field[Date] = field()
    contact: Field[ContactStruct] = field()
    aliases: Field[Array[Nullable[str]]] = field()


class UnitTable(Table[Estate]):
    """One asset at a site."""

    unit_id: Field[str] = field()
    site_id: Field[str] = field()
    label: Field[str] = field()


class DefectTable(Table[Estate]):
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

A nested JSON object becomes a `Struct`. Every source member reads as nullable,
because the source may omit the carrier or the member. Reach a member through
`extract`; presence composes:

```python
email = SiteTable.contact.extract(lambda contact: contact.email)
# Selection[Nullable[str]]
```

A present carrier still yields a nullable member for a source struct. A
`ComputedStruct` member is different: its witness supplies the type, so a
non-null witness under a present carrier stays non-null.

A `Struct` is never bound, placed in a table group or passed as `rows=`. It only
describes the value of a field. A nested record is also not a graph property;
bind its scalar members to separate property slots.

## Computed values and type witnesses

`computed_field(selection)` declares a value that comes from a selection rather
than from a source column. A projection uses it for its typed outputs; a
`ComputedStruct` uses it for a record that a row already carries:

```python
from kg_build_system import ComputedStruct, Field, Table, computed_field, field


class SiteSummaryStruct(ComputedStruct):
    """The member types a summary record carries."""

    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())
    name = computed_field(SiteTable.name.alter_rows().drop_null())


from estate.assets import Estate

class SummaryTable(Table[Estate]):
    site_id: Field[str] = field()
    summary: Field[SiteSummaryStruct] = field()
```

When `SiteSummaryStruct` is used as a field type, its member selections are
**type witnesses**. They fix each member's type but are not evaluated and do not
create a row plan. Under a present carrier, reading `summary.site_id` through
`extract` returns the nested data from the carrier row, typed as a present
string; `name` is present for the same reason, because its witness is a present
selection. A nullable witness or a nullable carrier makes the member nullable. A
witness only describes the record. To calculate a value from another relation,
declare a projection output instead. See
[computed structs](projections.md#computed-structs).

## Decisions you make

### Keep the value type, not the source's absence

Write `Field[str]` for the value, not a nullable annotation. Source access is
nullable because the source may omit a row value; the binding narrows or
defaults it. See
[nullability and the owner](types.md#a-field-declares-a-value-type).

### Declare an array at two levels

`Field[Array[str]]` names a list of non-null strings.
`Field[Array[Nullable[str]]]` names a list whose items may be null. That item
nullability stays in the declaration because a null item inside a list is a fact
about the value. Array presence is decided by the owner: a source array reads as
nullable, and a computed array output follows its selection.

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
not a union. It is a navigation and generation convenience, not a source
binding: each member table names its own asset. A group may therefore contain
tables from more than one asset. See [assets](assets.md).

### Generate a contract from an asset

An `@asset_contract(AssetContractOptions(...))` decorator on an asset makes
`kbs generate` write ordinary `Table[Asset]`, `Struct` and `TableGroup` classes
from a physical source. A generated source field always renders `Field[T]` from
its value type. The observed nullability claim is provenance for the manifest,
statistics and notes; it never adds absence to the rendered field. Generated
tables name the asset with `Table[Asset]`. A nullability `override` changes the
provenance claim, not the rendered annotation; change the asset contract and
regenerate, generated files are not hand-edited. Source access follows the owner:
a generated source field reads as nullable.

## Limits

- A field type must be a value record: a scalar, an array, a `Struct`,
  `ComputedStruct` or custom scalar. A table or projection cannot be a field
  type; bind that relation separately.
- A field annotation may not include absence. Use `Nullable[T]` for an array
  item, and narrow or default a source read in the binding.
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
