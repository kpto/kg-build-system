# Reimplementing the authoring fixes — interactive plan

## Ground truth

- Working branch: `feat/first-autonomous-exp-features-added`; at the time of writing HEAD is
  `693b234` (`Deleted assembler PoC script`), worktree clean, 425 tests passing, pyright 0.
- Reference: commit `36bc319` (*"Fixes done by AI along with the first AI open targets KG
  authoring"*), which lives on `feat/temp-ui` and `exp/first-ai-authoring-exp-byproduct`. It is
  **not an ancestor of this branch**; the merge-base is `22fedcd`.
- The reference is an answer key, not a patch. None of the ten items below is present here.
  Do not cherry-pick, revert or merge it. Read it per file:
  `git show 36bc319 -- <path>`.
- This branch already contains the new assembler (`29ebdae`, `assembler.py`, new workflow models).
  It stays as it is. The reference's old `workflow/assembly.py` changes and its `WorkflowStepDraft`
  changes do not apply.
- The reference's expression, type and target changes are largely portable. Its module changes
  (`core`, `meta_graph`, `neo4j`, `merging`) were written against the old workflow model and need
  adapting to the current one.
- Excluded from this rerun: the assembly rewrite (already done), the studio backend (another
  branch), the KG-specific bindings (another repo), and reference Item 11 (see below).

## Working agreement

- One item per turn. I propose the decision and the minimal diff; you approve or amend; I
  implement; I show the diff, the tests and pyright; you review; then the next item.
- Stop at every gate. Do not batch items. Do not "finish the list".
- No commits, reverts, branches or worktrees unless you ask.
- No edits outside the item. If the reference no longer fits, stop and present the options rather
  than forcing it.
- Every item updates `KG_BUILD_SYSTEM_SPEC.md` in the same turn. Code, test and spec change
  together.
- Verification is `uv run pytest -q` and `uv run pyright` (the project pins pyright in
  `pyproject.toml`; do not use `uvx`).
- Port the reference tests as a starting point, then adapt names and fixtures to this tree. A
  ported test that passes before the change is not evidence.

## Order

| # | Item | Depends on | Decision gate |
|---|---|---|---|
| 1 | Struct identity `(module, qualname)` | — | confirm repeated struct names still occur |
| 2 | Flat scalar-array properties | — | class creation vs target boundary for `Array[Date]` |
| 3 | Topology-typed property columns | — | none |
| 4 | String operations | — | none |
| 5 | `to_string()` on the base scalar expression | — | none |
| 6 | Array operations | 2, 3 | set semantics and `join` input rule |
| 7 | Row-source model | — | see `TEMP_RELATION_MODEL_SPEC.md` |
| 8 | Merge-module component scope | — | default scope and the missing folding test |
| 9 | Meta-graph array examples | 2 | none |

## Item 1 — Struct identity is `(module, qualname)`

- **Why.** Generated packages can emit same-named nested record structs per file. Name-keyed
  lookup resolves one module's struct as another's, and global name uniqueness refuses a legal
  blueprint.
- **Touch.** `kg_build_system/table/ir.py`, `compile/validation.py`,
  `modules/core/core.py`, `modules/targets/meta_graph/topology.py`.
- **Reference.** `git show 36bc319 -- kg_build_system/table/ir.py ...`
- **Prove.** `StructIdentityTests` (same name in two modules allowed, twice in one module
  refused); `DeclaredPathStructResolutionTests` (a non-null path found through the right
  module's struct).
- **Gate.** Confirm the KG work still produces repeated struct names; otherwise this is a
  correctness fix with no immediate trigger.

## Item 2 — A graph property may be a flat array of non-null scalars

- **Why.** Both targets store flat homogeneous lists natively. Neo4j arrays hold primitives only,
  so temporal and uuid items are refused.
- **Touch.** `topology/models.py` (`GraphScalar`, `GraphArray`, `require_graph_property`),
  `types/validation.py`, `types/__init__.py`,
  `modules/targets/neo4j/module.py` (`_supports_property`, `_ARRAY_ITEM_CAPABILITY`).
- **Reference.** `git show 36bc319 -- kg_build_system/topology/models.py
  kg_build_system/types/validation.py kg_build_system/modules/targets/neo4j/module.py`
- **Decisions.**
  - `Array[Date]` is a legal graph property at class creation; the Neo4j target refuses it at
    compile, where the capability boundary lives. Do not move that refusal into class creation.
  - Fix the two `where_items_present()` references in the refusal and docstring to
    `without_nulls()`; no such method exists.
- **Prove.** Class-creation refusal for `Array[Array[str]]` and `Array[str | None]`; a runtime
  array property through JSON and Neo4j; a Neo4j compile refusal for `Array[Date]`.
- **Gate.** Agree that `Array[Date]` is refused by the target, not by the type declaration.

## Item 3 — Property columns are cast to the topology type

- **Why.** Topology is the contract. The physical column must not depend on whether an
  expression happens to be typed or all-null. A bare `NULL` materializes as an integer; a
  property declared `time | None` must still be a `TIME` column.
- **Touch.** `modules/core/lowering.py` (cast each property column to the type declared on its
  target component), `modules/core/core.py` (reuse the existing logical-type-to-SQL helper);
  tests.
- **Reference.** `36bc319` fixed the symptom by typing the null literal. This item fixes the
  boundary instead: the topology declaration is the source of the physical type.
- **Decisions.**
  - Cast properties only; build and endpoint keys stay as they are.
  - Reuse `canonical_sql_type` and the existing `_sql_type` mapping; no target-specific code.
  - Leave custom and struct types uncast, as the source widening does.
- **Prove.** An all-null `Time | None` property produces a Parquet `TIME_MICROS` column; an
  all-null `Array[Date] | None` produces a `DATE` element; a mixed binding still unions; a
  wrong expression type is still refused at binding creation.
- **Gate.** None.

## Item 4 — String operations

- **Why.** Identifier pairs and CURIE normalization: `equals` for predicates, `replace` for
  `HP:`/`HP_`, and `before_separator`/`after_separator` for `Source:id`. The separator methods
  take a 1-based occurrence, so the first, second or later separator can be the cut point; the
  cut separator is excluded by default and `include_separator=True` keeps it.
- **Touch.** `expressions/text.py`; `engines/duckdb/lowering.py`; spec; tests.
- **Reference.** `git show 36bc319 -- kg_build_system/expressions/text.py
  kg_build_system/engines/duckdb/lowering.py`
  The reference names are `replaced`, `split_before` and `split_after`; this tree uses
  `replace`, `before_separator` and `after_separator`.
- **Prove.** Boolean equality, replacement, nth-occurrence cuts on each side, separator
  preservation, a missing occurrence, and empty-separator / non-positive-occurrence refusals.
- **Gate.** None.

## Item 5 — `to_string()` on the base scalar expression

- **Why.** Any scalar member can compose text key material without a per-project formatting
  rule. Putting it on `ValueExpression` gives bool, int, float, str, date, time, timestamp and
  uuid one operation; timestamp uses the framework's `T` separator, not DuckDB's space.
- **Touch.** `expressions/values.py`; `engines/duckdb/lowering.py`; spec; tests.
- **Reference.** `git show 36bc319 -- kg_build_system/expressions/numeric.py`
  The reference puts `text()` on `IntExpression`; this tree puts `to_string()` on the base expression.
- **Prove.** Each scalar unit stringifies; a nullable scalar returns a nullable text
  expression; arrays and structs are refused; timestamp text matches the canonical `T` form.
- **Gate.** None.

## Item 6 — Array operations

- **Why.** `transform_items` applies one explicit value expression to every item without
  fanning out rows; `drop_null_items` makes an item array a legal property; `sort`,
  `distinct` and `join` make order-independent, set-valued key material.
- **Touch.** `expressions/arrays.py`, `expressions/selections.py`,
  `expressions/models.py`, `expressions/ir.py`, `expressions/mapping.py`,
  `expressions/codec.py`, `expressions/ir_codec.py`, `expressions/visitors.py`,
  `engines/duckdb/lowering.py`, spec, tests.
- **Reference.** `git show 36bc319 -- kg_build_system/expressions/arrays.py
  kg_build_system/expressions/selections.py kg_build_system/engines/duckdb/lowering.py`
  The reference has `map_items`, `without_nulls`, `sorted` and `distinct`; this tree uses
  `transform_items` with a bound variable, `drop_null_items`, `sort` and `distinct`.
- **Depends on.** Items 2 and 3.
- **Prove.** `transform_items` with a nested member, an explicit operation and a typed literal;
  `drop_null_items`, `sort`, `distinct`, `join`; nullable propagation; a raw literal, a raw
  dict and a row effect are refused; typecheck assertions for the selection and expression forms.
  A typed dictionary lookup (`lookup_items`) is a separate future operation and is not part of
  this item.
- **Gate.** Confirm `distinct` keeps one copy per item and `join` refuses nullable/non-string
  items.

## Item 7 — Row-source model

`TEMP_RELATION_MODEL_SPEC.md` replaces the earlier `keep_if` item. The model is implemented
through its binding and lowering steps: `Shape`, `RowSource`, `ShapeType`, `any_of`/`all_of`,
`where`, `DerivedRowSource`, `projection_base()`, `rows=`/`bind` with `NodeValues`/`EdgeValues`,
row-source plans on projections and bindings, and filtered SQL lowering. The reference
project is migrated to `rows=`/`bind`; the legacy direct-expression form remains supported for
the Open Targets workspace. `keep_if` and binding filters are excluded.

## Item 8 — Merge module takes a component scope

- **Why.** Merging folds same-key rows with `min()` per column, which is only sound for
  components whose parallel rows are one fact. Edge families that keep parallel facts must stay
  out.
- **Touch.** `modules/operators/merging.py` (public configuration, JSON round-trip, scope);
  `modules/operators/__init__.py`; `modules/__init__.py`; spec; tests.
- **Reference.** `git show 36bc319 -- kg_build_system/modules/operators/merging.py
  kg_build_system/modules/operators/__init__.py kg_build_system/modules/__init__.py`
- **Decisions.**
  - `components=None` keeps today's behaviour: every record component.
  - `components` holds concrete `Node`/`Edge` classes, never free strings; JSON provenance
    stores their module and qualified name.
  - The row-folding test uses two components; only the named one folds duplicate keys.
- **Status.** Implemented and verified.

## Item 9 — Meta-graph examples survive array values

- **Why.** An array example is a list, so `dict.fromkeys` raises as soon as any component has an
  array property.
- **Touch.** `modules/targets/meta_graph/module.py` (`_ordered_examples`, canonical text key);
  tests.
- **Reference.** `git show 36bc319 -- kg_build_system/modules/targets/meta_graph/module.py
  tests/test_meta_graph_module.py`
- **Depends on.** Item 2.
- **Prove.** `ArrayExampleTests` with `ArrayExampleTable` / `ArrayExampleNode`.
- **Status.** Implemented and verified.

## Not in this rerun

- **Optional property slots** (`property(default=None)`). A declaration-level optional flag and a
  binding-level typed null produce the same graph records. The flag hides the distinction the
  model is meant to record: whether a member lacks the property or a binding supplies a null. A
  binding states a null explicitly with `literal(None, logical_type=...)`; a property that is not
  part of a member's concept belongs on a `NodeTemplate` mixin. The reference's flag stops at the
  binding factory and never reaches the blueprint or meta-graph, so it is not a recorded semantic.
- **Reference Item 11** (`assembly_preference="deferred"` removal). It belonged to the old
  `WorkflowStepDraft` claim order. In the shipped assembler `assembly_preference` is a live
  `WorkflowStep` field and an input to `_derive_ranks`; the report step still sets it at
  `modules/operators/conflict_validation.py:174`. Removing it is a separate rank decision, not a
  rerun item.
- **The assembly rewrite.** `workflow/assembler.py` and the new models stay untouched.
- **The studio backend.** It lives on another branch.
- **KG-specific bindings and surfaces.** They belong to the Open Targets workspace, not the
  framework.

## Definition of done, per item

1. Code carries the reason as a short docstring or comment.
2. New behaviour has a test that fails before the change and passes after it.
3. `uv run pytest -q` and `uv run pyright` are clean.
4. The relevant spec section is updated in the same turn.
5. I show the diff and the verification output; you approve; no commit unless you ask.

## Start here

Confirm these before Item 1:

1. Work on this branch, or in a scratch worktree at `22fedcd`?
2. Start with Item 1?
3. Port the reference tests and adapt them, or write fresh tests from the behaviour?
4. Leave everything uncommitted until the end, or commit one item at a time after your review?
