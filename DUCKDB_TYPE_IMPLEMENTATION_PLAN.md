# DuckDB type work — implementation plan

Self-contained brief for implementing the DuckDB type acceptance decision. It assumes no prior
conversation: the decisions, the measured evidence behind them, and the exact edit sites are all
recorded here.

- Normative type table: [`DUCKDB_TYPE_ACCEPTANCE_MATRIX.md`](DUCKDB_TYPE_ACCEPTANCE_MATRIX.md)
- Amends: `SOURCE_SCHEMA_TRUST_AND_NULLABILITY_SPEC.md` decisions **D1/D2** and §6 **A4/A6**
  (that spec explicitly defers this work to "one later decision covering all specific types")
- Baseline commit: `6d89c74`. Line references are from that commit and may drift.

## 1. The system in three lines

Typed Python declarations (tables, projections, topology, bindings) compile to a frozen
`BuildBlueprint`, then to a `WorkflowContractIR`, which executes on DuckDB through a dependency
graph of module steps. Authoring types are canonical *logical* types; DuckDB is the only execution
engine; graph properties are the narrowest of the three type sets.

## 2. Three type sets, two gates

```
DuckDB tags ──digest gate──> canonical types ──property gate──> graph property / key types
   set 1      (engines/duckdb)     set 2         (types)                set 3
```

- **Digest rejection** means "no meaning-preserving canonical form exists". Being unusable as a
  graph property is **never** a digest rejection — a transformation converts instead.
- Under this slice the property gate is empty: **set 3 == set 2** for scalars. Nested canonicals
  (`Array`, `Struct`) remain values that must be flattened by `expand()` before becoming properties.

## 3. Locked decisions

| # | Decision | Why |
| --- | --- | --- |
| 1 | Canonical `bool int float str date time timestamp uuid` (+ `Array[T]`, `Struct{…}`) | covers common cases only; `decimal`, `instant`, `interval`, `binary` stay deferred with reasons recorded |
| 2 | `uuid` is its own canonical type, **not** `str` | client already returns `uuid.UUID`; carried with no cast and no conversion |
| 3 | Canonical names are lowercase; **capitalised names mark representative types** | keeps the two vocabularies unmistakable in messages and in the meta-graph document |
| 4 | Representative types are exposed by `kg_build_system.types` as **aliases of stdlib classes** | `ValueExpression[T]`, `ValueSelection[T]`, `PropertySlot[T]` are parameterised by the class, so the annotation class must equal the value's class |
| 5 | Generated files import the **whole** representative set unconditionally from `kg_build_system.types` | an un-imported annotation raises `NameError` while the class body executes; unconditional import makes it structurally impossible |
| 6 | The ingest boundary **only widens**; any narrowing needs an author declaration | `TIME_NS → TIME` rounds and `TIMESTAMP_NS → TIMESTAMP` truncates **silently** — measured |
| 7 | The declared/narrowing gate lives at **generation time**, not runtime | the engine is only available there, and the generation fingerprint covers source bytes so later drift makes the contract stale |
| 8 | Reference project adopts **typed temporal properties** | the point of the work; requires decision 9's promotion mechanism (see §7) |
| 9 | A declared **temporal promotion** is supported for top-level columns | `read_json_auto` leaves `YYYY-MM-DDTHH:MM` as `VARCHAR`, so temporal typing of JSON feeds must be declared, not inferred |
| 10 | Wide integers (`UBIGINT`, `HUGEINT`, `UHUGEINT`) cast to `BIGINT` at the scan | without it a `HUGEINT` property silently becomes `DOUBLE` in Parquet export — measured |

## 4. Measured facts to trust (all on duckdb 1.5.5)

Re-verify with the commands in §12.

**Client conversions.** `BIGNUM`→`str`; `ARRAY[n]`→`tuple` while `LIST`→`list`; `ENUM`/`UNION`/
`VARIANT` lose their type identity; `UUID`→`uuid.UUID`; `DATE`/`TIME`/`TIMESTAMP*`→`datetime.*`;
`INTERVAL`→`timedelta`; `DECIMAL`→`Decimal`; `BLOB`→`bytes`; `TIMESTAMPTZ`→`datetime` whose
**tzinfo comes from the session `TimeZone`, not the data**. `json.dumps` rejects the
date/time/datetime/timedelta/Decimal/bytes/UUID family.

