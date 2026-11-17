---
title: "8. Derived relations"
summary: "A row source makes one row a value; a filter, join, group or expansion derives a grain, and a derived relation publishes its contract."
section: book
perspective: book
part: II
chapter: 8
order: 25
status: normative
verified: 2026-11-15
sources:
  - docs/content/appendix/reference/row-sources.md
  - docs/content/appendix/spec/grain.md
---

## One row is a decision before it is a query

A binding produces one record per row. That sentence hides the question this
chapter answers: one row of what? A source relation has a grain. `SitesSourceRelation` is
one row per site. A filter keeps that grain and removes rows. A join combines two
grains. A group collapses rows to one per key. An expansion turns one row into
several. A derived relation states the result as a contract, and the binding
inherits the meaning instead of inventing it.

A row source is a value with a shape and a plan. `SitesSourceRelation.row_source()`
returns a `RelationRowSource` over exactly one relation; every derived operation
returns a `DerivedRowSource`. Neither is a declaration class. A binding later takes
the value, never `SitesSourceRelation` itself, and a `Struct` is never a row source at
all.

```python
sites = SitesSourceRelation.row_source()
```

The shape is the answer to "what is in one row?"; the plan is the answer to "which
rows, and how were they produced?". Both travel together. Because the value is
frozen, an operation never edits the source it was given; it returns a new value
that names the old one as its input. That is what lets a derived relation pin one
plan and let several bindings read the same meaning.

A row source can be built and inspected before a target exists. That is the
practical advantage of making the grain a value: the plan is available to the
compiler and the shape is available to the type checker, without a database
connection and without writing a record. A grain can therefore be reviewed and
tested as a declaration, before the binding that consumes it is written.

## Filtering keeps the grain and discards rows

`where(predicate)` takes a callable that receives a typed row proxy and returns a
`Selection[bool]`. It keeps the rows whose predicate is true and preserves the
shape:

```python
depots = SitesSourceRelation.row_source().where(
    lambda site: site.site_name.alter_rows().drop_null().equals("Depot")
)
```

The predicate is a callable over a typed row, not a Python expression on a column.
It must return a `Selection[bool]`; a non-callable or a selection of another type
is refused. A source field reads as nullable, so narrow or default it before
comparing. A null predicate is not true, so its row is dropped. That last rule is
worth stating plainly: a filter never keeps a row whose predicate is unknown.

`where` does not rename, reorder or retype a member. If a later operation needs a
member that the source declares, the filtered row still has it.

## A join combines two grains on one scalar key

`join(other, *, on, how="inner")` combines two row sources on one equality. `on`
receives one row proxy per side and returns either a pair of scalar selections or
a single `equals` selection. The pair form is the general one:

```python
site_units = SitesSourceRelation.row_source().join(
    EquipmentSourceRelation.row_source(),
    on=lambda site, unit: (site.site_id, unit.site_id),
    how="left",
)
```

Join keys must be scalar, and they must resolve to the same base logical type;
their nullability may differ. Arrays and structs are refused. `how` is `inner`,
`left`, `right` or `full`, and it names which side may be unmatched. A null key
never matches in any mode, including an outer join: the unmatched row survives
because of the join mode, not because null equals null.

The result has a generated shape of `{on, left, right}`. `on` is the shared key.
`left` and `right` are record mirrors of the two input rows, and the missing side
is nullable for the join modes that can leave it out. Read them through `.shape`:

```python
site_name = site_units.shape.left.extract(lambda site: site.site_name)
unit_ref = site_units.shape.right.extract(lambda unit: unit.unit_ref)
```

For the left join above, a site with no equipment still has one row: the site side
is present, the unit side is null. A unit with no matching site is absent
entirely, because the left side drives the result. That is the grain: one row per
site-and-unit pair, plus one row for each unmatched site. If the intent is one row
per site, this join is the wrong grain, and no later `distinct` repairs it.

The generated shape is not a flattened set of columns. It keeps two record mirrors,
so two members with the same external name cannot collide: the site's `site_id` and
the unit's `site_id` live behind `.shape.left` and `.shape.right`. The cost is that
every read goes through `extract`, and the benefit is that an ambiguous reference
is impossible to write.

