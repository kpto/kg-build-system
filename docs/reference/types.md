# Type vocabulary

Every annotation used in a declaration normalizes to one canonical logical
type. The canonical names are lowercase — `bool`, `int`, `float`, `str`,
`date`, `time`, `timestamp`, `uuid` — plus `Array[T]`, a declared `Struct` or
`ComputedStruct`, and a declared `CustomDataType`. A capitalised spelling such as
`Date` is a *representative type*: the Python class an author writes, aliased to
the stdlib class the engine returns.

```python
from kg_build_system.types import Array, Date, Time, Timestamp, Uuid
```

`Date`, `Time`, `Timestamp` and `Uuid` are aliases of `datetime.date`,
`datetime.time`, `datetime.datetime` and `uuid.UUID`, not new classes. The
alias and the stdlib spelling are therefore the same annotation. See
[Types and nullability](../concepts/types.md).

## Canonical scalars

| Canonical | Author writes | Class | Notes |
| --- | --- | --- | --- |
| `bool` | `bool` | `bool` | Boolean value and predicate |
| `int` | `int` | `int` | `add`, `sub` |
| `float` | `float` | `float` | `add`, `sub` |
| `str` | `str` | `str` | Text operations and `to_string()` |
| `date` | `Date` | `datetime.date` | Canonical ISO text |
| `time` | `Time` | `datetime.time` | Canonical ISO text |
| `timestamp` | `Timestamp` | `datetime.datetime` | Canonical text keeps `T` |
| `uuid` | `Uuid` | `uuid.UUID` | Lowercase hyphenated text |

All eight are scalar units. Every one is valid as a property, a key, an array
item, and a literal, and every one has a canonical text form through
`to_string()`. Temporal and uuid values are stored, deduplicated and merged;
the file and meta-graph outputs write their canonical text. They expose no
comparison or filtering operators; use `to_string()` when identity needs
composition. A target may narrow what it stores — Neo4j refuses `uuid`
properties, as described below.

!!! warning "No implicit conversions"
    A value must be the class its unit names. A `Decimal` is not a `float`, a
    string is not a `timestamp`, and a `uuid.UUID` is not a `str`. Declare the
    type you actually receive, or convert it explicitly in the data contract.

## Arrays, structs, and custom scalars

| Form | Meaning | Example |
| --- | --- | --- |
| `Array[T]` | Ordered, homogeneous collection | `Field[Array[int]]` |
| `SomeStruct` | Nested source record declared with `Struct` | `Field[AddressStruct]` |
| `SomeComputedStruct` | Value record whose member expressions are type witnesses when carried by a row | `Field[ReadingSummaryStruct]` |
| `SomeCustomType` | Application-defined scalar declared with `CustomDataType` | `Field[Currency]` |

`Array` is a portable marker, deliberately not `list[T]`, `Sequence[T]`, or a
storage type. A source struct is a class whose fields are `Field[T]` members; a
computed struct uses `computed_field` members as type witnesses. A custom scalar
is a class derived from `CustomDataType`; it is identified by module and
qualified name, so it must be a top-level importable class.

```python
from kg_build_system import CustomDataType, Field, Struct, Table, field
from kg_build_system.types import Array


class Currency(CustomDataType):
    """An application-defined scalar, such as a currency code."""


class AddressStruct(Struct):
    city: Field[str] = field()
    postcode: Field[str] = field()


class SiteTable(Table):
    site_id: Field[str] = field()
    parent_site: Field[str] = field()
    address: Field[AddressStruct] = field()
    tags: Field[Array[str]] = field()
    budget: Field[Currency] = field()
```

Struct identity is the `(module, qualname)` pair, not the logical name. Two
structs with the same name in different modules are distinct declarations.
A struct is only a nested record; it is never a row source. Nesting is allowed:
a struct may contain structs and arrays of structs.

Custom scalars compose like any other scalar in data contracts, selections,
and property slots. Identity is the `(module, qualname)` pair, so the class must
be top-level and importable. They expose no operations of their own — no text,
numeric, comparison or `to_string()` operation — and a target may refuse to store
them: Neo4j refuses custom scalars and `uuid` properties. A struct cannot be a
graph property; reify what you need into scalar properties.

## Nullability

