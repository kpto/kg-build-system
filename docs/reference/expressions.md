# Expressions and selections

A selection names one typed value in a row and owns its null policy, while an
expression is the bindable calculation behind it.

The names on this page come from `kg_build_system`; canonical types such as
`STR`, `INT`, `NullableType` and `ArrayType` come from `kg_build_system.types`.
The model is explained on [Expressions](../concepts/expressions.md); declared
value types are on [Types](types.md); the row plan that carries a selection is
on [Row sources](row-sources.md).

## Selections

Reading a field gives a selection. A selection navigates shape and owns null
policy; it does not calculate.

| Selection | Holds | Produced by |
| --- | --- | --- |
| `ValueSelection[T]` | One present value | `alter_rows().drop_null()`, a non-null projection output, `default_to(...)` |
| `NullableSelection[T]` | One value or null | Every `Table` or source `Struct` field read; a nullable projection output; `at(index)` |
| `ArraySelection[T]` | One present array | Narrowing a nullable array; `slice(start, end)`; `default_to([])` |
| `StructSelection[S]` | One present struct | Narrowing a nullable struct; a non-null struct expression |

Every selection exposes `.logical_type`, the canonical logical type of the value.
A selection with a bindable value also exposes `.expression`, the calculation
without null policy.

```python
from kg_build_system import Field, Struct, Table, TableOptions, field
from kg_build_system.types import Array


class ContactStruct(Struct):
    email: Field[str] = field()


class SiteTable(Table):
    options = TableOptions(name="sites")
    site_id: Field[str] = field()
    name: Field[str] = field()
    survey_period: Field[str] = field()
    tags: Field[Array[str]] = field()
    aliases: Field[Array[str | None]] = field()
    contact: Field[ContactStruct] = field()


site_id = SiteTable.site_id              # NullableSelection[str]
identifier = site_id.alter_rows().drop_null()   # ValueSelection[str]
tags = SiteTable.tags                    # NullableSelection[Array[str]]
present_tags = tags.alter_rows().drop_null()    # ArraySelection[str]
```

## Expressions

`ValueInput[T]` is `ValueSelection[T] | ValueExpression[T]`. Bindings,
`computed_field` and `as_expression(...)` accept either form; call `.expression`
when an operation needs the calculation.

| Expression family | Value it calculates | Operations |
| --- | --- | --- |
| `ValueExpression[T]` | Any canonical scalar | `to_string()` |
| `IntExpression` / `FloatExpression` | `int` / `float` | `add(other)`, `sub(other)`, `to_string()` |
| `NumberExpression[T]` | Shared numeric base | `add(other)`, `sub(other)` |
| `StrExpression` | `str` | `prepend`, `append`, `equals`, `replace`, `before_separator`, `after_separator`, `to_string()` |
| `BoolExpression` | `bool` | `not_()`, `and_(other)`, `or_(other)`, `to_string()` |
| `ArrayExpression[T]` | An array | `transform_items`, `drop_null_items`, `sort`, `distinct`, `join(separator)` |
| `StructExpression[S]` | A struct | No value-specific operation |
| `NullableExpression[T, E]` | A nullable calculation | `to_string()` only |
| `CustomDataTypeExpression[C]` | A custom scalar | No value-specific operation |

A nullable expression deliberately exposes no `prepend`, `add`, `equals` or
other family operation. Narrow or default the selection first.

```python
identity = SiteTable.name.alter_rows().drop_null()
label = identity.expression.prepend("site::")
mailto = identity.expression.to_string().prepend("site::")
```

`as_expression(value: ValueInput[T]) -> ValueExpression[T]` normalises a
selection or an expression. It refuses anything else with
`expected a value selection or value expression`.

## `extract`

```text
NullableSelection.extract(
    selector: Callable[[S], ValueSelection[U]],
) -> ValueSelection[...]

StructSelection.extract(
    selector: Callable[[S], ValueSelection[U]],
) -> ValueSelection[...]
```

`extract` reads one declared member of a struct. The selector receives a
symbolic instance of the struct shape; return one of that shape's field
selections. `extract` is navigation: it adds no row effect and does not change
the row count.

| Carrier | Member | Result |
| --- | --- | --- |
| `NullableSelection[S]` | Source `Struct` member | `NullableSelection[U]` |
| `StructSelection[S]` | Source `Struct` member | `NullableSelection[U]` |
| `StructSelection[S]` | Non-null `ComputedStruct` witness | `ValueSelection[U]` |
| `NullableSelection[S]` | Non-null `ComputedStruct` witness | `NullableSelection[U]` |
| Any struct selection | Nested struct or array member | The matching structured selection, with parent nullability applied |

```python
email = (
    SiteTable.contact.alter_rows().drop_null()
    .extract(lambda contact: contact.email)
    .alter_rows().drop_null()
)
```