The `equals` form is text-only and needs present values on both sides. Defaulting
a key before comparing makes null keys compare equal, which is a deliberate
collapse of two different rows. The pair form never does that. Default a join key
only when a shared fallback identity is the intended model; otherwise narrow the
key or accept that a null key produces no match.

A join may consume another join or a grouped source, and the generated records
nest. Reading a nested shape is still `extract`; nothing about the nesting changes
the rule that a row has one grain.

## Grouping collects rows; it does not compute

`group_by(keys=..., by=...)` produces one row per key tuple. `keys` declares the
present key shape; `by` may return one key selection, a mapping of names to
selections, or `(name, selection)` pairs. Key names must be public Python
identifiers, unique within the group, and exactly the members of `keys`; keys
must be scalar:

```python
from kg_build_system import Selection, Shape


class SiteKey(Shape):
    site_id: Selection[str]


by_site = EquipmentSourceRelation.row_source().group_by(
    keys=SiteKey,
    by=lambda unit: {"site_id": unit.site_id},
)
site_id = by_site.shape.by.extract(lambda key: key.site_id)  # Selection[str]
members = by_site.shape.members                                # Selection[Array[EquipmentSourceRelation]]
```

Rows whose key tuple contains a null are dropped before grouping, so every
generated `by` member is present. The shape is `GroupedShape[S, K]`, with
`{by, members}`. `members` is a present array of record mirrors of the input row;
its order is unspecified.

The key record and the member array are the whole row. A group is not an input row
with extra columns, and it is not a count with a label. The key is a record of the
named scalar expressions; the members are the rows that share it. That shape is
why a group is useful for carrying a relationship forward and useless as a
substitute for an aggregate.

Grouping collects; it does not aggregate. There is no count, sum, minimum, maximum
or `having`. A grouped source answers "which rows share this key?", not "how many
are there?" or "what is their total?". If the graph needs a count or a total, that
is a separate operation over the collected members, not an option on `group_by`.
The absence is a boundary, not an omission: the row-source algebra is relational,
and aggregation belongs to a later module that consumes the grouped rows.

The grain matters for the binding that follows. A binding over a grouped source
emits one record per group, not one per input row. A group that looks like a
convenient way to collect equipment has already changed what one record means.
When the members are carried further, they are read like any array:

```python
unit_refs = members.transform_items(
    lambda member: member.extract(lambda unit: unit.unit_ref)
).drop_null_items()
```

`transform_items` applies one selection to every item without changing the row
count; `drop_null_items()` removes the null references so the array can become a
graph property later.

## Union and distinct answer the duplicate question

`union(other, all=True)` stacks two same-shaped row sources. The shapes are
compared member by member: external name and full logical type, including
nullability. A union never renames, casts or reorders members. `all=False` removes
duplicate rows; `all=True` keeps them.

```python
from kg_build_system import (
    Field, Omitted, SourceRelation, SourceRelationOptions, field,
)

from reference_project.asset.estate import Estate
from reference_project.relation.source.estate.equipment import EquipmentSourceRelation


class ArchivedEquipmentSourceRelation(SourceRelation[Estate]):
    """The retired units, declared with the equipment row shape."""

    # The contract is omitted here; the example is about the union shape.
    options = SourceRelationOptions(name="archived_equipment", contract=Omitted)
    unit_ref: Field[str] = field(meaning=Omitted)
    unit_name: Field[str] = field(meaning=Omitted)
    site_id: Field[str] = field(meaning=Omitted)
    in_service: Field[bool] = field(meaning=Omitted)
    survey_period: Field[str] = field(meaning=Omitted)


every_unit = EquipmentSourceRelation.row_source().union(
    ArchivedEquipmentSourceRelation.row_source(),
)
deduplicated = every_unit.distinct()
```

`distinct()` removes duplicate rows without changing the shape. It is the explicit
way to ask for a set of rows; `union(..., all=False)` asks for the same thing at
the seam between two inputs.

