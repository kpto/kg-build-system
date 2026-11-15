---
title: The binding is the fulfilment
summary: "Records and relations are two axes; the binding states whether a relation's grain, identity, coverage and meaning satisfy a record's purpose."
section: philosophy
order: 50
status: normative
verified: 2026-11-15
sources:
  - docs/content/book/intent.md
  - docs/content/appendix/philosophy/semantic-hierarchy.md
  - reference_project/binding/site/has_unit__unit.py
  - reference_project/build.py
  - AGENTS.md
---

> [!lede]
> A record states what the graph asserts. A relation states what the domain contains. The binding is the only place they meet, and it must state whether the relation fulfils the record, not merely which fields map. If the grain, identity, coverage or meaning is wrong, the binding cannot repair it; the design changes.

## What it is

| Record axis | At the binding | Relation axis |
| --- | --- | --- |
| Graph, node or edge purpose | Fulfilment | Relation purpose, stated in domain terms |
| Record grain and identity | Grain and identity match | `Definition.grain` and `Definition.identity` |
| Property purpose and direction | Coverage match | Row subset and source scope |
| Record limitations and labels | Meaning match | `Meaning` claims and limitations |

The binding owns neither side's meaning. It owns the **adequacy** between them.

That is why it is not an implementation detail and not a third design. A binding is a claim that the relation is sufficient for the record, with its shortfalls stated as limitations. The claim is reviewable on its own: the relation's contract, the record's meaning and the binding's fulfilment can be read together.

## Four questions

| Question | If the answer is no |
| --- | --- |
| Does the relation's grain match the record's grain? | The relation cannot fulfil the record; split the relation or change the record. |
| Does the relation carry the record's identity? | The binding cannot key the record; the gap is a limitation or a design error. |
| Does the relation's coverage match the record's purpose? | The binding states the shortfall as a limitation. |
| Does the relation's meaning fit the record's meaning? | The binding is using the wrong relation. |

The first two are structural. The last two are where the meaning lives. A binding can fail on any of them, and no amount of field mapping compensates.

## Rules

- Read a published relation whose contract already states the record's grain. A `SourceRelation` or `DerivedRelation` is published; a `Stage` is private and is never a binding input.
- Read a relation that is record-agnostic. If it names the record's properties, key or endpoints, the relation is the record in disguise and the binding is a copy. Move the design back to the record axis.
- A binding requires `Meaning` with a purpose. The purpose states the **fulfilment**: which relation satisfies which record purpose, at which grain, identity and coverage, and where it falls short. A mapping recipe alone is not a fulfilment.
- Assign every declared property exactly once. A missing property is refused; a defaulted value is a design decision, not a convenience.
- A build key is present and stable. A nullable key is either a row to drop or a data failure; it is never a silent default.
- Supply an endpoint token only when the declared side is abstract. Do not use a token to hide a topology decision.
- If the relation cannot state the record's coverage, the gap is a limitation under the binding's purpose, not a silent drop.
- If the relation carries a meaning the record does not assert, the binding is using the wrong relation.
- A simple binding is not a failure; a vacuous binding is. A simple binding states a real fulfilment in one sentence. A vacuous binding restates a one-to-one mapping and adds no grain, identity, coverage or meaning decision.
- If the relation already chose the record's grain, key and properties, the design happened on the relation side. Move those decisions back to the record; the relation stays domain-level.
- Keep `debug_name` for display. It is excluded from the identity digest, so it cannot carry the design.

## Example

The reference project has three grain situations:

| Binding | Rows | Why it fulfils |
| --- | --- | --- |
| `site_binding` | `Sites.row_source()` | The source relation is already the site grain. |
| `has_unit_binding` | `Equipment.row_source()` | The register carries both endpoint keys. |
| `has_defect_binding` | `Defect.row_source()` | The defect relation is three expansions below the survey document. |

The third case is the rule: the expansions belong to `Defect`, not to the binding. The binding offers a published relation to the record; it does not decide the grain.

```python
from kg_build_system import (
    BindingOptions, Claim, Limitation, Meaning, NodeValues, Purpose, node_binding,
)

from estate.graph.site.node import Site
from estate.relation.source.sites import Sites


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
                limitations=(Limitation("A row without site_id is absent."),),
            ),
            claims=(Claim("One Sites row yields one Site record."),),
        ),
    ),
)
```

The binding states the key, the property values and the relation it reads. It does not decide the grain; a defect binding reads `Defect` rather than performing the expansions itself.

## Limits

- One row produces one record. A binding cannot merge, deduplicate or rewrite records; those are planners.
- Binding identity includes the target, key, properties, row plan, mode, annotations and meaning. Changing the fulfilment changes the identity.
- A binding has no description. `debug_name` names it in the meta-graph; annotations record facts about it.
- Python mode carries `{module, qualname}`, not a live callable. It is an execution mode, not a place to hide a design.
- A same-grain direct join is legitimate only when the relation already has the record's grain. If the join creates a new grain, name it in a `DerivedRelation`.
- The framework cannot tell whether a binding is an honest fulfilment or a second design. [Review top-down](/appendix/philosophy/review-top-down) is how that is judged.

## Next

[Review top-down](/appendix/philosophy/review-top-down) — the order that catches a design that has collapsed into its binding.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-013 | Keep debug names out of the blueprint fingerprint. | 2026-11-02 | accepted | `docs/content/appendix/developer/system-design.md#identity` |
| D-015 | Make bindings accept row-source values, not declaration classes. | 2026-10-29 | accepted | `tests/test_authoring_api.py` |
| D-017 | Require projections to be pinned to exactly one row source. | 2026-10-29 | accepted | `docs/content/appendix/reference/derived-relations.md#projectionsource` |