A field declaration names the value type. Source access is nullable whatever the
declaration says, so `Field[str]` and `Field[str | None]` both read as
`NullableSelection[str]`. Write the value type: a top-level `| None` is stripped,
and relying on it is misleading.

```python
site_id = SiteTable.site_id              # NullableSelection[str]
parent = SiteTable.parent_site           # NullableSelection[str]
tags = SiteTable.tags                    # NullableSelection[Array[str]]
address = SiteTable.address              # NullableSelection[AddressStruct]
```

A `Projection` output is different: `computed_field(expression)` is typed by its
expression. A non-null expression publishes a non-null selection, and a nullable
expression publishes a nullable one.

A `ComputedStruct` member is readable only through `extract`, and its
`computed_field` expression is a type witness there, not an evaluated value. The
witness fixes the member type; the read is a field reference on the carrier row.

| Declaration | Value it names | Read as |
| --- | --- | --- |
| `Field[str]` | a string | `NullableSelection[str]` |
| `Field[str \| None]` | the same string value type | `NullableSelection[str]` |
| `Field[Array[str]]` | a list of non-null strings | `NullableSelection[Array[str]]` |
| `Field[Array[str \| None]]` | a list whose items may be null | `NullableSelection[Array[str \| None]]` |
| `Field[AddressStruct]` | a nested record | `NullableSelection[AddressStruct]` |
| `computed_field(expr)` | a projection output, or a `ComputedStruct` member witness | a selection typed by `expr` |

The two array levels are independent. Item nullability is a fact about the value
and stays in the declaration; array presence belongs to access. Nullability is
flattened: a nullable value never wraps another nullable value, and
`T | None | None` is simply `T | None`. Do not write the internal `Nullable[T]`
marker in declarations.

A generated package's source-nullability claim is not a top-level field type in
the blueprint: `field()` strips it, and the generator records the claim in the
file header and source digest instead. Access is nullable for every source field
whatever that header says.

Nulls pass through calculations. Selections own the policy:

- `default_to(value)` replaces null and keeps the row.
- `alter_rows().drop_null()` removes rows whose value is null and returns a
  present selection.
- `drop_null_items()` removes null array items; narrow the array to a present
  `ArraySelection` first.

```python
city = SiteTable.address.extract(lambda address: address.city).default_to("unknown")
postcode = (
    SiteTable.address.extract(lambda address: address.postcode)
    .alter_rows().drop_null()
)
```

A source struct member is nullable at every source step: selecting `city` from
`AddressStruct` gives `str | None`, even when the parent address is present,
because the member is source-backed. A `ComputedStruct` member uses its witness
type instead: a non-null witness under a present carrier stays non-null, and the
same member under a nullable carrier becomes nullable. The witness does not
evaluate; the carrier supplies the value. Selecting an already-nullable field
does not add a second layer of nullability.

## Graph property shape

A graph property is a scalar or a **flat, homogeneous array of non-null
scalars**. It is declared as a `PropertySlot[T]` and accepts a selection or
expression of `T`:

```python
from kg_build_system import Node, PropertySlot, property


class SiteNode(Node):
    name: PropertySlot[str] = property()
    rating: PropertySlot[float | None] = property()
    tags: PropertySlot[Array[str]] = property()
```

