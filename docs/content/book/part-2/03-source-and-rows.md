---
title: "6. Source and rows"
summary: "An asset names where rows come from; a table names their shape, and the source decides which values may be absent."
section: book
perspective: book
part: II
chapter: 6
order: 23
status: normative
verified: 2026-11-11
sources:
  - docs/content/book/part-2/03-source-and-rows.md
  - docs/content/book/part-2/03-source-and-rows.md
  - docs/content/appendix/reference/types.md
  - docs/content/appendix/spec/data.md
---

## A graph starts with rows it did not invent

Every record a build produces is made from a row, and every row comes from a source
outside the graph. Before topology, before bindings, the author answers two
questions that are easy to blur: which source does this data represent, and what
does one row of it look like? The framework splits those questions into two
declarations. An `Asset` names one logical unit of source data. A `Table[Asset]`
names a row shape read from that asset. The asset is the claim about origin; the
table is the claim about shape.

The running example is a monitored estate. One export carries sites, equipment,
surveys and logger readings, stored as several JSON files under one directory. The
author declares one `Estate` asset for the export and one table per relation.
`SitesTable` reads the site relation. The split is not ceremony: the export can
move, the tables stay; a second table can read the same export; and the graph
still records which logical source every row came from.

## An asset is one logical source unit

An `Asset` is a declaration class, not a connector and not a file handle. A
concrete asset subclasses `Asset` and assigns `options = AssetOptions(...)`:

```python
from pathlib import Path

from kg_build_system import (
    Asset, AssetAuthority, AssetLayout, AssetOptions, AssetProfile,
)

DATA = Path(__file__).parent / "data"


class Estate(Asset):
    options = AssetOptions(
        name="estate",
        version="2026-08",
        profile=AssetProfile(
            subject="monitored estate records",
            coverage="sites, equipment, surveys and logger readings",
            authority=AssetAuthority.PRIMARY,
            basis="estate registry and telemetry export",
        ),
        layout=AssetLayout(
            kind="json",
            locator=str(DATA),
            format="json",
            members={
                "sites": "sites.json",
                "equipment": "equipment.json",
                "surveys": "surveys.json",
            },
        ),
    )
```

The asset's name defaults to the class name in snake case, and must be unique
among the graph's assets. `version`, `website` and `annotations` are release
metadata. The required member is `profile`; `layout`, `semantics` and
`governance` are optional.

`AssetProfile` states four things:

| Member | Question it answers |
| --- | --- |
| `subject` | What do the rows describe? |
| `coverage` | Which parts of that subject are present, and which are missing? |
| `authority` | Is this the record, a derivation, a controlled reference or an inference? |
| `basis` | Which release, registry or process produced it? |

`authority` is an `AssetAuthority`: `primary`, `derived`, `reference` or
`inferred`. The value is a decision about trust, not a label. A `primary` asset is
the record itself; a derived asset is computed from another source; a reference
asset is a controlled list used to interpret other rows; an inferred asset is
produced by a process whose result is a claim rather than an observation. The
profile forces that decision into the graph, where a consumer can read it without
reading the loader that produced the file.

The profile is not a schema. It names no columns and no types; the table does
that. It is not a licence; `AssetGovernance` carries a licence, an owner and
frozen metadata, and it is data rather than an execution-time check. It is not a
layout; the layout says where the bytes are. Four questions, four places. Keeping
them apart means a licence change does not edit a column type, and a new storage
location does not edit a profile.

## Layout describes where to look, and proves nothing

`AssetLayout` is optional descriptive metadata: `kind`, `locator`, `format`,
`selector`, `partition_by`, `members` and `properties`. It is not an access
contract. It opens no file, validates no format, and proves no relation exists. A
build either reads the source or fails during execution; the layout does not
certify either outcome.

The default DuckDB source planner treats the layout as a set of hints. For one
relation it resolves `members[relation]` first, then a `selector` formatted with
`{table}` and `{table_path}`, then `locator` alone. It understands `parquet`,
`json` and `csv`. Any other format is another ordinary planner with its own
instruction kind. There is no adapter concept and no adapter registry: adding a
format does not register anything, it adds a planner and an executor that speak a
new exact instruction kind.

Two consequences follow. First, a storage move is a layout edit: changing
`locator` from a local directory to an object-store prefix leaves the table, the
graph and every binding untouched. Second, a layout that happens to match a file
does not make the declaration true. The build still checks the rows it reads,
because the layout cannot promise a column, a type or a relation. `partition_by`
is descriptive for the same reason; the source planner does not use it as a
contract.

