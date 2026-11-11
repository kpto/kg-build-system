---
title: "7. Values and nullability"
summary: "A field read is a typed selection; absence belongs to the owner, nulls travel through calculations, and every row effect is one explicit decision."
section: book
perspective: book
part: II
chapter: 7
order: 24
status: normative
verified: 2026-11-11
sources:
  - docs/book/part-2/04-values-and-nullability.md
  - docs/appendix/reference/expressions.md
  - docs/appendix/spec/selection.md
---

## A field read is a value with a type and a history

Read `SitesTable.site_name`. The result is not a `str`. It is a `Selection` whose
logical type is a nullable text value. You cannot compare it with `==`, add it to
another value, index it, or hand it to `str()`. You call its methods. That single
decision shapes everything else in this chapter: the authoring value carries the
type of one position in a row, and every operation you apply to it is written
down.

`Selection[T]` is the only authoring value. `NullableSelection[T]` is an alias for
`Selection[Nullable[T]]`, not a second class. A literal built with
`value_expression(...)` is also a `Selection`. Every value operation is a method on
the selection, except `all_of` and `any_of`, which combine boolean selections. The
compiler expression tree stays private: there is no `.expression`, `.value` or
`.model` accessor, and no SQL string. `selection.logical_type` exposes the
canonical logical type of the position and nothing more.

The absence of Python operators is deliberate. `+` would need one meaning for
numbers, another for text, and no defensible meaning for a timestamp. `==` would
suggest that any two values can be compared, although temporal and `uuid` values
have no comparison operation at all. A method name states the operation:
`add`, `equals`, `prepend`, `to_string`. The reader of the declaration can see
exactly which operation was requested, and the build preserves it rather than
guessing an intent from an expression tree.

## Absence belongs to the owner of the value

The declaration `Field[str]` says what the value is, not whether it is there.
Presence belongs to the owner that supplies the value. That rule has three cases:

| Owner | Declaration | Read as |
| --- | --- | --- |
| Source `Table` | `Field[str]` | `Selection[Nullable[str]]` |
| Source `Struct` member | `Field[str]` | `Selection[Nullable[str]]` |
| `Projection` output | `computed_field(Selection[T])` | `Selection[T]` |
| `Projection` output | `computed_field(Selection[Nullable[T]])` | `Selection[Nullable[T]]` |

A source table may omit a column, a source file may omit a member, and a row may
hold no value. A struct member is always nullable because the source may omit it;
a nullable carrier also makes every member nullable. `SitesTable.premises` reads
as nullable, so `premises.contact.email` stays nullable even if the file that was
inspected had a value in every row.

A nullable owner inside a field type is refused. `Field[Nullable[str]]` is not a
way to spell "may be absent"; it is a second schema that can drift from the source.
Absence is flattened, so a nullable of a nullable is simply nullable.
`Nullable[T]` and `T | None` are one canonical type: `Nullable` is the authoring
alias for the union, and generated or hand-written spellings type-check
identically.

Array presence is a separate question from item nullability. A source array reads
as nullable because the source may omit the array. Whether its items may be null
is a fact about the value and stays in the declaration:
`Field[Array[Nullable[int]]]` reads as
`Selection[Nullable[Array[Nullable[int]]]]`. The array may be absent; when present,
an item may still be null.

Absence is one representation for several situations. The source may not publish
the member, a particular row may hold no value for it, or the value may not apply
to that row. The declaration does not ask the source to distinguish those cases; it
records the one fact it can observe, that the owner supplied no value. The author
supplies the meaning when choosing an effect. A missing measurement can default to
a sentinel, a missing identity must drop the row, and a value that never applies
to the row is usually a sign that the field does not belong to this shape.

Who decides absence, then? Three parties, at three moments:

- The source decides that a read is nullable. The author cannot remove that with a
  declaration.
- The computed selection decides a projection output: a present selection
  publishes a present output, a nullable selection publishes a nullable one.
- A row effect decides what happens to a row whose value is absent. That decision
  is always explicit, and it is the subject of the next two sections.

## Keeping the row and removing the row are different answers

There are two ways to answer a nullable value, and they mean different things.

`default_to(value)` replaces absence with a fallback and keeps the row. The result
is present. The fallback must have the member's exact value type; a mismatch is
refused when the operation is written, not discovered later in the data.