A union is row-wise, not column-wise. It does not align members by name at query
time; it requires the declarations to agree before either side is read. A union is
not a source relation group. A group is a catalog of relations and produces no
rows; a union produces rows and requires both sides to have one shape. The two
declarations can name different assets and still union, provided their row shapes
agree. The result does not merge the assets; it stacks the rows.

`order_by(*keys, ascending=True)` orders rows without changing the grain. A key
names a member of the row source, and one direction applies to every key.

```python
ordered = deduplicated.order_by("unit_ref", ascending=True)
```

Order is not identity. It is observable only through a later ordering or a
materialised relation, and it never makes two rows distinct. Use `distinct()` for
duplicates and `order_by` for presentation or a deterministic export, not as a
substitute for either.

## Unnest changes the grain to one row per item

`unnest(selector, out=...)` reads one direct array field and produces one row per
item. It keeps every other field and narrows the selected member to the item.
The output shape is declared because one named member changes type:

```python
from kg_build_system import (
    Array, Field, Nullable, Omitted, Selection, Shape, SourceRelation, field,
)


class SiteScores(SourceRelation[Estate]):
    site_id: Field[str] = field(meaning=Omitted)
    scores: Field[Array[int]] = field(meaning=Omitted)


class ScoredSite(Shape):
    site_id: Selection[Nullable[str]]
    scores: Selection[int]


scored_sites = SiteScores.row_source().unnest(
    lambda site: site.scores,
    out=ScoredSite,
)
score = scored_sites.shape.scores  # Selection[int]
```

A null or empty array produces no rows. The selector must read a declared field,
not a computed expression; `unnest` is a relation-level operation and needs a
member of the input shape. The runtime validates `out` against every generated
member, external name and logical type.

This is a grain decision, not a formatting choice. Before the expansion, one row
is one site and the scores are an array. After it, one row is one site-and-score
pair, and a site with no scores disappears. If the graph wants one node per site
carrying its scores as a property, the array is the right shape and `unnest` is
the wrong operation.

`Selection.expand` is the value-level spelling of the same fan-out inside a
product. Use one or the other for a given expansion, never both. Expanding two
arrays in one plan produces the product of the two fan-outs, not a paired row;
pairing is `zip`, and a keyed match is a join.

## A derived relation publishes a contract

A derived relation is a relation first. Its row plan is how the relation is
computed, not what it is. State the relation in one sentence with no graph nouns
and no operator verbs: “one condition severity per defect” is a relation; “join
defects to conditions and drop nulls” is an operator. The second is a derived row
source, not a derived relation.

A row source is a value; a derived relation turns it into a published relation. It
pins exactly one row source at class creation, publishes typed outputs with
`computed_field`, and becomes a row-source provider itself:

```python
from kg_build_system import (
    Claim, Contract, Definition, DerivedRelation, DerivedRelationOptions,
    FieldDefinition, Limitation, Meaning, Omitted, Purpose, computed_field,
)

ordered_units = site_units.order_by("on", ascending=True)


class SiteUnitRelation(DerivedRelation(ordered_units)):
    """One row per site and unit, with the site name and unit reference."""

    options = DerivedRelationOptions(
        name="site_unit",
        contract=Contract(
            definition=Definition(
                grain="One row per site and unit pair.",
                identity=("site_id", "unit_ref"),
            ),
            meaning=Meaning(
                purpose=Purpose(
                    text="Use this relation as the site-to-unit register.",
                    limitations=(
                        Limitation(
                            "Sites with no installed unit are absent."
                        ),
                    ),
                ),
                claims=(
                    Claim(
                        "A row carries the site name and the unit "
                        "reference for one installed unit."
                    ),
                ),
            ),
        ),
    )

    site_id = computed_field(
        ordered_units.shape.left.extract(lambda site: site.site_id)
        .alter_rows().drop_null(),
        definition=FieldDefinition(
            value="The estate registry's site identifier.",
        ),
        meaning=Omitted,
    )
    site_name = computed_field(
        ordered_units.shape.left.extract(lambda site: site.site_name),
        definition=FieldDefinition(
            value="The site's display name.",
            null_meaning="The register records no name for the site.",
        ),
        meaning=Omitted,
    )
    unit_ref = computed_field(
        ordered_units.shape.right.extract(lambda unit: unit.unit_ref)
        .alter_rows().drop_null(),
        definition=FieldDefinition(
            value="The unit reference assigned by the equipment register.",
        ),
        meaning=Omitted,
    )
    in_service = computed_field(
        ordered_units.shape.right.extract(lambda unit: unit.in_service),
        definition=FieldDefinition(
            value="Whether the unit is in service.",
            null_meaning="The register records no service state for the unit.",
        ),
        meaning=Omitted,
    )
```

