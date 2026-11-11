---
title: Selection specification
summary: A selection MUST be the only typed value; every operation MUST be a method and every row effect MUST be explicit.
section: spec
perspective: spec
subject: selection
spec: SPEC-003
order: 30
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/expressions/model/public/selection.py
  - kg_build_system/distribution/languages/expressions/model/public/selections/effects.py
  - kg_build_system/distribution/languages/expressions/service/public/boolean.py
  - kg_build_system/distribution/languages/expressions/service/public/expression.py
  - docs/appendix/reference/expressions.md
evidence:
  - tests/test_authoring_api.py
  - tests/distribution/test_expression_operations.py
  - tests/typecheck/authoring.py
  - tests/typecheck/authoring_negative.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Selection and nullability</span><a href="/appendix/subjects/selection">Overview</a><a href="/book/part-2/04-values-and-nullability">Guide</a><a href="/appendix/spec/selection" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/meaning-first">Philosophy</a><a href="/appendix/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** `Selection[T]` MUST be the only authoring value type; `value_expression(...)` MUST return a `Selection[T]`, and no second authoring expression class MUST be exposed.
- **R2.** `NullableSelection[T]` MUST be an alias for `Selection[Nullable[T]]`, not a distinct class.
- **R3.** Every value operation MUST be a method on `Selection`, except `all_of` and `any_of`, which MUST accept `Selection[bool]`; Python operators and the `.expression`, `.value` and `.model` escape hatches MUST NOT exist.
- **R4.** A row effect MUST be reached only through `alter_rows()`, which MUST be one-shot; a second effect on the same handle MUST raise `TypeError`.
- **R5.** `alter_rows().drop_null()` MUST be available only on a nullable selection, `expand()` only on an array, and `drop_if(predicate)` on every selection; an effect MUST change the row plan, and therefore the grain, of the product that reads it.
- **R6.** `extract`, `at`, `slice`, `lookup` and `zip` MUST be value operations that do not change the row count; `lookup` MUST return `Selection[Nullable[Array[S]]]` and `at` MUST return a nullable item.
- **R7.** `unique`, `sort`, `concat`, `transform_items`, `drop_null_items`, `default_to`, `prepend`, `append`, `equals`, `add`, `sub`, `not_`, `and_`, `or_` MUST return a `Selection` and MUST preserve the row plan; `all_of` and `any_of` MUST return a `Selection[bool]` and MUST preserve it too.
- **R8.** A null key MUST NEVER match in `lookup` or `join`, and `group_by` MUST drop null keys before grouping.
- **R9.** There MUST be no casts and no implicit conversions; `to_string()` MUST exist for the eight unit scalars only.
- **R10.** `Date`, `Time`, `Timestamp`, `Uuid` and custom scalar values MUST NOT expose comparison, filtering or arithmetic operations, and custom scalars MUST NOT support `to_string()`.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/test_authoring_api.py` | One `Selection` type, one-shot `alter_rows()`, valid effects per shape and no `.expression` escape hatch. |
| `tests/distribution/test_expression_operations.py` | `lookup`, `zip` and row-source `unnest` typing, null-key behaviour and explicit grain composition. |
| `tests/typecheck/authoring.py` | Static result types for navigation, array, text, Boolean and row-effect operations. |
| `tests/typecheck/authoring_negative.py` | An invalid effect and a removed operation do not type-check. |

## API

| Name | Meaning |
| --- | --- |
| `Selection[T]` | One typed value in a row. |
| `NullableSelection[T]` | The alias `Selection[Nullable[T]]`. |
| `alter_rows()` | One-shot handle for a row effect. |
| `RowEffects` | Present-selection handle exposing `drop_if` only. |
| `NullableRowEffects` | Nullable-selection handle exposing `drop_null` and `drop_if`. |
| `ArrayRowEffects` | Array handle exposing `expand` and `drop_if`. |
| `NullableArrayRowEffects` | Nullable-array handle exposing `drop_null`, `expand` and `drop_if`. |
| `extract` | Reads one declared struct member. |
| `at`, `slice` | Indexes or ranges an array without changing rows. |
| `lookup` | Reads another relation by key as a nullable array of records. |
| `zip` | Pairs two arrays by position into `Pair` values. |
| `Pair` | One left/right record produced by `zip`. |
| `value_expression` | Builds a literal `Selection`. |
| `all_of`, `any_of` | Combine Boolean selections. |

The facade groups and defining modules are listed in [API surface](/appendix/reference/api).

## Limits

- No Python operators or indexing syntax: no `+`, `==`, `and`, `in` or `rows[i]`. Use the methods.
- No casts and no implicit conversions; `to_string()` covers the eight unit scalars only.
- Temporal, `uuid` and custom scalar values have no comparison or filtering operation; custom scalars have no value operations.
- A struct or custom value is not a literal; build it from row selections.
- There are no user-defined variables or functions; the only bound variable is a `transform_items` item.
- `lookup` takes no `how`; compose left, inner and one-row-per-match grain with `drop_null()` and `expand()`.
- `order_by` on selections is unsupported; the row-source `order_by` is the supported form.
- Some text, array and Boolean helpers accept a nullable receiver at runtime although the public type surface presents them on present selections; numeric `add` and `sub` refuse a nullable operand.

## Rationale

A selection keeps every value typed and every absence decision visible, so a reader can see where a row disappears without reading generated SQL. Hiding the expression tree and gating effects behind one-shot handles makes the model auditable rather than clever. That is [explainability is authored](/appendix/philosophy/explainability-is-authored): the build preserves the operations declared, not an inferred intent.

## Next

[Selection subject](/appendix/subjects/selection) — the hub for this subject.