**Computation truth.** `CAST(127 AS TINYINT) + 1` **aborts** (arithmetic stays at the operand
width); `FLOAT * DOUBLE` → `FLOAT`; `BIGINT + UBIGINT` → `HUGEINT`; `DECIMAL / DECIMAL` → `DOUBLE`;
`DATE + INTERVAL` → `TIMESTAMP`; `DATE - DATE` → `BIGINT`; `NaN = NaN` is true and `NaN` is the
maximum; arithmetic and casts are checked, never wrapping.

**Parquet round-trip losses** (relevant because graph properties are exported untyped):
`HUGEINT`/`UHUGEINT`→`DOUBLE`, `BIGNUM`/`BIT`/`ENUM`→`VARCHAR`, `ARRAY[n]`→`LIST`,
`UNION`→`STRUCT(tag, …)`.

**Reader inference of date-shaped strings** — this is what makes §7 necessary:

| value | `read_json_auto` | `read_csv_auto` |
| --- | --- | --- |
| `2026-08-02` | `DATE` | `DATE` |
| `2026-08-02T14:20` (no seconds) | **`VARCHAR`** | `TIMESTAMP` |
| `2026-08-02T14:20:00` | `TIMESTAMP` | `TIMESTAMP` |
| `2026-08-02T14:20:00+02` | `TIMESTAMP` | — |

`CAST(text AS TIMESTAMP)` is **checked**: malformed text and out-of-range dates both error, which is
what makes a declared promotion safe.

**Type surface.** `SELECT type_name FROM duckdb_types() WHERE type_oid IS NOT NULL` gives 39
canonical tags. `cursor.description[i][1]` is a `DuckDBPyType` with only `.id` and `.children`;
`.id` is the lowercase family tag and **`.id` for JSON is `varchar`**, while `.children` carries
decimal precision/scale, array size, map key/value and enum labels.

## 5. Vocabulary to build

| Canonical | Representative | Class | Canonical SQL type at the scan |
| --- | --- | --- | --- |
| `bool` | `bool` | builtin | `BOOLEAN` |
| `int` | `int` | builtin | `BIGINT` |
| `float` | `float` | builtin | `DOUBLE` |
| `str` | `str` | builtin | `VARCHAR` |
| `date` | `Date` | `datetime.date` | `DATE` |
| `time` | `Time` | `datetime.time` | `TIME` |
| `timestamp` | `Timestamp` | `datetime.datetime` | `TIMESTAMP` |
| `uuid` | `Uuid` | `uuid.UUID` | `UUID` |
| `Array[T]` | `Array[T]` | `kg_build_system.types.Array` | `T[]` |
| `Struct{…}` | declared `Struct` subclass | framework | `STRUCT(…)` |

Representative import line in every generated file that declares anything:

```python
from kg_build_system import Field, Struct, Table, TableOptions, field
from kg_build_system.types import Array, Date, Time, Timestamp, Uuid
```

## 6. Work packages

### WP1 — representative types in the `types` package
- Define `Date`, `Time`, `Timestamp`, `Uuid` in `kg_build_system/types/models.py` next to the
  existing authoring markers `Array` and `Nullable` (`models.py:19-23`), as plain aliases
  (`Timestamp = datetime.datetime`, …).
- Export them from `kg_build_system/types/__init__.py` and its `__all__`.
- Add the four **classes** to `_UNITS` in `types/normalization.py:13`. Nothing else in
  `normalize_type` changes: it dispatches on class identity, so both spellings converge.
- Widen the static bounds: `AuthoringDataType` (`table/fields.py:23-26`),
  `GraphValue`/`NonNullableGraphValue` (`topology/models.py:14-20`),
  `SelectionUnit` (`expressions/selections.py:21`).
- **Acceptance:** `Field[Date | None]`, `Field[Timestamp]`, `Field[Uuid]` and their stdlib spellings
  all normalise to the expected `UnitType`; `uv run pyright` clean; add `assert_type` rows to
  `tests/typecheck_unified_fields.py` and `tests/typecheck_graph_bindings.py`.

### WP2 — canonical vocabulary
- Replace the three independent `{"bool", "int", "float", "str"}` literals — `types/models.py:34`,
  `types/codec.py:41-45`, `types/ir_codec.py:43-46` — with one exported name set.
- Add constants `DATE`, `TIME`, `TIMESTAMP`, `UUID` beside `BOOL/INT/FLOAT/STR` (`models.py:80-83`).
- Extend `UnitTypeIR.name: Literal[...]` (`types/ir.py:10-11`) and remove the
  `cast(Any, value.name)` in `types/mapping.py:11-12` that currently hides the narrowing from Pyright.
