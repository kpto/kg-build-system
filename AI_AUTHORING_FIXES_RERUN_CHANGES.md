# Authoring fixes rerun — change summary

Status: all items complete. Current HEAD is `300b7a3`; three naming cleanups in the
spec/validation comments are uncommitted. Full suite: **467 passed, 6 skipped, 410
subtests passed**; pyright **0 errors**.

## Scope

- Branch: `feat/first-autonomous-exp-features-added`.
- Reference: commit `36bc319` from the first AI Open Targets authoring attempt, used as an
  answer key only. It is not an ancestor of this branch.
- Excluded by decision: optional property slots (`property(default=None)`), `keep_if` and
  binding filters, `lookup`, `group_by`, and `join`. The Open Targets workspace is untouched;
  legacy direct-expression bindings remain supported.
- The reference project is migrated to the new binding API.

## Item 1 — Struct identity is `(module, qualname)`

- `table/ir.py` — `struct_type_key` recovers the identity from the symbol ID.
- `compile/validation.py` — struct-name uniqueness is per module (`module::name`), not global.
- `modules/core/core.py` — struct lookup and the non-null path walk key on `(module, qualname)`.
- `modules/targets/meta_graph/topology.py` — uses the shared helper instead of a private copy.
- Tests: same-named structs in different modules are legal; same name in one module is refused;
  paths resolve through the right declaration.

Commit: `d821e5b`.

## Item 2 — Flat scalar-array graph properties

- `topology/models.py` — `GraphScalar`, `GraphArray`, arrays in `GraphValue`; keys stay scalar.
- `types/validation.py` — `require_graph_property` accepts one-level arrays of non-null scalars;
  refuses nested arrays, struct arrays and nullable items.
- `modules/targets/neo4j/module.py` — `_supports_property` and `_ARRAY_ITEM_CAPABILITY`;
  `Array[bool/int/float/str]` export, other item types are a target capability gap.
- `KG_BUILD_SYSTEM_SPEC.md` — property shape and target boundary.
- Decision: `Array[Date]` is a legal declaration and is refused by the Neo4j target at compile.

Commit: `c9e44bf`.

## Item 3 — Topology-typed property columns

- `modules/core/lowering.py` — `sql_type_for` and `_binding_property_types`; every property
  column is cast to the type declared on its target component.
- `modules/core/core.py` — reuses the shared helper for source widening.
- All-null `Time | None` becomes `TIME_MICROS`; all-null arrays keep their list shape.
- Keys are not cast.

Commit: `ddc69da`.

## Item 4 — String operations

- `expressions/text.py`:
  - `equals(value)` → `BoolExpression` (`=`).
  - `replace(search, replacement)` → `StrExpression` (`replace`).
  - `before_separator(separator, occurrence=1, *, include_separator=False)`.
  - `after_separator(separator, occurrence=1, *, include_separator=False)`.
- Occurrence is 1-based. `before` returns the whole string when the separator does not occur;
  `after` returns `""` and keeps later separators.
- `include_separator=True` preserves the separator at the cut point.
- Internal operators are `before_separator` / `after_separator`; one shared lowering path.
- SQL: `STRING_SPLIT` + `LIST_SLICE` + `ARRAY_TO_STRING`, with `CASE` only when preserving.

Commit: `10cda68`.

## Item 5 — `to_string()` on the base scalar expression

- `expressions/values.py` — `ValueExpression.to_string()`.
- Accepts `bool`, `int`, `float`, `str`, `date`, `time`, `timestamp`, `uuid`.
- Returns `StrExpression`, or `NullableExpression[str, StrExpression]` for nullable input.
- Arrays, structs and custom types are refused.
- SQL: `CAST(x AS TEXT)`; timestamps use `REPLACE(..., ' ', 'T')` to match canonical text.

Commit: `e82cca8`.

## Item 6 — Array operations

- `expressions/arrays.py`, `expressions/selections.py`:
  - `transform_items(selector)` — callable-only; selector returns a `ValueExpression`; maps
    every item without expanding rows. Nested access uses `pick` chains; a literal is
    `lambda _: value_expression(...)`; raw literals, raw dictionaries, Python operators and
    row effects are refused.
  - `drop_null_items()` — explicit null-item removal; a null array stays null.
  - `sort()` — `LIST_SORT`.
  - `distinct()` — `LIST_DISTINCT`; order is not preserved, so `distinct().sort()` is the
    deterministic sequence.
  - `join(separator)` — `ARRAY_TO_STRING`; requires non-null string items.
