# Data contracts

Data contracts are the first layer of a build. They describe rows as typed Python
classes, before anything is known about nodes, edges or files. A contract is not
a schema document beside the code: the class **is** the schema.

## A table is a shape and a row source

A `Table` subclass does two jobs at once. It is a **shape** whose fields type
every value, and it is a **row source** that a binding can read:

```python
from kg_build_system import Field, Table, TableOptions, field

class PeopleTable(Table):
    """One row per person in the directory."""

    options = TableOptions(name="people", description="The personnel directory.")
    person_id: Field[str] = field()
    name: Field[str] = field()
```

The same class provides the relation row source a binding passes as
`rows=PeopleTable.row_source()`. The `bind` callable receives a shape instance —
a symbolic proxy of `PeopleTable`, not data and not a dictionary. `row.name` is a
selection over a logical field; reading it does not touch a file. Rows appear
only when the build executes.

`name` defaults to the class name with the `Table` suffix removed and converted
to snake case, so `PeopleTable` becomes `people`. `description` defaults to the
class docstring; an explicit option wins. `options` is class metadata, never a
field and never a graph property.

## Two field constructors, one descriptor

`Field[T]` is the single member descriptor for every declaration. What differs is
how the member is backed:

| Constructor | Backs | Where it is used |
| --- | --- | --- |
| `field()` | a source column or source struct member | `Table` fields and `Struct` members |
| `computed_field(expression)` | a typed expression | `Projection` outputs and `ComputedStruct` members |

`T` is the value type: `str`, `int`, `float`, `bool`, `Date`, `Time`,
`Timestamp`, `Uuid`, a nested `Struct` or `ComputedStruct`, or an `Array` of one
of those.

```python
from kg_build_system import Field, Table, TableOptions, field
from kg_build_system.types import Timestamp

class VisitTable(Table):
    """One inspection visit."""

    options = TableOptions(name="visit")
    visit_id: Field[str] = field()
    """Stable visit identifier."""
    inspected_on: Field[Timestamp] = field()
    notes: Field[str] = field()
```

The declaration names the value the source holds. It does not promise that a
row supplies one. Every one of those fields reads as a nullable selection,
including `visit_id`:

```python
visit_id = VisitTable.visit_id              # NullableSelection[str]
present = visit_id.alter_rows().drop_null() # ValueSelection[str]
```

`Field[str | None]` is accepted and stripped to `Field[str]`; write the value
type. Array item nullability is different, because it is a fact about the value:
`Field[Array[str | None]]` says the array's items may be null. The binding decides
what absence means with `alter_rows().drop_null()` or `default_to(...)`. See
[types and nullability](types.md).

## Nested structs

A `Struct` is a shape only. It cannot be source-bound, placed in a table group,
or passed as `rows=`. Its purpose is to describe a nested record inside a table
or another struct.

```python
from kg_build_system import Field, Struct, StructOptions, Table, TableOptions, field
from kg_build_system.types import Array

class AddressStruct(Struct):
    """A postal address."""

    options = StructOptions(name="address")
    city: Field[str] = field()
    postcode: Field[str] = field()

class CustomerTable(Table):
    """One customer record."""

    options = TableOptions(name="customer")
    customer_id: Field[str] = field()
    tags: Field[Array[str]] = field()
    address: Field[AddressStruct] = field()
    previous_addresses: Field[Array[AddressStruct | None]] = field()
```

`StructOptions` is the struct counterpart of `TableOptions`: the same `name` and
`description` metadata, with no row-source meaning. Names default the same way,
so `AddressStruct` becomes `address`.

A source struct is nullable at every step. `address` is a nullable selection, and
`city` is a nullable string even though it is declared `Field[str]`. Access a
member with `extract`, which composes the parent's nullability with the member's
kind:

```python
city = CustomerTable.address.extract(lambda value: value.city)
# NullableSelection[str]: the address may be absent, and a source member is
# nullable in its own right.
```