```python
site_name = SitesTable.site_name.default_to("Unnamed site")
```

`alter_rows().drop_null()` removes the row whose value is null and returns a
present selection. The row is gone, not the column.

```python
named_site = SitesTable.site_name.alter_rows().drop_null()
```

Choosing between them is a modelling decision, not a formatting preference.
Default a value that is genuinely optional for the record: a display label, a
description, a missing measurement that still leaves a meaningful record. Drop a
row when the value is required for the record to exist at all, and especially when
the value is an identity. Defaulting a key collapses identity: two rows that were
never distinguished receive the same fallback key, and the graph merges records
that the source kept apart. Drop an unidentified row with
`alter_rows().drop_null()` unless a shared fallback identity is deliberate.

Array items are a third case. `drop_null_items()` removes null items from an array
and keeps the row. Narrow the array to a present selection first:

```python
scores = SitesTable.priority_scores.alter_rows().drop_null().drop_null_items()
```

A null array, an empty array and an array of null items are three different facts.
The first two produce no rows when expanded; the third produces rows whose value
is null, which is why a graph property that demands non-null items needs
`drop_null_items()` before the binding.

## Every row effect passes through one gate, once

A value operation preserves the row count. `prepend`, `equals`, `add`, `at`,
`slice`, `extract`, `lookup` and `zip` compute a value for the row they receive.
A row effect does not: it decides whether the row survives, or how many rows the
array becomes. Row effects are reached only through `alter_rows()`.

```python
scores = SitesTable.priority_scores.alter_rows().expand()
```

`alter_rows()` returns a one-shot handle. The handle exposes only the effects that
are valid for that selection:

| Effect | Available on | Result |
| --- | --- | --- |
| `drop_null()` | A nullable selection | The present selection, one row removed for each null |
| `drop_if(predicate)` | Every selection | The same type, rows whose predicate is not true removed |
| `expand()` | A present or nullable array | The item selection, one row per item |

The handle is consumed by its first effect. A second effect needs a second
`alter_rows()`, and reusing a consumed handle raises `TypeError` with
`already consumed`. That is not a guard against a rare mistake; it is the model.
A row effect changes the row plan of every product that reads the selection, even
when the selection feeds only one property. Each effect must be visible at the
point where the author decided it, so the code cannot hide a chain of row
decisions behind one handle. The effect is not local to the expression that
carries it: a binding reads the resulting plan, so the record count is settled
before the mapping runs.

`drop_if(predicate)` keeps rows whose predicate is true and removes rows whose
predicate is false or null. The predicate receives the selection itself:

```python
depots = (
    SitesTable.site_name.alter_rows().drop_null()
    .alter_rows()
    .drop_if(lambda name: name.equals("Depot"))
)
```

`expand()` is the only fan-out among value operations. It produces one row per
array item, returns the item selection, and produces no rows for a null or empty
array. Expanding an array is a grain decision, so it is worth asking whether the
expansion belongs to the value plan at all; chapter 8 returns to that question
when it introduces the row-source spelling.

## Nulls travel through calculations

A null does not become zero, an empty string or false when it enters a
calculation. It stays null unless an operation says otherwise. The boolean
operations follow three-valued logic: `and_` is false when either side is false,
`or_` is true when either side is true, and an unknown side yields null. A null
predicate is not true, so a `where` or `drop_if` that keeps only true rows drops
that row.

```python
in_scope = (
    EquipmentTable.in_service.alter_rows().drop_null()
    .and_(EquipmentTable.survey_period.alter_rows().drop_null().equals("2026-08"))
)
```

The operations are deliberately narrow. `equals` is the only comparison, and it
exists on text only. `add` and `sub` exist on `int` and `float`. There is no
ordering operator, no `in`, and no indexing syntax. `not_`, `and_`, `or_`, `all_of`
and `any_of` combine boolean selections. Text has `prepend`, `append`, `replace`,
`before_separator` and `after_separator`. Arrays have `sort`, `unique`, `concat`,
`transform_items`, `drop_null_items`, `at`, `slice` and `zip`.

`to_string()` produces the canonical text form of the eight scalar units: `bool`,
`int`, `float`, `str`, `date`, `time`, `timestamp` and `uuid`. A timestamp keeps
the `T` separator, and a uuid is lowercase and hyphenated. Arrays, structs and
custom scalars are refused.

