# Types and nullability

A type is the claim a value makes: what kind of value it is, whether it can be
absent, and what you can do with it.

A build crosses a boundary that Python does not check: a file, a warehouse table
or an API response becomes rows, then selections, then graph properties. Types
are the claim every part shares across that boundary. They let compilation reject
a text value bound to an integer property, or a nullable value used as an
identifier, before any data is read.

## The vocabulary

Every annotation normalises to one logical type. The framework keeps a small,
portable vocabulary rather than mirroring the type system of a source:

| You write | The value it names |
| --- | --- |
| `bool` | a truth value |
| `int` | a signed 64-bit integer |
| `float` | a double-precision number |
| `str` | text |
| `Date` | a calendar date |
| `Time` | a time of day |
| `Timestamp` | a local date and time |
| `Uuid` | a universally unique identifier |
| `Array[T]` | an ordered list of one item type |
| `SomeStruct`, `SomeComputedStruct` | a nested record |
| `SomeCustomDataType` | an application-defined scalar |

`Date`, `Time`, `Timestamp` and `Uuid` are representative names from
`kg_build_system`. They are aliases of the standard-library classes, not
subclasses, so `Field[Uuid]` and `Field[uuid.UUID]` are the same annotation.
Choose one spelling for a declaration and keep it.

Physical sources are wider than this vocabulary. The framework widens a value
only when the meaning survives: integer widths that fit the signed 64-bit range
become `int`, both `FLOAT` and `DOUBLE` become `float`, and `JSON` and `ENUM`
become `str`. Anything with no meaning-preserving form is refused rather than
guessed. Refusal is listed under [limits](#limits).

Temporal and `uuid` values have a canonical text form, so they survive the
workflow plan, deduplication and output unchanged. They have no comparison or
filtering operators; call `to_string()` when one must become part of an identity.
A target may still narrow what it stores: Neo4j refuses `uuid` properties because
it has no property type for them.

## Custom scalars

A scalar that belongs to your application extends the vocabulary without teaching
the framework what it means:

```python
from kg_build_system import CustomDataType, Field, Table, field


class Currency(CustomDataType):
    """An application-defined scalar, such as a currency code."""


from estate.assets import Estate

class BudgetTable(Table[Estate]):
    budget: Field[Currency] = field()
```

A custom scalar is identified by its module and qualified name, so it must be a
top-level importable class. It composes as a field type, an array item, a key and
a property slot, but it exposes no value operations: no text, numeric or
comparison methods, and no `to_string()`. A target may refuse to store it, as
Neo4j does.

## A field declares a value type

A `Field[T]` declares the value type. It never declares `T | None`; a source
field is not a nullable annotation, and a nullable source read does not mean the
declaration is nullable. Presence is decided by the owner that supplies the
value.

| Owner | Declaration | The read |
| --- | --- | --- |
| Source `Table` | `Field[T]` | `NullableSelection[T]` |
| Source `Struct` member | `Field[T]` | `NullableSelection[T]` |
| `Projection` output | `computed_field(value)` | The type of `value` |
| `ComputedStruct` member | `computed_field(value)` | The witness type, composed with the carrier's presence |

A source may omit any column or nested member, so source access always includes
the possibility of absence. This keeps the declaration honest: `Field[str]` says
the value is a string, not that every row supplies one. The binding decides what
absence means:

```python
from estate.table import SiteTable

site_id = SiteTable.site_id.alter_rows().drop_null()  # present key
name = SiteTable.name.default_to("Unnamed site")      # present with fallback
region = SiteTable.region_id                          # still nullable
```

`alter_rows().drop_null()` narrows the read and removes rows where the value is
absent. `default_to()` keeps the row and replaces the absent value. Both return a
present `Selection[T]`. For a key, dropping is the honest choice: a fallback
collapses distinct records into one identity. A nullable graph property can carry
the absence through, which is often right for a value that is genuinely unknown.

Item nullability is different. It describes a present list, so it belongs to the
value type and stays in the declaration:

```python
class SiteTable(Table[Estate]):
    aliases: Field[Array[Nullable[str]]] = field()
```

`aliases` reads as `Selection[Nullable[Array[Nullable[str]]]]`. The outer
nullability is the source row; the inner nullability is the item. Call
`drop_null_items()` after narrowing the array when a property requires non-null
items.

A `ComputedStruct` used as a field type describes a record the row already
carries. Its member selections are type witnesses: they fix each member's type,
but the carrier supplies the value. A present carrier leaves a present witness
present; a nullable carrier makes the member nullable. See
[computed structs](projections.md#computed-structs).

## What a value may become

A graph property is a stored scalar or a flat, homogeneous list of non-null
scalars. That shape is what every target can preserve without inventing a
representation:

| Shape | As a property | Why |
| --- | --- | --- |
| `str`, `int`, `float`, `bool`, `Date`, `Time`, `Timestamp`, `Uuid` | yes | a stored scalar |
| a scalar that may be absent | yes | the property may be absent |
| `Array[T]` of non-null scalars | yes | a flat list |
| an array that may be absent | yes | the same list, or absent |
| `Array[Nullable[T]]` | no | no target stores null items faithfully |
| a struct or an array of structs | no | a nested record is not a property value |
| a nested array | no | nesting has no flat representation |

Keys are narrower still. A build key, a source key and a target key must be
present scalars, because a key identifies one record. An array or a struct cannot
do that, and neither can a nullable selection. Group keys follow the same scalar
rule; rows whose key is null are dropped before grouping.

The survey graph makes the property shape concrete:

```python
from estate.table import SiteTable
from kg_build_system import Node, NodeValues, PropertySlot, node_binding, property
from kg_build_system import Array, Date


class SiteNode(Node):
    name: PropertySlot[str] = property()
    surveyed_on: PropertySlot[Date] = property()
    labels: PropertySlot[Array[str]] = property()


site_binding = node_binding(
    target=SiteNode,
    rows=SiteTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=row.name.default_to("Unnamed site"),
            surveyed_on=row.surveyed_on.alter_rows().drop_null(),
            labels=row.aliases.alter_rows().drop_null().drop_null_items(),
        ),
    ),
)
```

`site_id` is narrowed because the source read is nullable. `name` gets a
fallback. `surveyed_on` satisfies a required property by dropping rows that
cannot supply it. `aliases` is declared `Array[Nullable[str]]`; the binding
removes its null items so it matches the flat `Array[str]` property. Array
presence and item nullability are separate decisions, explained on
[expressions](expressions.md#arrays-are-values-until-you-expand-them).

## Decisions you make

- **Declare the value, not the source's absence.** `Field[T]` names the value.
  Source access is nullable because the source may omit it.
- **Choose a null policy deliberately.** Drop the row, supply a fallback, or let
  a nullable property carry the absence. A nullable key is always narrowed.
- **Keep item nullability in the value type.** `Array[Nullable[T]]` is a real
  value shape; remove the null items when a property cannot hold them.
- **Convert at the boundary.** A value must be the class its type names; convert
  at the source rather than relying on a cast.
- **Stay within the target's property types.** A flat array of non-null scalars is
  portable; a target may refuse a type it cannot store.

## Limits

- `Any`, `list[T]`, `dict[K, V]`, tuples and unions of two real types are not
  logical types. Use `Array[T]` for a list and declare a `Struct` for a record.
- A field annotation may not be nullable. Item nullability uses `Nullable[T]`
  inside an array; source nullability comes from the owner.
- A value must be the class its type names. A `Decimal` is not a `float`, and a
  string is not a `Timestamp`; convert at the source boundary.
- A physical column with no meaning-preserving type is refused during generation.
  Export it in a supported type or declare that table by hand.
- A struct or a custom scalar must be a top-level importable class.
- Temporal values, `uuid` and custom scalars have no comparison operations.
  `to_string()` exists for the eight canonical scalars only.
- A null literal needs an explicit nullable type; an empty array literal needs an
  explicit item type.
- A target may accept fewer property types than the framework models. Neo4j
  refuses `uuid` and custom scalar properties.

## Next steps

Continue with [assets](assets.md) to declare the logical source package a
table names and the optional layout a source planner reads.

## Reference

For the complete type vocabulary, canonical names, nullability rules and refusal
list, see the [types reference](../reference/types.md).
