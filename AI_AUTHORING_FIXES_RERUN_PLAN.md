# Re-running the AI authoring fixes, one item at a time

Source: commit `36bc31912b2ad3801b337f1ac1006b03d471a18e` — *"Fixes done by AI along with the first AI
open targets KG authoring"*, 33 files, +2095/−107. The commit is the answer key: read it per file with

```bash
git show 36bc3191 -- kg_build_system/table/ir.py      # or any path below
git show --stat 36bc3191                              # the whole inventory
```

Each item below states what to change, why it was needed, how to know it is done, and which files hold
the original. Reasons are the commit's own, from its docstrings, comments and spec text; the two places
where a reason is my inference are marked *(inferred)*.

## Before starting: there is nothing to revert

As of this writing the `kg-build-system` worktree is clean apart from untracked `experiments/`, and
`36bc3191` is an ancestor of `HEAD` (`d2d03b2`), with 14 commits after it. Among them is the `studio/`
backend, whose source generator already maps `map_items`, `without_nulls` and `keep_if` in
`studio/backend/studio_backend/generate/expressions.py`, with `map_items` nullability inference asserted
in `studio/backend/tests/test_infer.py`. Inside the framework, `struct_type_key`,
`require_graph_property` and `keep_if` are live API. So:

- `git checkout .` / `git restore` recovers nothing — no tracked file is modified.
- `git revert 36bc3191` would collide with those 14 commits and leave the studio backend emitting calls
  to methods that no longer exist.

Two routes that do give a clean "start again", neither run yet:

1. **Separate worktree at the parent** (keeps this checkout untouched):
   `git worktree add ../kgb-rerun 36bc3191^` then implement here item by item, diffing against
   `git show 36bc3191 -- <path>`. Copy this plan file over, since it is untracked here.
2. **Current tree, item by item**: treat each item as "confirm the decision and the test still earn
   their place", re-deriving anything you want changed. Nothing is destroyed; the commit stays history.

Tell me which and I will drive. I will not revert or branch anything without you saying so.

## The seven places a new operation lands

Items 5–8 add authoring operations. Each one has to appear in all seven, which is what made the commit
large; the checklist is repeated per item.

1. authoring method on the value family (`expressions/*.py`), with its docstring stating the source
   shape it reads
2. selection-side overloads (`expressions/selections.py`) so it is usable where fields are declared
3. an IR operator string, recorded in the expression IR and nothing else
4. DuckDB lowering (`engines/duckdb/lowering.py`) into inspectable SQL
5. planner treatment if it has a row effect (`relational/planner.py`, `relational/ir.py`)
6. a spec paragraph in `KG_BUILD_SYSTEM_SPEC.md`
7. tests: runtime IR, lowered SQL, and the static harness `tests/typecheck_graph_bindings.py`

---

## Item 1 — Struct identity is `(module, qualname)`, not a name

- [ ] `kg_build_system/table/ir.py` — add `_STRUCT_SYMBOL_PREFIX = "python:struct:"` and
      `struct_type_key(struct) -> tuple[str, str] | None`, exported in `__all__`.
- [ ] `kg_build_system/compile/validation.py` — replace the global "struct names" uniqueness rule with
      uniqueness of `f"{module}::{name}"`, message `struct names within a module`.
- [ ] `kg_build_system/modules/core/core.py` — `_declared_non_null_paths` takes
      `Mapping[tuple[str, str], StructIR]`, its `parents` cycle guard holds pairs, and
      `_declared_read_paths` indexes `blueprint.structs` by `struct_type_key`.
- [ ] `kg_build_system/modules/targets/meta_graph/topology.py` — delete the private `_struct_key`,
      import the shared one.

**Why.** "A `StructTypeIR` names a struct by module and qualified name, and the blueprint stores that
same identity only inside the struct's symbol ID." Generated packages emit same-named nested record
structs per file, so name-keyed lookup resolved one module's struct as another's, and the global
uniqueness rule refused a legal build. "Names are display, identity is this pair."

