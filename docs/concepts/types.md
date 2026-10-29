# Types and nullability

Every field, property and expression in a build carries a logical type. The type
is written as a Python annotation and normalised to one canonical form, so the
same claim has the same meaning in a table, in an expression and in the compiled
contract.

This page covers the vocabulary you write and the rules that decide whether a
value may become a graph property or a key. How a table is declared is on
[data contracts](data-contracts.md); where its rows come from is on
[sources](sources.md).

## The canonical scalars

A scalar is one value. There are eight canonical scalars, named in lowercase;
the name is what the framework, the contract and every error message use.

| Canonical name | Annotation | Holds |
| --- | --- | --- |
| `bool` | `bool` | a truth value |
| `int` | `int` | a signed 64-bit integer |
| `float` | `float` | a double-precision number |
| `str` | `str` | text |
| `date` | `Date` | a calendar date |
| `time` | `Time` | a time of day |
| `timestamp` | `Timestamp` | a local date and time |
| `uuid` | `Uuid` | a universally unique identifier |

Physical sources are wider than this vocabulary, and the framework widens rather
than guesses: the integer widths that fit a signed 64-bit range digest to `int`,
both `FLOAT` and `DOUBLE` to `float`, and `JSON` and `ENUM` to `str`. A type with
no meaning-preserving canonical form is refused at generation instead — see
[unsupported types](#unsupported-types).

Temporal and `uuid` values have limits. They are stored, deduplicated, merged and
written in canonical text, but they expose no comparison or filtering operators;
`equals` exists on text only. Use `to_string()` when a temporal or `uuid` value
must become part of an identity. Neo4j refuses `uuid` properties because the
target has no property type for them.

## Representative classes

`Date`, `Time`, `Timestamp` and `Uuid` come from `kg_build_system.types`. They
are aliases of `datetime.date`, `datetime.time`, `datetime.datetime` and
`uuid.UUID`, not subclasses. The capitalised spelling keeps annotations readable
and avoids shadowing the `date` and `time` names author code often imports.

```python
from kg_build_system import Field, Table, field
from kg_build_system.types import Timestamp, Uuid


class RegisterTable(Table):
    site_id: Field[Uuid] = field(name="site_id")
    opened_on: Field[Timestamp] = field(name="opened_on")
```

Both spellings normalise to the same type, because dispatch is on the class
itself: `Field[Uuid]` and `Field[uuid.UUID]` cannot drift into two meanings. Use
whichever reads better in your project, and do not mix them in one declaration.

`site_id` and `opened_on` name value types. Neither promises that a row supplies
the value: reading either gives a nullable selection. Date, time, timestamp and
uuid values have one canonical text form, which they keep when frozen into the
contract. That is what makes them safe to concatenate into an identity: a
timestamp is written with the `T` separator and a uuid in lowercase hyphenated
form. `to_string()` is on
[expressions](expressions.md#string-number-and-boolean-operations).

## Custom scalars

An application-defined scalar is a class derived from `CustomDataType`. It
extends the vocabulary without teaching the framework what the value means:

```python
from kg_build_system import CustomDataType, Field, Table, field


class Currency(CustomDataType):
    """An application-defined scalar, such as a currency code."""


class BudgetTable(Table):
    budget: Field[Currency] = field()
```

- Identity is the `(module, qualname)` pair, not the class name, so two
  `Currency` classes in different modules are different types.
- The class must be declared at top level and be importable; a declaration
  inside a function fails with `logical type declarations must be importable
  top-level classes`.
- A custom scalar composes as a field type, an array item, a key and a
  `PropertySlot`. It exposes no value operations: no text, numeric or comparison
  methods, and `to_string()` refuses it because only canonical unit scalars have
  a canonical text form.
- A target may refuse it. The Neo4j bundle refuses custom scalar properties,
  just as it refuses `uuid`.

## Arrays

`Array[T]` is an ordered collection of one item type. The item may be any
supported type, including another array or a struct.

The array itself is a value; reading it is always nullable. What the declaration
does decide is whether the items may be null:

| Declaration | The value it names | Read as |
| --- | --- | --- |
| `Array[int]` | a list of non-null integers | `NullableSelection[Array[int]]` |
| `Array[int \| None]` | a list whose items may be null | `NullableSelection[Array[int \| None]]` |

Do not write the array as `Array[int] | None`. A top-level `| None` on a field is
stripped to its value type, because access owns presence. Item nullability is
different: it is a fact about a present list and stays in the declaration.

!!! warning "A nullable item is not the same as an empty list"
    An absent array and an empty array both produce *no rows* when expanded. A
    null item inside a present array still produces one row, with a null value.
    Narrow the nullable array before operating on it; see
    [fan-out](expressions.md#expand-fans-out-rows).

## Structs

A struct is a nested record: a named set of typed fields that travels as one
value. Declare a source struct by subclassing `Struct` and referencing it from a
field.

```python
from kg_build_system import Field, Struct, Table, field
from kg_build_system.types import Array, Uuid


class ContactStruct(Struct):
    email: Field[str] = field()
    phone: Field[str] = field()


class SiteTable(Table):
    site_id: Field[Uuid] = field(name="site_id")
    name: Field[str] = field(name="name")
    labels: Field[Array[str]] = field(name="labels")
    contact: Field[ContactStruct] = field(name="contact")
    alternates: Field[Array[ContactStruct | None]] = field(name="alternates")
```

A struct is a *shape*, never a row source: it has no location and cannot be
bound. A source struct's members are nullable at every source step. `contact`
reads as a nullable struct selection; extracting a member reads as nullable even
when the member is declared `Field[str]`. A nested source member is never a
non-null selection on its own.

`extract` composes the parent's nullability with the member's kind. Source
members are already nullable, so they stay nullable under either parent. A
`ComputedStruct` used as `Field[T]` is different: its member expressions are
**type witnesses**, not evaluated values and not a row plan, so a filter or
expansion in a witness has no row effect. A non-null witness stays non-null
under a present carrier and becomes nullable under a nullable carrier; the read
is a field reference on the carrier record, so the carrier's data supplies the
value. Struct fields are not usable on their own; outside `extract` the
framework refuses them with
`a struct member selection is only valid inside extract`.

## Nullability on access

Reading a source field is always nullable, whatever its declaration says. The
declaration names the value type; the selection owns presence.

- `Table.field` and a source `Struct` member yield `NullableSelection[T]`,
  including arrays and structs.
- `Projection.field` carries the type of its expression. A non-null expression
  yields a non-null selection; a nullable expression yields
  `NullableSelection`.
- A `ComputedStruct` member is read only through `extract`; its witness
  expression fixes the member type, so a non-null witness is non-null under a
  present carrier.
- A top-level `T | None` on a source field is stripped to `T`. Never rely on it
  to change access, and do not write it.
- Array item nullability (`Array[T | None]`) remains a property of the value.
- Nullability propagates through `extract`, and through array operations after
  the array has been narrowed to a present selection.

```python
name = SiteTable.name                         # NullableSelection[str]
present = name.alter_rows().drop_null()       # ValueSelection[str]
fallback = name.default_to("unknown")         # ValueSelection[str]
```

A nullable selection offers `default_to`, `drop_null`, `extract`, and the
`alter_rows()` gate. It exposes no typed value calculations and no array
operations until you narrow it. Array operations such as `sort`, `unique`,
`concat`, `drop_null_items`, `at`, and `slice` exist on a present
`ArraySelection`, so narrow first:

```python
labels = SiteTable.labels.alter_rows().drop_null()  # ArraySelection[str]
joined = labels.sort().unique().concat(",")         # ValueSelection[str]
```

A generated package does not put a top-level source-nullability claim into the
contract. `field()` strips a top-level `| None`, and the generator renders only
the value type, so `Field[str]` in a generated table is the same blueprint field
type whether the source called the column `required`, `optional` or nothing.
The source's claim is recorded as a header comment and in the manifest's source
digest; access is still a nullable selection.

`override={"relation.column": {"nullable": False}}` overrules the source's
nullability claim for one whole top-level column. It can assert or decline a
claim and runs the Parquet null-statistics pre-flight, but it does not make the
field non-null on access and does not appear in the blueprint field type.
Nullability is never inferred from the values in a sample.

## What a graph property may hold

A property must survive as a stored scalar or a flat list, never a nested
structure. That gives one accepted shape and a short list of refusals.

| Declaration | Accepted as a property | Why |
| --- | --- | --- |
| `PropertySlot[str]` | yes | a scalar |
| `PropertySlot[str \| None]` | yes | a scalar that may be absent |
| `PropertySlot[Array[str]]` | yes | a flat list of non-null scalars |
| `PropertySlot[Array[str] \| None]` | yes | the same, or absent |
| `PropertySlot[Array[str \| None]]` | no | no target stores a list with nulls faithfully |
| `PropertySlot[SomeStruct]` | no | a nested record is not a property value |
| `PropertySlot[Array[SomeStruct]]` | no | a list of records is not a property value |
| `PropertySlot[Array[Array[int]]]` | no | nesting has no flat representation |

The two refusals you are most likely to meet tell you the remedy:

```text
SiteNode.priority_scores array properties require non-null items; apply drop_null_items() to drop null items
SiteNode.contacts array properties require scalar items; flatten nested structures with expand() instead
```

A struct or a nested array is a perfectly good *table* field and a good
intermediate expression value. It only has to be flattened — or have its null
items dropped — before it is bound to a property. Narrow a nullable array first;
both operations are on [expressions](expressions.md#array-operations).

## Keys must be non-null scalars

A node key and both edge endpoint keys identify records. An absent or array
value cannot do that, so the binding factories refuse one immediately:

| What you pass | Result |
| --- | --- |
| `row.site_id.alter_rows().drop_null()` | accepted |
| `row.site_id`, even when declared `Field[str]` | `build_key must not be nullable` |
| an array selection | `build_key must be a scalar` |
| a struct selection | `build_key must be a scalar` |

The two exits have different consequences, so choose deliberately:

- `alter_rows().drop_null()` drops the row. Nothing is emitted for it. This is
  the right choice when an unidentified record should not exist.
- `default_to(...)` keeps the row and gives every absent value the same fallback.
  Two records that were never distinguished now share one key, and a later
  deduplication or merge step will treat them as one entity.

!!! warning "Never default a key to make a build pass"
    A key fallback collapses distinct records into one graph identity. If the data
    cannot identify a record, drop the row (`alter_rows().drop_null()`) rather
    than inventing an identity.

## Unsupported types

Three different things are refused, at three different moments.

**Python annotations the framework does not model.** `Any`, `list[str]`,
`dict[str, str]`, tuples, and unions of two real types all fail when the
declaration is imported:

```text
unsupported logical type annotation: list[str]
logical types must be explicit; Any is not supported
logical unions are limited to T | None
```

A `Struct` or custom scalar declared inside a function is refused with `logical
type declarations must be importable top-level classes`.

**Physical types with no canonical form.** Generation refuses a column rather
than coercing it. The refused families are `DECIMAL`, `BIGNUM`, `BIT`, `BLOB`,
`TIME WITH TIME ZONE`, `TIMESTAMP WITH TIME ZONE`, `INTERVAL`, `MAP`, `UNION`,
`VARIANT`, anonymous `ROW`, untyped `NULL`, `TYPE`, and the extension-conditional
geometry types.

**Values that cannot be literals.** A literal is built from a canonical scalar or
an array of them; a struct value cannot be embedded in an expression. A null
literal needs an explicit nullable type, which is why `value_expression(None)`
fails with `a null literal requires an explicit nullable logical type`.

A refused column has two exits, both outside the compiled contract: export the
column in a supported type, or declare that table by hand outside a generated
package. Hand-editing a generated file is refused on purpose.

## Reading an error

Type errors name the declaration and both sides of the mismatch. The left side is
what the slot accepts; the right side is what your expression produces.

```text
SiteNode.site_name expects UnitType(name='str'), but the expression resolves to NullableType(value=UnitType(name='str'))
```

Read that as: the property wants a present string, the expression may be absent.
The fix is a null policy — `alter_rows().drop_null()` or `default_to(...)` — not
a cast.

| Message contains | It is about | Look at |
| --- | --- | --- |
| `must not be nullable` | a key | the key expression, not the properties |
| `must be a scalar` | a key or property annotation | the declared property type |
| `array properties require non-null items` | a property annotation | the item type, then `drop_null_items()` |
| `array properties require scalar items` | a property annotation | the item type, then `alter_rows().expand()` and `extract` |
| `unsupported logical type annotation` | a field or property annotation | the Python type you wrote |
| `cannot be read as the declared '...' format` | a source | the source format, not the table |

## What to remember

- Write canonical types; aliases normalise to one meaning. Custom scalars are
  top-level `CustomDataType` subclasses identified by module and qualname.
- A field declaration names a value type. Every source access is nullable, even
  when the declaration has no `| None`.
- `| None` on a source field is stripped; item nullability (`Array[T | None]`)
  is a fact about the value.
- A generated package's source-nullability claim is a header/digest fact, not a
  blueprint field type; access stays nullable.
- A projection field is typed by its expression. A `ComputedStruct` member
  expression is a type witness, not an evaluated value.
- Keys must be present scalars. Choose `alter_rows().drop_null()` or a
  deliberate fallback, never a silent one.
- Temporal and `uuid` values have canonical text but no comparison operators;
  custom scalars have no value operations.
- Properties hold scalars or flat non-null arrays; narrow the array and drop null
  items first.
- A type error is a design message: read which side is nullable or composite,
  then change how the value is produced.

The type vocabulary itself is listed on the [type
reference](../reference/types.md); the errors a build raises after compilation
are collected under [debugging](../guides/debugging.md).

Next: [Sources](sources.md) attaches these declarations to physical files.
