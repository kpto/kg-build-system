---
title: Design in meaning
summary: "Name the domain and state the claims; do not let SQL verbs, stage names or source columns become the model."
section: philosophy
order: 30
status: normative
verified: 2026-11-15
sources:
  - docs/content/appendix/philosophy/index.md
  - docs/content/book/intent.md
  - AGENTS.md
  - reference_project/graph/common.py
  - reference_project/manifest.py
---

> [!lede]
> The framework has a vocabulary for meaning: graph names, edge labels, properties, purposes, claims and limitations. If those names describe joins, staging areas and temporary rows, the graph is explainable only as a pipeline. The language is expressive enough to be abused.

## What it is

A design surface is made of names and statements:

| Element | Design | Plumbing |
| --- | --- | --- |
| Node or edge name | `Site`, `HAS_UNIT` | `Row1`, `left_join_02` |
| Property name | `name`, `city`, `as_at` | `col_a`, `tmp_value` |
| Source relation | `Sites`, the source contract | `equipment_rows` |
| Derived relation | `Defect`, the defect grain | `distinct_expand_3` |
| Stage | `_DefectRows`, private to its package | `tmp_defect`, imported elsewhere |
| Binding debug name | `site_binding`, `has_unit_binding` | `left_join_sites_equipment` |
| Claim | `A site holds installed equipment.` | `The pipeline ran successfully.` |
| Graph purpose | `Estate asset management.` | `Run the survey pipeline.` |
| Description | What the component means to a reader | How the SQL was written |

The plan can keep technical step names. The blueprint should not.

## Rules

- A name is a contract. A key is built from graph names; a name that describes the implementation leaks it into every artifact.
- Use the domain verb for an edge: `HAS_UNIT`, `MEASURES`, `OBSERVED_DURING`. Use the SQL verb only below the binding.
- Name a `SourceRelation` for the domain relation it supplies and a `DerivedRelation` for the grain it publishes. `Defect` is a grain; `expand_areas_elements_defects` is a recipe.
- A `Stage` is private. Its name may be technical because no consumer reads it; if another module imports it or a binding reads it, the name has escaped the package and the published relation is missing.
- Put a claim in `Meaning`, not in a docstring or a comment. A declaration has no docstring; its meaning is published to a consumer.
- A published relation must not name a record's properties, key or endpoints. A relation named for the record is the record in disguise.
- Use meanings for prose, labels for target names and annotations for typed payloads. They are different channels; one does not substitute for another.
- If the only explanation of a record is a chain of joins, the design has not been expressed. Add the node, edge, relation contract or claim that states the result.
- Keep `name` for display. It is not part of the identity digest and it is not a design statement.

## Example

The same estate relation, named two ways:

| Plumbing name | Design name |
| --- | --- |
| `eq_join_sites_equipment` | `HasUnit` |
| `equipment_rows` | `Equipment` |
| `unit_join_02` | `has_unit_binding` |
| `tmp_defect` | `Defect` |

The design name is not cosmetic. It changes the key, the binding identity and the label a consumer sees.

```python
from kg_build_system import (
    Claim, Edge, EdgeLabel, EdgeOptions, Graph, GraphOptions, Meaning, Node,
    NodeOptions, Omitted, PropertySlot, Purpose, property,
)


class EstateGraph(Graph):
    options = GraphOptions(
        name="estate",
        meaning=Meaning(
            purpose=Purpose(text="Estate asset management."),
            claims=(Claim("A site holds installed equipment."),),
        ),
    )


class Site(Node):
    options = NodeOptions(meaning=Meaning(claims=(Claim("A site is a monitored premises."),)))

    name: PropertySlot[str] = property(meaning=Omitted)


class Unit(Node):
    options = NodeOptions(meaning=Meaning(claims=(Claim("A unit is installed equipment."),)))

    name: PropertySlot[str] = property(meaning=Omitted)


class HasUnit(Edge[Site, Unit]):
    options = EdgeOptions(
        annotations=(EdgeLabel("HAS_UNIT"),),
        meaning=Meaning(claims=(Claim("A site contains the unit."),)),
    )
```

The edge says *site has unit*. It does not say “left join equipment on site_id”. The join still exists in the plan, but it is not the model. A defect relation is named `Defect`; its intermediate expansions live in a private `Stage`, not in the published name.

## Limits

- The compiler checks keys, references and types, not whether a name means anything. `Row1` and `col_a` are valid names.
- A claim is a promise, not a proof. The framework publishes it; it does not evaluate its truth.
- A label and an annotation are not claims. Putting a statement in a comment does not make it part of the delivered meaning.
- A label is a target-facing name, not a definition. `HAS_UNIT` does not by itself state the direction; the edge generic and the endpoints do.
- A stage name is plan evidence. It is not a published name and must not appear in a consumer's model.
- Good names do not rescue a wrong topology. A well-named source-shaped graph is still source-shaped.
- The plan's step names may stay technical; do not confuse plan evidence with blueprint design.

## Next

[Explainability is authored](/appendix/philosophy/explainability-is-authored) — what the framework can and cannot make explainable.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add meaning and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_meaning_language.py` |
| D-031 | Build the blueprint from symbols and typed refs; group feature code into modules and type execution resources. | 2026-11-04 | accepted | `tests/distribution/test_typed_refs.py` |