- **Acceptance:** `UnitType("uuid")` constructs and round-trips through `encode_type`/`decode_type`
  and `encode_type_ir`/`decode_type_ir`; `UnitType("decimal")` still raises.

### WP3 — expression dispatch, no new classes
- `expressions/factory.py:37-44` is a **bare subscript**: a new unit name raises `KeyError`, not the
  intended `TypeError` at `:45`. Fix the lookup and route `date`/`time`/`timestamp`/`uuid` to the
  generic `ValueExpression` — no new expression families, no new operators in this slice.
- `expressions/literals.py:13-22` (`_infer`) and `:55` (the `expected` dict, also a bare subscript)
  need the four classes so `value_expression(datetime(2026, 1, 1))` works and a wrong literal raises
  `TypeError`.
- **Acceptance:** `tests/test_typed_expressions.py` extended; a mismatched literal still raises
  `TypeError` naming the expected type.

### WP4 — the digest table and the inference gate
- New `kg_build_system/engines/duckdb/types.py` holding the matrix as data:
  `duckdb tag → (canonical | declared-only | refused + reason)`, plus
  `canonical → canonical SQL type`.
- Replace `_SCALAR_TYPES` (`schema_inference.py:62-85`) and `_REJECTED_TYPES` (`:88-113`) with reads
  of that table. Move `schema_inference.py` off its own copies.
- Correct the drift: add `BIGNUM` and `TIME_NS` (both currently in **neither** dict, so they fall to
  the generic "unsupported type" branch); delete the unreachable keys `VARINT`, `CHAR`, `BPCHAR`,
  `TEXT`, `STRING`, `REAL` — `DESCRIBE` normalises to canonical names, and `VARINT` is reported as
  `BIGNUM`, so the intended `→ int` mapping can never fire.
- Fix the `"VARCHAR"` fallbacks at `:202-205` (`_array_item_text`) and `:423`, which invent a type
  for list elements and struct members; they must carry the real inferred type.
- `_resolve_scalar` (`:181-195`) gains a third exit for declared-only types, naming the measured
  behaviour ("rounds nanoseconds", "aborts above 2^63-1").
- Keep `test_domain_boundaries.py` honest: `code_generation` must not import `compile`/`workflow`/
  `modules`/`api` (`:48-74`), and `engines` stays a lower layer (`:62-70`).
- **Acceptance:** a new test enumerates `duckdb_types()` canonical tags and asserts each is
  classified exactly once and that no table key is unreachable. This test is what keeps the matrix
  from going stale; it replaces the deleted `scripts/` tooling.

### WP5 — widening at the source view
- `SourceRelationInstructionIR` (`modules/core/ir.py:47-61`): `declared_columns: tuple[str, ...]`
  becomes a sequence of `(name, canonical type)`. Payloads are `strict` + `extra="forbid"`, so the
  shape change forces `CoreModule.VERSION` `"2"` → `"3"` (`modules/core/core.py:491`).
- Built at `CoreModuleCompiler._source_step` (`core.py:318-349`); applied in
  `CoreExecutor._define_source` (`core.py:626-662`), whose whole view is line `642`,
  `SELECT * FROM {scan_function}('{location}')`. Emit
  `CAST("col" AS <canonical>) AS "col"` for every declared column.
- **Preserve column names** — `_require_declared_columns` (`core.py:504-542`) diffs `DESCRIBE` output
  against `declared_columns` and would report spurious "absent field" failures.
- Widen **before** the aggregation union (`core.py:598-614`), or partitions disagree on type.
- `BLUEPRINT_SCHEMA_VERSION` `3` → `4` (`compile/models.py:13`, `:27`); decoders at
  `compile/codec.py:384-386` and `compile/validation.py:32-33` reject anything else.
- **Acceptance:** a source whose physical type is narrower than the canonical builds; one requiring
  an undeclared narrowing fails at generation, not at execution.

### WP6 — declared temporal promotion (enables decision 8)
- `DataContractInferenceConfig` (`schema_inference.py:711-717`) gains a top-level
  `promote: dict[str, canonical_name]`, e.g. `{"recorded_on": "timestamp"}`.
- The provider treats the promoted column as the declared canonical type for contract purposes while
  the reader still reports `VARCHAR`; the scan applies the checked `CAST`.
- Scope limit, deliberately: **top-level columns only.** Nested promotion (e.g. `areas[].defects[].
  observed_on`) needs `read_json(columns={…})`, which would replace sniffing with a declared schema
  and change JSON's trust tier from *defaulted* to *declared* — a separate decision.
