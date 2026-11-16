---
title: "11. Binding as fulfilment"
summary: "A binding is where a published relation fulfils a record's purpose: grain, identity, coverage and the gaps stated as limitations."
section: book
perspective: book
part: II
chapter: 11
order: 28
status: normative
verified: 2026-11-15
sources:
  - docs/content/appendix/reference/bindings.md
  - docs/content/appendix/spec/binding.md
---

A node or edge declaration states what a record is and what it is for. A relation
states what rows exist and what that relation means. A binding states whether and
how the relation fulfils the record: its grain, its identity, its coverage and its
meaning. It is not an implementation detail. It is the adequacy claim between two
declarations that must not absorb each other.

## Fulfilment is the binding's job

A binding answers four questions:

| Question | If the answer is no |
| --- | --- |
| Does the relation's grain match the record's grain? | The relation cannot fulfil the record; split the relation or change the record. |
| Does the relation carry the record's identity? | The binding cannot key the record; the gap is a limitation or a design error. |
| Does the relation's coverage match the record's purpose? | The binding states the shortfall as a limitation. |
| Does the relation's meaning fit the record's meaning? | The binding is using the wrong relation. |

The first two are structural. The last two are where the meaning lives. A binding
can therefore fail: if the grain is wrong, or the identity is absent, or the
coverage contradicts the purpose, field mapping does not repair it. The design
changes, not the binding.

A simple binding is not a failure. If the relation genuinely has the record's grain
and identity, the fulfilment can be one-to-one. What is a failure is a vacuous
binding: if the relation already chose the record's grain, key and properties, the
design happened on the relation side, and the binding is a copy. Move the record
knowledge back to topology and the binding; do not add more processing to the
relation.

The mechanical mapping is still real, and the rest of this chapter states it. The
point is what the mapping is for: it is the evidence that the relation is adequate
for the record, not a recipe that gives the record its meaning.

## The purpose names the use and the answer

A binding purpose is not a description of the row plan. It names the record's use
in a clause, then states how this relation answers it: the grain, the identity and
the coverage the relation actually supplies.

- “Supply `HAS_DISEASE` edges from each row's `diseaseId`” is a mapping recipe. It
  says what the expression does and nothing about the record's use.
- “The evidence relation fulfils the `HAS_DISEASE` use as the attribution that lets
  a consumer gather the release's evidence for one disease: each release row names
  the disease it is about and supplies one edge, keyed by the evidence and disease
  ids, covering every release row. The relation supplies the release's resolved
  term, not the source label, and asserts no causation.” is a fulfilment.

The second names the use, the relation, the grain, the identity and the coverage.
The limitations carry the shortfall. A purpose that only restates the record's
purpose has not said how the relation answers it; a purpose that only describes the
expression has not said what record it serves.

## The binding is the only place a relation meets a record

A topology declaration never reads data. A relation declaration never names a node
or an edge. The binding is the only declaration that imports both sides, and that is
why it is the seam.

`node_binding` and `edge_binding` accept two forms. The direct form names a key and
a properties instance. The row-derived form names a row source and a callable. The
callable receives a typed row proxy, not a dictionary and not data, and returns
`NodeValues` or `EdgeValues`:

