---
title: Select values
summary: Read, calculate and narrow one typed value; absence is settled by the owner and every row effect is explicit.
section: author
order: 30
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/expressions/model/public/selection.py
  - kg_build_system/distribution/languages/expressions/model/public/selections/effects.py
  - docs/reference/expressions.md
subject: selection
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Selection and nullability</span><a href="/subjects/selection">Overview</a><a href="/author/values" class="active">Guide</a><a href="/spec/selection">Spec</a><a href="/reference/api">API</a><a href="/philosophy/meaning-first">Philosophy</a><a href="/review/contracts">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> A `Selection[T]` is one typed value in a row. You read a field through it, compute a new value, navigate a record or an array, and decide what absence means. There is no second expression type and no SQL string.

## What it is

Every operation is a method on the selection. A literal is built with `value_expression`, which also returns a selection. The private expression tree is never exposed.

| Need | Operation |
| --- | --- |
| Read a nested member | `extract(lambda value: value.member)` |
| Index or range an array | `at(index)`, `slice(start, end)` |
| Keep the row, replace absence | `default_to(value)` |
| Drop the row on absence | `alter_rows().drop_null()` |
| Drop the row on a condition | `alter_rows().drop_if(predicate)` |
| One row per array item | `alter_rows().expand()` or `RowSource.unnest` |
| Arrays | `unique`, `sort`, `concat`, `transform_items`, `drop_null_items` |
| Text | `prepend`, `append`, `before_separator`, `after_separator`, `to_string` |
| Booleans | `not_`, `and_`, `or_`, `all_of`, `any_of` |
| Numbers | `add`, `sub` |
| Comparison | `equals` only |
| Another relation | `lookup` |
| Pair arrays by position | `zip` |

## Rules

- `Selection[T]` is the only authoring value. `NullableSelection[T]` is `Selection[Nullable[T]]`, not a class.
- A source read is nullable; a computed read follows its selection. `default_to` keeps the row and returns present; `alter_rows().drop_null()` removes the row and returns present.
- `alter_rows()` returns a one-shot handle. Reusing it raises `TypeError`; call `alter_rows()` again.
- The handle exposes only valid effects: `drop_null` on nullable selections, `expand` on arrays, `drop_if` everywhere.
- A row effect on a selection changes the row plan of the product that reads it, even when the selection feeds one property.
- Three-valued logic: `and_` is false when either side is false, `or_` is true when either side is true, and an unknown side yields null.
- A null key never matches in `lookup` or `join`; `group_by` drops null keys.
- `lookup` returns a nullable array. Compose grain explicitly: keep it for left, `drop_null()` for inner, `expand()` for one row per match.

## Example

```python
from kg_build_system import value_expression

site_name = SitesTable.site_name.default_to("Unnamed site")

label = (
    SitesTable.site_name
    .alter_rows().drop_null()
    .prepend("site::")
)

is_active = (
    EquipmentTable.in_service.alter_rows().drop_null()
    .and_(EquipmentTable.survey_period.alter_rows().drop_null().equals("2026-08"))
)

month = value_expression("2026-08")
```

```python
from kg_build_system import Array, Field, Table, field

class Site(Table):
    site_id: Field[str] = field()
    tags: Field[Array[str]] = field()

one_tag_per_row = Site.row_source().unnest(lambda row: row.tags)
```

## Limits

- No Python operators: no `+`, `==`, `and`, `in` or indexing syntax. Use the methods.
- No casts and no implicit conversions. `to_string()` exists for the eight unit scalars only.
- Temporal and `uuid` values have no comparison or filtering operation. Custom scalars have no value operations.
- A struct or custom value is not a literal; build it from row selections.
- There are no user-defined variables or functions. The only bound variable is a `transform_items` item.
- A nullable receiver is accepted by some text, array and boolean helpers at runtime although the public type surface presents them on present selections. Numeric `add` and `sub` still refuse a nullable operand.
- The `order_by` documented for selections is not the row-source `order_by`; the row-source form is the supported one.

> [!note] Extension point
> A model rule is not an extension point. Everything else names the object that replaces it; the ladder is in [Extend the toolchain](/operate/extend#extension-ladder).

## Next

[Set the grain](/author/grain) — combine values into a relation and decide what one row means.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-014 | Unify authoring around `Selection[T]` with owner-derived nullability. | 2026-11-05 | accepted | `tests/test_authoring_api.py` |
| D-018 | Gate every row effect behind a one-shot `alter_rows()` handle. | 2026-10-29 | accepted | `tests/test_authoring_api.py` |
| D-019 | Add `lookup`, `zip` and row-source `unnest` as explicit value/grain operations. | 2026-11-05 | accepted | `tests/distribution/test_expression_operations.py` |
| D-020 | Use `extract` as the member-read name and remove compatibility aliases. | 2026-11-04 | accepted | `tests/test_authoring_api.py` |
