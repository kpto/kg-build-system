---
title: Meaning before mechanism
summary: "Declare what a record is before deciding which relation, join or source supplies it."
section: philosophy
order: 10
status: normative
verified: 2026-11-15
sources:
  - docs/content/book/intent.md
  - docs/content/appendix/philosophy/index.md
  - AGENTS.md
  - reference_project/graph/common.py
  - reference_project/manifest.py
---

> [!lede]
> A source schema is a description of what arrived, not a design of what the graph should be. If you start with the source relation, the joins and the columns, the graph becomes a mirror of the feed. Start with the record and its meaning; then decide which relation can supply it.

## What it is

A build makes three kinds of decision, in this order:

| Layer | Question | Declarations |
| --- | --- | --- |
| Design | What exists, what is it for, and how is it connected? | `Graph` + `Meaning`, topology, labels |
| Relation | Which domain relation exists, at which grain? | asset, `SourceRelation`, `Struct`, `DerivedRelation`, selection, row source |
| Fulfilment | Which relation supplies which record? | node or edge binding |

The order is not a workflow rule for the compiler; it is a rule for the author. The compiler links any valid order. The design is coherent only when the lower layer serves the higher one.

## Rules

- Write the graph purpose and its claims before the first source relation. If the purpose is empty, the record axis has no root.
- Declare nodes and edges because a consumer needs them, not because the source has columns for them.
- Name a `DerivedRelation` for the grain it publishes, not for the operations that produced it.
- Treat a `SourceRelation` as a contract with the domain; a one-to-one copy of the source is a choice, not a default.
- Declare a field's value, unit and null meaning on `field(...)` or `computed_field(...)`. The relation contract states the grain and identity; it does not repeat field names, types or provenance.
- State a relation's purpose in domain terms, with no graph nouns and no operator verbs. If it cannot be stated that way, it is a private `Stage`, not a published relation.
- A published relation must not name a record's properties, key or endpoints. If it does, the binding is a copy of the record, not a fulfilment of it.
- If the topology cannot be stated without naming a source column, the design is not finished. Find the domain noun first.
- If the source genuinely is the domain, say so. “The feed is the model” is a legitimate design when it is stated, not when it is accidental.

## Example

A source-shaped relation:

```python
from kg_build_system import (
    Field, SourceRelation, SourceRelationOptions, field,
)

from estate.asset import Estate


class Row1(SourceRelation[Estate]):
    options = SourceRelationOptions(name="row1")

    col_a: Field[str] = field()
    col_b: Field[str] = field()
```

The same source, designed:

```python
from kg_build_system import (
    Claim, Contract, Definition, Field, FieldDefinition, Graph, GraphOptions,
    Meaning, Node, NodeOptions, PropertySlot, Purpose, SourceRelation,
    SourceRelationOptions, field, property,
)

from estate.asset import Estate


class EstateGraph(Graph):
    options = GraphOptions(
        name="estate",
        meaning=Meaning(
            purpose=Purpose(text="Estate asset management."),
            claims=(Claim("A site holds installed equipment."),),
        ),
    )


class Site(Node):
    options = NodeOptions(
        meaning=Meaning(
            purpose=Purpose(text="Use this node as the published site register."),
        ),
    )

    name: PropertySlot[str] = property()
    city: PropertySlot[str] = property()


class Sites(SourceRelation[Estate]):
    options = SourceRelationOptions(
        name="sites",
        contract=Contract(
            definition=Definition(
                grain="One row per premises.",
                identity=("site_id",),
            ),
            meaning=Meaning(
                purpose=Purpose(text="Supply the site register to domain consumers."),
            ),
        ),
    )

    site_id: Field[str] = field()
    site_name: Field[str] = field(
        definition=FieldDefinition(
            value="Name used for the premises.",
            null_meaning="The register has not named the premises.",
        ),
    )
```

`Row1` is valid. It compiles and publishes. It just does not state what a row is; a binding that reads it directly would first require a contract. `Site` states the record; `Sites` states the domain relation that supplies it. The relation is chosen afterwards and can change without changing the node. Its purpose belongs to the relation axis, not to the graph.

## Limits

- The framework cannot prevent a source-shaped graph. It makes the choice visible; it does not make it for you.
- Topology-first does not mean source-blind. A property type, a nullable field and a grain are constraints from the data; the design must be satisfiable.
- Some sources have no domain beyond their columns. Then say that, and name the node for the source's role; do not invent a domain noun.
- A purpose statement is not a substitute for a design. It is the root the design is read under.
- This page states an authoring discipline, not a compiler rule. [Review top-down](/appendix/philosophy/review-top-down) is how the discipline is checked.

## Next

[Two axes, one fulfilment](/appendix/philosophy/semantic-hierarchy) — how records and relations carry meaning.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-021 | Model an asset as one logical source unit and keep layout descriptive, not an access contract. | 2026-11-04 | accepted | `tests/distribution/test_asset_language.py` |
| D-023 | Add meaning and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_meaning_language.py` |
| D-031 | Build the blueprint from symbols and typed refs; group feature code into modules and type execution resources. | 2026-11-04 | accepted | `tests/distribution/test_typed_refs.py` |
