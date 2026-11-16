---
title: Two axes, one fulfilment
summary: "Records and relations carry their own meaning; the binding is the fulfilment, and a relation purpose is not a local purpose under the graph."
section: philosophy
order: 20
status: normative
verified: 2026-11-15
sources:
  - docs/content/book/intent.md
  - docs/content/appendix/developer/data-and-expressions.md
  - reference_project/binding/common.py
  - AGENTS.md
---

> [!lede]
> A graph is not one purpose tree. It is two axes with one fulfilment. The record axis says what the graph asserts; the relation axis says what the domain contains. Each side carries its own `Meaning`, and the binding is the only place where one side answers the other.

## What it is

| Axis | Directory | Declarations | Meaning owner |
| --- | --- | --- | --- |
| Records | `graph/` | `Graph`, `Node`, `Edge`, property | Graph-local. The graph declaration owns the project's root purpose; a node, edge or property states its own use. |
| Domain | `relation/` | `SourceRelation`, `DerivedRelation`; `Stage` private | Domain-level. A relation read by a binding states a `Contract`: `Definition` plus `Meaning`; a derived relation always states one. |
| Fulfilment | `binding/` | node and edge bindings | The adequacy between one relation contract and one record. |

```text
records                                 relations
graph/                                  relation/
what the graph asserts                  what the domain contains
  graph purpose                           relation contract
    node, edge, property                    definition: grain, identity
      Meaning                                 Meaning: domain purpose
          ▲                                       │
          └──────────── binding ──────────────────┘
                      fulfilment
```

The graph purpose is the root of the record axis only. It does not become the parent of a relation purpose. A relation used by two graphs keeps one domain meaning; what changes is the binding that makes it relevant to each graph.

A published relation states a contract. A `DerivedRelation` always states one; a `SourceRelation` may omit it until a binding reads it directly, and then it states one too. `Definition` states the grain and the identity. `Meaning` states the domain purpose, contextless claims and the limitations of that purpose. A field carries its own `FieldDefinition`; name, type and provenance are derived. A `Stage` is private inside a derived-relation package: it composes intermediate rows and carries a definition but no contract meaning. A binding never reads a stage.

## Rules

- A project has one graph purpose on the graph declaration. A node, edge or property states a local use of its own; it does not copy the root text.
- Every declaration attaches `Meaning` inline. A structural helper may pass a `Meaning` value through; it does not accept purpose, claim or limitation text.
- A claim is contextless and never owns a limitation. A limitation lives inside the purpose it bounds.
- A declaration with no positive use carries claims only. Do not invent a purpose to fill a shape.
- State a relation purpose in domain terms. It must not be a local purpose under the graph, and it must be readable without a node, edge, binding or pipeline step.
- A published relation is record-agnostic. It must not name a record's properties, key or endpoints; if it does, the binding is a copy and the design has collapsed onto one axis.
- A stage carries a definition only. It is not a published relation, is not imported outside its package and is not a binding input; it appears in the blueprint as internal lineage.
- A binding requires `Meaning` with a purpose. The purpose states which relation fulfils which record, at which grain, identity and coverage, and where it falls short.
- Structural inheritance is not meaning inheritance. A category's label and meaning do not flow to a concrete child; a template's annotations do. Attach the concrete component's meaning explicitly.
- The framework does not check consistency across the axes. The author makes the two sides coherent; the reviewer reads each side and then the binding.

## Example

```python
from kg_build_system import (
    BindingOptions, Claim, Contract, Definition, Field, Graph, GraphOptions,
    Limitation, Meaning, Node, NodeOptions, NodeValues, Omitted,
    PropertySlot, Purpose, SourceRelation, SourceRelationOptions, field,
    node_binding, property,
)

from estate.asset import Estate


class EstateGraph(Graph):
    options = GraphOptions(
        name="estate",
        meaning=Meaning(
            purpose=Purpose(
                text="Estate asset management.",
                limitations=(Limitation("Unregistered equipment is absent."),),
            ),
            claims=(Claim("A site holds installed equipment."),),
        ),
    )


class Site(Node):
    options = NodeOptions(
        meaning=Meaning(
            purpose=Purpose(
                text="Use this node as the published site register.",
                limitations=(Limitation("Closed sites are absent."),),
            ),
            claims=(Claim("A site has one name."),),
        ),
    )

    name: PropertySlot[str] = property(meaning=Omitted)


class Sites(SourceRelation[Estate]):
    options = SourceRelationOptions(
        name="sites",
        contract=Contract(
            definition=Definition(
                grain="One row per premises.",
                identity=("site_id",),
            ),
            meaning=Meaning(
                purpose=Purpose(
                    text="Supply the site register to domain consumers.",
                    limitations=(Limitation("Unregistered premises are absent."),),
                ),
            ),
        ),
    )

    site_id: Field[str] = field(meaning=Omitted)
    site_name: Field[str] = field(meaning=Omitted)


site_binding = node_binding(
    target=Site,
    rows=Sites.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=Site(name=row.site_name.default_to("Unnamed site")),
    ),
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                text="Sites fulfils the site register at one row per site.",
            ),
            claims=(Claim("One Sites row yields one Site record."),),
        ),
    ),
)
```

Read the two axes separately. The graph purpose says what the project is for. The `Site` purpose says what this record is used as, and omits closed sites. The `Sites` purpose says what the domain relation supplies, with no graph noun. The binding purpose names both sides and the grain; it is not a third meaning, and it copies neither purpose.

## Limits

- There is no parent link between axes and no propagation. `Meaning` has no inheritance and no cross-axis consistency check.
- A relation purpose is not a narrower graph purpose. A relation consumed by two graphs keeps one contract; each graph gets its own binding.
- A project may publish topology without a `Graph`. Then no graph purpose exists, and the absence is a limit to name; the record axis has no root.
- A relation contract can be valid and still be wrong for a record. The four binding checks find that; the compiler does not.
- A binding with a purpose can still be a dishonest fulfilment. The framework checks the shape and the rule, not the judgment.
- A stage has no contract meaning. It cannot serve a consumer, and a binding that reads one has bypassed the published relation.

## Next

[Design in meaning](/appendix/philosophy/design-in-meaning) — how names and claims carry the design.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add meaning and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_meaning_language.py` |
| D-027 | Support polymorphic categories/templates with one normative base order. | 2026-09-01 | accepted | `docs/content/appendix/reference/topology.md#base-order` |
