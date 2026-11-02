# Types and nullability

A type is the claim a value makes: what kind of value it is, whether it can be
absent, and what you can do with it.

A build crosses a boundary that Python does not check: a file, a warehouse table
or an API response becomes rows, then expressions, then graph properties. Types
are the claim every layer shares across that boundary. They let compilation reject
a text value bound to an integer property, or a nullable field used as an
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
`kg_build_system.types`. They are aliases of the standard-library classes, not
subclasses, so `Field[Uuid]` and `Field[uuid.UUID]` are the same annotation.
Choose one spelling for a declaration and keep it.

Physical sources are wider than this vocabulary. The framework widens a value
only when the meaning survives: integer widths that fit the signed 64-bit range
become `int`, both `FLOAT` and `DOUBLE` become `float`, and `JSON` and `ENUM`
become `str`. Anything with no meaning-preserving form is refused rather than
guessed. Refusal is listed under [limits](#limits).

Temporal and `uuid` values have a canonical text form, so they survive the
contract, deduplication and output unchanged. They have no comparison or
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


class BudgetTable(Table):
    budget: Field[Currency] = field()
```

A custom scalar is identified by its module and qualified name, so it must be a
top-level importable class. It composes as a field type, an array item, a key and
a property slot, but it exposes no value operations: no text, numeric or
comparison methods, and no `to_string()`. A target may refuse to store it, as
Neo4j does.

## Nullability belongs to the declaration

A source field reads the type its annotation declares. The declaration is the
presence claim; reading it does not add nullability:

| You read | You get |
| --- | --- |
| `Field[str]` | `ValueSelection[str]` |
| `Field[str \| None]` | `NullableSelection[str]` |
| `Field[Array[str]]` | `ArraySelection[str]` |
| `Field[Array[str \| None]]` | `ArraySelection[str \| None]` |
| `Field[Array[str] \| None]` | `NullableSelection[Array[str]]` |
| `Field[SomeStruct]` | `StructSelection[SomeStruct]` |
| `Field[SomeStruct \| None]` | `NullableSelection[SomeStruct]` |
| a projection's `computed_field(expression)` | a selection typed by the expression |
| a `ComputedStruct` member through `extract` | the witness type, composed with the carrier's presence |

This is the rule authors most often encounter. A source may omit a value, so
declare it nullable when that is true. Do not add `| None` to a field the source
always supplies: it makes every read nullable and forces needless narrowing. Item
nullability is a separate decision, because it describes a present list, so
`Array[str | None]` stays.

A `ComputedStruct` used as a field type describes a record the row already
carries. Its member expressions are type witnesses: they fix each member's type
and nullability, but the carrier supplies the value. A present carrier leaves a
non-null witness non-null; a nullable carrier makes it nullable. See
[computed structs](projections.md#computed-structs).

The binding or expression decides what absence means:

```python
from estate.table import SiteTable

site_id = SiteTable.site_id                        # ValueSelection[str]
key = site_id                                      # already a present scalar
name = SiteTable.name                              # ValueSelection[str]
tags = SiteTable.aliases.drop_null_items()         # ArraySelection[str]
```

When a field is declared `Field[str | None]`, `alter_rows().drop_null()`
narrows it and removes unidentified rows, while `default_to()` keeps the row and
replaces the null. Both are no-ops on a present selection. For a key, dropping is
the honest choice: a fallback makes every unidentified row share one graph
identity. A nullable graph property can also carry the absence through, which is
often the right answer for a value that is genuinely unknown.

Generated tables follow the same rule. An `ENFORCED` or `DECLARED` source claim
renders `Field[T]`; a `DEFAULTED` claim renders `Field[T | None]`. The generator
records the tier in the header and manifest as provenance, and the rendered field
decides how the access reads. A nullability `override` changes the claim and the
rendered field. Nullability is not inferred from sample values.

## What a value may become

A graph property is a stored scalar or a flat, homogeneous list of non-null
scalars. That shape is what every target can preserve without inventing a
representation:

| Shape | As a property | Why |
| --- | --- | --- |
| `str`, `int`, `float`, `bool`, `Date`, `Time`, `Timestamp`, `Uuid` | yes | a stored scalar |
| `T \| None` | yes | the property may be absent |
| `Array[T]` of non-null scalars | yes | a flat list |
| `Array[T] \| None` | yes | the same list, or absent |
| `Array[T \| None]` | no | no target stores null items faithfully |
| a struct or an array of structs | no | a nested record is not a property value |
| a nested array | no | nesting has no flat representation |

Keys are narrower still. A build key, a source key and a target key must be
non-null scalars, because a key identifies one record. An array or a struct cannot
do that, and neither can a nullable value. Group keys follow the same scalar rule;
rows whose key is null are dropped before grouping.

The survey graph makes the property shape concrete:

```python
from estate.table import SiteTable
from kg_build_system import Node, NodeValues, PropertySlot, node_binding, property
from kg_build_system.types import Array, Date


class SiteNode(Node):
    name: PropertySlot[str] = property()
    surveyed_on: PropertySlot[Date | None] = property()
    labels: PropertySlot[Array[str]] = property()


site_binding = node_binding(
    target=SiteNode,
    rows=SiteTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=row.name.default_to("Unnamed site"),
            surveyed_on=row.surveyed_on,
            labels=row.aliases.drop_null_items(),
        ),
    ),
)
```

The key must be present; a `Field[str | None]` declaration would be narrowed with
`drop_null()`, while a `Field[str]` key is already present. `surveyed_on` is
nullable on the property, so it can carry an absent value when the source
declaration allows one. `aliases` is declared `Array[str | None]`; the binding
removes its null items so it matches the flat `Array[str]` property. Array
presence and item nullability are separate decisions, explained on
[expressions](expressions.md#arrays-are-values-until-you-expand-them).

## Decisions you make

- **Write the presence the source promises.** `Field[str]` reads present;
  `Field[str | None]` reads nullable. The declaration decides access.
- **Choose a null policy deliberately.** Drop the row, supply a fallback, or let
  a nullable property carry the absence. A nullable key is always narrowed.
- **Convert at the boundary.** A value must be the class its type names; convert
  at the source rather than relying on a cast.
- **Stay within the target's property types.** A flat array of non-null scalars is
  portable; a target may refuse a type it cannot store.

## Limits

- `Any`, `list[T]`, `dict[K, V]`, tuples and unions of two real types are not
  logical types. Use `Array[T]` for a list and declare a `Struct` for a record.
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

Continue with [sources](sources.md) to attach these typed declarations to
physical files.

## Reference

For the complete type vocabulary, canonical names, nullability rules and refusal
list, see the [types reference](../reference/types.md).
