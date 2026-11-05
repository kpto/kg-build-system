# Expressions and selections

`Selection[T]` is the single authoring type. It navigates a row shape, calculates
a typed value, and owns the decision about absence. `NullableSelection[T]` is the
alias `Selection[Nullable[T]]`.

There is no expression family and no `.expression`, `.value` or `.model`
accessor. Every operation is a method on the selection, and the compiler
expression tree stays private.

The names on this page come from `kg_build_system`; canonical types such as
`STR`, `INT`, `NullableType` and `ArrayType` also come from there. The model is
explained on [Expressions](../concepts/expressions.md); declared value types are
on [Types](types.md); the row plan that carries a selection is on
[Row sources](row-sources.md).

## Source and computed access

A field declaration names a value type, never `T | None`. Presence is decided by
the owner that supplies the value:

| Owner | Declaration | Read as |
| --- | --- | --- |
| Source `Table` | `Field[T]` | `Selection[Nullable[T]]` |
| Source `Struct` member | `Field[T]` | `Selection[Nullable[T]]` |
| `Projection` output | `computed_field(Selection[T])` | `Selection[T]` |
| `Projection` output | `computed_field(Selection[Nullable[T]])` | `Selection[Nullable[T]]` |
| `ComputedStruct` member | `computed_field(Selection[T])` | `Selection[T]`, composed with the carrier |
| `ComputedStruct` member | `computed_field(Selection[Nullable[T]])` | `Selection[Nullable[T]]`, composed with the carrier |

```python
from kg_build_system import (
    Array, Field, Nullable, Projection, Struct, Table, TableOptions,
    computed_field, field,
)


class ContactStruct(Struct):
    email: Field[str] = field()


from estate.assets import Estate

class SiteTable(Table[Estate]):
    options = TableOptions(name="sites")
    site_id: Field[str] = field()
    name: Field[str] = field()
    region_id: Field[str] = field()
    survey_period: Field[str] = field()
    tags: Field[Array[str]] = field()
    labels: Field[Array[str]] = field()
    aliases: Field[Array[Nullable[str]]] = field()
    contact: Field[ContactStruct] = field()
    count: Field[int] = field()
    active: Field[bool] = field()


class RegionTable(Table[Estate]):
    region_id: Field[str] = field()
    name: Field[str] = field()


site_id = SiteTable.site_id      # Selection[Nullable[str]]
tags = SiteTable.tags            # Selection[Nullable[Array[str]]]
aliases = SiteTable.aliases      # Selection[Nullable[Array[Nullable[str]]]]
contact = SiteTable.contact      # Selection[Nullable[ContactStruct]]
```

Every selection exposes `.logical_type`, the canonical logical type of the
selected position. It does not expose the compiler node behind it.

## `extract`

```text
Selection[S].extract(selector: Callable[[S], Selection[U]]) -> Selection[U]
Selection[Nullable[S]].extract(selector) -> Selection[Nullable[U]]
```

`extract` reads one declared member of a struct. The selector receives a typed
instance of the struct shape and returns one of that shape's field selections. It
is navigation: it adds no row effect and does not change the row count.

Presence composes:

| Carrier | Member | Result |
| --- | --- | --- |
| `Selection[S]` | Source `Struct` member `Field[T]` | `Selection[Nullable[T]]` |
| `Selection[Nullable[S]]` | Any source `Struct` member | `Selection[Nullable[T]]`; the nullable carrier wins |
| `Selection[S]` | Non-null `ComputedStruct` witness | `Selection[T]` |
| `Selection[Nullable[S]]` | Non-null `ComputedStruct` witness | `Selection[Nullable[T]]` |
| Any struct selection | Nested struct or array member | The matching selection, with parent presence applied |

```python
email = (
    SiteTable.contact
    .extract(lambda contact: contact.email)
)
# Selection[Nullable[str]]: the source carrier is nullable and the member is a
# source field, so the result stays nullable.
```

A source struct member is always nullable because the source may omit it. A
`ComputedStruct` member keeps the type of its witness; a nullable carrier makes
it nullable.

| Error | Trigger |
| --- | --- |
| `extract requires a struct selection` | `extract` is called on a non-struct |
| `struct selectors must return a declared field selection` | The selector returns something other than a field selection |
| `struct selectors must return a field from their input declaration` | The selector returns a field from another declaration |
| `a struct member selection is only valid inside extract` | A member selection is read outside an `extract` selector |

