---
title: Set the grain
summary: A row source is a value whose shape and plan decide what one row means; join, group, union and unnest change that meaning.
section: author
order: 40
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/data/model/public/row_sources.py
  - kg_build_system/distribution/languages/data/service/_private/rows.py
  - docs/author/grain.md
subject: grain
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Grain, row sources and projections</span><a href="/subjects/grain">Overview</a><a href="/author/grain" class="active">Guide</a><a href="/spec/grain">Spec</a><a href="/reference/api">API</a><a href="/philosophy/design-in-semantics">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> A binding produces one record per row. The grain is the answer to “what is one row?” It is chosen by the row source, not by the binding, and it is the most common source of double-counted or missing records.

## What it is

`Table.row_source()` starts with the source grain. Each operator derives a new value:

| Operator | Grain effect |
| --- | --- |
| `where(predicate)` | Same shape, fewer rows. |
| `join(other, on=..., how=...)` | Combines two grains; a null key never matches. |
| `group_by(by=...)` | One row per key; null keys are dropped. |
| `union(other, all=...)` | Stacks same-shaped rows; `all=False` removes duplicates. |
| `distinct()` | Same shape, duplicate rows removed. |
| `order_by(*keys, ascending=...)` | Same rows, ordered. |
| `unnest(selector)` | One row per array item; other fields preserved. |
| `lookup(...)` | A value, not a grain change; returns a nullable array. |
| `zip(...)` | Pairs two arrays by position; equal lengths required. |

<figure class="kb-plate">
  <img src="/_assets/grain.svg" alt="A row source passes through where, join, group, distinct and order; a projection names the grain a binding reads.">
  <figcaption>Filtering and joining change which rows exist; a projection names the grain and publishes typed outputs.</figcaption>
</figure>

## Rules

- `rows=` takes a row-source value, never a declaration class: `SitesTable.row_source()`.
- `where` receives a symbolic row and must return `Selection[bool]`.
- Join keys must be scalar, present and the same type on both sides. `how` is `inner`, `left`, `right` or `full`.
- `group_by` takes key expressions; it has no count, sum, min, max or `having`.
- `union` requires matching shapes. `unnest` requires a direct array field read; a null or empty array produces no rows.
- `lookup` reads another relation by key and returns a nullable array. A null key never matches.
- A projection output is the supported place to name and reuse a derived grain.

## Example

```python
from reference_project.table.equipment import EquipmentTable
from reference_project.table.projections.defects import DefectProjection

units = EquipmentTable.row_source()
defects = DefectProjection.row_source()

unit_defects = units.join(
    defects,
    on=lambda unit, defect: (unit.unit_ref, defect.unit_ref),
    how="left",
)

active_units = units.where(
    lambda unit: unit.in_service.alter_rows().drop_null()
)
```

`unit_defects` has one row per unit-and-defect pair; a unit with no defect still has one row because the join is left. `active_units` has the equipment grain.

## Limits

- Grouping collects members; it does not aggregate them. A count or sum is a computed output or a later module.
- A generated join or group shape is typed at runtime but is not exposed to the static type checker.
- A flat query has one driving source. Additional relations must be read with `lookup`, not by adding a second source to a product.
- `zip` refuses unequal lengths; it does not pad or truncate.
- `unnest` is the row-source spelling of an array grain. `Selection.expand` is a row effect inside a product; do not use both for the same fan-out.
- Null keys silently produce no join rows or no group. Narrow or default the key first when absence is a data error.

> [!note] Extension point
> A model rule is not an extension point. Everything else names the object that replaces it; the ladder is in [Extend the toolchain](/operate/extend#extension-ladder).

## Next

[Project rows](/author/projections) — give a derived grain a name and typed outputs.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-015 | Make bindings accept row-source values, not declaration classes. | 2026-10-29 | accepted | `tests/test_authoring_api.py` |
| D-016 | Own the relational row-source algebra in the data language as a small frozen plan DTO. | 2026-10-29 | accepted | `docs/developer/data-and-expressions.md#row-source-model` |
| D-019 | Add `lookup`, `zip` and row-source `unnest` as explicit value/grain operations. | 2026-11-05 | accepted | `tests/distribution/test_expression_operations.py` |