```python
from kg_build_system import (
    Claim, Contract, Definition, EdgeValues, Field, Limitation, Meaning,
    NodeValues, Omitted, Purpose, SourceRelation, SourceRelationOptions,
    edge_binding, field, node_binding,
)

from reference_project.asset.estate import Estate
from reference_project.relation.source.estate.sites import SitesSourceRelation


class EquipmentSourceRelation(SourceRelation[Estate]):
    options = SourceRelationOptions(
        name="equipment",
        contract=Contract(
            definition=Definition(
                grain="One row per registered unit.",
                identity=("unit_ref",),
            ),
            meaning=Meaning(
                claims=(
                    Claim(
                        "A unit row carries the site at which the unit "
                        "is installed."
                    ),
                ),
            ),
        ),
    )
    site_id: Field[str] = field(meaning=Omitted)
    unit_ref: Field[str] = field(meaning=Omitted)
    unit_name: Field[str] = field(meaning=Omitted)
    in_service: Field[bool] = field(meaning=Omitted)
    survey_period: Field[str] = field(meaning=Omitted)


site_binding = node_binding(
    target=SiteNode,
    rows=SitesSourceRelation.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=row.site_name.default_to("Unnamed site"),
            summary=row.site_name.default_to("Unnamed site"),
        ),
    ),
    meaning=Meaning(
        purpose=Purpose(
            text=(
                "Use the published site register to populate the "
                "site record."
            ),
            limitations=(
                Limitation("Unregistered sites are absent."),
            ),
        ),
        claims=(Claim("One site row supplies one site record."),),
    ),
)

unit_binding = node_binding(
    target=UnitNode,
    rows=EquipmentSourceRelation.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        properties=UnitNode(
            name=row.unit_name.default_to("Unnamed unit"),
            in_service=row.in_service.default_to(False),
            survey_period=row.survey_period,
            summary=row.unit_name.default_to("Unnamed unit"),
        ),
    ),
    meaning=Meaning(
        purpose=Purpose(
            text=(
                "Use the equipment register to populate the unit "
                "record."
            ),
            limitations=(
                Limitation("Equipment outside the register is absent."),
            ),
        ),
    ),
)

has_unit_binding = edge_binding(
    target=HasUnitEdge,
    rows=EquipmentSourceRelation.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        source_build_key=row.site_id.alter_rows().drop_null(),
        target_build_key=row.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(
            as_at=row.survey_period.default_to("Unrecorded period"),
        ),
    ),
    meaning=Meaning(
        purpose=Purpose(
            text=(
                "Use the equipment register to assert which site "
                "holds each unit."
            ),
            limitations=(
                Limitation(
                    "A unit whose site is not recorded has no edge."
                ),
            ),
        ),
    ),
)
```

`SitesSourceRelation` is the site relation declared for the estate feed;
`EquipmentSourceRelation` reads the equipment register.

A binding requires a meaning with a purpose, as the graph declaration and a derived
relation do. The reason here is the seam: a binding exists to claim that one
declaration fulfils another, and a fulfilment with no purpose has nothing to be
adequate to. The binding's purpose states the fulfilment — which relation satisfies
which record purpose, at grain, identity and coverage, and where it falls short —
not the record's purpose and not the relation's.

`rows` takes a row-source value over a published relation, never a `SourceRelation`
or `DerivedRelation` class. A filter or a reshape belongs in the row source or in a
derived relation. The row source has already decided the grain; the binding maps one
row of that grain to one record.

A stage is not a published relation. A `Stage` row source is a valid row source
inside its own package and nowhere else: `node_binding` and `edge_binding` refuse
it, because a stage has a definition and no contract. If the grain you want to bind
is worth a purpose and a consumer, publish it as a derived relation; if it is an
intermediate step, it stays inside the package that owns it.

The two forms are exclusive. Supplying `build_key` and `rows` together, or only half
of either form, is refused. The direct form is not a shortcut around rows: a
class-level selection still evaluates per row. A selection names a field
symbolically; it is not a constant.

Why insist that the binding is the only place a relation meets a record? Because
every other answer collapses one side into the other. If topology read a relation,
the design would depend on a source schema. If a relation named a node, the data
language would need graph vocabulary and the graph language would need data
vocabulary. If a planner invented records, the mapping would be a runtime behaviour
rather than a declaration. The seam keeps the record's purpose above it and the
relation's meaning below it; the binding is the only place that states their
adequacy.

## A project is laid out by axis

The two axes are visible in the directory tree, and the tree is part of the model.
The estate project is one example:

```text
estate_project/
  asset/
    estate.py
  graph/
    graph.py
    site/
      node.py
      has_unit__unit.py
  relation/
    source/
      sites.py
      equipment.py
      surveys.py
    derived/
      site_score/
        relation.py
        _stage_site_score.py
  binding/
    site/
      binding.py
      has_unit__unit.py
  pipeline/
  modules/
  manifest.py
```

| Directory | What it holds |
| --- | --- |
| `asset/` | One file per `Asset` declaration. |
| `graph/` | The graph declaration and the node, edge and property declarations. |
| `relation/source/` | One file per `SourceRelation`. |
| `relation/derived/` | One package per `DerivedRelation`, with `relation.py` and its `_stage_*.py` files. |
| `binding/` | The bindings, grouped by the node they target. |
| `pipeline/`, `modules/` | Optional machinery outside the declaration languages. |

Four rules make the tree mean what it looks like.

- A concrete public declaration has its own file. `sites.py` declares
  `SitesSourceRelation`; `graph/site/node.py` declares `SiteNode`;
  `graph/site/has_unit__unit.py` declares `HasUnitEdge`. The file name is a
  shortened form of the declaration, and a predicate edge reads
  `<predicate>__<target>`.
- `__init__.py` is a facade. It carries a docstring, re-exports and `__all__`; it
  declares nothing and contains no logic.
- A derived relation is a package, because it owns a published declaration and any
  number of stages. `relation.py` holds the `DerivedRelation`; each `_stage_*.py`
  holds one `Stage`. Nothing outside the package imports a stage module.
- Files are small because declarations are small. Do not split one declaration
  across files to meet a line count, and do not merge two declarations because they
  happen to be short.

The dependency direction is the axis order: `asset <- relation <- binding -> graph`.
An asset imports nothing above it; a relation imports assets, not the graph and not
bindings; a binding imports the relation and the record it fulfils; the graph
imports neither relation nor binding. That direction is why a relation can be
tested without a graph and why a topology change cannot silently change a relation.

Four structure tests guard the tree, and they belong beside the build tests:

1. no declaration or logic in `__init__.py`;
2. one public declaration per file;
3. no module outside a derived-relation package imports its stages;
4. no binding reads a stage row source.

## A key is a present scalar, and an edge has three

Every binding supplies a build key. The key identifies one record within its
component. It is a present scalar selection. A nullable selection is refused; an
array or struct selection is refused; a Python literal is refused unless it is
wrapped in `value_expression(...)`.

A key read from a source field is nullable, because source access is nullable
regardless of what the file claims. The author narrows it:

```python
build_key=row.site_id.alter_rows().drop_null()
```

`drop_null()` drops the row when the value is absent. That is usually the right
answer for an identifier: a record without a key cannot be identified.
`default_to()` is legal on a key, but every missing identifier then shares one
identity. Use it only when a shared sentinel is genuinely correct, never to keep a
row alive.

An edge supplies three keys: its own `build_key`, a `source_build_key` and a
`target_build_key`. The endpoint keys name the nodes the relation grounds. A null
endpoint key cannot ground a relation, so the row is dropped rather than given an
invented endpoint. The relation's own key is separate from the endpoint keys
because a relation is its own record; two edges may connect the same pair of nodes
with different meanings or different `as_at` values.

Keys may overlap between producers. Two bindings can emit the same key
independently, and the graph will hold both records until a deduplication or merge
planner runs. The key states identity within a component; it does not enforce
uniqueness across the whole build. Uniqueness is a planner decision, and making it
a binding refusal would force every producer to know about every other producer.

## Every property once, and null is a topology decision

A binding assigns every declared property exactly once, including properties
inherited from a template or a category. A missing property is refused. An extra
property is refused. A bare value is refused; a property value is a selection or an
expression.

The null rule is the subtle part:

- A required property needs a present selection. A nullable source read must be
  narrowed with `default_to(...)` or `drop_null()`.
- An optional property accepts a nullable selection, because the topology already
  says absence is meaningful.