A nested struct is not itself a graph property; bind its scalar members to
property slots. A `ComputedStruct` is the expression-backed counterpart: a value
record whose members are declared with `computed_field`; see
[projections](projections.md#computed-structs).

## Arrays

`Array[T]` is the portable ordered collection marker. Use it rather than
`list[T]` or a storage type. A field names the array value; access owns whether
the array is present:

| Declaration | Value it names |
| --- | --- |
| `Field[Array[str]]` | a list of non-null strings |
| `Field[Array[str \| None]]` | a list whose items may be null |

Do not write `Field[Array[str] | None]`: an outer `| None` is stripped because
access is nullable either way. The item union stays, because a null item inside
a present list is a different fact.

Arrays expand and transform explicitly. First narrow the nullable selection to a
present `ArraySelection`, then use the array operations:

```python
tags = CustomerTable.tags.alter_rows().drop_null()
tag = tags.alter_rows().expand()

addresses = CustomerTable.previous_addresses.alter_rows().drop_null()
address = addresses.drop_null_items().alter_rows().expand()
city = address.extract(lambda value: value.city)
```

A null array produces no rows when expanded; an empty array also produces no
rows. An array with null items still produces rows, and those items remain
nullable until `drop_null_items()` removes them. The two cases are independent,
which is why the item union is declared. For a graph property,
`drop_null_items()` converts a nullable-item array into the flat scalar array it
accepts.

!!! warning "Nested collections are not graph properties"
    A graph property is a scalar or a flat, homogeneous array of non-null
    scalars. Arrays of structs and nested arrays are expanded into rows and bound
    member by member. `drop_null_items()` is the explicit conversion for arrays
    with null items; there is no implicit coercion.

## Field names and descriptions

The Python attribute and the external field name are related but not identical.
By default the external name is the attribute in snake case. `name=` overrides
it, which is how a handwritten contract reads a differently spelled column:

```python
class PeopleTable(Table):
    """One row per person."""

    options = TableOptions(name="people")
    person_id: Field[str] = field()
    """Stable identifier used by every downstream record."""
    display_name: Field[str] = field(name="name")
    """The name shown in the directory."""
```

Here `display_name` is the attribute and `name` is the field name expressions
and the source see. A documentation string written directly below the
declaration describes the member; an explicit `description=` argument wins.
Descriptions resolve when the class is created, so an inherited member keeps the
description of the class that declared it.

Tables and structs use their class docstring as the declaration description, and
`TableOptions(description=...)` or `StructOptions(description=...)` overrides it.
Write descriptions about meaning, not derivation: "the date the visit happened",
not "the value after the join".

!!! tip "A real member named `options`"
    `options` is reserved for declaration metadata. If the data has a column
    named `options`, declare the attribute as `options_`; one trailing
    underscore is dropped from the inferred external name.

## Table groups

A `TableGroup` names a family of concrete tables and nested groups. It is a
catalog and source-binding convenience, not a shape and not a union type.

```python
from kg_build_system import TableGroup, TableGroupOptions


class ReadingsTableGroup(TableGroup):
    """One relation per logger family."""

    options = TableGroupOptions(name="readings")
    temperature = TemperatureTable
    mechanical = MechanicalTableGroup
```

Group members can be given as class attributes or through
`TableGroupOptions(members=(...))`. Members must be final tables or other
groups; a table may appear only once and catalog paths must be unique.

One source binding can cover the whole family when the layout names each
member:

```python
readings_source = bind_source(
    target=ReadingsTableGroup,
    config=DataSourceConfig(
        str(DATA / "readings"), format=InputFormat.JSON,
        layout="{group_path}/{table_name}.json",
    ),
)
```

The group is not a row source. A binding still targets a concrete table such as
`TemperatureTable`, and the group source resolves that table to its physical
path. See [sources](sources.md) for layouts and partition conventions.

## Generated contracts

`kbs generate` can write these declarations from a source. A request in
`table/__init__.py` produces an owned package beside it:

```text
people_graph/table/
  __init__.py                 # author-owned requests
  people/__init__.py          # generated PeopleTable
```

The generated declaration names each member's value type:

```python
class PeopleTable(Table):
    options = TableOptions(name='people')
    person_id: Field[str] = field(name='person_id')
    name: Field[str] = field(name='name')
    city: Field[str] = field(name='city')
```

CSV and JSON sources do not declare nullability, so the generator records no
presence claim and every member still reads as nullable. Parquet sources can
contribute declared nullability, and a request can state a source guarantee with
`override={"people.city": {"nullable": False}}`; that changes the source-schema
claim recorded in the contract, not how access behaves. Narrow or default the
value in the binding either way.

Generated contracts are ordinary `Table`, `Struct` and `TableGroup` classes and
compile exactly like handwritten ones. They are marked "do not edit": change the
request and regenerate instead. `mode="table_group"` generates a nested group
for a directory of relations, and `override` can declare a type the reader
reports as text, such as a timestamp. The full workflow is on
[Install](../start/install.md).

## Why contracts are typed

Every member's annotation is normalized to a logical type. That single fact
drives everything downstream:

- `Field[str]` reads as a nullable string selection; `Field[int]` as a nullable
  integer selection. Narrow it and the value type decides which operations exist.
- `computed_field` carries its expression's type, including nullability.
- Graph properties have their own declared types. A binding that supplies a
  string to an integer property is rejected before any rows are read.
- Nested structs and array items keep their types through `extract` and
  `alter_rows().expand()`, so a mistake five levels into a JSON document is
  still a type error.
- The same declaration supplies the shape used by expressions and the row source
  used by a binding, so the two cannot drift apart.

That is why an author writes no SQL, no column-mapping dictionary and no separate
schema file. The typed class is the contract; the build derives the rest.

## What to remember

- A `Table` is both the typed shape expressions read and the row source a
  binding consumes.
- `field()` declares source backing; `computed_field(expression)` declares
  expression backing.
- A declaration names the value type. Every source field reads as nullable;
  narrow it with `alter_rows().drop_null()` or `default_to(...)`.
- Array item nullability is declared with `Array[T | None]`; array presence is
  owned by access.
- Structs are shapes only; reach their members with `extract`. A
  `ComputedStruct` is an expression-backed value record, not a row source.
- A graph property is a scalar or a flat array of non-null scalars, never a
  nested structure.

Next: [Types and nullability](types.md) turns these annotations into checked
logical types; for row values see [expressions](expressions.md) and
[projections](projections.md).
