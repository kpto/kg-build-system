---
title: Grain specification
summary: A row source fixes what one row means; every filter, join, group, union and unnest derives a new grain.
section: spec
perspective: spec
subject: grain
spec: SPEC-004
order: 40
status: normative
verified: 2026-11-15
sources:
  - kg_build_system/distribution/languages/data/model/public/row_sources.py
  - kg_build_system/distribution/languages/data/service/_private/rows.py
  - kg_build_system/distribution/languages/expressions/model/public/selection.py
  - kg_build_system/distribution/languages/data/service/_private/declarations.py
  - docs/content/appendix/reference/row-sources.md
evidence:
  - tests/test_authoring_api.py
  - tests/distribution/test_expression_operations.py
  - docs/content/appendix/reference/row-sources.md
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Grain, row sources and derived relations</span><a href="/appendix/subjects/grain">Overview</a><a href="/book/part-2/05-grain-and-projections">Guide</a><a href="/appendix/spec/grain" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/design-in-meaning">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** A row source MUST be a value carrying a shape and a plan. `rows=` MUST accept a row-source value and MUST NOT accept a `SourceRelation` or `DerivedRelation` declaration class.
- **R2.** `SourceRelation.row_source()` and `DerivedRelation.row_source()` MUST return a bindable `RelationRowSource` over exactly one relation. `Stage.row_source()` MUST return a `StageRowSource`, which MUST NOT be bindable. Every derived operation MUST return a `DerivedRowSource` and MUST compose with the next operation.
- **R3.** `where`, `distinct` and `order_by` MUST preserve the input shape. `union` MUST require member-by-member equal shape, including external name and full logical type; `all=False` MUST remove duplicates. A union MUST NOT rename, cast or reorder members.
- **R4.** `join` MUST pair scalar key selections of the same base logical type. Its `how` MUST be `inner`, `left`, `right` or `full`, and a null key MUST NOT match in any mode.
- **R5.** `group_by` MUST produce one row per key tuple and MUST drop any row whose key tuple contains null. Its shape MUST be `{by, members}`; grouping MUST collect members and MUST NOT aggregate them.
- **R6.** `unnest` MUST read a direct array field and MUST produce one row per item while preserving every other field. A null or empty array MUST produce no rows.
- **R7.** `Selection.lookup(...)` MUST return a nullable array of target records. A null key MUST NOT match, and `lookup` MUST NOT accept a `how` argument.
- **R8.** `Selection.zip(other)` MUST pair two arrays by position. It MUST refuse unequal lengths rather than pad or truncate, and an absent input MUST produce an absent result.
- **R9.** A `DerivedRelation` MUST pin exactly one row source, MUST declare at least one `computed_field`, and every output MUST share that one row plan. `DerivedRelation()` and a bare `DerivedRelation` subclass MUST be refused.
- **R10.** A derived relation MUST NOT introduce a second driving source; an additional relation MUST be read with `lookup`. Source and derived relation names MUST be unique in one namespace, and a collision MUST be refused.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/test_authoring_api.py` | `rows=` accepts a row-source value and refuses the declaration class; a derived relation requires a source, rejects class sugar and exposes typed outputs. |
| `tests/distribution/test_expression_operations.py` | `lookup` returns a nullable array and yields null for a null key; `zip` refuses unequal lengths; `unnest` emits one row per item and none for empty or null arrays. |
| `docs/content/appendix/reference/row-sources.md` | The shape effects, key rules, generated shapes and refusals of the row-source algebra. |

## API

| Public name | Role |
| --- | --- |
| `RowSource` | A value with a shape and a plan; derived operations return a new value. |
| `RelationRowSource` | A bindable scan over one source or derived relation. |
| `StageRowSource` | A private scan over one stage; not bindable. |
| `DerivedRowSource` | A filtered, joined, grouped or otherwise derived row source. |
| `SourceRelation.row_source()` | Starts the plan at a source-relation grain. |
| `DerivedRelation.row_source()` | Reads the one row plan a derived relation pins. |
| `Stage.row_source()` | Reads a stage plan inside its derived relation; the result is not bindable. |
| `where(predicate)` | Same shape, fewer rows; the predicate returns `Selection[bool]`. |
| `join(other, *, on, how="inner")` | Equi-join on one scalar key pair; null keys never match. |
| `group_by(*, by=...)` | One row per key tuple, shaped as `{by, members}`. |
| `union(other, *, all=True)` | Stacks same-shaped rows; `all=False` removes duplicates. |
| `distinct()` | Same shape, duplicate rows removed. |
| `order_by(*keys, ascending=True)` | Same shape, ordered rows. |
| `unnest(selector)` | One row per direct array item; null or empty yields none. |
| `Selection.lookup(...)` | A nullable array of target records for a key. |
| `Selection.zip(other)` | A position-paired array of records; lengths must match. |
| `computed_field(...)` | The derived output constructor; outputs share one row plan. |

## Limits

- Grouping collects members. It has no count, sum, min, max or `having`; an aggregate is a computed output or a later module.
- A generated join, group or unnest shape is correct at runtime but exposed to a static checker as `Any`.
- `zip` refuses unequal lengths at execution. It does not pad, truncate or raise at authoring.
- `unnest` is the row-source spelling of an array grain; `Selection.expand` is a row effect inside a product. Do not use both for the same fan-out.
- A null key silently produces no join row and no group. Narrow or default the key first when absence is a data error.
- A derived relation has no imperative body and cannot introduce a second driving source. Read another relation with `lookup`.
- A stage composes its row plan inside one derived relation. It is lineage, not a consumer relation, and a binding cannot read it.
- Row order is observable only through a later ordering or a materialised relation.

## Rationale

The grain is a design decision, not an accident of a query. Making it a value with a shape and a plan lets an author name one row once and reuse that meaning through filters, joins and derived relations. A binding then inherits the grain instead of inventing it, which keeps the seam thin and double-counting visible.

## Next

Read the [grain subject](/appendix/subjects/grain) for the authoring-level view.