**Verify.** `StructIdentityTests` in `tests/test_blueprint_ir.py` (same name in two modules passes,
twice in one module is refused) and `DeclaredPathStructResolutionTests` in
`tests/test_source_schema_trust.py` (a non-null path found through the right module's struct).

**Answer key.** the four paths above.

---

## Item 2 — A graph property may be a flat array of non-null scalars

- [ ] `kg_build_system/topology/models.py` — split `GraphScalar` out of the old `GraphValue` alias, add
      `type GraphArray = Array[GraphScalar]`, widen `GraphValue` to include it, keep
      `NonNullableGraphValue = GraphScalar` so keys stay scalar; switch `properties_for` from
      `require_scalar` to `require_graph_property`.
- [ ] `kg_build_system/types/validation.py` — add `require_graph_property`: pass a scalar through to
      `require_scalar`; accept `Array` whose item is neither `Array` nor `Struct` ("flatten nested
      structures with `expand()` instead") nor `NullableType` ("apply `where_items_present()` to drop
      null items"); else return the type unchanged.
- [ ] `kg_build_system/types/__init__.py` — export `require_graph_property` (and `Array`,
      `NullableType`, which the callers need).
- [ ] `kg_build_system/modules/targets/neo4j/module.py` — replace `_capability_key` with
      `_supports_property`, add `_ARRAY_ITEM_CAPABILITY = frozenset({"bool","int","float","str"})`,
      and extend the refusal message to list `Array[bool] … Array[str]`.
- [ ] **fix a defect the original shipped and `HEAD` still carries**: the refusal says "apply
      `where_items_present()` to drop null items", and the docstring repeats it, but no such method
      exists anywhere in the framework — the operation added in Item 7 is `without_nulls()`. An author
      following the message hits an `AttributeError`. Name the real method, and check the docstring of
      `require_graph_property` too (`kg_build_system/types/validation.py:38` and `:51`).

**Why.** Both targets store flat homogeneous lists natively, and set-valued facts in the source data are
common. The boundary is the target's: Neo4j arrays hold primitives only (Cypher Manual, "Property
values"), so temporal and uuid items are refused, and "a null item would be an absent value the array
cannot represent".

**Verify.** `ArrayPropertyTests` in `tests/test_relational_lowering.py`. A property declared
`Array[Date]` or `Array[str | None]` must be refused at class creation with the stated messages.

**Answer key.** `git show 36bc3191 -- kg_build_system/topology/models.py kg_build_system/types/validation.py kg_build_system/modules/targets/neo4j/module.py`

---

## Item 3 — A null literal carries its declared type in SQL

- [ ] `kg_build_system/engines/duckdb/lowering.py` — add `_typed_null_sql_type(logical_type)`: unwrap
      `NullableTypeIR`, map `UnitTypeIR` through `CANONICAL_SQL_TYPES`, compose `f"{item}[]"` for
      `ArrayTypeIR`, return `None` for anything else; in the literal path, emit
      `CAST(NULL AS <type>)` when a type is known and plain `exp.convert(None)` otherwise.
- [ ] `tests/test_typed_literals_sql.py` — the `NullableType(TIME)` expectation becomes
      `CAST(NULL AS TIME)`.

**Why.** "A bare `NULL` column materializes as an integer", which misrepresents the component's declared
schema in the Parquet output. Structs cannot be property types, hence only units and arrays compose.

**Verify.** The literal SQL test; a build whose component has an unbound slot keeps a `TIME`-typed
column rather than an integer one.

**Depends on.** nothing; it is what makes Item 4 usable.

---

## Item 4 — Optional property slots via PEP 681 `default=None`

- [ ] `kg_build_system/topology/models.py` — `_PropertyDeclaration` gains `optional: bool = False`;
      `property()` gains `default: Any = ...` and sets `optional=default is None`; `properties_for`
      raises `"<Class>.<slot> may default to null only when nullable"` for a non-null slot.
- [ ] `kg_build_system/binding/factories.py` — in `_require_properties`, when a `TypeError` comes from a
      slot that is `optional` and whose `logical_type` is a `NullableType`, bind
      `ValueExpression(literal(None, logical_type=expected))` instead of raising.

**Why.** A binding promises to fill every slot its concrete component resolves; a category needs to mark
a property some members do not state. Using PEP 681's default channel means "a type checker models the
generated constructor parameter as optional too", and the authored declaration and the checked one stay
one thing. A shadowing re-declaration without the default is a fresh promise.

**Verify.** `InheritedSlotOptionalityTests` in `tests/test_topology_hierarchy.py`, plus fixtures
`TermCategory` / `BareTerm` / `NamedTerm` in `tests/typecheck_topology_hierarchy.py` proving a type
checker accepts a binding that omits the optional slot and rejects one omitting a promised slot.

**Depends on.** Item 3 — the typed null is what reaches the output.

---

## Item 5 — String operations: `equals`, `replaced`, `split_before`, `split_after`

- [ ] `kg_build_system/expressions/text.py` — four methods on `StrExpression`; `equals` returns
      `BoolExpression` with `logical_type=BOOL`, the others `StrExpression`.
- [ ] `kg_build_system/engines/duckdb/lowering.py` — `equals` → `EQ`; `replaced` → `replace`;
      `split_before` → `list_extract(string_split(x, sep), 1)`; `split_after` →
      `array_to_string(list_slice(string_split(x, sep), 2, -1), sep)`.
- [ ] spec: the `StrExpression` line in the bindable families block, plus a paragraph on the
      identifier-pair reading.

**Why.** `split_before`/`split_after` are "the identifier-pair reader of this vocabulary": a source ships
`Reactome:R-HSA-70635` as one string and the two halves name a database and a reference. `split_after`
re-joins the remainder so later separators stay in the payload —
`Wikipedia:Neural_development#Neuron_migration` on `:` yields the whole page title. `replaced` is "the
identity-space normalizer of this vocabulary", `HP:0000118` to `HP_0000118`, "without inventing a
bespoke operation per pair". `equals` exists to feed `keep_if` (Item 8).

**Verify.** `test_string_equality_produces_a_boolean_predicate` in `tests/test_typed_expressions.py`;
`BooleanPredicateTests` and the split/replace cases in `tests/test_relational_lowering.py`.

---

## Item 6 — `IntExpression.text()`

- [ ] `kg_build_system/expressions/numeric.py` — `text()` returning `StrExpression`, operator `"text"`.
- [ ] `kg_build_system/engines/duckdb/lowering.py` — `text` → `CAST(<x> AS VARCHAR)`.
- [ ] spec: the `IntExpression` line gains `text`.

**Why.** "key material's cast": a source that names a record with a numeric member can compose it into a
string key "without the framework inventing a per-project formatting rule", and the text is DuckDB's
canonical cast — "the same digits a reader of the source would see".

**Verify.** `IntTextCastTests` with `NumericKeyTable` / `NumericKeyNode` in
`tests/test_relational_lowering.py`.

---

## Item 7 — Array operations: `map_items`, `without_nulls`, `sorted`, `distinct`, `join`

- [ ] `kg_build_system/expressions/arrays.py` — the five methods on `ArrayExpression`; `join` requires
      non-null string items and returns `StrExpression`; `without_nulls` narrows
      `Array[T | None]` to `Array[T]`.
- [ ] `kg_build_system/expressions/selections.py` — the same five on the selection classes, with the
      overload set per element kind (nullable data type, nested struct, data type, unit), plus the
      shared `_map_items` and `_selected_member` helpers `ArrayExpression` delegates to.
- [ ] `kg_build_system/engines/duckdb/lowering.py` — `map_items` → `list_transform`; `without_nulls` →
      `list_filter` (a null array stays null, only null items drop); `sorted` → `list_sort`;
      `distinct` → `list_distinct`; `join` → `array_to_string`.
- [ ] spec: the `ArrayExpression` family line, and the paragraphs on projecting a member, on
      order-independent keys, and on `distinct` as a set-valued property.

**Why.** `map_items` projects one declared member out of every element (`Array[S]` → `Array[member]`) and
records an operation, "not a row effect: no rows are added" — a nullable member or element makes the
items nullable and a null array maps to a null array. `sorted` makes an array's content independent of
the order the source listed it in, "so a key built from the items names the same record no matter how the
source ordered it". `distinct` is "the projection of a repeated nested member into a set-valued property:
the same event named by three liabilities of one record is one item". `without_nulls` is explicit because
property arrays must hold non-null items and no target stores null items faithfully. `join` turns the
sorted set into the key string.

**Verify.** `test_map_items_projects_an_array_member` (including nullable-member propagation) in
`tests/test_typed_expressions.py`; `ArrayPropertyTests` in `tests/test_relational_lowering.py`; overloads
exercised in `tests/typecheck_graph_bindings.py`.

**Depends on.** Item 2 to be useful as a property, Item 3 for a null array's typed output.

---

## Item 8 — `keep_if(predicate)`: a Boolean value as a row filter

- [ ] `kg_build_system/expressions/values.py` — `keep_if` on `ValueExpression`, returning `Self`: the
      value passes through unchanged, keeping its family, and records a `filter` row effect
      (`RowSemantics` mode `filter`).
- [ ] `kg_build_system/relational/ir.py` — `FilterIR` gains `mode: Literal["present", "true"] = "present"`.
- [ ] `kg_build_system/relational/planner.py` — `lower_product` collects `keep_if`: require two
      arguments ("keep_if requires two arguments"), require the predicate's logical type to be the bool
      unit ("keep_if requires a Boolean predicate"), deduplicate through the same key set as
      `where_present`, append `Filter(predicate, "true")`.
- [ ] `kg_build_system/engines/duckdb/lowering.py` — `where_present` and `keep_if` both lower to their
      own value: "the row effect already became a plan filter".
- [ ] spec: the "Every bindable expression also carries `keep_if(predicate)`" note, the new
      *### Row predicates* section, the IR paragraph listing `expand`, `where_present`, `keep_if`,
      `map_items`, and the `lower_product` paragraph.

**Why.** A projection often must drop rows without altering a sibling product. Like `where_present` it is
a local filter owned by the projection or binding; the two differ in kind — a null-presence test against a
predicate held true — which is what the `mode` field carries, and the planner combines them into one
predicate.

**Verify.** `test_keep_if_filters_rows_and_retains_the_family` in `tests/test_typed_expressions.py`,
including the `TypeError` for a non-Boolean predicate and the assertion that the row semantics mode is
`filter`; `BooleanPredicateTests` for the combined SQL.

**Depends on.** Item 5, since `equals` is what usually supplies the predicate.

---

## Item 9 — `MergeCompatibleFactsModule` takes a component scope

- [ ] `kg_build_system/modules/operators/merging.py` — the private empty `_Configuration` becomes public
      `MergeCompatibleFactsModuleConfiguration` with `components: tuple[str, ...] | None = None`;
      `__post_init__` normalises a JSON list back to a tuple and rejects non-strings or empty strings;
      step generation skips components outside the scope; `freeze_json({"components": None or list(scope)})`
      replaces `freeze_json({})`; `CONFIGURATION_TYPE` follows.
- [ ] `kg_build_system/modules/operators/__init__.py` and `kg_build_system/modules/__init__.py` — export
      the configuration.

**Why.** "Merging folds same-key rows into one record (a `min()` per column), so it is only sound for
components whose parallel same-key rows are meant to be one fact — node components re-emitted by several
sources, for example. Edge families that deliberately keep parallel facts must stay outside the scope."
The JSON round-trip normalisation is needed because registration serialises configuration.

**Verify.** A registration round-trip test and a two-component build where only the named component's
same-key rows fold.

---

## Item 10 — Meta-graph examples survive array values

- [ ] `kg_build_system/modules/targets/meta_graph/module.py` — `_inclusive_values` calls a new
      `_ordered_examples(values, limit)` that dedupes and orders by the canonical text form
      (`_example_order_key`) instead of `dict.fromkeys`.

**Why.** "an array example is a list, which is unhashable, so `dict` identity dedup is unavailable" — the
old line raised as soon as any component had an array property, which Item 2 makes possible.

**Verify.** `ArrayExampleTests` with `ArrayExampleTable` / `ArrayExampleNode` in
`tests/test_meta_graph_module.py`.

**Depends on.** Item 2.

---

## Item 11 — Drop `assembly_preference="deferred"` (assembly work)

- [ ] `kg_build_system/modules/operators/conflict_validation.py` — remove the keyword from the step
      registration.

**Why.** Part of the assembly rewrite this plan deliberately leaves out: "chain membership is derived from
the declared candidate predicates, not from claim side effects, so a consumer cannot bind to a
pre-operator artifact and export raw records as final; pass-through operators therefore claim eagerly."
A step no longer needs to declare that it defers.

**Verify.** The assembly tests in `tests/test_workflow_adaptation.py` and whatever the rewrite settles on.
Related: the port-assembly proof of concept lives in `experiments/` (`assembler_v2.py`,
`assembler_v2_checks.py`), untracked, and survives any revert or branch.

---

## Definition of done, per item

1. the code change, with the reason kept in the code as a comment or docstring rather than only here
2. the test named above passing, and failing before the change
3. `uvx pyright` clean on the touched files, and on the static harnesses where they were extended
4. `KG_BUILD_SYSTEM_SPEC.md` updated in the same item, since these are spec changes with code attached
5. one commit per item, message naming the source shape that required it