## `default_to`

```text
Selection[Nullable[T]].default_to(value: T | Selection[T]) -> Selection[T]
```

Replaces an absent value with a fallback and keeps the row. The result is
present. A nullable array becomes a present array; a nullable struct becomes a
present struct. On a present selection the method is not exposed.

```python
period = SiteTable.survey_period.default_to("Unrecorded period")
labels = SiteTable.tags.default_to([])
```

The fallback must have the member's exact value type. A mismatch raises
`expression input has logical type ...; expected ...` when `default_to` is
called.

## `alter_rows()`

```python
selection.alter_rows()
```

Returns a one-shot handle exposing only the row effects valid for that
selection. Each effect returns a selection, not another handle, so a second
effect needs a second `alter_rows()`. Reusing a consumed handle raises
`TypeError` with `already consumed`.

| Effect | Available on | Returns | Row behaviour |
| --- | --- | --- | --- |
| `drop_if(predicate)` | Every selection | The same selection type | Keeps rows whose predicate is true |
| `drop_null()` | Nullable selection | A present selection | Drops rows whose value is null |
| `expand()` | Present or nullable array | The item selection | One row per item; absent or empty array produces no rows |

`drop_if(predicate)` receives the selection itself and must return
`Selection[bool]`. A false or null predicate drops the row.

```python
active = (
    SiteTable.name.alter_rows().drop_null()
    .alter_rows()
    .drop_if(lambda value: value.equals("Depot"))
)
```

A selection exposes no direct `drop_null()`, `drop_if()` or `expand()`. An effect
that is not valid for the selection is absent from the handle type; the type
checker reports the missing method.

| Error | Trigger |
| --- | --- |
| `drop_if requires a callable predicate` | `drop_if` receives a non-callable |
| `drop_if predicates must return a Selection[bool]` | The predicate returns something else |
| `row effect handle has already been consumed` | The same handle is used twice |

## Navigation

| Method | Available on | Returns | Notes |
| --- | --- | --- | --- |
| `at(index)` | Array selection | `Selection[Nullable[item]]` | `index` is an int or integer selection; 0-based; out of bounds gives null |
| `slice(start, end)` | Array selection | The same array type | `start` and `end` are ints or integer selections; 0-based, end-exclusive |

`at` and `slice` are navigation. They do not change the row count and do not need
`alter_rows()`.

```python
tags = SiteTable.tags.alter_rows().drop_null()
first = tags.at(0)             # Selection[Nullable[str]]
window = tags.slice(0, 2)      # Selection[Array[str]]
```

## `lookup`

```text
Selection.lookup(
    relation: type[S] | RelationRef,
    key: Selection[Any] | None = None,
    *,
    target_key: str | Selection[Any] | None = None,
) -> Selection[Nullable[Array[S]]]
```

Reads every target record whose key equals this row's key. The result is a value:
an array of target records, or null when no target matches. A null key never
matches. The target may be a `Table` or a `Projection`.

`key` defaults to the source selection; pass it explicitly when the source key is
not `self`. `target_key` defaults to the column name of a direct field key; pass
it explicitly when the target column has a different name.

`lookup` itself is ungated: it does not choose a join mode. Row behaviour is
composed from the result:

| Grain | Write |
| --- | --- |
| Left | `selection.lookup(Target, selection)` |
| Inner | `selection.lookup(Target, selection).alter_rows().drop_null()` |
| One row per match | `...drop_null().alter_rows().expand()` |

```python
regions = SiteTable.region_id.lookup(RegionTable, SiteTable.region_id)

left = regions
inner = regions.alter_rows().drop_null()
one_per_match = inner.alter_rows().expand()
```

`lookup` has no `how` argument. Passing one raises `TypeError`.

## Array operations

A source array reads as a nullable array because the source may omit it. Narrow
it before using the value operations.