`SiteTable.contact` is nullable, so the carrier is narrowed first. The source
member `email` is nullable in its own right, so the second `drop_null()` is
still needed to produce a `ValueSelection[str]`.

| Error | Trigger |
| --- | --- |
| `extract requires a nullable struct selection` | `extract` is called on a nullable non-struct |
| `struct selectors must return a declared field selection` | The selector returns something other than a field selection |
| `struct selectors must return a field from their input declaration` | The selector returns a field from another declaration |
| `a struct member selection is only valid inside extract` | A member selection is read outside an `extract` selector and `.expression` is requested |

## Null policy and row effects

A null travels through every calculation. The selection decides what happens to
the **row** that holds it.

### `default_to(value)`

```text
NullableSelection.default_to(value: T | ValueExpression[T]) -> ValueSelection[T]
```

Replaces a null with `value` and keeps the row. The result is present. A nullable
array becomes an `ArraySelection`; a nullable struct becomes a
`StructSelection`.

```python
period = SiteTable.survey_period.default_to("Unrecorded period")
labels = SiteTable.tags.default_to([])
```

The fallback must have the member's exact value type. A mismatch raises
`expression input has logical type ...; expected ...` when `default_to` is
called.

| Error | Trigger |
| --- | --- |
| `expression input has logical type ...; expected ...` | The fallback does not match the value type |

### `alter_rows()`

```python
selection.alter_rows()
```

Returns a one-shot handle exposing only the row effects valid for that
selection. Each effect returns a selection, not another handle, so a second
effect needs a second `alter_rows()`.

| Effect | Available on | Returns | Row behaviour |
| --- | --- | --- | --- |
| `drop_if(predicate)` | Every selection | The same selection type | Keeps rows whose predicate is true |
| `drop_null()` | `NullableSelection` | `ValueSelection`, `ArraySelection` or `StructSelection` | Drops rows whose value is null |
| `expand()` | `ArraySelection` or `NullableSelection[Array[T]]` | The item selection | One row per item; absent or empty array produces no rows |

`drop_if(predicate)` receives the selection itself and must return a
`BoolExpression`. A false or null predicate drops the row.

```python
active = (
    SiteTable.name.alter_rows().drop_null()
    .alter_rows()
    .drop_if(lambda value: value.expression.equals("Depot"))
)
```

`drop_null()` and `expand()` are also available directly on the matching
selection. Writing them through `alter_rows()` makes the row effect visible.

| Error | Trigger |
| --- | --- |
| `drop_if requires a callable predicate` | `drop_if` receives a non-callable |
| `drop_if predicates must return a BoolExpression` | The predicate returns something else |

A row effect not listed for a selection is not exposed on that selection; the
type checker reports the missing method.

The row effects differ in what happens to the row:

| Operation | Row effect |
| --- | --- |
| `default_to(value)` | None; the row survives with a present value |
| `alter_rows().drop_null()` | Drops the row when the value is null |
| `alter_rows().drop_if(...)` | Drops the row when the predicate is false or null |
| `alter_rows().expand()` | Produces one row per array item; absent and empty arrays produce none |

## Array operations

A source array reads as a nullable selection. Narrow it to an `ArraySelection`
before using the value operations.

| Method | Available on | Returns | Notes |
| --- | --- | --- | --- |
| `drop_null_items()` | `ArraySelection[T]` | `ArraySelection` without null items | A non-null-item array is unchanged |
| `sort()` | `ArraySelection` | The same array type | Orders items ascending |
| `unique()` | `ArraySelection` | The same array type | Keeps one copy per item |
| `concat(separator)` | `ArraySelection[str]` | `ValueSelection[str]` | Joins non-null string items; an empty array gives `""` |
| `at(index)` | `ArraySelection` | `NullableSelection` of the item | `index` is an int or integer expression; 0-based; out of bounds gives null |
| `slice(start, end)` | `ArraySelection` | The same array type | `start` and `end` are ints or integer expressions; 0-based, end-exclusive |
| `transform_items(selector)` | `ArraySelection` | `ArraySelection` of the selector result | Applies one expression to every item without changing rows |

```python
tags = SiteTable.tags.alter_rows().drop_null()   # ArraySelection[str]
key = tags.sort().unique().concat(":")
first = tags.at(0).alter_rows().drop_null()
window = tags.slice(0, 2)
tag = tags.alter_rows().expand()
```

`concat(separator)` refuses an array whose items may be null; call
`drop_null_items()` first. `transform_items(selector)` preserves the item's
nullability, runs for null items too, and may not contain a row effect. The
selector receives the item expression; for struct items it receives a
`StructSelection`.

```python
aliases = SiteTable.aliases.alter_rows().drop_null().drop_null_items()
```

