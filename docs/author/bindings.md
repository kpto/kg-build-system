---
title: Bind records
summary: A binding maps one row context onto one concrete node or edge, supplies every property and states the key that identifies the record.
section: author
order: 70
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/binding/service/public/builders.py
  - kg_build_system/distribution/languages/binding/service/_private/symbols.py
  - reference_project/bindings/site/__init__.py
  - docs/author/bindings.md
subject: binding
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Bindings</span><a href="/subjects/binding">Overview</a><a href="/author/bindings" class="active">Guide</a><a href="/spec/binding">Spec</a><a href="/reference/api">API</a><a href="/philosophy/binding-is-the-seam">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> The binding is the only declaration that imports both sides: the row shape and the graph meaning. It answers four questions: which rows, which record, which key and which property values.

## What it is

`node_binding` and `edge_binding` accept either a direct form or a row-derived form:

| Form | Node | Edge |
| --- | --- | --- |
| Direct | `build_key=`, `properties=` | plus `source_build_key=`, `target_build_key=` |
| Row-derived | `rows=`, `bind=lambda row: NodeValues(...)` | `bind=lambda row: EdgeValues(...)` |

The row-derived form is the normal one: the lambda receives a typed row proxy and returns the key and properties together. The two forms are exclusive.

## Rules

- A binding target is concrete. An abstract node, an abstract edge or a template is not a binding target.
- `rows=` takes a row-source value, never a class.
- Every declared property is assigned exactly once. A missing or extra property is refused.
- A build key is a present scalar. A nullable source read must be narrowed with `alter_rows().drop_null()` before it can be a key.
- An edge supplies its own key, a source key and a target key. A null endpoint key cannot ground the relation; drop the row rather than inventing an endpoint.
- An endpoint token is required only when the declared edge side is abstract. It must name a concrete node equal to or descending from that category.
- Two bindings on one component with the same content are refused as a duplicate identity. A `debug_name` distinguishes producers for display but is not part of the digest.
- Binding identity hashes the canonical binding document except `debug_name` and `python_ref`. Changing a property, key, row plan, annotation or semantics changes the identity.

## Example

```python
from kg_build_system import (
    Edge, EdgeValues, Node, NodeValues, PropertySlot, edge_binding,
    node_binding, property,
)

from reference_project.table.equipment import EquipmentTable
from reference_project.table.sites import SitesTable


class SiteNode(Node):
    name: PropertySlot[str] = property()
    city: PropertySlot[str] = property()


class UnitNode(Node):
    name: PropertySlot[str] = property()


class HasUnitEdge(Edge[SiteNode, UnitNode]):
    pass


site_binding = node_binding(
    target=SiteNode,
    rows=SitesTable.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.site_id.alter_rows().drop_null(),
        properties=SiteNode(
            name=row.site_name.default_to("Unnamed site"),
            city=(
                row.premises.extract(lambda value: value.contact)
                .extract(lambda value: value.location)
                .extract(lambda value: value.city)
                .default_to("Unlisted city")
            ),
        ),
    ),
)

has_unit_binding = edge_binding(
    target=HasUnitEdge,
    rows=EquipmentTable.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.unit_ref.alter_rows().drop_null(),
        source_build_key=row.site_id.alter_rows().drop_null(),
        target_build_key=row.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(),
    ),
)
```

## Limits

- One row produces one record. A row that must produce several records needs a projection with the right grain, not a loop in the binding.
- A binding does not merge records. Duplicate keys survive until a deduplication or merge planner runs.
- A property cannot be omitted because it is “usually null”. A nullable property is declared nullable at topology and supplied as a nullable selection.
- Python mode carries a `{module, qualname}` reference, not a callable body. It is an execution mode, not an escape hatch from the declarative model.
- Binding identity includes the row plan. Two visually similar bindings over different grains are different identities.

## Next

[Declare meaning](/author/meaning) — make the record’s meaning part of the graph.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-013 | Keep debug names out of the blueprint fingerprint. | 2026-11-02 | accepted | `docs/developer/system-design.md#identity` |
| D-015 | Make bindings accept row-source values, not declaration classes. | 2026-10-29 | accepted | `tests/test_authoring_api.py` |
| D-028 | Require an `endpoint(...)` token only when the declared edge side is abstract. | 2026-09-01 | accepted | `docs/reference/bindings.md#endpoint-tokens` |