- `expressions/models.py`, `ir.py`, `mapping.py`, `codec.py`, `ir_codec.py`, `visitors.py` —
  internal bound `VariableExpression` / `VariableExpressionIR` for the selector body.
- Semantics: `transform_items` lowers to `LIST_TRANSFORM`; `drop_null_items` to `LIST_FILTER`;
  `sort` to `LIST_SORT`; `distinct` to `LIST_DISTINCT`; `join` to `ARRAY_TO_STRING`.

Commit: `8de2c0d`.

## Item 7 — Row-source model

- `types/models.py`, `normalization.py` — `Shape`, `ShapeType`; `Struct` is shape-only.
- `table/models.py` — `RowSource`; `Table` and `Projection` are both `Shape` and `RowSource`;
  `TableGroup` is not.
- `expressions/boolean.py` — `any_of` / `all_of`, empty identities `False` / `True`.
- `table/rows.py` — `DerivedRowSource`; `where(predicate)` is callable-only, shape-preserving
  and chainable.
- `table/models.py` — `projection_base()`, generated shape views, inherited fields, shadowing,
  and projection-of-projection. Both documented forms work:
  `class P(active.projection_base())` and
  `class P(active.projection_base(), active.shape)`.
- `binding/models.py`, `factories.py` — `NodeValues` / `EdgeValues`; `rows=` accepts a
  `RowSource` class or a `DerivedRowSource`; `bind=` returns the value object. Legacy
  `build_key`/`properties` bindings remain supported.
- `table/ir.py`, `binding/ir.py`, `compile/compiler.py`, `compile/codec.py`,
  `compile/validation.py` — `RowSourcePlanIR` on projections and bindings; codec,
  validation and binding fingerprint include it.
- `relational/ir.py`, `planner.py`, `engines/duckdb/lowering.py` — `FilterIR.mode`
  (`present` / `true`); external predicates lower to `WHERE`.
- `reference_project/` — all 14 bindings migrated to `rows=`/`bind=`;
  `uv run python -m reference_project.build` succeeds.
- `TEMP_RELATION_MODEL_SPEC.md` — status and implementation notes updated.

Commits: `3a411f4` (framework), `9128cce` (reference project).

## Item 8 — Merge module component scope

- `modules/operators/merging.py` — public
  `MergeCompatibleFactsModuleConfiguration(components=...)`.
  `components` holds concrete `Node`/`Edge` classes, never free strings; `None` means every
  record component.
- `to_json` stores each class by module and qualified name; `__post_init__` resolves it when
  the blueprint is loaded.
- Step generation skips components outside the scope.
- `modules/operators/__init__.py`, `modules/__init__.py` — export the configuration.
- `modules/interfaces.py` — `ModuleRegistrationConfiguration.to_json()` default; compiler uses
  it for module provenance.
- Test: two components with duplicate keys; only the scoped one folds, the other keeps both
  parallel rows.

Commit: `c38b2b4`.

## Item 9 — Meta-graph array examples

- `modules/targets/meta_graph/module.py` — `_ordered_examples` deduplicates by canonical text
  key instead of `dict.fromkeys`, which failed on unhashable list examples.
- Test: `Array[str]` property examples survive as `[["x", "y"], ["z"]]`.

Commit: `300b7a3`.

## Implementation notes

- The row-source plan is `RowSourcePlanIR`; the existing product-level `RelationPlanIR`
  remains separate.
- `Table.shape` is the table class; `Projection.shape` and `active.shape` are generated
  shape views carrying the fields, so the documented two-base projection form works.
- Legacy direct-expression bindings remain supported for the Open Targets workspace; the
  reference project uses the new `rows=`/`bind=` form.

## Verification

```text
467 passed, 6 skipped, 410 subtests passed
0 errors, 0 warnings, 0 informations
```

The reference project builds, and pyright is clean across the framework, reference project and
typecheck fixtures.

## Commits

| Commit | Change |
|---|---|
| `d821e5b` | Struct identity |
| `c9e44bf` | Array graph properties |
| `ddc69da` | Topology-typed property columns |
| `10cda68` | String operators |
| `e82cca8` | Base `to_string()` |
| `8de2c0d` | Array operators |
| `3a411f4` | Row-source model |
| `9128cce` | Reference project migration |
| `c38b2b4` | Merge component scope |
| `300b7a3` | Meta-graph array examples |

## Uncommitted naming cleanup

The rename `without_nulls` → `drop_null_items` and `sorted` → `sort` left three stale
references; they are corrected in the working tree:

- `types/validation.py` — refusal text and docstring.
- `topology/models.py` — array-property comment.
- `KG_BUILD_SYSTEM_SPEC.md` — key-material and null-conversion wording.