| Error | Trigger |
| --- | --- |
| `join requires an array of non-null strings` | `concat` is called on an array with nullable or non-string items |
| `transform_items selectors must not contain row effects` | The selector contains `expand`, `drop_null` or another row effect |

The array operations exist only on `ArraySelection`; narrow a nullable array
first. A scalar or nullable selection does not expose them.

The underlying `ArrayExpression` exposes `distinct()` and
`join(separator)`; `unique()` and `concat(separator)` are the selection names.

## String, number and boolean operations

| Family | Methods | Result |
| --- | --- | --- |
| Any canonical scalar | `to_string()` | `StrExpression`, or a nullable string expression |
| Text | `prepend(value)`, `append(value)` | `StrExpression` |
| Text | `replace(search, replacement)` | `StrExpression` with every occurrence replaced |
| Text | `equals(value)` | `BoolExpression` |
| Text | `before_separator(separator, occurrence=1, *, include_separator=False)` | `StrExpression` |
| Text | `after_separator(separator, occurrence=1, *, include_separator=False)` | `StrExpression` |
| `int`, `float` | `add(other)`, `sub(other)` | The same numeric family |
| `bool` | `not_()`, `and_(other)`, `or_(other)` | `BoolExpression` |

`prepend`, `append`, `replace`, `equals`, `add` and `sub` accept a Python value
of the right type or a `ValueExpression` of that type, never a selection. Use
`.expression` or `as_expression(...)`.

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
| `to_string() requires a scalar unit` | The expression is an array, struct or custom scalar |

## Literals

```python
def value_expression(
    value: Any,
    *,
    logical_type: LogicalType | None = None,
) -> ValueExpression: ...
```

`value_expression()` constructs a typed literal and checks the Python class at
that point. `as_expression()` normalises a selection or expression; see
[Expressions](#expressions).

| Python value | Inferred result |
| --- | --- |
| `str` | `StrExpression` |
| `int` | `IntExpression` |
| `float` | `FloatExpression` |
| `bool` | `BoolExpression` |
| `Date`, `Time`, `Timestamp`, `Uuid` | `ValueExpression` of that unit |
| A homogeneous list of literals | `ArrayExpression` of the item type |
| `None` | Refused unless `logical_type` is nullable |

```python
from kg_build_system import value_expression
from kg_build_system.types import ArrayType, INT, NullableType, STR


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

A literal array may contain null items when its item type allows them; an
explicit item type must then be nullable as well. A struct, `ComputedStruct` or
custom scalar is not a literal; build it from row expressions instead.

## `any_of()` and `all_of()`

```text
any_of(*predicates: BoolExpression) -> BoolExpression
all_of(*predicates: BoolExpression) -> BoolExpression
```

| Function | Result with no arguments | Combination |
| --- | --- | --- |
| `any_of()` | `False` | True if any predicate is true |
| `all_of()` | `True` | True only if every predicate is true |

```python
from kg_build_system import any_of

active_sites = SiteTable.row_source().where(
    lambda site: any_of(
        site.name.alter_rows().drop_null().expression.equals("Depot"),
        site.name.alter_rows().drop_null().expression.equals("Workshop"),
    )
)
```

Each argument must be a `BoolExpression`. A null predicate is not true, so a
`where` that keeps only true rows drops that row.

## Type and error rules

| Rule | Consequence |
| --- | --- |
| Every source field read is nullable | Narrow or default before a key, a required property or a typed operation |
| A projection output follows its expression | A non-null expression publishes a non-null selection; a nullable expression publishes a nullable one |
| A nullable expression exposes only `to_string()` | `prepend`, `add`, `equals` and other family operations require a present selection |
| Operations take a Python value or a `ValueExpression` | Pass `.expression` or `as_expression(...)`, not a selection |
| `equals` is text-only | Non-text equality uses the row-source key pair |
| `to_string()` is scalar-only | Arrays, structs and custom scalars have no canonical text form |
| `extract` returns declared members only | A selector cannot invent a field |
| Row effects are opt-in | `expand`, `drop_null` and `drop_if` are reached through `alter_rows()` or their direct selection form |
| `expand` is the only fan-out | Every other operation preserves the row count |
| Nulls propagate through calculations | `default_to` keeps the row; `drop_null` removes it |

## What to remember

- A selection navigates and owns null policy; an expression calculates.
- Every source field reads as nullable. Narrow it with
  `alter_rows().drop_null()` or replace it with `default_to(...)`.
- `alter_rows()` is a one-shot opt-in, and each effect returns a selection.
- `expand()` produces one row per item; `drop_null()` and `drop_if()` reduce the
  rows; `default_to()` keeps the row.
- Nullability propagates through `extract`, array operations and calculations.
- A binding or projection has one row plan; effects do not leak into another
  product.

Next: [Row sources](row-sources.md) choose the grain a binding reads.