There is no unpinned derived relation. `DerivedRelation()` and
`class R(DerivedRelation)` are refused, and a derived relation with no
`computed_field` is refused. `field()` is not legal for an output: a derived
relation has no source columns of its own. The output is typed by its selection,
so a present selection publishes a present output and a nullable selection
publishes a nullable one.

The contract is the same two-part value the source relation states. The grain and
identity are structural: a binding checks its key against the identity, and its
record count against the grain. The meaning states the domain purpose, the claims
and the limitations, and it is not a fragment under the graph purpose. A derived
relation requires a purpose, not merely claims: it exists because a use asked for
that grain, and that use is its purpose. A source relation may state claims only,
because the source does not choose its consumers. A derived relation that several
records read states one shared domain meaning; the binding that follows states
which record purpose it fulfils.

An output is read as a materialised value. `SiteUnitRelation.site_id` elsewhere is
the output of the published relation, not the selection that produced it. That is
what makes a derived relation a contract rather than a macro: the expression is
private to the declaration, and a reader depends on the name, the type, the grain
and the meaning.

Every output shares the one pinned row plan. A filter or an expansion written for
one output changes the grain for every output and for every binding that reads the
relation. That is why the expansion belongs in the row source, the stage or the
derived relation, not in a single output that happens to need it. Two unrelated
arrays expanded in one relation multiply the fan-outs; a second grain needs a
second derived relation.

A derived relation cannot introduce a second driving source. All outputs read the
pinned plan, possibly through chained expansions and struct navigation. A second
relation is read with `lookup`, which states the key and leaves the grain choice to
the author. Derived-relation dependencies are ordered before their dependants and
must be acyclic.

The name is part of the contract. It defaults to the class name with one
`Relation` suffix removed and converted to snake case, and
`DerivedRelationOptions` states it explicitly. A derived relation name must be
unique among derived relations and among source relations, because both are logical
source names in one namespace. A collision is refused rather than resolved by
import order.

A derived relation is final: it may not inherit another final derived relation.
Pin a new source instead.

Publish a derived relation when the relation is reused or deserves a contract. A
bare row source is fine when one binding reads a filtered relation and nothing else
needs the name. A derived relation earns its place when several consumers must
agree on what the relation means, or when a derived grain is easier to review as a
declaration than as an expression inside another declaration.

## A stage is a private sub-relation

A single derivation sometimes needs an intermediate shape: a join, then an
expansion, then a selection of outputs. That intermediate is a `Stage`. It is a
real declaration with a grain and typed outputs, and it is not a published
relation.

```python
from kg_build_system import (
    Contract, Definition, DerivedRelation, DerivedRelationOptions,
    FieldDefinition, Meaning, Omitted, Purpose, Stage, StageOptions,
    computed_field,
)


class SiteScoreStage(Stage(scored_sites)):
    """One row per site and priority score."""

    options = StageOptions(
        name="site_score_stage",
        definition=Definition(
            grain="One row per site and priority score.",
            identity=("site_id", "score"),
        ),
    )

    site_id = computed_field(scored_sites.shape.site_id, meaning=Omitted)
    score = computed_field(scored_sites.shape.priority_scores, meaning=Omitted)


site_score_rows = SiteScoreStage.row_source()


class SiteScoreRelation(DerivedRelation(site_score_rows)):
    options = DerivedRelationOptions(
        name="site_score",
        contract=Contract(
            definition=Definition(
                grain="One row per site and priority score.",
                identity=("site_id", "priority_score"),
            ),
            meaning=Meaning(
                purpose=Purpose(
                    text="Use this relation to compare sites by priority score.",
                ),
            ),
        ),
    )

    site_id = computed_field(site_score_rows.shape.site_id, meaning=Omitted)
    priority_score = computed_field(
        site_score_rows.shape.score,
        name="priority_score",
        definition=FieldDefinition(
            value="The priority score recorded for the site.",
            unit="priority point",
        ),
        meaning=Omitted,
    )
```

