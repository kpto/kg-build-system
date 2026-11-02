# Expressions

An expression is a typed value in a row: it names a field, walks into a nested
record, fans a list into rows, or calculates a result.

A binding needs values for keys and properties. Writing those as SQL strings or
Python lambdas over dictionaries loses two things the build depends on: the type
of the result and whether it may be absent. Expressions sit between typed rows
and the records built from them. Every step is an explicit method call on a typed
object, so the compiler can check what a value may become and you can see where a
row changes.

## Selections and expressions

Two kinds of object appear in a row plan:

- A **selection** is a typed position in a row. It navigates shape and chooses a
  null policy, but it does not calculate.
- An **expression** is a calculation. It has a result type and no null policy of
  its own.

Reading a field gives a selection. Asking it for `.expression` gives a bindable
expression. This split is load-bearing: a nullable expression exposes no typed
calculations, so narrowing happens before arithmetic or comparison.

| You want to | Write |
| --- | --- |
| name a field | `row.site_id` |
| decide what a null means | `alter_rows().drop_null()`, `default_to(...)` |
| walk into a struct | `extract(...)` |
| turn a list into rows | `alter_rows().expand()` |
| filter rows by a value | `alter_rows().drop_if(...)` |
| change a present list | `sort()`, `unique()`, `concat()`, `drop_null_items()` |
| calculate a value | `prepend`, `add`, `equals`, `to_string()` |

A binding and a projection output accept either a selection or an expression.

## Start from the declared access

A source field reads the type it declares. `Field[str]` reads as a present
`ValueSelection[str]`; `Field[str | None]` reads as a nullable
`NullableSelection[str]`. The declaration owns presence. Narrow or default a
nullable value before using it, and leave a present value alone:

```python
from estate.table import DefectTable, SiteTable

key = SiteTable.site_id.alter_rows().drop_null()        # no-op when declared Field[str]
name = SiteTable.name.default_to("Unnamed site")        # no-op when declared Field[str]
```

When a field is declared `Field[str | None]`, `drop_null()` removes the row and
`default_to()` supplies a fallback.

A projection field and a `ComputedStruct` member are different. A projection's
`computed_field(expression)` carries the expression's type, so a non-null
expression reads as non-null. A `ComputedStruct` member is read through `extract`;
its expression is a type witness, and the carrier's nested data supplies the
value.

## Row effects are explicit

Some operations change which rows exist. They are reached through `alter_rows()`,
a one-shot handle that exposes only the effects valid for that selection. Its
methods return a selection, not another handle, so a second effect needs a second
opt-in:

```python
tag = (
    DefectTable.tags
    .alter_rows().drop_null()
    .alter_rows().expand()
)
```

`expand()` turns an array into its items and produces one row per item. An absent
array and an empty array both produce no rows. A null item in a present array
produces one row whose value is null.

`drop_null()` removes the row when a nullable value is absent. It acts on the
whole row, even when the expression is used for only one property: dropping an
unnamed site means the site produces no node, not a node with an empty name. On a
present selection it is a no-op.

`drop_if(predicate)` keeps rows whose value satisfies a boolean predicate. The
predicate is value-scoped and must return a `BoolExpression`; a false or null
predicate drops the row.

`default_to(value)` does not change the row. It replaces a null and returns a
non-null selection of the same shape. On a present selection it is a no-op. The
fallback must have the field's exact type.

## Calculations keep the type

Once a value is non-null, expression methods calculate with it:

```python
label = name.expression.prepend("site: ")
```

Text has `prepend`, `append`, `replace`, `before_separator`, `after_separator`
and `equals`. Numbers have `add` and `sub`. Booleans have `not_`, `and_` and
`or_`. Every canonical scalar has `to_string()`, which is the way into an
identity. Nullability propagates through a calculation: a nullable input yields a
nullable result.

Methods that combine values accept a Python literal or an expression, not a
selection. Use `.expression` or `as_expression(...)` when a selection is one of
the inputs.

`value_expression(...)` creates a literal and infers its type from the Python
value. A bare `None` has no type, so a null literal needs an explicit nullable
type; fields and selections are the usual way to carry absence.

## Arrays are values until you expand them

A source array reads the type it declares. `Field[Array[str]]` reads as a present
`ArraySelection`; `Field[Array[str] | None]` reads as nullable, so narrow it
first. Then either use the array as a value or expand it into rows. `expand` is
the only row effect; the rest calculate a new array:

```python
tags = DefectTable.tags.alter_rows().drop_null()   # ArraySelection[str]; no-op if present
tag_key = tags.sort().unique().concat("|")         # ValueSelection[str]
first = tags.at(0)                                 # NullableSelection[str]
```

`sort`, `unique`, `concat`, `at`, `slice` and `transform_items` work on a present
array. `at` and `slice` navigate without changing rows, so they do not need
`alter_rows()`. `at` returns a nullable item because an index may be out of
bounds. `concat` joins string items and refuses an array whose items may be null;
call `drop_null_items()` first.

`drop_null_items()` is the explicit conversion from `Array[T | None]` to
`Array[T]`. A graph property accepts the flat array, not the nullable-item one:

```python
aliases = SiteTable.aliases.alter_rows().drop_null().drop_null_items()
```

## Filters and group keys

`row_source().where(...)` filters rows with a callable that receives a symbolic
shape instance and returns a `BoolExpression`. `Table.where` and
`Projection.where` are shorthand for the same filter. Filters chain, and every
filter is kept:

```python
open_defects = DefectTable.row_source().where(
    lambda row: row.status.alter_rows().drop_null().expression.equals("open"),
)
```

Use `any_of` and `all_of` to combine predicates. Both have an empty identity, so
a generated condition is safe when its list is empty.

Group keys are scalar inputs to `group_by`. Rows whose key is null are dropped
before grouping, so every generated key member is non-null. The join, union,
group and order operations themselves are on [row sources](row-sources.md).

## Decisions you make

- **Narrow when the declaration is nullable.** A key, a required property or an
  array operation starts with `drop_null()` or `default_to()` when its source
  field is declared `T | None`; both calls are no-ops on a present value.
- **Drop the row or keep it.** `drop_null()` means the record should not exist;
  `default_to()` means the absence has an honest fallback. For a key, dropping is
  almost always right, because a fallback collapses distinct records into one
  identity.
- **Expand only when the list is the grain.** Expanding one array multiplies the
  row; expanding two unrelated arrays multiplies both counts. Everything else in
  the row is repeated, so a constant key is emitted several times. Deduplication
  is a module concern.
- **Write one row plan per product.** A projection or binding has one row plan:
  the filters on its source plus the effects its expressions require, each applied
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
  are handled by bindings and modules, not by `expand`.
- Boolean filters use three-valued logic: a null predicate drops the row, so
  narrow a nullable value before comparing it.

## Next steps

Continue with [row sources and grain](row-sources.md) to filter, join, group and
union these row plans.

## Reference

For every selection, expression method, array operation and row effect, see the
[expressions and selections reference](../reference/expressions.md).