- **Acceptance:** promoting a column holding `2026-07-14T06:15` yields `Field[Timestamp | None]`;
  promoting a column with unparseable text fails the build with the DuckDB conversion error.

### WP7 — property paths and targets
- `modules/targets/file.py:157-175`: replace `json.dumps(..., default=str)` with an explicit
  per-canonical encoder. `default=str` would otherwise write `2026-07-14 06:15:00` (space, not
  ISO-8601 `T`) and never complain about a future unmapped type.
- `modules/targets/meta_graph/topology.py:45-46` `display_type` follows automatically.
- `modules/targets/meta_graph/render.py:186-193` `typeFamily` is JS with only `bool/int/float/str`;
  the new names silently render as `composite`. Extend it, and bump the document
  `schema_version` `Literal[2]` → `Literal[3]` (`meta_graph/ir.py:78`).
- `modules/targets/meta_graph/module.py:92,192` order example values with `key=repr` and serialise
  with `default=str`; define a canonical text form and ordering per canonical type or example
  determinism is accidental.
- `modules/targets/neo4j/module.py:105-117` validates property **names** only and `_select_sql`
  (`:473-475`) exports properties **uncast**. Add a target capability declaration plus a
  compile-time diagnostic — a capability gap is the target's problem to report, not a reason to
  shrink the vocabulary or to coerce silently.

### WP8 — pin the session state
- `workflow/executor.py` sets four DuckDB knobs and none that affect semantics. Pin `TimeZone` at
  connection setup, beside `configure_framework_macros`, and record the pinned value in contract
  provenance. Measured default here: `Europe/London`, inherited from the machine.

## 7. Reference project conversion (decision 8)

All reference temporal values are `YYYY-MM-DDTHH:MM` **without seconds**, which `read_json_auto`
infers as `VARCHAR` (§4). So regenerating changes nothing on its own — WP6 is the enabler.

| Column | Location | Today | After WP6 |
| --- | --- | --- | --- |
| `surveyed_on` | `surveys.json`, top level | `Field[str \| None]` | `Field[Timestamp \| None]` |
| `recorded_on` | `readings/temperature.json`, `readings/mechanical/vibration.json` | `Field[str \| None]` | `Field[Timestamp \| None]` |
| `observed_on` | nested in `areas[].defects[]` and their `observations[]` | `Field[str \| None]` | unchanged — needs nested promotion |
| `survey_period` | `equipment.json` | `Field[str \| None]` | unchanged — values are `2026-Q3`, a period label |

Then, per column that becomes typed:
- the `PropertySlot` in the owning `reference_project/topology/<node>/__init__.py` becomes
  `PropertySlot[Timestamp]`;
- bindings in `reference_project/bindings/...` must satisfy the exact-type rule
  (`binding/factories.py:21-24`), so a nullable `Timestamp` needs `where_present()` or
  `default_to(...)` just as the existing string properties do;
- `reference_project/build/{graph.jsonl,meta_graph.json,build_report.json,workflow_contract.json}`
  and the `neo4j-import` Parquet bundle are regenerated and re-committed.

Spec note: `SOURCE_SCHEMA_TRUST_AND_NULLABILITY_SPEC.md` §6 **A7** records that these values were
deliberately written as `YYYY-MM-DDTHH:MM` to dodge the old rejection. Decision 8 reverses part of
A7; the spec must say so, and the no-seconds format is now load-bearing for §4's VARCHAR behaviour —
worth a comment in the data or the request so nobody "fixes" the format and silently starts
inferring `TIMESTAMP` without a declaration.

## 8. Version and fingerprint bumps

| Artefact | Now | To | Site |
| --- | --- | --- | --- |
| Blueprint schema | `3` | `4` | `compile/models.py:13`, `:27` |
| Core module | `"2"` | `"3"` | `modules/core/core.py:491` |
| Generation format | `"4"` | `"5"` | `code_generation/rendering.py:25` |
| Meta-graph document | `2` | `3` | `modules/targets/meta_graph/ir.py:78` |
| Workflow contract | `1` | unchanged | `test_domain_boundaries.py:152-156` pins its exact field set |

`FORMAT_VERSION` is a fingerprint input, so every generated package goes stale at once — intended.
Also add `# ruff: noqa: F401` to the generated header beside `# fmt: off` and `# isort: skip_file`,
since the representative import line is now unconditional.

## 9. Tests to update

