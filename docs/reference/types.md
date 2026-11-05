# Types

This page lists the canonical logical types an author writes and the rules that
decide how a value is stored, bound and exported.

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

| Declaration | Value it names | Source read |
| --- | --- | --- |
| `Field[Array[str]]` | a list of non-null strings | `Selection[Nullable[Array[str]]]` |
| `Field[Array[Nullable[str]]]` | a list whose items may be null | `Selection[Nullable[Array[Nullable[str]]]]` |
| `Field[Array[SomeStruct]]` | a list of nested records | `Selection[Nullable[Array[SomeStruct]]]` |

Two nullability questions are independent:

- **Array presence** belongs to the owner. A source array reads as nullable
  because the source may omit the array; a computed array output is present when
  its selection is present.
- **Item nullability** is a fact about the value. `Array[Nullable[T]]` stays in
  the declaration and is retained by normalization.

A null array produces no rows when expanded. An empty array also produces no
rows. An array with null items still produces rows; remove the null items with
`drop_null_items()` before using the array as a graph property.

## Structs and computed structs

| Form | Meaning | Example |
| --- | --- | --- |
| `SomeStruct` | Source-backed nested record declared with `Struct` | `Field[AddressStruct]` |
| `SomeComputedStruct` | Value record whose member selections type the value | `Field[ReadingSummaryStruct]` |

A struct is a nested-record shape only. It is never a row source, has no
location, and cannot be bound. A struct may contain structs and arrays of
structs. Its identity is the `(module, qualname)` pair, so two structs with the
same name in different modules are distinct.

```python
from kg_build_system import Field, Struct, Table, field
from kg_build_system import Array


class AddressStruct(Struct):
    city: Field[str] = field()
    postcode: Field[str] = field()


from estate.assets import Estate

class SiteTable(Table[Estate]):
    site_id: Field[str] = field()
    address: Field[AddressStruct] = field()
    previous_addresses: Field[Array[AddressStruct]] = field()
```

A source struct member reads as nullable because the source may omit it. A
`ComputedStruct` member selection is a **type witness** when the computed struct
is carried by a row: it fixes the member type, but it is not evaluated. The
carrier row supplies the value, and `extract` is the only way to read it.

A field type must be a value record. `Field[SomeTable]` and `Field[SomeProjection]`
are refused; use `extract` for a record already carried by a field, or bind the
relation separately.

## Nullability

A field declaration names a value type. Presence comes from the owner:

```python
site_id = SiteTable.site_id          # Selection[Nullable[str]]
address = SiteTable.address          # Selection[Nullable[AddressStruct]]
```

A `Projection` output is different: `computed_field(value)` is typed by `value`.
A non-null selection publishes a non-null output, and a nullable selection
publishes a nullable one.

| Owner and declaration | Read as |
| --- | --- |
| Source `Table`: `Field[str]` | `Selection[Nullable[str]]` |
| Source `Table`: `Field[Array[str]]` | `Selection[Nullable[Array[str]]]` |
| Source `Table`: `Field[Array[Nullable[str]]]` | `Selection[Nullable[Array[Nullable[str]]]]` |
| Source `Table`: `Field[AddressStruct]` | `Selection[Nullable[AddressStruct]]` |
| `Projection`: `computed_field(present selection)` | `Selection[T]` |
| `Projection`: `computed_field(nullable selection)` | `Selection[Nullable[T]]` |
| `ComputedStruct` member through `extract` | The witness type, composed with the carrier's presence |

Nullability is flattened: a nullable value never wraps another nullable value,
and a nullable of a nullable is simply nullable. Do not write the internal
`Nullable[T]` marker in a field annotation; it is for array items and canonical
types.

A source struct member is always nullable because the source may omit it. A
nullable carrier also makes any member nullable. A `ComputedStruct` member uses
its witness type instead: a non-null witness under a present carrier stays
non-null, and the same witness under a nullable carrier becomes nullable.

Nulls pass through calculations. A selection owns the null policy:

- `default_to(value)` replaces null and keeps the row; it is not exposed on a
  present selection.
- `alter_rows().drop_null()` removes rows whose value is null and returns a
  present selection; it is not exposed on a present selection.
- `drop_null_items()` removes null array items; narrow the array to a present
  selection first.

```python
city = SiteTable.address.extract(lambda address: address.city).default_to("unknown")
postcode = (
    SiteTable.address.extract(lambda address: address.postcode)
    .alter_rows().drop_null()
)
```