A stage states a `Definition` and no meaning. That is the whole difference. It has
a grain and an identity because the next stage or the published relation needs to
know what one row is; it has no purpose, no claims and no limitations because
nobody outside its package is offered it. It is recorded in
`data.derived_relations` with `visibility="internal"` as plan lineage, not as a
consumer relation: its outputs are not addressable through a `FieldRef` from
another package, `lookup` cannot target it, and a binding cannot read it.

The package is the boundary. A derived relation is one package under
`relation/derived/`: `relation.py` holds the published declaration and
`_stage_*.py` holds its stages, one per file. Nothing outside the package imports a
stage module, and the published relation is the only name a consumer sees. The
stage's name is a plan handle: it appears in the blueprint as internal lineage,
never as a consumer relation, and its module is private under the same rule. Name
it for what it computes, and let the type and the visibility — not an underscore —
say that it is not a contract.

The rule is not a style preference. If an intermediate shape needs a consumer, a
purpose or a claim, it is a derived relation and it gets its own package. If it
only exists because one derivation is easier to read in three steps, it is a stage.
Promoting a stage to a published relation is a real change: it needs a name in the
shared namespace, a contract and a consumer that makes it reachable.

## A published relation must not know the record

A published relation — source or derived — may contain as much domain processing as
it needs. What it must not contain is the record's contract.

- It must be stateable without the record.
- It must not name the record's property names, build key, endpoint tokens, node
  or edge class.
- If it does, the relation is the record in disguise. The binding is then a
  copy, not a fulfilment.

The test has two sides:

1. **Relation:** can I state this relation without naming the record, its
   properties, its key or its endpoints?
2. **Binding:** what does this relation not guarantee for the record — identity,
   coverage, property selection, null meaning, endpoint resolution?

A simple binding is allowed when the relation genuinely has the record's grain
and the source is the relation. A vacuous binding is not: if the relation already
chose the record's grain, key and properties, the design happened on the wrong
axis. Move the record knowledge back to topology and the binding; do not add more
processing to the relation.

| Shape | Reading |
| --- | --- |
| `TargetNodeData`: one row per target, fields id/symbol/name/biotype, purpose “the data for TargetNode” | The node's relation with a name. The binding copies. |
| `TargetAnnotation`: one gene-annotation record per Ensembl gene, with symbol, name, biotype and the release's source | A domain relation. The binding resolves the key, selects the fields the node asserts, and states the coverage and gaps. |

## The grain is a decision, not an accident

Each operation answers the same question differently:

| Operation | What one row means afterwards |
| --- | --- |
| `where` | The input grain, with fewer rows |
| `join` | One row per matching pair, plus unmatched rows the mode keeps |
| `group_by` | One row per key tuple, with the members collected |
| `union` | The input grain, stacked across two same-shaped sources |
| `distinct` | The input grain, with duplicate rows removed |
| `order_by` | The input grain, ordered |
| `unnest` | One row per array item, with the other fields preserved |

Double-counted and missing records are almost always grain errors, not expression
errors. A join that multiplies rows, a group read as if it were the input, or an
expansion used to flatten a nested document all change the meaning of one record.
The row-source value makes that meaning visible before a binding is written, and
the derived relation makes it a contract that later chapters can bind to.

Null keys deserve the last word. A null join key never matches, and a null group
key is dropped before grouping. Both rules are silent at execution: no error, just
a row that does not appear. When absence in a key is a data error, narrow the key
first. When an unmatched row must survive, choose a join mode that keeps it rather
than defaulting the key and inventing a match.

The next chapter takes this published grain and asks where a domain rule belongs
when the shipped vocabulary has no operation for it.

## Next

[9. Extending the meaning model](/book/part-2/06-extension) — from a published grain to the vocabulary the domain still needs.