| Shape | Accepted as a property | Reason |
| --- | --- | --- |
| Scalar `T` | Yes | Stored natively |
| <code>T &#124; None</code> | Yes | Property may be absent |
| `Array[T]` with non-null scalar items | Yes | Flat homogeneous list |
| <code>Array[T] &#124; None</code> | Yes | The same list, or absent |
| <code>Array[T &#124; None]</code> | No | Properties cannot hold null items; narrow the array, then use `drop_null_items()` |
| `Array[Array[T]]` | No | Nested arrays are not a graph value; flatten with `alter_rows().expand()` |
| `Array[SomeStruct]` | No | Struct members do not survive the boundary; reify them |
| `SomeStruct` | No | Properties are flat scalars or lists |

Keys follow a narrower rule: a build key, source key, or target key must be a
**non-null scalar** expression. Arrays and structs are refused, and so is a
nullable scalar. Every source field reads as nullable, so a key written from one
narrows first. An array of strings becomes key material through `concat(...)`;
apply `sort()` and `unique()` after narrowing the array.

```python
build_key = SiteTable.site_id.alter_rows().drop_null()
target_key = (
    SiteTable.parent_site.alter_rows().drop_null().expression.to_string()
)
```

A target may narrow the types it stores. The Neo4j module accepts `bool`,
`int`, `float`, `str`, `date`, `time`, and `timestamp` properties; it refuses
`uuid` and custom scalars because Neo4j has no property type for them. Its
array properties hold `bool`, `int`, `float`, or `str` items only. A refused
property fails at compile rather than being coerced. See
[Outputs](../concepts/outputs.md).

## What is refused, and why

| Declaration | Why it is refused | What to do |
| --- | --- | --- |
| `Any` | The logical type must be explicit | Name the concrete type |
| <code>T &#124; U</code> with two non-null members | Logical unions do not exist | Use one type, or separate fields |
| `list[T]`, `Sequence[T]`, `dict[K, V]`, `tuple[...]` | Only the portable `Array` marker and declared structs exist | Use `Array[T]` or a `Struct` |
| A struct or custom type declared inside a function | It cannot be resolved by module and qualified name | Declare it at module level |
| `value_expression(None)` | A null literal has no inferable type | Pass `logical_type=NullableType(STR)` (or the matching canonical type) |
| `value_expression([])` or an all-null array literal | The item type cannot be inferred | Pass `logical_type=ArrayType(INT)` (or the matching item type) |
| A struct or custom value as a literal | Literals are portable scalars and arrays only | Build the value from row expressions |
| Mixed-type array literal | Array items must have one logical type | Normalise the items first |
| Nested array, array of structs, or nullable item array as a property | No target stores that shape faithfully | `alter_rows().expand()`, reify, or narrow then `drop_null_items()` |
| Nullable, array, or struct build key | A key must identify a row unambiguously | Narrow with `alter_rows().drop_null()`, or use a string array's `concat()` |
| `DECIMAL`, `BIGNUM`, `BIT`, `BLOB`, `INTERVAL`, `TIMESTAMP WITH TIME ZONE`, `MAP`, `VARIANT`, and other non-canonical physical types | They have no meaning-preserving canonical type | Export the column in a supported type, or declare the table by hand |

!!! note "`logical_type` takes a canonical type"
    `NullableType`, `ArrayType`, `STR` and `INT` come from
    `kg_build_system.types`. A Python annotation such as `str | None` is not a
    canonical type and is refused here.

!!! note "Refusal is not coercion"
    A value with no meaning-preserving canonical form is refused by name. The
    framework does not silently stringify, truncate, or widen it.

## Quick examples

A complete pair of declarations, with the three common shapes:

```python
from kg_build_system import (
    Field, Node, NodeValues, PropertySlot, Table, field, node_binding, property,
)
from kg_build_system.types import Array, Timestamp


class ReadingTable(Table):
    reading_id: Field[str] = field()
    recorded_on: Field[Timestamp] = field()
    value: Field[float] = field()
    labels: Field[Array[str | None]] = field()


class ReadingNode(Node):
    recorded_on: PropertySlot[Timestamp | None] = property()
    value: PropertySlot[float | None] = property()
    labels: PropertySlot[Array[str]] = property()


reading_binding = node_binding(
    target=ReadingNode,
    rows=ReadingTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.reading_id.alter_rows().drop_null(),
        properties=ReadingNode(
            recorded_on=row.recorded_on,
            value=row.value,
            labels=row.labels.default_to([]).drop_null_items(),
        ),
    ),
)
```

The build key is narrowed to a present string. The nullable timestamp and float
pass through unchanged because the properties accept absence. The labels array
is made present when the source omits it, then its null items are removed,
because `Array[str]` is a valid property shape and `Array[str | None]` is not.

## What to remember

- Eight canonical scalars, one `Array[T]`, structs for nesting, and `T | None`
  for absence that a declaration or property genuinely allows.
- A field declaration names a value type. Source access is always nullable.
- A computed field is typed by its expression.
- Graph properties are scalars or flat arrays of non-null scalars.
- Keys are present scalars; narrow every source value used as one.
- Refusal is explicit. Convert at the source boundary rather than relying on a
  cast.

See the [Public API](api.md) for every declaration name, and the
[Glossary](glossary.md) for the surrounding vocabulary.