| Method | Available on | Returns | Notes |
| --- | --- | --- | --- |
| `drop_null_items()` | Array selection | The same array with non-null items | A non-null-item array is unchanged |
| `sort()` | Array selection | The same array type | Orders items ascending |
| `unique()` | Array selection | The same array type | Keeps one copy per item |
| `concat(separator)` | Array of non-null strings | `Selection[str]` | Joins items; an empty array gives `""` |
| `transform_items(selector)` | Array selection | An array of the selector result | Applies one selection to every item without changing rows |
| `zip(other)` | Array selection | An array of `Pair[L, R]` | Pairs two arrays by position; presence composes |

```python
tags = SiteTable.tags.alter_rows().drop_null()
key = tags.sort().unique().concat(":")
first = tags.at(0)
window = tags.slice(0, 2)
tag = tags.alter_rows().expand()
aliases = SiteTable.aliases.alter_rows().drop_null().drop_null_items()
```

`concat(separator)` refuses an array whose items may be null; call
`drop_null_items()` first. `transform_items(selector)` preserves the item's
nullability and may not contain a row effect.

### `zip`

```text
Selection[Array[L]].zip(other: Selection[Array[R]]) -> Selection[Array[Pair[L, R]]]
Selection[Nullable[Array[L]]].zip(...) -> Selection[Nullable[Array[Pair[L, R]]]]
```

`zip` pairs two arrays by position. The arrays must have the same length; a
mismatch is refused at execution with a message naming `equal length`. An absent
input makes the result absent. This is a value operation, not a row-level cross
or zip.

`Pair[L, R]` is a value record with present `left` and `right` members. Expand
the paired array first, then read a member with `extract`:

```python
paired = (
    SiteTable.tags.alter_rows().drop_null()
    .zip(SiteTable.labels.alter_rows().drop_null())
)
left = paired.alter_rows().expand().extract(lambda pair: pair.left)
right = paired.alter_rows().expand().extract(lambda pair: pair.right)
```

| Error | Trigger |
| --- | --- |
| `join requires an array of non-null strings` | `concat` is called on an array with nullable or non-string items |
| `transform_items selectors must not contain row effects` | The selector contains `expand`, `drop_null` or another row effect |
| `zip requires two arrays of equal length` | The two arrays differ in length at execution |

## String, number and boolean operations

Every method below exists only on the matching present selection. A nullable
selection exposes no family operation, so narrow or default it first.

| Family | Methods | Result |
| --- | --- | --- |
| Any canonical scalar | `to_string()` | `Selection[str]` |
| Text | `prepend(value)`, `append(value)` | `Selection[str]` |
| Text | `replace(search, replacement)` | `Selection[str]` with every occurrence replaced |
| Text | `equals(value)` | `Selection[bool]` |
| Text | `before_separator(separator, occurrence=1, *, include_separator=False)` | `Selection[str]` |
| Text | `after_separator(separator, occurrence=1, *, include_separator=False)` | `Selection[str]` |
| `int`, `float` | `add(other)`, `sub(other)` | The same numeric type |
| `bool` | `not_()`, `and_(other)`, `or_(other)` | `Selection[bool]` |

`prepend`, `append`, `replace`, `equals`, `add` and `sub` accept a Python value
of the right type or a `Selection` of that type.

```python
label = SiteTable.name.alter_rows().drop_null().prepend("site::")
mailto = SiteTable.site_id.alter_rows().drop_null().to_string().prepend("site::")
count = SiteTable.count.alter_rows().drop_null().add(1)
active = SiteTable.active.alter_rows().drop_null().and_(True)
```

`to_string()` accepts the eight canonical unit scalars — `bool`, `int`, `float`,
`str`, `date`, `time`, `timestamp` and `uuid`. A timestamp keeps the `T`
separator; a uuid is lowercase and hyphenated. Arrays, structs and custom scalars
are refused with `to_string() requires a scalar unit`.

`before_separator` and `after_separator` count occurrences from `1`; the
separator at the cut is excluded unless `include_separator=True`. If the
separator does not occur that many times, `before` returns the whole string and
`after` returns `""`.

`equals` is the only comparison and exists on text only. Numbers have addition
and subtraction, not comparison. Boolean combinations follow three-valued logic:
true if any predicate is true, false if all are false, and null otherwise.

| Error | Trigger |
| --- | --- |
| `separator must be non-empty` | `before_separator("")` or `after_separator("")` |
| `occurrence must be at least 1` | `occurrence=0` or a negative occurrence |
| `to_string() requires a scalar unit` | The selection is an array, struct or custom scalar |

