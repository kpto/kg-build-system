# Types

This page lists the canonical logical types an author writes and the rules that decide how a value is stored, bound and exported.

Every annotation normalizes to one logical type before it reaches the workflow plan.
The canonical name is lowercase; a capitalised name such as `Date` is a
representative type, not a second type. The concepts behind these rules are on
[types and nullability](../concepts/types.md); the physical ingest side is on
[assets and ingest](ingest.md).

```python
from kg_build_system import Array, Date, Time, Timestamp, Uuid
```

## Canonical scalars

There are eight canonical scalar units. Each is valid as a property, a key, an
array item and a literal.

| Canonical | Author writes | Python class | Notes |
| --- | --- | --- | --- |
| `bool` | `bool` | `bool` | Boolean value and predicate |
| `int` | `int` | `int` | Signed 64-bit integer |
| `float` | `float` | `float` | Double-precision number |
| `str` | `str` | `str` | Text; supports `to_string()` and text operations |
| `date` | `Date` | `datetime.date` | Canonical ISO date text |
| `time` | `Time` | `datetime.time` | Canonical ISO time text |
| `timestamp` | `Timestamp` | `datetime.datetime` | Canonical text keeps the `T` separator |
| `uuid` | `Uuid` | `uuid.UUID` | Lowercase hyphenated text |

All eight scalars have a canonical text form through `to_string()`. Temporal and
`uuid` values are stored, deduplicated and merged, but they expose no comparison
or filtering operators; call `to_string()` when a temporal or `uuid` value must
participate in an identity. Arrays, structs and custom scalars have no canonical
text form.

!!! warning "No implicit conversions"
    A value must be the class its unit names. A `Decimal` is not a `float`, a
    string is not a `timestamp`, and a `uuid.UUID` is not a `str`. Declare the
    type you actually receive, or convert it explicitly in the data contract.

## Representative types

`Date`, `Time`, `Timestamp` and `Uuid` are aliases of `datetime.date`,
`datetime.time`, `datetime.datetime` and `uuid.UUID`. They are not subclasses,
and the alias and the stdlib spelling are the same annotation.

```python
from kg_build_system import Field, Table, field
from kg_build_system import Timestamp, Uuid


from estate.assets import Estate

class RegisterTable(Table[Estate]):
    site_id: Field[Uuid] = field(name="site_id")
    opened_on: Field[Timestamp] = field(name="opened_on")
```

`Field[Uuid]` and `Field[uuid.UUID]` normalize to the same type, because dispatch
is on the class itself. Use one spelling consistently in a declaration.

## Custom scalars

An application-defined scalar is a class derived from `CustomDataType`.

```python
from kg_build_system import CustomDataType, Field, Table, field


class Currency(CustomDataType):
    """An application-defined scalar, such as a currency code."""


from estate.assets import Estate

class BudgetTable(Table[Estate]):
    budget: Field[Currency] = field()
```

- Identity is the `(module, qualname)` pair, not the logical class name. Two
  `Currency` classes in different modules are different types.
- The class must be top-level and importable. A declaration inside a function is
  refused with `logical type declarations must be importable top-level classes`.
- A custom scalar may be a field type, an array item, a key or a `PropertySlot`.
- It exposes no value operations: no text, numeric or comparison methods, and
  `to_string()` refuses it. A target may refuse to store it; Neo4j refuses custom
  scalar properties.

## Arrays

`Array[T]` is the portable ordered-collection marker. It is deliberately not
`list[T]`, `Sequence[T]` or a storage type. The item may be any supported type,
including another array or a struct.

| Declaration | Value it names | Read as |
| --- | --- | --- |
| `Field[Array[str]]` | a list of non-null strings | `ArraySelection[str]` |
| `Field[Array[str \| None]]` | a list whose items may be null | `ArraySelection[str \| None]` |
| `Field[Array[SomeStruct]]` | a list of nested records | `ArraySelection[SomeStruct]` |
| `Field[Array[str] \| None]` | the same list, or absent | `NullableSelection[Array[str]]` |

Two nullability questions are independent:

- **Array presence** is declared. `Field[Array[T]]` reads a present
  `ArraySelection`; `Field[Array[T] | None]` reads
  `NullableSelection[Array[T]]`.
- **Item nullability** is a fact about the value. `Array[T | None]` stays in the
  declaration and is retained by normalization.

A null array produces no rows when expanded. An empty array also produces no
rows. An array with null items still produces rows; remove the null items with
`drop_null_items()` before using the array as a graph property.

## Structs and computed structs

| Form | Meaning | Example |
| --- | --- | --- |
| `SomeStruct` | Source-backed nested record declared with `Struct` | `Field[AddressStruct]` |
| `SomeComputedStruct` | Value record whose member expressions type the value | `Field[ReadingSummaryStruct]` |