`properties` carries descriptive values, including a `credentials` reference. The
reference names where a credential comes from; it is not a secret and not a
licence check. Governance stays data.

## One source unit can back several tables

The estate export backs both `SitesTable` and `EquipmentTable`. Each table names
`Estate` in its declaration, and the relation carries that identity as an
`AssetRef`. This is not inheritance: an asset is terminal, and a concrete asset
does not inherit another concrete asset. The tables are separate because they have
separate row shapes and separate grains.

Provenance follows the identity, not the path. Two relations read from one export
can be traced to the same asset even when their layout members differ, and a
relation read from a second export cannot borrow the first asset's profile. A
consumer that asks "where did this row come from?" gets an answer in the graph,
not in a build script.

A `TableGroup` records the catalog of relations that belong together:

```python
from kg_build_system import TableGroup, TableGroupOptions

from reference_project.table.equipment import EquipmentTable


class EstateTableGroup(TableGroup):
    """Every relation read from the estate export."""

    options = TableGroupOptions(name="estate")
    sites = SitesTable
    equipment = EquipmentTable
```

A table group is not a shape and not a row source; it produces no rows. Its
members are final tables or nested groups, at least one is required, and a cycle
or a duplicate catalog path is refused. The group's job is discovery: an author or
a tool can enumerate the relations belonging to one source without knowing their
module paths. It does not add an asset of its own; every member table names its
own asset, which is why a group cannot quietly mix two sources and call them one.

## A row shape is a class

A table's members are class attributes annotated `Field[T]` and built with
`field()`. A nested record is another declaration class, derived from `Struct`,
used as `Field[SomeStruct]`. The class is the schema. There is no separate mapping
document, no column list in options, and no dictionary that maps names to types:
the class body is the row, and every field is a typed column.

```python
from kg_build_system import Array, Field, Nullable, Struct, Table, TableOptions, field

from reference_project.assets import Estate


class ContactStruct(Struct):
    email: Field[str] = field()
    room: Field[str] = field()


class PremisesStruct(Struct):
    contact_name: Field[str] = field()
    contact: Field[ContactStruct] = field()


class SitesTable(Table[Estate]):
    """One row per monitored site."""

    options = TableOptions(name="sites")
    site_id: Field[str] = field()
    site_name: Field[str] = field()
    premises: Field[PremisesStruct] = field()
    priority_scores: Field[Array[Nullable[int]]] = field()
```

`field()` accepts an external `name`, a `description`, and `annotations`. The
external name defaults to the snake-case attribute with one trailing underscore
removed; the description defaults to the string literal written directly below the
assignment. A table name defaults to the class name with one `Table` suffix removed
and converted to snake case, so `SitesTable` becomes `sites`; `TableOptions(name=...)`
states it explicitly. The name is unique among logical source names, and a table and
a projection share that namespace, so a projection called `sites` would be refused.

`TableOptions` also carries a description, portable annotations and optional
semantics; the class docstring is the default description. None of that becomes a
field or a graph property. The declaration metadata describes the relation, and the
fields describe the row. A reader of the delivered model sees both, kept apart, so a
description change cannot alter the shape and a new field does not rewrite the
relation's identity.

The nested classes are not tables. `PremisesStruct` and `ContactStruct` have no
`row_source()`, cannot be bound, and cannot be table-group members; they describe a
record inside a row. A struct may contain structs and arrays of structs. Its
identity is the `(module, qualname)` pair, so two structs with the same name in
different modules are different types. That identity lets generated source and
hand-written source name the same record without a central registry.

## The type set is small on purpose

A field type is one of eight canonical scalars, `Array[T]`, a declared struct, or a
declared custom scalar.

| Canonical | Author writes | Notes |
| --- | --- | --- |
| `bool` | `bool` | Boolean value and predicate |
| `int` | `int` | Signed 64-bit integer |
| `float` | `float` | Double-precision number |
| `str` | `str` | Text |
| `date` | `Date` | ISO date |
| `time` | `Time` | ISO time |
| `timestamp` | `Timestamp` | ISO date-time with the `T` separator |
| `uuid` | `Uuid` | Lowercase hyphenated text |

