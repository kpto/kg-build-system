---
title: Design in semantics
summary: "Name the domain and state the claims; do not let SQL verbs and staging names become the model."
section: philosophy
order: 30
status: normative
verified: 2026-11-10
sources:
  - docs/content/appendix/philosophy/index.md
  - docs/content/book/part-2/01-meaning-and-purpose.md
  - kg_build_system/distribution/languages/annotations/
  - reference_project/topology/
---

> [!lede]
> The framework has a vocabulary for meaning: graph names, edge labels, properties, claims, frames and limitations. If those names describe joins, staging areas and temporary rows, the graph is explainable only as a pipeline. The language is expressive enough to be abused.

## What it is

A design surface is made of names and statements:

- **Node/edge graph name** — design: `SiteNode`, `HAS_UNIT`; plumbing: `Row1`, `left_join_02`.
- **Property** — design: `name`, `city`, `as_at`; plumbing: `col_a`, `tmp_value`.
- **Projection** — design: `DefectProjection`, the defect grain; plumbing: `distinct_expand_3`.
- **Binding debug name** — design: `site_binding`, `has_unit_binding`; plumbing: `left_join_sites_equipment`.
- **Graph claim** — design: `A site holds installed equipment.`; plumbing: `The pipeline ran successfully.`
- **Description** — design: what the component means to a reader; plumbing: how the SQL was written.

The plan can keep technical step names. The blueprint should not.

## Rules

- A name is a contract. A key is built from graph names; a name that describes the implementation leaks it into every artifact.
- Use the domain verb for an edge: `HAS_UNIT`, `MEASURES`, `OBSERVED_DURING`. Use the SQL verb only below the binding.
- Name a projection for the grain it publishes, not the operations that produced it. `DefectProjection` is a grain; `expand_areas_elements_defects` is a recipe.
- Put a claim in `Semantics`, not in a docstring or a comment. A docstring explains to a developer; a claim is published to a consumer.
- Use descriptions for prose, labels for target names and annotations for typed payloads. They are different channels; one does not substitute for another.
- If the only explanation of a record is a chain of joins, the design has not been expressed. Add the node, edge or claim that states the result.
- Keep `debug_name` for display. It is not part of the identity digest and it is not a design statement.

## Example

The same estate relation, named two ways:

| Plumbing name | Design name |
| --- | --- |
| `eq_join_sites_equipment` | `HasUnitEdge` |
| `equipment_rows` | `EquipmentTable` |
| `unit_join_02` | `has_unit_binding` |
| `tmp_defect` | `DefectProjection` |

The design name is not cosmetic. It changes the key, the binding identity and the label a consumer sees.

```python
from kg_build_system import (
    Claim, Edge, EdgeLabel, EdgeOptions, Graph, GraphOptions, GraphSemantics,
    Node, PropertySlot, Purpose, property,
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
    name: PropertySlot[str] = property()


class UnitNode(Node):
    name: PropertySlot[str] = property()


class HasUnitEdge(Edge[SiteNode, UnitNode]):
    options = EdgeOptions(annotations=(EdgeLabel("HAS_UNIT"),))
```

The edge says *site has unit*. It does not say “left join equipment on site_id”. The join still exists in the plan, but it is not the model.

## Limits

- The compiler checks keys, references and types, not whether a name means anything. `Row1` and `col_a` are valid names.
- A graph claim is a promise, not a proof. The framework publishes it; it does not evaluate its truth.
- A description and an annotation are not claims. Putting a statement in a docstring does not make it part of the semantic contract.
- A label is a target-facing name, not a definition. `HAS_UNIT` does not by itself state the direction; the edge generic and the endpoints do.
- Good names do not rescue a wrong topology. A well-named source-shaped graph is still source-shaped.
- The plan’s step names may stay technical; do not confuse plan evidence with blueprint design.

## Next

[Explainability is authored](/appendix/philosophy/explainability-is-authored) — what the framework can and cannot make explainable.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add semantics and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_semantics_language.py` |
| D-031 | Build the blueprint from symbols and typed refs; group feature code into modules and type execution resources. | 2026-11-04 | accepted | `tests/distribution/test_typed_refs.py` |