```python
site_key = SitesTable.site_id.alter_rows().drop_null().to_string()
```

There are no casts and no implicit conversions. A `Decimal` is not a `float`, a
string is not a `timestamp`, and a `uuid.UUID` is not a `str`. Temporal and `uuid`
values are stored, deduplicated and merged, but they expose no comparison or
filtering operation; call `to_string()` when one must participate in an identity.
Custom scalars expose no value operations at all. A value that has no
meaning-preserving operation is not coerced into one.

A nullable selection exposes no family operation. `prepend`, `equals`, `add` and
their siblings appear on the present selection, so a nullable read is narrowed or
defaulted before the operation. Numeric `add` and `sub` also refuse a nullable
operand even when the receiver is present. The type checker reports the missing
method rather than letting the build invent a meaning for "null plus one".

## Reading another relation is a value, not a join

A projection has one driving source. When one of its rows needs a record from
another relation, the author reads it by key as a value:

```python
units = SitesTable.site_id.lookup(EquipmentTable)

left = units
inner = units.alter_rows().drop_null()
one_per_unit = inner.alter_rows().expand()
```

`lookup(relation, key=None, *, target_key=None)` returns
`Selection[Nullable[Array[S]]]`: every target record whose key equals this row's
key, or null when nothing matches. The target may be a `Table` or a `Projection`.
`key` defaults to the receiver, and `target_key` defaults to the column name of a
direct field key; pass either explicitly when the source and target names differ.
A null key never matches.

`lookup` states no join mode. It returns a value and lets the author compose the
grain: keep the nullable array for a left read, `drop_null()` for an inner read,
and `drop_null()` followed by `expand()` for one row per match. It accepts no
`how` argument. That is the point: the value operation answers "which records
match this key?", and the row effect answers "what does the row become?".

This is also the only way a product reads a second relation. Adding a second
driving source to a projection is refused; a lookup is explicit about the key and
about the grain it creates.

## Two arrays can be paired without a key

`zip` pairs two arrays by position. It is a value operation, not a join: there is
no key, no matching and no row multiplication.

```python
from kg_build_system import Array, Field, Table, field

from reference_project.assets import Estate


class SiteTagTable(Table[Estate]):
    site_id: Field[str] = field()
    tags: Field[Array[str]] = field()
    labels: Field[Array[str]] = field()


paired = (
    SiteTagTable.tags.alter_rows().drop_null()
    .zip(SiteTagTable.labels.alter_rows().drop_null())
)
tag = paired.alter_rows().expand().extract(lambda pair: pair.left)
label = paired.alter_rows().expand().extract(lambda pair: pair.right)
```

The two arrays must have the same length. A mismatch is refused when the value is
evaluated; `zip` does not pad, truncate or drop the excess. An absent input makes
the result absent. The paired value is a `Pair` with present `left` and `right`
members; expand the paired array first, then read a member with `extract`.

The table above is a second declaration over the same estate asset, not a second
asset. It shows the intended shape of a table that pairs a tag list with a label
list. The same asset can back it because an asset is a logical source unit, and a
table is a row shape read from that unit.

## Expansion has two spellings, and one job

`Selection.expand` is the value-level spelling: a row effect inside a product that
already reads the row. `RowSource.unnest` is the relation-level spelling: it
changes the grain of the whole relation, keeps every other field, and narrows the
selected member to the item. A null or empty array produces no rows in either
form.

Do not use both for the same fan-out. Expand a nested array once, at the level
where the grain should change, and read the result from there. Expanding two
arrays in one plan is two fan-outs multiplied together, not a join; chapter 8
returns to that trap when it names a projection.

## Absence is a decision a reader can audit

Every absent value has an owner: the source that may omit it, the computed
selection that publishes it, or the effect that removes the row. Every decision
has a spelling: `default_to` keeps the row, `drop_null` removes it, `drop_if`
states a predicate, `expand` changes the row count. Nulls travel through
calculations instead of being silently replaced, and operations that the value
cannot support are absent rather than guessed.

A consumer of the graph can therefore read where a row disappears and why. That
is the difference between a null policy and a null accident. The next chapter
takes these values and asks what one row means once they are combined into a
relation.

## Next

[8. Grain and projections](/book/part-2/05-grain-and-projections) — from one typed value to the meaning of one row.