A struct is a nested-record shape only. It is never a row source, has no
location, and cannot be bound. A struct may contain structs and arrays of
structs. Its identity is the `(module, qualname)` pair, so two structs with the
same name in different modules are distinct.

```python
from kg_build_system import Field, Struct, Table, field
from kg_build_system import Array


class AddressStruct(Struct):
    city: Field[str | None] = field()
    postcode: Field[str] = field()


from estate.assets import Estate

class SiteTable(Table[Estate]):
    site_id: Field[str] = field()
    parent_site: Field[str | None] = field()
    address: Field[AddressStruct | None] = field()
    previous_addresses: Field[Array[AddressStruct]] = field()
```

A source struct member reads its declared presence. A non-null member of a
present carrier is present, a nullable member is nullable, and a nullable
carrier makes the member nullable. A `ComputedStruct` member expression is a
**type witness** when the computed struct is carried by a row: it fixes the
member type and nullability, but it is not evaluated. The carrier row supplies
the value, and `extract` is the only way to read it.

A field type must be a value record. `Field[SomeTable]` and
`Field[SomeProjection]` are refused; use `extract` for a record already carried
by a field, or bind the relation separately.

## Nullability

A field declaration names the value type and its presence. `Field[str]` reads as
`ValueSelection[str]`; `Field[str | None]` reads as `NullableSelection[str]`.

```python
site_id = SiteTable.site_id          # ValueSelection[str]
parent = SiteTable.parent_site       # NullableSelection[str]
address = SiteTable.address          # NullableSelection[AddressStruct]
```

A `Projection` output is different: `computed_field(expression)` is typed by its
expression. A non-null expression publishes a non-null selection, and a nullable
expression publishes a nullable one.

| Declaration | Value it names | Read as |
| --- | --- | --- |
| `Field[str]` | a string | `ValueSelection[str]` |
| `Field[str \| None]` | the same string value type, possibly absent | `NullableSelection[str]` |
| `Field[Array[str]]` | a list of non-null strings | `ArraySelection[str]` |
| `Field[Array[str \| None]]` | a list whose items may be null | `ArraySelection[str \| None]` |
| `Field[Array[str] \| None]` | the same list, possibly absent | `NullableSelection[Array[str]]` |
| `Field[AddressStruct]` | a nested record | `StructSelection[AddressStruct]` |
| `Field[AddressStruct \| None]` | a nested record, possibly absent | `NullableSelection[AddressStruct]` |
| `computed_field(expr)` | a projection output, or a computed-struct member witness | a selection typed by `expr` |

Nullability is flattened: a nullable value never wraps another nullable value,
and `T | None | None` is simply `T | None`. Do not write the internal
`Nullable[T]` marker in declarations.

A source struct member reads its declaration: selecting `city` from a present
`AddressStruct` gives `ValueSelection[str]` for `Field[str]` and
`NullableSelection[str]` for `Field[str | None]`. A nullable carrier makes the
member nullable as well. A `ComputedStruct` member uses its witness type
instead: a non-null witness under a present carrier stays non-null, and the same
witness under a nullable carrier becomes nullable.

Nulls pass through calculations. A selection owns the null policy:

- `default_to(value)` replaces null and keeps the row; it is a no-op on a
  present value.
- `alter_rows().drop_null()` removes rows whose value is null and returns a
  present selection; it is a no-op on a non-null selection.
- `drop_null_items()` removes null array items; narrow the array to a present
  `ArraySelection` first.

```python
city = SiteTable.address.extract(lambda address: address.city).default_to("unknown")
postcode = (
    SiteTable.address.extract(lambda address: address.postcode)
    .alter_rows().drop_null()
)
```