- `tests/test_source_schema_trust.py` — heaviest: the unmappable-types loop (`:445-462`) loses
  `DATE`/`TIME`/`TIMESTAMP`/`_S`/`_MS`; the nested-rejection fixture (`:472-484`) is built on `DATE`
  and must switch to a still-rejected type; `:486-497` asserts a `DATE` column raises, which
  inverts; `:602-603` pins `CoreModule.VERSION`.
- `tests/test_logical_types.py` — `:22-34` vocabulary and rejection cases; `:59-64` asserts
  `UnitType("decimal")` raises; add codec round-trips for the new names (none exist today).
- `tests/test_typed_expressions.py:23-30` and `tests/test_unified_fields.py:55-63` exercise the
  four-name dispatch dict directly.
- `tests/test_meta_graph_module.py` — `:364-374` `test_display_type_matches_the_authoring_vocabulary`
  is *the* vocabulary assertion; `:750-792` hard-codes type strings and an expected `families` list.
- `tests/test_blueprint_ir.py:95,136,155-159` and `tests/test_topology_hierarchy.py:456,458` pin
  blueprint schema version 3.
- `tests/test_code_generation.py:135,204-207` assert rendered `Field[str]` text; `:412-465` asserts a
  nested-array shape that the LIST widening changes; `:467-503` pins the rejection error wording.
- `tests/test_domain_boundaries.py:78-91` — `kg_build_system.__all__` must not gain `*IR` names; the
  representative aliases are safe, but verify.
- Static: `tests/typecheck_unified_fields.py:35-45`, `typecheck_data_declarations.py:33-36`,
  `typecheck_graph_bindings.py`, `typecheck_topology_hierarchy.py`. These go red **first**, because
  the `TypeVar` bounds reject the new classes until WP1 lands.

## 10. Documents to amend

- `SOURCE_SCHEMA_TRUST_AND_NULLABILITY_SPEC.md` — preamble `:11-14`; §5 decision 4 `:343-346`; §6 A4
  `:469-511` (the deferred decision being closed); A6 `:625-630` (records the override exit as
  removed — decision 7 reinstates it in generation); A7 `:667-676`; D1/D2 rows `:719-720`.
- `KG_BUILD_SYSTEM_SPEC.md` §3 `:62-102` for the new `UnitType` vocabulary and §15 delivery scope.
- `EDIT_TIME_GENERATED_PACKAGE_SPEC.md` `:253-258` states JSON is rejected — now false; and
  `:197-207` shows the `Field[str]` rendering example.
- `DUCKDB_TYPE_ACCEPTANCE_MATRIX.md` — the normative table; already records `uuid` (lowercase
  canonical), the representative-type rule and the unconditional generated import.

## 11. Sequencing

1. **WP1 + WP2 + WP3** — vocabulary and dispatch. No behaviour change for existing types, so the
   suite stays green throughout. Independent of everything else.
2. **WP4** — the digest table plus the `duckdb_types()` completeness test. Lands the drift guard on
   its own and lets the provider delegate.
3. **WP5** — widening, payload, blueprint and core version bumps.
4. **WP6** — declared promotion.
5. **Reference project** — regenerate, retarget properties, rebuild artifacts. First real end-to-end
   proof; depends on 1–4.
6. **WP7** — targets, in three independently shippable pieces.
7. **WP8** — tiny, can ride along anywhere.

## 12. Verification

```powershell
uv run pyright                      # static contracts, includes tests/typecheck_*.py
uv run pytest -q                    # runtime suite (pytest is now a declared dev dependency)
uv run kbs generate --check         # from the repo root; freshness of generated contracts
uv run kbs generate                 # regenerate, then re-run the two checks above
python reference_project/build.py   # end-to-end build; inspect reference_project/build/
```

Engine facts worth re-checking after any DuckDB upgrade:

```sql
SELECT type_name FROM duckdb_types() WHERE type_oid IS NOT NULL ORDER BY type_oid;
SELECT current_setting('TimeZone');
SELECT typeof(CAST('2026-08-02T14:20' AS TIMESTAMP));
```

## 13. Explicitly out of scope

`DECIMAL(p, s)` (needs a parameterised canonical plus DuckDB's result-width growth rules, and no
division operator — `DECIMAL / DECIMAL` returns `DOUBLE`); `instant` and zoned times; `interval`;
`binary`; `MAP`; `VARIANT`; nanosecond precision; **all new expression operators** — including
comparison and filtering, so temporal properties store, deduplicate, merge and export correctly but
cannot yet be compared or filtered in the authoring language.
