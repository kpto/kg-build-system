# Expressions

A binding needs values, not SQL. Expressions name a field, walk into a nested
record, fan a list out into rows, and transform what you find. Every step is an
explicit method call on a typed object: no Python operators, no string SQL, no
hidden conversions.

Two facts make the model easy to hold: a value knows its logical type including
nullability, and every operation says whether it changes the row. Row-changing
operations are reached through a one-shot handle, `alter_rows()`, so their cost
is visible where you write them.

## Selections and expressions

Reading a field gives a **selection**: a typed position in a row. A selection
navigates shape and chooses a null policy, but it does not calculate. Asking a
selection for `.expression` gives a **bindable expression**: a calculation whose
result is a value, with no null policy of its own.

| You want to | Use | Lives on |
| --- | --- | --- |
| name a field | `row.site_id` | selection |
| decide what a null means | `alter_rows().drop_null()`, `default_to(...)` | selection |
| walk into a struct | `extract(...)` | selection |
| turn a list into rows | `alter_rows().expand()` | selection |
| filter by a value | `alter_rows().drop_if(...)` | selection |
| change a present list | `drop_null_items()`, `sort()`, `unique()`, `concat()`, `transform_items(...)` | selection |
| calculate a value | `prepend`, `add`, `equals`, `to_string` | expression |

The split is load-bearing: a nullable expression exposes no typed calculations
— no `prepend`, `add` or `equals` — so narrowing is type-checked.

```python
from kg_build_system import (
    Array, Field, Struct, Table, as_expression, field, value_expression,
)


class ContactStruct(Struct):
    email: Field[str] = field()


class SiteTable(Table):
    site_name: Field[str] = field()
    kind: Field[str] = field()
    status: Field[str] = field()
    survey_period: Field[str] = field()
    tags: Field[Array[str]] = field()
    aliases: Field[Array[str | None]] = field()
    contacts: Field[Array[ContactStruct]] = field()


identity = SiteTable.site_name.alter_rows().drop_null()   # ValueSelection[str]
label = identity.expression.prepend("site:")              # StrExpression
prefixed = value_expression("kg:").append(as_expression(identity))
```

Bindings accept either form, which is what `ValueInput` means in the API, and a
projection field accepts either too.

## Literals and normalisation

`value_expression` infers a literal's type from the Python class and checks it at
that point: `value_expression("derived")` is a `StrExpression`,
`value_expression(1.5)` a `FloatExpression`, `value_expression(False)` a
`BoolExpression`.

A bare `None` has no type, so `value_expression(None)` fails with `a null literal
requires an explicit nullable logical type`. A null literal is legal only when
you pass that type explicitly; fields and selections are the usual way to carry
an absent value.

`as_expression` normalises either a selection or an expression to an expression.
Expression methods take a Python value or a `ValueExpression`, never a selection,
so write `.expression` or `as_expression(...)` when combining, as above.

## Field access

`Table.field` reads a source column. It is always a `NullableSelection[T]`, even
when the declaration is `Field[T]` without `| None`, and even for arrays and
structs. A declaration names the value type; access owns nullability, so binding
a source value always starts by narrowing or defaulting it.

`Projection.field` and a `ComputedStruct` member are different: they are
expression-backed, so they carry their expression's type. A non-null expression
gives a non-null selection, and a nullable expression gives a nullable one.

Field access works at class level and, inside `bind`, on the symbolic shape
instance the lambda receives. Reading a projection field returns the projection's
*materialised output*, not the calculation behind it, so a later projection
reuses it — see [projections](projections.md).

Source struct members are only valid inside `extract`. Reading
`ContactStruct.email` outside a selector gives a member selection that refuses to
become an expression with
`a struct member selection is only valid inside extract`.

## `extract`

`extract` selects one declared member of a struct. The selector receives a
symbolic instance of the struct shape, so the member comes back with its declared
type.

```python
contact = SiteTable.contacts.alter_rows().drop_null().alter_rows().expand()
email = contact.extract(lambda item: item.email)   # NullableSelection[str]
```

- The selector must return a field declared by the struct it was given; anything
  else fails with `struct selectors must return a declared field selection`.
- Parent nullability propagates. A nullable parent makes every member nullable;
  a present parent leaves a non-null computed member non-null, while a source
  member is nullable in its own right.
- Source members are nullable at every source step. `contact` is present above,
  but `email` is still nullable because it is a source field.

`extract` is a path, not an operation: it does not change the row count and adds
no null handling of its own.

## `expand` fans out rows

`expand()` turns an array into its items and produces **one row per item**. It is
a row effect, so you reach it through `alter_rows()`. Narrow the nullable array to
a present `ArraySelection` when you want to make that presence explicit, then
expand:

```python
# One row per contact. A site with no contacts contributes no rows.
contacts = SiteTable.contacts.alter_rows().drop_null().alter_rows().expand()
```

`alter_rows()` returns a one-shot handle that exposes only the row effects
available on that selection: `drop_if` on every selection, `expand` on an array,
and `drop_null` on a nullable selection. Each method returns a selection, not
another handle, so a second effect needs another opt-in:

```python
# Drop the absent array first, then fan out its items.
tags = SiteTable.tags.alter_rows().drop_null().alter_rows().expand()
```

Calling `alter_rows().expand()` on the nullable selection also works; an absent
array contributes no rows either way. The two-step form makes the array present
first and is the form used here.

This is the one operation that fans one row out into several.

- An absent array and an empty array both yield **zero rows** for that input.
- A null item in a present array yields one row whose value is null. If the item
  type is `T | None`, the expanded selection is nullable and you still need
  `alter_rows().drop_null()` or `default_to(...)` to bind a non-null property.
- Expansions nest: expanding `elements` inside an expanded area yields one row
  per element of that area, and a further `defects` expansion one row per defect
  of that element. Expanding two unrelated arrays multiplies the two fan-outs.
  Two uses of the same expansion share one fan-out, identified by the field path
  it expands, and the result belongs to the product using it.

!!! warning "Everything else in the row is repeated"
    If an expanded value builds a node whose key does not depend on the item, the
    same key is emitted several times. Deduplication is a module concern.

## `drop_null`

`drop_null()` removes a null by removing the row. It is a row effect, so you
write it through `alter_rows()`:

```python
identity = SiteTable.site_name.alter_rows().drop_null()   # ValueSelection[str]
```

It is attribute-level: a nullable scalar becomes non-null, a nullable array
becomes a present array, and a nullable struct becomes a present struct. Every
row in the same product whose value is null disappears, even when the expression
is used in only one property: `SiteTable.site_name.alter_rows().drop_null()` in a
binding drops a site with no name rather than emitting a node with an empty one.

Use it when an incomplete record should not exist: always for keys, and for a
non-null property whose value you refuse to invent. Dropping the same field in
two property expressions adds the filter once. A nullable selection also exposes
`drop_null()` directly; the guide writes it through `alter_rows()` so the row
change is visible.

## `drop_if`

`drop_if(predicate)` filters rows by this value. It is a row effect and lives on
the `alter_rows()` handle. The predicate is **value-scoped**: it receives the
selection itself and must return a `BoolExpression`. The row survives when the
predicate is true.

```python
active = (
    SiteTable.kind.alter_rows().drop_null()
    .alter_rows().drop_if(lambda value: value.expression.equals("active"))
)
```

The first gate drops rows with no kind; the second keeps only active kinds. A
false or null predicate drops the row, so narrow a nullable value before
comparing it. `drop_if` changes which rows survive, not the value's type or
nullability.

## `default_to`

`default_to(value)` replaces a null and keeps the row. The result is non-null and
has the same shape, so a nullable array becomes a present array:

```python
period = SiteTable.survey_period.default_to("Unrecorded period")
labels = SiteTable.aliases.default_to([])   # ArraySelection[str | None]
```

The fallback must have the member's exact type: an `int` field takes `0`, not
`"0"`, and an array field takes a list of that item type. A mismatch is raised
while the binding is declared.

Reserve it for an absence that is meaningful and a fallback that is honest. On a
key it is almost never honest: every null gets the same key, and a later merge
treats those records as one entity.

## Array operations

A source array reads as a nullable selection. Narrow it first to get a present
`ArraySelection`, then use the array operations. `expand` is the one row effect;
the rest calculate a new array value.

| Operation | Available on | Result | Null and row behaviour |
| --- | --- | --- | --- |
| `alter_rows().drop_null()` | nullable array | `ArraySelection[T]` | drops rows with an absent array |
| `alter_rows().expand()` | nullable or present array | item selection | one row per item; absent/empty → no rows |
| `drop_null_items()` | `ArraySelection[Array[T \| None]]` | `ArraySelection[Array[T]]` | drops null items |
| `sort()` | present array | same array type | orders items ascending |
| `unique()` | present array | same array type | keeps one copy per item |
| `concat(sep)` | present `ArraySelection[str]` | `str` | empty array → `""` |
| `transform_items(fn)` | present array | array of `fn` results | item nullability preserved |
| `at(index)` | present array | nullable item selection | 0-based; out of bounds → null |
| `slice(start, end)` | present array | same array type | 0-based, end-exclusive |

```python
tags = SiteTable.tags.alter_rows().drop_null()   # ArraySelection[str]
key = tags.sort().unique().concat(":")
first = tags.at(0).alter_rows().drop_null()      # drop rows with no first tag
window = tags.slice(0, 2)                        # ArraySelection[str]
tag = tags.alter_rows().expand()                 # one row per tag
```

