---
title: "6. Source and rows"
summary: "An asset names where rows come from; a source relation states their grain, identity and meaning; a field states what one value is."
section: book
perspective: book
part: II
chapter: 6
order: 23
status: normative
verified: 2026-11-15
sources:
  - docs/content/appendix/reference/types.md
  - docs/content/appendix/spec/data.md
---

## A graph starts with rows it did not invent

Every record a build produces is made from a row, and every row comes from a source
outside the graph. Before topology, before bindings, the author answers two
questions that are easy to blur: which source does this data represent, and what
does one row of it look like? The framework splits those questions into two
declarations. An `Asset` names one logical unit of source data. A
`SourceRelation[Asset]` names a row shape read from that asset and states its
contract. The asset is the claim about origin; the relation is the claim about
shape and meaning.

The running example is a monitored estate. One export carries sites, equipment,
surveys and logger readings, stored as several JSON files under one directory. The
author declares one `Estate` asset for the export and one source relation per
member file. `SitesSourceRelation` reads the site relation. The split is not ceremony: the
export can move, the relations stay; a second relation can read the same export;
and the graph still records which logical source every row came from.

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
                "readings": "readings.json",
            },
        ),
    )
```

The asset's name defaults to the class name in snake case, and must be unique
among the graph's assets. `version`, `website` and `annotations` are release
metadata. The required member is `profile`; `layout`, `meaning` and
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

The profile is not a schema. It names no columns and no types; the source relation
does that. It is not a licence; `AssetGovernance` carries a licence, an owner and
frozen metadata, and it is data rather than an execution-time check. It is not a
layout; the layout says where the bytes are. Four questions, four places. Keeping
them apart means a licence change does not edit a field definition, and a new
storage location does not edit a profile.

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
`locator` from a local directory to an object-store prefix leaves the relation, the
graph and every binding untouched. Second, a layout that happens to match a file
does not make the declaration true. The build still checks the rows it reads,
because the layout cannot promise a column, a type or a relation. `partition_by`
is descriptive for the same reason; the source planner does not use it as a
contract.

`properties` carries descriptive values, including a `credentials` reference. The
reference names where a credential comes from; it is not a secret and not a
licence check. Governance stays data.

## One source unit can back several relations

The estate export backs both `SitesSourceRelation` and `EquipmentSourceRelation`. Each relation
names `Estate` in its declaration, and the relation carries that identity as an
`AssetRef`. This is not inheritance: an asset is terminal, and a concrete asset
does not inherit another concrete asset. The relations are separate because they
have separate row shapes, contracts and grains.

Provenance follows the identity, not the path. Two relations read from one export
can be traced to the same asset even when their layout members differ, and a
relation read from a second export cannot borrow the first asset's profile. A
consumer that asks "where did this row come from?" gets an answer in the graph,
not in a build script.

A `SourceRelationGroup` records the catalog of relations that belong together:

```python
from kg_build_system import SourceRelationGroup, SourceRelationGroupOptions

from reference_project.relation.source.estate.equipment import EquipmentSourceRelation
from reference_project.relation.source.estate.sites import SitesSourceRelation


class EstateRelationGroup(SourceRelationGroup):
    """Every relation read from the estate export."""

    options = SourceRelationGroupOptions(name="estate")
    sites = SitesSourceRelation
    equipment = EquipmentSourceRelation
```

A source relation group is not a shape and not a row source; it produces no rows.
Its members are final source relations or nested groups, at least one is required,
and a cycle or a duplicate catalog path is refused. The group's job is discovery:
an author or a tool can enumerate the relations belonging to one source without
knowing their module paths. It does not add an asset of its own; every member
relation names its own asset, which is why a group cannot quietly mix two sources
and call them one.

## A relation is a contract

A source relation is not just a column list. It is a contract with two parts, and
both are stated on the declaration:

```text
Contract
  definition: grain, identity
  meaning: purpose, claims, limitations
```

The `Definition` answers the structural question: what is one row, and what
distinguishes one row from another? The `Meaning` answers the domain question: what
is this relation for, what does it assert, and what does it exclude? A relation with
a row shape and no contract is a file description; a relation with a contract is a
published object another declaration can rely on. The contract is complete or it is
absent: a definition without a meaning, or a meaning without a definition, is not a
contract this framework publishes.

```python
from kg_build_system import (
    Claim, Contract, Definition, Field, Limitation, Meaning, Purpose,
    SourceRelation, SourceRelationOptions, field,
)

from reference_project.asset.estate import Estate


