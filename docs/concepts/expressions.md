# Expressions

An expression is a typed value in a row: it reads a field, walks into a nested
record, fans a list into rows, or calculates a result.

A binding needs values for keys and properties. Writing those as SQL strings or
Python lambdas over dictionaries loses the type of the result and whether it may
be absent. Expressions sit between typed rows and the records built from them.
Every step is an explicit method call on a typed object, so compilation can check
what a value may become and you can see where a row changes.

## One authoring type

`Selection[T]` is the only authoring value type. It is a typed position in a
row: it navigates shape, calculates a value, and owns the decision about
absence. There is no separate expression object and no `.expression` escape
hatch; every operation is a method on the selection itself.

`Selection[T]` holds one value of type `T`. `NullableSelection[T]` is an alias
for `Selection[Nullable[T]]`, the same type with an absent value allowed.

| You want to | Write |
| --- | --- |
| name a field | `row.site_id` |
| decide what a null means | `alter_rows().drop_null()`, `default_to(...)` |
| walk into a struct | `extract(...)` |
| turn a list into rows | `alter_rows().expand()` |
| filter rows by a value | `alter_rows().drop_if(...)` |
| read another relation by key | `lookup(...)` |
| pair two lists by position | `zip(...)` |
| change a present list | `sort()`, `unique()`, `concat()`, `drop_null_items()` |
| calculate a value | `prepend`, `add`, `equals`, `to_string()` |

A binding and a projection output accept a selection. A literal is written with
`value_expression(...)`, which also returns a `Selection`.

A selection is an inline fragment in the blueprint, not a separately named
symbol. Its leaves are typed references: a field read names a `FieldRef`, an
operation names an `OperationRef`, and a literal is a canonical value. When a
calculation deserves a name that other declarations can read, use a projection
output or a computed field; those are the named, shared values.

## Nullability comes from the owner

A field declaration names a value type, never `T | None`. Presence is decided by
the owner that supplies the value:

- A source `Table` or source `Struct` may omit a value in its data, so every
  field read yields `NullableSelection[T]`.
- A computed `Projection` output or `ComputedStruct` member is backed by the
  selection you declare, so it yields exactly the selection's type.

```python
from kg_build_system import (
    Array, Field, Nullable, Projection, Struct, Table, computed_field, field,
)

from estate.assets import Estate


class ContactStruct(Struct):
    email: Field[str] = field()


class SiteTable(Table[Estate]):
    site_id: Field[str] = field()
    name: Field[str] = field()
    region_id: Field[str] = field()
    tags: Field[Array[str]] = field()
    aliases: Field[Array[Nullable[str]]] = field()
    contact: Field[ContactStruct] = field()


class RegionTable(Table[Estate]):
    region_id: Field[str] = field()
    name: Field[str] = field()


class SiteProjection(Projection(SiteTable.row_source())):
    site_id = computed_field(SiteTable.site_id.alter_rows().drop_null())
    label = computed_field(SiteTable.name.alter_rows().drop_null())
```

`SiteTable.site_id` reads as `Selection[Nullable[str]]`, even though it is
declared `Field[str]`. `SiteProjection.site_id` reads as `Selection[str]`
because its `computed_field` narrows the source value before publishing it.

A nested array item is different. Item nullability belongs to the value, so
`Field[Array[Nullable[str]]]` is allowed and reads as
`Selection[Nullable[Array[Nullable[str]]]]`. The outer nullable is the source
row; the inner nullable is the item.

## Narrow or default

Because source access is nullable, a value is narrowed before it is used as a
key, a required property, or the input of a present-only operation:

```python
site_id = SiteTable.site_id.alter_rows().drop_null()  # Selection[str]
name = SiteTable.name.default_to("Unnamed site")      # Selection[str]
```

`alter_rows().drop_null()` removes the row when the value is absent and returns
the present selection. `default_to(value)` keeps the row, replaces the absent
value, and returns the present selection. On a present selection the effects are
absent from the handle type.