A generated package renders every source field as `Field[T]` from its value type.
The observed source claim is provenance for the manifest, statistics and notes;
it never adds absence to the rendered field. Access then follows the owner: a
generated source field reads as nullable because it belongs to a source table.
See [generated nullability](ingest.md#generated-nullability).

## Graph property shape

A graph property is a scalar or a **flat, homogeneous array of non-null
scalars**. It is declared as a `PropertySlot[T]` and accepts a selection of `T`.

```python
from kg_build_system import Node, PropertySlot, property
from kg_build_system import Array


class SiteNode(Node):
    name: PropertySlot[str] = property()
    rating: PropertySlot[float] = property()
    tags: PropertySlot[Array[str]] = property()
```

| Shape | Accepted as a property | Reason |
| --- | --- | --- |
| Scalar `T` | Yes | Stored natively |
| a scalar that may be absent | Yes | The property may be absent |
| `Array[T]` with non-null scalar items | Yes | Flat homogeneous list |
| an array that may be absent | Yes | The same list, or absent |
| `Array[Nullable[T]]` | No | Properties cannot hold null items; narrow the array, then use `drop_null_items()` |
| `Array[Array[T]]` | No | Nested arrays are not a graph value; flatten with `alter_rows().expand()` |
| `Array[SomeStruct]` | No | Struct members do not survive the boundary; reify them |
| `SomeStruct` | No | Properties are flat scalars or lists |

Custom scalars count as scalars for property shape, but a specific target may
still refuse them.

## Keys

A build key, source key or target key must be a **present scalar** selection.
Arrays and structs are refused, and so is a nullable scalar. A key from a source
field is narrowed first because source access is nullable.

```python
build_key = SiteTable.site_id.alter_rows().drop_null()
target_key = SiteTable.site_id.alter_rows().drop_null().to_string()
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
| A field annotation that includes absence | A field names the value; the owner decides presence | Declare `Field[T]` and narrow or default the source read |
| <code>T &#124; U</code> with two non-null members | Logical unions do not exist | Use one type, or separate fields |
| `list[T]`, `Sequence[T]`, `dict[K, V]`, `tuple[...]` | Only the portable `Array` marker and declared structs exist | Use `Array[T]` or a `Struct` |
| A struct or custom type declared inside a function | It cannot be resolved by module and qualified name | Declare it at module level |
| A `Table` or `Projection` as a field type | A row source is not a value record | Use a `Struct` or `ComputedStruct`, or bind the relation separately |
| `value_expression(None)` | A null literal has no inferable type | Pass `logical_type=NullableType(STR)` (or the matching canonical type) |
| `value_expression([])` or an all-null array literal | The item type cannot be inferred | Pass `logical_type=ArrayType(INT)` (or the matching item type) |
| A struct or custom value as a literal | Literals are portable scalars and arrays only | Build the value from row selections |
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
- A generated source field always renders `Field[T]`; observed source
  nullability is provenance, not a rendered type.
- A text-canonical value is written in its canonical form: ISO for `date`,
  `time` and `timestamp`, lowercase hyphenated text for `uuid`.

## Quick example

```python
from kg_build_system import (
    Field, Node, NodeValues, PropertySlot, Table, field, node_binding, property,
)
from kg_build_system import Array, Nullable, Timestamp


from estate.assets import Estate

class ReadingTable(Table[Estate]):
    reading_id: Field[str] = field()
    recorded_on: Field[Timestamp] = field()
    value: Field[float] = field()
    labels: Field[Array[Nullable[str]]] = field()


class ReadingNode(Node):
    recorded_on: PropertySlot[Timestamp] = property()
    value: PropertySlot[float] = property()
    labels: PropertySlot[Array[str]] = property()


reading_binding = node_binding(
    target=ReadingNode,
    rows=ReadingTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.reading_id.alter_rows().drop_null(),
        properties=ReadingNode(
            recorded_on=row.recorded_on.alter_rows().drop_null(),
            value=row.value.alter_rows().drop_null(),
            labels=row.labels.alter_rows().drop_null().drop_null_items(),
        ),
    ),
)
```

Every source field reads as nullable, so each required property narrows it. The
build key is present after `drop_null()`. The labels array is made present by
narrowing, then its null items are removed, because `Array[str]` is a valid
property shape and `Array[Nullable[str]]` is not.

## What to remember

- Eight canonical scalars, one `Array[T]`, structs for nesting, and `Nullable[T]`
  for item nullability or a canonical type.
- A field declaration names a value type; the owner decides presence. Source
  fields read nullable; computed fields read exactly their selection type.
- A computed field is typed by its selection; a computed-struct member selection
  is a type witness.
- Graph properties are scalars or flat arrays of non-null scalars.
- Keys are present scalars; narrow a nullable source read before using it as one.
- The digest gate widens canonical types, requires a declaration for a
  declared-only type, and refuses a type with no canonical meaning.
- Generated fields always render `Field[T]`; observed nullability is provenance.

Next: [Assets and ingest](ingest.md) attaches these types to physical data.
See also the [Authoring API](index.md), [Generation](generation.md) and the
[Glossary](glossary.md).