`drop_null_items()` is how a nullable-item list becomes bindable. Narrow the array
first, then clean the items:

```python
aliases = SiteTable.aliases.alter_rows().drop_null().drop_null_items()
```

`at(index)` and `slice(start, end)` are navigation, not row effects: they do not
need `alter_rows()`. Indices are 0-based and `slice` is end-exclusive. `at`
returns a nullable selection because an index may be out of bounds; narrow it
with `alter_rows().drop_null()` when the element must exist.

`concat(separator)` joins non-null string items and refuses an array whose items
may be null; call `drop_null_items()` first.

`transform_items` applies one expression to every item without changing the row
count. A nullable item type stays nullable after the transform, and the selector
runs for null items too, so write it to handle them. The selector may not contain
a row effect: an `alter_rows().expand()` or `alter_rows().drop_null()` inside it
fails with `transform_items selectors must not contain row effects`. There is no
`map_items` method.

## String, number and boolean operations

| Family | Methods |
| --- | --- |
| any scalar | `to_string()` |
| text | `prepend`, `append`, `replace`, `before_separator`, `after_separator`, `equals` |
| int, float | `add`, `sub` |
| bool | `not_`, `and_`, `or_` |

`to_string()` is the way into an identity: every canonical scalar has one text
form, timestamps carry the `T` separator, and a nullable value yields a nullable
string. Arrays and structs are refused with `to_string() requires a scalar unit`.

`before_separator` and `after_separator` take a separator, an occurrence counted
from 1, and an optional `include_separator`. When the separator does not occur
that many times, `before` returns the whole string and `after` returns `""`.

`equals` is the only comparison, and it exists on text only. Arithmetic is
addition and subtraction. Numbers are not compared directly; reshape the data
rather than stringifying it.

## `any_of` and `all_of`

Predicates are `BoolExpression` values. `any_of` and `all_of` combine them and
carry the empty identities `any_of() == False` and `all_of() == True`, so a
generated condition is safe when its list is empty.

```python
from kg_build_system import any_of

active_sites = SiteTable.row_source().where(lambda site: any_of(
    site.status.alter_rows().drop_null().expression.equals("active"),
    site.status.alter_rows().drop_null().expression.equals("pending"),
))
```

Boolean combinations follow three-valued logic: true if any predicate is true,
false if all are false, and null otherwise. A `where` keeps only true, so a null
predicate drops the row — which is why comparing a nullable field needs
`alter_rows().drop_null()` first: the comparison, not the filter, refuses the
null.

## `where` on row sources

`Table.row_source().where(...)` and `Projection.row_source().where(...)` return a
filtered row source with the same shape. `Table.where` and `Projection.where` are
shorthand for the same filter. The predicate is a callable that receives a
symbolic shape **instance**, not the class, and must return a `BoolExpression`; a
bare expression fails with `where requires a callable predicate`, a non-boolean
with `where predicates must return a BoolExpression`.

Filters chain and every filter is kept; pass the result as `rows=` to a binding,
or as the base of a projection. Filtering is the only transformation a row source
offers: there is no `join`, `group_by` or `union` on row sources.

## Row effects and scope

| Operation | Row effect | Effect on nullability |
| --- | --- | --- |
| `alter_rows().expand()` | one row per item | item nullability preserved |
| `alter_rows().drop_null()` | drops null rows | removes the null |
| `alter_rows().drop_if(predicate)` | drops rows whose value fails the predicate | unchanged |
| `where(...)` | drops non-matching rows | shape unchanged |
| `default_to(...)` | none | removes the null |
| array and scalar operations | none | preserved |

A product — one projection or one binding — has one row plan: the filters on its
row source plus the effects its expressions require, each applied once and never
spread to another product. `expand` nests in the order the expansions appear,
which is how a chain of expansions walks a document from the outside in.

The practical rule: before adding `drop_null` or `expand`, ask what should happen
to the row. If it should survive, use `default_to` or a nullable property; if it
should not exist, filter it.

## What to remember

- Selections navigate and own null policy; expressions calculate.
- Every source field reads as nullable, so narrow it before a key, a required
  property, or an array operation.
- `alter_rows()` is a one-shot opt-in. Each effect returns a selection, so a
  second effect needs a second `alter_rows()`.
- `expand()` is the only operation that fans one row into many; filters such as
  `drop_null()` reduce the rows instead.
- `drop_null()` drops the row; `default_to()` keeps it. Decide which fact you
  mean before writing either.
- Nullability propagates through every path, array operation and `extract`.
- A binding or projection has one row plan. Effects do not leak between
  products.

Next: [Projections](projections.md) gives a row plan a name other declarations
can share.
