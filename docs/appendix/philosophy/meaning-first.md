---
title: Meaning before mechanism
summary: "Declare what a record is before deciding which table, join or projection produces it."
section: philosophy
order: 10
status: normative
verified: 2026-11-10
sources:
  - docs/appendix/philosophy/index.md
  - docs/book/part-2/04-topology-and-bindings.md
  - reference_project/topology/
  - reference_project/table/
---

> [!lede]
> A source schema is a description of what arrived, not a design of what the graph should be. If you start with the table, the joins and the columns, the graph becomes a mirror of the feed. Start with the record and its meaning; then decide which rows can supply it.

## What it is

A build makes three kinds of decision, in this order:

| Layer | Question | Declarations |
| --- | --- | --- |
| Design | What exists, what does it mean, and how is it connected? | `Graph` + semantics, topology, labels |
| Contract | What rows can supply it? | asset, table, struct, selection, row source, projection |
| Mapping | Which row becomes which record? | node or edge binding |

The order is not a workflow rule for the compiler; it is a rule for the author. The compiler will happily link any valid order. The design is coherent only when the lower layer serves the higher one.

## Rules

- Write the purpose and the graph claims before the first table. If the purpose is empty, the rest has no root.
- Declare nodes and edges because a consumer needs them, not because the source has columns for them.
- Name a projection for the grain it publishes, not for the operations that produced it.
- Treat a table as a source contract; treat a node as a design decision. A one-to-one copy of the source is a choice, not a default.
- If the topology cannot be stated without naming a source column, the design is not finished. Find the domain noun first.
- If the source genuinely is the domain, say so. “The feed is the model” is a legitimate design when it is stated, not when it is accidental.

## Example

A source-shaped graph:

```python
from kg_build_system import Node, PropertySlot, property


class Row1(Node):
    col_a: PropertySlot[str] = property()
    col_b: PropertySlot[str] = property()
```

The same source, designed:

```python
from kg_build_system import (
    Claim, Graph, GraphOptions, GraphSemantics, Node, NodeLabel, NodeOptions,
    PropertySlot, Purpose, property,
)


class EstateGraph(Graph):
    options = GraphOptions(
        name="estate",
        semantics=GraphSemantics(
            claims=(Claim("A site holds installed equipment."),),
            purpose=Purpose(text="Estate asset management."),
        ),
    )


class SiteNode(Node):
    options = NodeOptions(annotations=(NodeLabel("Site"),))

    name: PropertySlot[str] = property()
    city: PropertySlot[str] = property()
```

`Row1` is valid. It compiles, binds and publishes. It just does not state what a row is. `SiteNode` states the record; the table that supplies `name` and `city` is chosen afterwards, and can change without changing the node.

## Limits

- The framework cannot prevent a source-shaped graph. It makes the choice visible; it does not make it for you.
- Topology-first does not mean source-blind. A property type, a nullable field and a grain are constraints from the data; the design must be satisfiable.
- Some sources have no domain beyond their columns. Then say that, and name the node for the source’s role; do not invent a domain noun.
- A purpose statement is not a substitute for a design. It is the root the design is read under.
- This page states an authoring discipline, not a compiler rule. [Review top-down](/appendix/philosophy/review-top-down) is how the discipline is checked.

## Next

[One purpose, read downward](/appendix/philosophy/semantic-hierarchy) — how meaning connects across the layers.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-021 | Model an asset as one logical source unit and keep layout descriptive, not an access contract. | 2026-11-04 | accepted | `tests/distribution/test_asset_language.py` |
| D-023 | Add semantics and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_semantics_language.py` |
| D-031 | Build the blueprint from symbols and typed refs; group feature code into modules and type execution resources. | 2026-11-04 | accepted | `tests/distribution/test_typed_refs.py` |
