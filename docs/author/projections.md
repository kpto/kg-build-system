---
title: Project rows
summary: A projection pins one row source, names the grain, and publishes typed outputs that bindings can read.
section: author
order: 50
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/data/model/public/declarations.py
  - reference_project/table/projections/defects.py
  - docs/author/projections.md
subject: grain
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Grain, row sources and projections</span><a href="/subjects/grain">Overview</a><a href="/author/projections" class="active">Guide</a><a href="/spec/grain">Spec</a><a href="/reference/api">API</a><a href="/philosophy/design-in-semantics">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> A row source is a value. A projection gives it a name, pins it, and publishes the columns other declarations can read. Use one when the grain is reused or deserves a contract; use a bare row source when it is not.

## What it is

`Projection(source)` pins exactly one row source at class creation. Every `computed_field` is an output on that one row plan. The projection is itself a row-source provider: `DefectProjection.row_source()` reads the pinned grain.

A projection is a named logical partition. It is not a table and does not read a second source. All outputs share the row plan, including its filters and expansions.

## Rules

- Pin exactly one source: `class P(Projection(SomeTable.row_source()))`. `Projection()` and `class P(Projection)` are refused.
- Declare at least one `computed_field`. A projection with no outputs is refused.
- Outputs are computed expressions. A projection does not have a source `field()`.
- All outputs share one row plan; a filter or expansion in one output changes the grain for every output and every binding that reads it.
- The name must be unique across relations and projections.
- A projection can read a table or another projection’s row source. The planner orders projections dependencies-first and refuses a cycle.

## Example

```python
from kg_build_system import Projection, computed_field

from reference_project.table.surveys import SurveysTable

area = SurveysTable.areas.alter_rows().expand()
element = area.extract(lambda value: value.elements).alter_rows().expand()
defect = element.extract(lambda value: value.defects).alter_rows().expand()


class DefectProjection(Projection(SurveysTable.row_source())):
    """One row per defect, with the element and visit it came from."""

    survey_id = computed_field(SurveysTable.survey_id.alter_rows().drop_null())
    surveyed_on = computed_field(SurveysTable.surveyed_on)
    unit_ref = computed_field(element.extract(lambda value: value.unit_ref))
    defect_id = computed_field(defect.extract(lambda value: value.defect_id))
    title = computed_field(defect.extract(lambda value: value.title))
    condition_rating = computed_field(
        defect.extract(lambda value: value.condition_rating)
    )
    observed_on = computed_field(defect.extract(lambda value: value.observed_on))
    observations = computed_field(defect.extract(lambda value: value.observations))
```

`DefectProjection.row_source()` is now one row per defect. The defect node and the two relations hanging off it read that same grain.

## Limits

- A projection has no imperative body. There is no `build(row)` method; use `computed_field`.
- A projection cannot introduce a second driving source. Read another relation with `lookup`.
- The generated shape of a projection is typed at runtime but is not a static type-checker name.
- A projection name collision with a table is refused; the language keys both by their graph name.
- Expanding three nested arrays in one plan is three fan-outs, not a join. If the document nests arrays, expand the levels in order and name the result once.

## Next

[Declare topology](/author/topology) — the node and edge meanings the rows will become.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-017 | Require projections to be pinned to exactly one row source. | 2026-10-29 | accepted | `docs/reference/projections.md#projectionsource` |
| D-019 | Add `lookup`, `zip` and row-source `unnest` as explicit value/grain operations. | 2026-11-05 | accepted | `tests/distribution/test_expression_operations.py` |