A generated package's source-nullability claim determines the rendered field: a
`DEFAULTED` tier renders `Field[T | None]`, while an `ENFORCED` or `DECLARED`
tier renders `Field[T]`. Access then follows the rendered declaration. See
[generated nullability](ingest.md#generated-nullability).

## Graph property shape

A graph property is a scalar or a **flat, homogeneous array of non-null
scalars**. It is declared as a `PropertySlot[T]` and accepts a selection or
expression of `T`.

```python
from kg_build_system import Node, PropertySlot, property
from kg_build_system import Array


class SiteNode(Node):
    name: PropertySlot[str] = property()
    rating: PropertySlot[float | None] = property()
    tags: PropertySlot[Array[str]] = property()
```

| Shape | Accepted as a property | Reason |
| --- | --- | --- |
| Scalar `T` | Yes | Stored natively |
| <code>T &#124; None</code> | Yes | The property may be absent |
| `Array[T]` with non-null scalar items | Yes | Flat homogeneous list |
| <code>Array[T] &#124; None</code> | Yes | The same list, or absent |
| <code>Array[T &#124; None]</code> | No | Properties cannot hold null items; narrow the array, then use `drop_null_items()` |
| `Array[Array[T]]` | No | Nested arrays are not a graph value; flatten with `alter_rows().expand()` |
| `Array[SomeStruct]` | No | Struct members do not survive the boundary; reify them |
| `SomeStruct` | No | Properties are flat scalars or lists |

Custom scalars count as scalars for property shape, but a specific target may
still refuse them.

## Keys

A build key, source key or target key must be a **non-null scalar** expression.
Arrays and structs are refused, and so is a nullable scalar. A key written from a
source field declared `Field[T | None]` narrows first; a `Field[T]` key is
already present.

```python
build_key = SiteTable.site_id.alter_rows().drop_null()
target_key = SiteTable.parent_site.alter_rows().drop_null().expression.to_string()
```

An array of strings becomes key material through `concat(...)`. Narrow the array
first, then apply `sort()` and `unique()` before joining it.

!!! warning "Defaulting a key collapses identity"
    `default_to(...)` keeps the row, so two records that were never distinguished
    receive the same key. Drop an unidentified row with
    `alter_rows().drop_null()` unless a shared fallback identity is deliberate.

## DuckDB dispositions

The generation digest gate classifies every DuckDB type it understands into one
of three dispositions. The full mapping is below; the gate's effect on a
generated package is on [assets and ingest](ingest.md#digest-gate).

| Disposition | Meaning |
| --- | --- |
| `canonical` | Digestible as reported, or through the widening cast the source view applies automatically |
| `declared_only` | Digestible only through an author declaration, because the only available cast narrows the value or its precision |
| `refused` | No meaning-preserving canonical type exists |

| DuckDB type | Disposition | Canonical result |
| --- | --- | --- |
| `BOOLEAN` | `canonical` | `bool` |
| `TINYINT`, `SMALLINT`, `INTEGER`, `BIGINT`, `UTINYINT`, `USMALLINT`, `UINTEGER` | `canonical` | `int`, widened to `BIGINT` |
| `UBIGINT`, `HUGEINT`, `UHUGEINT` | `declared_only` | `int` through a checked cast to `BIGINT` |
| `FLOAT`, `DOUBLE` | `canonical` | `float`; `FLOAT` is widened to `DOUBLE` |
| `VARCHAR`, `JSON`, `ENUM` | `canonical` | `str` |
| `UUID` | `canonical` | `uuid` |
| `DATE` | `canonical` | `date` |
| `TIME` | `canonical` | `time` |
| `TIME_NS` | `declared_only` | `time`, rounded silently to microseconds |
| `TIMESTAMP`, `TIMESTAMP_S`, `TIMESTAMP_MS` | `canonical` | `timestamp` |
| `TIMESTAMP_NS` | `declared_only` | `timestamp`, nanoseconds dropped silently |
| `LIST`, `ARRAY` | `canonical` | `Array[item]`, composed from the item type |
| `STRUCT` | `canonical` | a struct, composed from the member types |
| `DECIMAL`, `BIGNUM`, `BIT`, `BLOB`, `TIME WITH TIME ZONE`, `TIMESTAMP WITH TIME ZONE`, `INTERVAL`, `MAP`, `UNION`, `VARIANT`, `ROW`, `NULL`, `TYPE`, `GEOMETRY`, `GEOGRAPHY` | `refused` | no canonical type |

A declared-only type requires an explicit request override. The checked cast
tests the declaration against the data and aborts on a value that does not fit;
the gate does not narrow silently.

| Refused type | Reason |
| --- | --- |
| `DECIMAL` | Exact numeric needs a parameterized canonical type and result-width rules; division returns `DOUBLE` |
| `BIGNUM` | An unbounded integer has no bounded canonical type |
| `BIT` | A bit string has no meaning-preserving canonical text form |
| `BLOB` | Binary has no total order, so merge and dedup cannot carry it |
| `TIME WITH TIME ZONE` | No canonical zoned time-of-day type exists |
| `TIMESTAMP WITH TIME ZONE` | An instant is not a local date-time, and its fetched offset depends on the session time zone |
| `INTERVAL` | Calendar-aware months are not a fixed duration |
| `MAP` | A mapping has no canonical flat shape in this release |
| `UNION` | A tagged sum has no framework analogue |
| `VARIANT` | Per-row self-describing typing has no canonical form |
| `ROW` | An anonymous record has no field names to declare |
| `NULL` | An untyped column is an absent declaration |
| `TYPE` | An internal pseudo-type |
| `GEOMETRY`, `GEOGRAPHY` | Extension-conditional and not portable |

Aliases resolve to their reported family before lookup: `JSON` to `VARCHAR`,
`TIMETZ` to `TIME WITH TIME ZONE`, and `TIMESTAMPTZ` to
`TIMESTAMP WITH TIME ZONE`. A type name outside the table is unsupported, not
refused: generation reports it rather than accepting it by default.

Acceptance by the digest gate is not acceptance as a graph property. A physical
array or struct may digest correctly and still be refused as a property shape;
property shape and target capability are separate checks.

## Annotation and value refusals

| Declaration | Why it is refused | What to do |
| --- | --- | --- |
| `Any` | The logical type must be explicit | Name the concrete type |
| <code>T &#124; U</code> with two non-null members | Logical unions do not exist | Use one type, or separate fields |
| `list[T]`, `Sequence[T]`, `dict[K, V]`, `tuple[...]` | Only the portable `Array` marker and declared structs exist | Use `Array[T]` or a `Struct` |
| A struct or custom type declared inside a function | It cannot be resolved by module and qualified name | Declare it at module level |
| A `Table` or `Projection` as a field type | A row source is not a value record | Use a `Struct` or `ComputedStruct`, or bind the relation separately |
| `value_expression(None)` | A null literal has no inferable type | Pass `logical_type=NullableType(STR)` (or the matching canonical type) |
| `value_expression([])` or an all-null array literal | The item type cannot be inferred | Pass `logical_type=ArrayType(INT)` (or the matching item type) |
| A struct or custom value as a literal | Literals are portable scalars and arrays only | Build the value from row expressions |
| A mixed-type array literal | Array items must have one logical type | Normalize the items first |

!!! note "`logical_type` takes a canonical type"
    `NullableType`, `ArrayType`, `STR` and `INT` come from
    `kg_build_system`. A Python annotation such as `str | None` is not a
    canonical type and is refused here.

!!! note "Refusal is not coercion"
    A value with no meaning-preserving canonical form is refused by name. The
    framework does not silently stringify, truncate or widen it.

## Limits

- Temporal and `uuid` values have canonical text but no comparison or filtering
  operators. Use `to_string()` when they must be compared or composed.
- Custom scalars have no value operations and no canonical text form.
- A struct is never a graph property and never a row source.
- A property array must be flat and hold non-null scalars; nested arrays and
  arrays of structs are expanded into rows, and nullable items are removed with
  `drop_null_items()`.
- Neo4j accepts `bool`, `int`, `float`, `str`, `date`, `time` and `timestamp`
  properties. It refuses `uuid` and custom scalars because it has no property
  type for them. Its array properties hold `bool`, `int`, `float` or `str` items
  only. A refused property fails at compile rather than being coerced.
- A generated package's nullability claim decides the rendered field:
  `DEFAULTED` renders `Field[T | None]`; `DECLARED` or `ENFORCED` renders
  `Field[T]`.
- A text-canonical value is written in its canonical form: ISO for `date`,
  `time` and `timestamp`, lowercase hyphenated text for `uuid`.

## Quick example

```python
from kg_build_system import (
    Field, Node, NodeValues, PropertySlot, Table, field, node_binding, property,
)
from kg_build_system import Array, Timestamp


from estate.assets import Estate

class ReadingTable(Table[Estate]):
    reading_id: Field[str] = field()
    recorded_on: Field[Timestamp | None] = field()
    value: Field[float | None] = field()
    labels: Field[Array[str | None] | None] = field()


class ReadingNode(Node):
    recorded_on: PropertySlot[Timestamp | None] = property()
    value: PropertySlot[float | None] = property()
    labels: PropertySlot[Array[str]] = property()


reading_binding = node_binding(
    target=ReadingNode,
    rows=ReadingTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.reading_id,
        properties=ReadingNode(
            recorded_on=row.recorded_on,
            value=row.value,
            labels=row.labels.default_to([]).drop_null_items(),
        ),
    ),
)
```

The build key is already a present string because `reading_id` is declared
`Field[str]`. The nullable timestamp and float pass through unchanged because the
properties accept absence. The labels array is made present when the source omits
it, then its null items are removed, because `Array[str]` is a valid property
shape and `Array[str | None]` is not.

## What to remember

- Eight canonical scalars, one `Array[T]`, structs for nesting, and `T | None`
  for absence that a declaration or property genuinely allows.
- A field declaration names a value type and its presence. `Field[T]` reads non-null; `Field[T | None]` reads nullable.
- A computed field is typed by its expression; a computed-struct member
  expression is a type witness.
- Graph properties are scalars or flat arrays of non-null scalars.
- Keys are present scalars; narrow a nullable source value before using it as
  one.
- The digest gate widens canonical types, requires a declaration for a
  declared-only type, and refuses a type with no canonical meaning.

Next: [Assets and ingest](ingest.md) attaches these types to physical data.
See also the [Authoring API](index.md), [Generation](generation.md) and the
[Glossary](glossary.md).