`alter_rows().drop_null()` inside a property assignment is a row filter for the
whole binding, not a per-property mask. If a unit has no name and the binding writes
`name=row.unit_name.alter_rows().drop_null()`, the entire unit record disappears,
not just the name. Use `default_to(...)` when the row remains meaningful without
the value, and use a nullable property when absence is part of the design.

This is why the topology decision comes first. A property declared required is a
promise that every record has a value. A property declared optional is a promise
that a reader must handle absence. A binding cannot change either promise; it can
only satisfy it or fail.

The relation's field definition is the other half of the same decision. A
`null_meaning` says what absence denotes in the domain, and the binding's meaning
states what that absence costs the record: a dropped record, a defaulted property,
or an optional property left absent. Reading those two statements together is how a
reviewer sees why a null disappeared or survived.

The same rule applies to arrays. A property declared `Array[str]` requires a present
array with non-null items. A property declared `Array[str] | None` accepts an absent
array, but not an array containing nulls. The framework refuses an array whose items
are nullable; flatten the value or drop the row.

## Endpoints are named only where the design is abstract

An edge binding resolves its endpoints from the declared edge. When the declared
side is concrete, the endpoint is already fixed. When the declared side is an
abstract category, the binding must name the concrete node the row grounds:

```python
source_node=endpoint(SiteNode)
target_node=endpoint(UnitNode)
```

An `endpoint(...)` token is required exactly when the declared side is abstract. It
must name a concrete node that equals or descends from that category. A token cannot
widen the category, name a template, or point at another edge. Supplying a token for
a concrete side is allowed and documents the component used, but it is not
required.

The asymmetry is deliberate. A concrete endpoint is a design decision already made.
An abstract endpoint deliberately leaves the choice open so that several concrete
kinds can share one relation family; the binding is where that choice becomes
concrete for a set of rows. Requiring a token there makes the choice visible
instead of letting a default decide it.

## Identity is the content, not the label

Two bindings that map the same rows to the same component with the same keys,
properties, endpoints, meaning and row plan, and with no distinguishing
`name`, are the same binding. The framework enforces that by deriving a
content identity: the SHA-256 digest of the canonical binding document, truncated
to sixteen hexadecimal characters, with `name` and `python_ref` removed.

The digest covers the target and kind, the build key, the edge endpoint keys, every
property selection, the resolved endpoint components, the row-source plan, the
binding annotations and the meaning. Change any of those and the identity changes.
Rename a producer and the digest does not change; only the display prefix does.

`name` is the human handle. It prefixes the identity string for display and
appears in the meta-graph's binding entries, but it does not enter the digest. This
is the right split: the name helps a reader find a producer, while the content
decides whether two producers are the same mapping. A `name` distinguishes
producers without changing the content they produce, and it cannot carry design.

Two bindings on one component with the same content and no distinguishing
`name` are refused as a duplicate blueprint symbol. That refusal is a feature.
A silent second producer would make the graph's record count depend on import order
or on which binding the planner happened to see first. The refusal says the model
has one mapping stated twice, and the author should keep one or change the other.

## What the seam refuses to do

A binding does not aggregate, join, expand, deduplicate, merge or rewrite rows. One
input row produces one record. A binding reads a row source whose grain already
matches the record. If a defect grain is three expansions below a survey document,
those expansions belong to a derived relation named for the grain, and the binding
reads that relation. A join belongs in a row source, a stage or a derived relation,
not in a loop inside `bind`.

The refusals are not limitations of the factory. They protect the review surface. A
binding that could join would be a second planner. A binding that could emit
several records per row would hide grain. A binding that could merge would make the
record count a runtime fact. Keeping the seam thin is what makes "which rows become
which record" answerable by reading one declaration.

Python mode does not escape the model. It carries a `{module, qualname}` reference,
not a live callable body. It is an execution mode for a mapping that needs
imperative code, not a place to put a design that the declarative surface cannot
express.

## Next

[12. Generating declarations](/book/part-2/09-generation) — turn an observed source schema into ordinary declarations without making generation part of the build.