The choice is semantic, not cosmetic. For a key, dropping is almost always
right: a fallback collapses distinct records into one identity. For a
descriptive property, a fallback may be honest; for a property that genuinely
may be absent, keep the nullable selection and let a nullable property carry it.

## Row effects are explicit

Some operations change which rows exist. They are reached through
`alter_rows()`, a one-shot handle that exposes only the effects valid for that
selection. Each effect returns a selection, not another handle, so a second
effect needs a second opt-in:

```python
tag = (
    SiteTable.tags
    .alter_rows().drop_null()
    .alter_rows().expand()
)
```

`expand()` turns an array into its items and produces one row per item. An absent
array and an empty array both produce no rows. A null item in a present array
produces one row whose value is null.

`drop_null()` removes the row when a nullable value is absent. It acts on the
whole row, even when the selection is used for only one property: dropping an
unnamed site means the site produces no node, not a node with an empty name.
`drop_null()` is not available on a selection that cannot be null.

`drop_if(predicate)` keeps rows whose value satisfies a Boolean predicate. The
predicate receives the selection and must return `Selection[bool]`; a false or
null predicate drops the row. `drop_if` is available on every selection.

| Selection | Row-effect handle exposes |
| --- | --- |
| Present scalar or struct | `drop_if` |
| Nullable scalar or struct | `drop_null`, `drop_if` |
| Present array | `expand`, `drop_if` |
| Nullable array | `drop_null`, `expand`, `drop_if` |

An effect that is not valid for the selection is absent from the handle type, so
the type checker reports the wrong use before the build runs.

## Navigation

`extract(selector)` reads one declared member of a struct. The selector receives
a typed instance of the struct shape and returns a field selection. It is
navigation: it adds no row effect and does not change the row count.

`at(index)` and `slice(start, end)` navigate an array without changing rows.
`at` returns a nullable item because an index may be out of bounds.

```python
email = SiteTable.contact.extract(lambda contact: contact.email)
first_tag = SiteTable.tags.alter_rows().drop_null().at(0)
window = SiteTable.tags.alter_rows().drop_null().slice(0, 2)
```

Presence composes through `extract`. A source struct member is nullable; a
nullable carrier makes even a present member nullable. A computed-struct member
keeps the type of its witness, composed with the carrier's presence.

## Read another relation with lookup

`lookup` reads every record of another relation whose key equals this row's key.
It is a value operation, not a row effect: the result is a nullable array of
target records, or null when no target matches. A null key never matches.

Row behaviour is composed from the result:

| Grain | Write |
| --- | --- |
| Left: keep this row, array or null | `value.lookup(Target, value)` |
| Inner: keep rows with a match | `value.lookup(Target, value).alter_rows().drop_null()` |
| One row per match | `value.lookup(Target, value).alter_rows().drop_null().alter_rows().expand()` |

```python
regions = SiteTable.region_id.lookup(RegionTable, SiteTable.region_id)
region = (
    regions
    .alter_rows().drop_null()
    .alter_rows().expand()
    .extract(lambda value: value.name)
)
```

`lookup` itself is ungated and composable: it does not choose a join mode. The
caller states the grain with `drop_null` and `expand`. The target may be a table
or a projection; pass `target_key=` when the target column has a different name
from the source key. There is no `how` argument and no implicit join.

## Pair lists with zip

`zip` pairs two arrays by position into one array of `Pair` records. The arrays
must have the same length; a mismatch is refused at execution. An absent input
makes the result absent. This is a value operation, not a row-level cross join.

```python
paired = (
    SiteTable.tags.alter_rows().drop_null()
    .zip(SiteTable.aliases.alter_rows().drop_null())
)
left = paired.alter_rows().expand().extract(lambda pair: pair.left)
right = paired.alter_rows().expand().extract(lambda pair: pair.right)
```

`Pair[L, R]` is a value record with present `left` and `right` members. Expand the
paired array before reading its members with `extract`.

## Arrays are values until you expand them

A source array reads as a nullable array because the source may omit it. Narrow
it first, then either use it as a value or expand it into rows:

```python
tags = SiteTable.tags.alter_rows().drop_null()  # Selection[Array[str]]
key = tags.sort().unique().concat("|")          # Selection[str]
first = tags.at(0)                              # Selection[Nullable[str]]
tag = tags.alter_rows().expand()                # Selection[str], one row per item
```

`sort`, `unique`, `concat`, `at`, `slice`, `transform_items` and `drop_null_items`
work on a present array. `at` and `slice` navigate without changing rows, so they
do not need `alter_rows()`. `at` returns a nullable item because an index may be
out of bounds. `concat` joins string items and refuses an array whose items may be
null; call `drop_null_items()` first.

`drop_null_items()` is the explicit conversion from `Array[Nullable[T]]` to
`Array[T]`. A graph property accepts the flat array, not the nullable-item one:

```python
aliases = SiteTable.aliases.alter_rows().drop_null().drop_null_items()
```

## Expand an array in the row source

`Selection.expand` is the row effect on a selection: it multiplies the rows of
the product that reads it. When the expansion *is* the grain of a relation, use
`RowSource.unnest` instead. It expands one direct array field and preserves every
other member of the row:

```python
one_tag_per_row = SiteTable.row_source().unnest(lambda site: site.tags)
```

A null or empty array produces no rows. The selected field is narrowed to its
item type; every other field keeps the source shape. A projection pinned to that
derived source reads the item through the generated shape:

```python
class TagProjection(Projection(one_tag_per_row)):
    site_id = computed_field(one_tag_per_row.shape.site_id.alter_rows().drop_null())
    tag = computed_field(one_tag_per_row.shape.tags)
```

## Filters and group keys

`row_source().where(...)` filters rows with a callable that receives a typed row
proxy and returns `Selection[bool]`. Filters chain, and every filter is kept:

```python
depots = SiteTable.row_source().where(
    lambda row: row.name.alter_rows().drop_null().equals("Depot"),
)
```

Use `any_of` and `all_of` to combine predicate selections. Both have an empty
identity, so a generated condition is safe when its list is empty.

Group keys are scalar selections. Rows whose key is null are dropped before
grouping, so every generated key member is non-null. The join, union, group and
order operations themselves are on [row sources](row-sources.md).

## Decisions you make

- **Narrow source access.** A source field reads nullable, so a key or a
  required property starts with `drop_null()` or `default_to()`.
- **Drop the row or keep it.** `drop_null()` means the record should not exist;
  `default_to()` means the absence has an honest fallback.
- **Expand only when the list is the grain.** Expanding one array multiplies the
  row; expanding two unrelated arrays multiplies both counts. Everything else in
  the row is repeated, so a constant key is emitted several times. Deduplication
  is a planner concern.
- **Write one row plan per product.** A projection or binding has one row plan:
  the filters on its source plus the effects its selections require, each applied
  once. Two uses of the same expanded field share one fan-out; effects never leak
  into another product.
- **Order expansions from the outside in.** A chain of expansions walks a nested
  document one level at a time. Reach a struct member with `extract` before
  expanding the array inside it.

## Limits

- There are no Python operators, no SQL strings and no implicit conversions.
  `+` does not add, and `==` does not compare.
- `equals` exists on text only. Numbers have `add` and `sub` but no comparison.
  Reshape the data rather than stringifying it to compare.
- `to_string()` exists for the eight canonical scalars only. Arrays, structs and
  custom scalars are refused.
- Temporal and `uuid` values expose no comparison or filtering operations.
  Custom scalars expose no value operations at all.
- A struct member selection is valid only inside `extract`; reading one elsewhere
  is refused.
- A `transform_items` selector may not contain a row effect.
- An expansion repeats every other value in the row. Identity and deduplication
  are handled by bindings and planners, not by `expand`.
- Boolean filters use three-valued logic: a null predicate drops the row, so
  narrow a nullable value before comparing it.

## Next steps

Continue with [row sources and grain](row-sources.md) to filter, join, group and
union these row plans.

## Reference

For every selection method, array operation, lookup, zip and row effect, see the
[expressions and selections reference](../reference/expressions.md).