## Literals

```python
def value_expression(
    value: Any,
    *,
    logical_type: LogicalType | None = None,
) -> Selection[Any]: ...
```

`value_expression()` constructs a typed literal and checks the Python class at
that point. It returns a `Selection`, so a constant can be used wherever a
selection is accepted.

| Python value | Inferred result |
| --- | --- |
| `str` | `Selection[str]` |
| `int` | `Selection[int]` |
| `float` | `Selection[float]` |
| `bool` | `Selection[bool]` |
| `Date`, `Time`, `Timestamp`, `Uuid` | `Selection` of that unit |
| A homogeneous list of literals | `Selection[Array[item]]` |
| `None` | Refused unless `logical_type` is nullable |

```python
from kg_build_system import value_expression
from kg_build_system import ArrayType, INT, NullableType, STR

prefix = value_expression("site::")
nothing = value_expression(None, logical_type=NullableType(STR))
numbers = value_expression([1, 2], logical_type=ArrayType(INT))
```

`logical_type` takes a canonical logical type, not a Python annotation:
`NullableType(STR)` and `ArrayType(INT)` are canonical; `str | None` is not.

| Error | Trigger |
| --- | --- |
| `a null literal requires an explicit nullable logical type` | `value_expression(None)` |
| `an empty array literal requires an explicit logical type` | `value_expression([])` |
| `an all-null array literal requires an explicit logical type` | An array containing only nulls |
| `array literal items must have one logical type` | Mixed item types |
| `unsupported expression literal ...` | A value that is not a canonical scalar or array |
| `literal must be <unit>, not <class>` | The value does not match the supplied logical type |
| `literal cannot embed struct or custom-type values` | A struct or custom value is used as a literal |
| `expression input has logical type ...; expected ...` | An operation receives a value of the wrong type |

A literal array may contain null items when its item type allows them. A struct,
`ComputedStruct` or custom scalar is not a literal; build it from row selections
instead.

## `any_of()` and `all_of()`

```text
any_of(*predicates: Selection[bool]) -> Selection[bool]
all_of(*predicates: Selection[bool]) -> Selection[bool]
```

| Function | Result with no arguments | Combination |
| --- | --- | --- |
| `any_of()` | `False` | True if any predicate is true |
| `all_of()` | `True` | True only if every predicate is true |

```python
from kg_build_system import any_of

active_sites = SiteTable.row_source().where(
    lambda site: any_of(
        site.name.alter_rows().drop_null().equals("Depot"),
        site.name.alter_rows().drop_null().equals("Workshop"),
    )
)
```

Each argument must be a `Selection[bool]`. A null predicate is not true, so a
`where` that keeps only true rows drops that row.

## Type and error rules

| Rule | Consequence |
| --- | --- |
| Source access is nullable | Every source `Field[T]` reads as `Selection[Nullable[T]]`; narrow or default before a key, a required property or a present-only operation |
| Computed access follows the selection | `computed_field(value)` publishes exactly the type of `value` |
| A nullable selection exposes no family operation | `prepend`, `add`, `equals` and other family operations require a present selection |
| Row effects are opt-in | `expand`, `drop_null` and `drop_if` are reached only through `alter_rows()` |
| `expand` is the only fan-out | Every other value operation preserves the row count |
| Nulls propagate through calculations | `default_to` keeps the row; `drop_null` removes it |
| `lookup` states no join mode | The caller composes left, inner or one-per-match |
| `zip` is a value operation | It pairs arrays; it does not join rows |

## What to remember

- `Selection[T]` is the only authoring type; `NullableSelection[T]` is
  `Selection[Nullable[T]]`.
- Source fields read nullable; computed fields read exactly the declared
  selection type. `extract` composes carrier presence.
- `alter_rows()` is a one-shot opt-in, and each effect returns a selection.
- `expand()` produces one row per item; `drop_null()` and `drop_if()` reduce the
  rows; `default_to()` keeps the row.
- `lookup` reads another relation, `zip` pairs arrays, and `RowSource.unnest`
  expands an array as the grain of a relation.
- A binding or projection has one row plan; effects do not leak into another
  product.

Next: [Row sources](row-sources.md) choose the grain a binding reads.