class SitesSourceRelation(SourceRelation[Estate]):
    """One row per monitored site."""

    options = SourceRelationOptions(
        name="sites",
        contract=Contract(
            definition=Definition(
                grain="One row per monitored site.",
                identity=("site_id",),
            ),
            meaning=Meaning(
                purpose=Purpose(
                    text=(
                        "Use this relation as the estate's published "
                        "site register."
                    ),
                    limitations=(
                        Limitation(
                            "Sites added after the release are absent."
                        ),
                    ),
                ),
                claims=(
                    Claim(
                        "A site row carries the site's name, premises "
                        "and priority scores."
                    ),
                ),
            ),
        ),
    )

    site_id: Field[str] = field()
    site_name: Field[str] = field()
    # The premises block and the priority scores are declared with the row
    # shape below.
```

The grain is a sentence about one row: "One row per monitored site." It is not an
operator description. If the declaration needed "after unnesting the scores" to
state its grain, the unnesting happened in the wrong place; a relation states what
one row is, and the row source states how the rows were produced.

The identity names the field or field tuple whose value distinguishes one row. The
language resolves that name to a `FieldRef` in the model, so a consumer reads a
reference rather than a string. A relation with no identity cannot be bound:
without it there is nothing for a build key to satisfy. A composite identity is a
tuple, and its order is part of the statement.

The meaning is the same unit vocabulary as everywhere else: an optional purpose,
contextless claims, and the limitations that purpose owns. A source relation may
state claims only. It describes what the source holds, and the use is chosen by
whoever binds it, so requiring a purpose would force the author to invent one. A
derived relation must state a purpose, because it exists only because some use
asked for that grain; chapter 8 states that rule. The meaning is a domain
statement either way, not a fragment under the graph purpose. "Use this relation
as the estate's published site register" says what the relation is for in the
domain; it does not repeat "estate asset management", and it does not depend on a
graph declaration existing. Chapter 4 states why the two axes are separate, and
chapter 11 states how a binding joins them.

The contract is also where the relation is kept record-agnostic. A published
relation states a grain, an identity and a domain meaning; it must not name a
node, an edge, a record property, a build key or an endpoint. If it does, the
record was designed on the relation side, and the binding can only copy it.

A source relation may be read by several bindings and by several derived relations.
The contract is what they share: the name, the grain, the identity and the
meaning. Changing a row shape under a stable contract is a contract change, not a
private refactor.

## A field definition states what the value is

A relation contract describes the row. A `FieldDefinition` describes one value in
it:

```python
from kg_build_system import Field, FieldDefinition, SourceRelation, field

from reference_project.asset.estate import Estate


class SitesSourceRelation(SourceRelation[Estate]):
    site_id: Field[str] = field(
        definition=FieldDefinition(
            value="The estate registry's stable site identifier.",
            null_meaning="The row does not identify a site.",
        ),
    )
    site_name: Field[str] = field(
        definition=FieldDefinition(
            value="The site's display name.",
            null_meaning="The register records no name for the site.",
        ),
    )
    # The premises block and the priority scores follow the same pattern.
```

`FieldDefinition` has three members, and each answers a question the type cannot:

| Member | Question it answers |
| --- | --- |
| `value` | What is this value in the domain? |
| `unit` | In which unit is it measured? |
| `null_meaning` | What does absence of the value denote? |

`unit` is stated only for a measured value: a logger reading is in kilowatt hours,
a survey score is in priority points, an identifier and a flag have no unit. The
unit is not a formatting hint. It is what makes two numeric fields comparable, and
what stops a consumer from adding a reading in one unit to a reading in another.

`null_meaning` is a domain statement, not a type. Source access is nullable
whatever the file contains, so the read type cannot say whether absence means "not
surveyed", "surveyed and found none" or "the export of this release omitted the
member". The field definition is where the author says which, and the binding's
meaning is where the consequence for the record is stated.

A field definition does not restate the source name, the logical type or the
storage path. The declaration already carries the name and the type, and the asset
already carries the source. Repeating them would create a second schema that drifts
from the first: a field renamed in the class but not in the definition, or a type
widened in one place and not the other. The definition states only what the other
declarations cannot.

The definition is a commitment, not a description. A binding whose build key reads a
field must satisfy the relation's identity; a consumer that compares two measured
values reads their units; a reader of an absent value reads the null meaning beside
the property that carries it. Meaning states what the author asserts; definition
states the structure the build and the consumer act on.

## A row shape is a class

A source relation's members are class attributes annotated `Field[T]` and built
with `field()`. A nested record is another declaration class, derived from
`Struct`, used as `Field[SomeStruct]`. The class is the schema. There is no
separate mapping document, no column list in options, and no dictionary that maps
names to types: the class body is the row, and every field is a typed column.

```python
from kg_build_system import (
    Array, Field, Nullable, SourceRelation, SourceRelationOptions, Struct,
    field,
)

from reference_project.asset.estate import Estate


class ContactStruct(Struct):
    email: Field[str] = field()
    room: Field[str] = field()


class PremisesStruct(Struct):
    contact_name: Field[str] = field()
    contact: Field[ContactStruct] = field()