`Date`, `Time`, `Timestamp` and `Uuid` are aliases of the corresponding standard
library classes, not subclasses and not second types. `Field[Uuid]` and
`Field[uuid.UUID]` normalize to the same logical type, so one spelling in a
declaration is a style choice rather than a semantic one.

Arrays use the `Array[T]` marker, never `list[T]`, `Sequence[T]` or a storage type.
Items may be scalars, structs or another array. A custom scalar is a class derived
from `CustomDataType`; it is identified by `(module, qualname)`, must be top-level
and importable, and carries no value operations of its own.

The small set is a contract with everything downstream. One logical type has to
survive the row source, the workflow plan, the engine and the binding target. A
type that cannot cross that boundary is not an authoring type. This is why `Any` is
refused, why `list[T]`, `dict[K, V]` and tuples are refused, why a union of two
non-null types is refused, and why a `Table` or `Projection` cannot be a field
type: a relation is not a value record, and it is read with `row_source()`.

Nested item absence is a different question from owner absence.
`Field[Array[Nullable[int]]]` is legal: the array's items may be null, which is a
fact about the value. `Field[str | None]` is a static type error: a field declares
a value type, and the owner declares presence. The next section is about that
owner.

## The source owns absence

Read `SitesTable.site_name` and the type is `Selection[Nullable[str]]`, even though
the declaration writes `Field[str]`. The source may omit a column, a JSON member
may be absent, and a row may hold no value. The annotation says what the value is
when it exists. Presence belongs to the owner that supplies the value, and for a
source table that owner is the source.

A source struct member is always nullable because the source may omit it, and a
nullable carrier makes every member nullable. `SitesTable.priority_scores` reads as
`Selection[Nullable[Array[Nullable[int]]]]`: the array may be absent, and its items
may be null. Two independent questions, two independent answers. A nullable owner
inside a field type is refused: `Field[Nullable[str]]` is not a way to write "may
be absent"; it is a second schema that drifts from the source. Absence is
flattened, so a nullable of a nullable is simply nullable.

The rule matters most for generated source. A declaration package generated from
an observed file writes every field as `Field[T]`. Observation is provenance: a
profile, a manifest, statistics and notes may record that a column had no nulls in
the release that was read, but the declaration never adds `| None`, because the
next release may. Access follows the owner instead: every source read is nullable,
and the consumer narrows or defaults it at the point where absence means
something.

A source field's declared name and logical type are the contract. Nullability is
not part of the declaration, but it is part of the read, and a build never assumes
otherwise just because one file happened to be complete.

## A final table ends the declaration line

`Table` is final. A concrete table may not inherit another final table, because a
second inheritance path would make "which asset does this row come from?" depend on
class order. Reuse across tables goes through a `StructTemplate`, which shares
field slots and annotations, not through one table inheriting another. `Struct` and
`ComputedStruct` are composable value records and carry no such guard.

A template is a mixin whose options carry annotations only: it has no name, no
description and no place in the delivered model. It shares field slots with a
`Table`, `Struct` or `ComputedStruct` host and comes first in the base list. It
cannot be mixed into a `Projection` or a `TableGroup`, because neither host extends
a source row shape. The distinction is narrow but useful: a template shares the
fields an author writes, not the identity of the relation that owns them.

Three refusals protect the declaration:

- A concrete table with no asset parameter is refused: the row shape and its
  source are one declaration.
- A table parameter that is not an `Asset` subclass is refused.
- A table that declares a source field with `computed_field()`, or a projection
  output with `field()`, is refused; the host decides which constructor is legal.

`Table` is also not a value type. `Field[SomeTable]` and `Field[SomeProjection]`
are refused. A relation that a row needs becomes a nested struct, a lookup, or a
separate binding, never a column whose value is a whole relation.

## What the row contract hands to the rest of the book

The asset states origin and profile; the layout describes where to look and proves
nothing; one asset can back several tables; the table states a row shape in a small
canonical type set; nested records are structs; every source read is nullable
because the source owns presence; a table group catalogs the relations without
producing rows.

A consumer can rely on four things: relation identity, asset provenance, field
names and logical types, and the knowledge that a value may be absent until the
author decides otherwise. None of those depend on the storage format, the file
layout or the order in which declarations are imported.

The next chapter takes the value a field read returns, shows how to compute with
it, and explains how an author answers absence without hiding the decision.

## Next

[7. Values and nullability](/book/part-2/04-values-and-nullability) — from a nullable read to a typed value with an explicit decision.
