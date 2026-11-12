---
title: The binding is the seam
summary: "The binding is the only place data and graph meet; keep the design above it and the plumbing below it."
section: philosophy
order: 50
status: normative
verified: 2026-11-10
sources:
  - docs/content/book/part-2/02-topology.md
  - kg_build_system/distribution/languages/binding/
  - reference_project/bindings/
  - reference_project/table/projections/defects.py
---

> [!lede]
> Topology is above the seam; assets, tables, selections and plans are below it. The binding is the narrow place where a row becomes a record. If the binding is doing design work, the design is in the wrong place.

## What it is

| Above the seam | At the seam | Below the seam |
| --- | --- | --- |
| Purpose, claims and frames | Concrete target | Asset and layout |
| Node and edge meaning | Build key | Table and field types |
| Property meaning and direction | One value per property | Selection and null policy |
| Category and template meaning | Edge source/target keys | Row source, join, group, unnest |
| Labels and limits | Endpoint tokens | Projection, plan and executor |

The binding is the only declaration that imports both the row shape and the graph meaning. That is why it is the seam, and why it should be thin.

## Rules

- Read a row source whose grain already matches the record. If the binding needs a multi-level expansion or a join, the grain belongs in a projection.
- Assign every declared property exactly once. A missing property is refused; a defaulted value is a design decision, not a convenience.
- A build key is present and stable. A nullable key is either a row to drop or a data failure; it is never a silent default.
- Supply an endpoint token only when the declared side is abstract. Do not use a token to hide a topology decision.
- A binding’s semantics fragment describes the mapping (“one row per site”), not the node’s meaning. The node owns its meaning; the binding owns the mapping.
- Keep `debug_name` for display. It is excluded from the identity digest, so it cannot carry the design.
- If the binding needs a source column the topology does not declare, either the topology is incomplete or the source is wrong. Resolve it above the seam.

## Example

The reference project has three different grain situations:

| Binding | Rows | Why |
| --- | --- | --- |
| `site_binding` | `SitesTable.row_source()` | The source row is already the site grain. |
| `has_unit_binding` | `EquipmentTable.row_source()` | The register carries both the site and unit keys. |
| `has_defect_binding` | `DefectProjection.row_source()` | The defect grain is three expansions below the survey document. |

The third case is the rule: the expansions belong to `DefectProjection`, not to the binding. The binding reads a named grain and maps it.

```python
from kg_build_system import (
    Node, NodeValues, PropertySlot, node_binding, property, value_expression,
)

from reference_project.table.sites import SitesTable


class SiteNode(Node):
    name: PropertySlot[str] = property()
    summary: PropertySlot[str] = property()
    source_version: PropertySlot[str] = property()


def build_site(row: SitesTable) -> NodeValues[SiteNode, str]:
    name = row.site_name.default_to("Unnamed site")
    return NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=name,
            summary=name,
            source_version=value_expression("survey-2026-08"),
        ),
    )


site_binding = node_binding(
    target=SiteNode,
    rows=SitesTable.row_source(),
    bind=build_site,
)
```

The binding states the key, the property values and the grain it reads. It does not decide how to flatten the survey; that decision is a projection above it.

## Limits

- One row produces one record. A binding cannot merge, deduplicate or rewrite records; those are planners.
- Binding identity includes the target, key, properties, row plan, mode, annotations and semantics. Changing the mapping changes the identity.
- A binding has no description. `debug_name` names it in the meta-graph; annotations record facts about it.
- Python mode carries `{module, qualname}`, not a live callable. It is an execution mode, not a place to hide a design.
- A same-grain direct join is legitimate at the seam only when the result simply supplies the record. If the join creates a new grain, name it in a projection.
- The framework cannot tell whether a binding is thin or a second design. [Review top-down](/appendix/philosophy/review-top-down) is how that is judged.

## Next

[Review top-down](/appendix/philosophy/review-top-down) — the order that catches a thin-looking design.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-013 | Keep debug names out of the blueprint fingerprint. | 2026-11-02 | accepted | `docs/content/appendix/developer/system-design.md#identity` |
| D-015 | Make bindings accept row-source values, not declaration classes. | 2026-10-29 | accepted | `tests/test_authoring_api.py` |
| D-017 | Require projections to be pinned to exactly one row source. | 2026-10-29 | accepted | `docs/content/appendix/reference/projections.md#projectionsource` |