class SitesSourceRelation(SourceRelation[Estate]):
    """One row per monitored site."""

    options = SourceRelationOptions(name="sites")
    site_id: Field[str] = field()
    site_name: Field[str] = field()
    premises: Field[PremisesStruct] = field()
    priority_scores: Field[Array[Nullable[int]]] = field()
```

`field()` accepts an external `name`, a `description`, `annotations`, a `meaning`
and a `definition`. The external name defaults to the snake-case attribute with
one trailing underscore removed; the description defaults to the string literal
written directly below the assignment. A relation name defaults to the class name
with one `Relation` suffix removed and converted to snake case, so `SitesSourceRelation`
becomes `sites`; `SourceRelationOptions(name=...)` states it explicitly. The name
is unique among logical source names, and a source relation and a derived relation
share that namespace, so a derived relation called `sites` would be refused.

`SourceRelationOptions` also carries a description and portable annotations; the
class docstring is the default description. None of that becomes a field or a graph
property. The declaration metadata describes the relation, and the fields describe
the row. A reader of the delivered model sees both, kept apart, so a description
change cannot alter the shape and a new field does not rewrite the contract.

The nested classes are not relations. `PremisesStruct` and `ContactStruct` have no
`row_source()`, cannot be bound, and cannot be source-group members; they describe
a record inside a row. A struct may contain structs and arrays of structs. Its
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
non-null types is refused, and why a `SourceRelation` or a `DerivedRelation` cannot
be a field type: a relation is not a value record, and it is read with
`row_source()`.

Nested item absence is a different question from owner absence.
`Field[Array[Nullable[int]]]` is legal: the array's items may be null, which is a
fact about the value. `Field[str | None]` is a static type error: a field declares
a value type, and the owner declares presence. The next section is about that
owner.

## The source owns absence

Read `SitesSourceRelation.site_name` and the type is `Selection[Nullable[str]]`, even
though the declaration writes `Field[str]`. The source may omit a column, a JSON
member may be absent, and a row may hold no value. The annotation says what the
value is when it exists. Presence belongs to the owner that supplies the value, and
for a source relation that owner is the source.

A source struct member is always nullable because the source may omit it, and a
nullable carrier makes every member nullable. `SitesSourceRelation.priority_scores` reads
as `Selection[Nullable[Array[Nullable[int]]]]`: the array may be absent, and its
items may be null. Two independent questions, two independent answers. A nullable
owner inside a field type is refused: `Field[Nullable[str]]` is not a way to write
"may be absent"; it is a second schema that drifts from the source. Absence is
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
otherwise just because one file happened to be complete. The field definition's
`null_meaning` is where the domain consequence of absence is written.

## A final source relation ends the declaration line

`SourceRelation` is final. A concrete source relation may not inherit another final
source relation, because a second inheritance path would make "which asset does
this row come from?" depend on class order. Reuse across relations goes through a
`StructTemplate`, which shares field slots and annotations, not through one
relation inheriting another. `Struct` and `ComputedStruct` are composable value
records and carry no such guard.

A template is a mixin whose options carry annotations only: it has no name, no
description and no place in the delivered model. It shares field slots with a
`SourceRelation`, `Struct` or `ComputedStruct` host and comes first in the base
list. It cannot be mixed into a `DerivedRelation` or a `SourceRelationGroup`,
because neither host extends a source row shape. The distinction is narrow but
useful: a template shares the fields an author writes, not the identity of the
relation that owns them.

Three refusals protect the declaration:

- A concrete source relation with no asset parameter is refused: the row shape and
  its source are one declaration.
- A relation parameter that is not an `Asset` subclass is refused.
- A source relation that declares a field with `computed_field()`, or a derived
  relation output with `field()`, is refused; the host decides which constructor is
  legal.

`SourceRelation` is also not a value type. `Field[SomeSourceRelation]` and
`Field[SomeDerivedRelation]` are refused. A relation that a row needs becomes a
nested struct, a lookup, or a separate binding, never a column whose value is a
whole relation.

## What the row contract hands to the rest of the book

The asset states origin and profile; the layout describes where to look and proves
nothing; one asset can back several relations; the source relation states a
contract of grain, identity and domain meaning; a field definition states what a
value is, in which unit, and what absence denotes; the class body states the row
shape in a small canonical type set; nested records are structs; every source read
is nullable because the source owns presence; a relation group catalogs the
relations without producing rows.

A consumer can rely on five things: relation identity, asset provenance, field
names and logical types, the contract's grain and meaning, and the knowledge that a
value may be absent until the author decides otherwise. None of those depend on the
storage format, the file layout or the order in which declarations are imported.

The next chapter takes the value a field read returns, shows how to compute with
it, and explains how an author answers absence without hiding the decision.

## Next

[7. Values and nullability](/book/part-2/04-values-and-nullability) — from a nullable read to a typed value with an explicit decision.
