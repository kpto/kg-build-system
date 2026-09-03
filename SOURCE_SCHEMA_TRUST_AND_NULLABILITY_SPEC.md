# Source Schema Trust and Nullability — Specification

## Status

**Implemented**, except for the exits that were considered and dropped: A5d, recorded
in §9, and the work items no longer listed above. The rest of A1–A8 landed, together
with the A7 migration of the reference project. Coverage lives in
`tests/test_source_schema_trust.py`; §9 records where the implementation departs from
a work item's wording, and why. The open decisions D1–D5 were settled (§7) before
implementation.
How an individual type is *represented* — dates, timestamps, decimals — was left out of
scope here and deferred to a later decision covering all specific types together (§8);
this document decided only that a type with no total mapping is rejected rather than
guessed at.

**Amendment — DuckDB type acceptance.** That later decision has since been taken, and it
partly supersedes this document. The normative type table is
[`DUCKDB_TYPE_ACCEPTANCE_MATRIX.md`](DUCKDB_TYPE_ACCEPTANCE_MATRIX.md); the plan is
[`DUCKDB_TYPE_IMPLEMENTATION_PLAN.md`](DUCKDB_TYPE_IMPLEMENTATION_PLAN.md). They supersede
**D1** for `date`, `time`, `timestamp` and `uuid`, which became canonical types that the
digest gate accepts rather than refuses, while **D2** stands: `decimal` remains refused and
deferred. They close **A4**'s deferral, reinstate the in-band override **A6** had recorded
as removed — now at generation time, as a declared temporal promotion — and reverse part of
**A7**. Superseded passages are marked where they stand rather than deleted, because this
document stays the record of the decision as it was taken. What survives of it intact is
the rule that a type with no meaning-preserving canonical form is refused rather than
guessed at, and that nullability is never inferred from a value's shape.

This document specifies how data-contract inference decides nullability, and how the
framework verifies declared non-nullability against the data that actually arrives.
It amends `KG_BUILD_SYSTEM_SPEC.md` §§3 (canonical logical types), 9 (table groups and
physical sources) and 10 (blueprint IR) — written `KG_BUILD_SYSTEM_SPEC.md §n` below, so
that a bare `§n` always means a section of this document. It is independent of
`TABLE_LAYER_ALIGNMENT_SPEC.md`, which stays deferred.

All measurements quoted below were taken against the installed wheel in an isolated
project. Appendix A carries the fixture, the verification script and its output; nothing
outside that directory is required.

**Revision note.** An earlier version concluded that DuckDB discards the nullability a
Parquet file declares and that pyarrow was therefore needed to read it. That was wrong:
`DESCRIBE` reports *catalog constraints*, while DuckDB exposes the file's own
`REQUIRED`/`OPTIONAL` repetition types through `parquet_schema()`, per node, per file,
with `duckdb_type` already mapped. See §2.1, §2.2 and §8. The dependency is gone from
the plan and the track is now dependency-free.

---

## 1. Problem

Inference over a physical source produces a logical contract. Two defects were
measured in that step, pointing in opposite directions, and neither is currently
detectable.

1. **Over-claiming.** Struct members inferred from a schema-less source are declared
   non-nullable. `data/articles.json` contains `"email": null` twice; the generated
   contract declares `email: Field[str]`.
2. **Under-claiming.** Parquet records `required`/`optional` per field, per list item
   and per struct member. Inference consults only `DESCRIBE`, which reports catalog
   constraints, so a Parquet `required` column is inferred nullable — even though
   `parquet_schema()` exposes that same declaration (§2.2). The two defects are not
   symmetric: on a Parquet file inference under-claims at top level and over-claims at
   member level, in the same pass.

The first defect was followed end to end. A node bound from that contract produced
(excerpted — `_kg_binding_symbol` and `type` dropped; the full records are in
appendix A):

```json
{"build_key": "author::ra@example.org", "email": "ra@example.org", "kind": "node"}
{"build_key": "author::",               "email": null,             "kind": "node"}
```

`succeeded: True`, no failures, exit code 0. Three distinct violations were reported
as success:

- a property declared non-null at both the contract and the ontology was emitted null;
- the non-null-scalar build key invariant was voided, because
  `concat('author::', NULL)` returns the well-formed non-null string `'author::'`,
  which the invariant is satisfied by as a *value*;
- every null-keyed entity therefore shared one graph identity, so
  `collapse_exact_duplicates` or `merge_compatible_facts` would merge distinct
  entities into one node.

A null in a property is a data-quality defect. A null in an identity produces a wrong
graph. Nothing in the contract, the report or the exit code distinguishes the two.

---

## 2. Evidence

### 2.1 `DESCRIBE` reports constraints, not source metadata

The `null` column of `DESCRIBE` answers one question: *does an enforced `NOT NULL`
constraint exist on this relation?* It is not a summary of what the source declares.
Calibrated against known cases:

| expression | `null` | reading |
|---|---|---|
| literal `42` | `YES` | no constraint possible |
| a Parquet column the file marks `required` | `YES` | answers a different question |
| stored table column with `NOT NULL` | `NO` | correct |
| stored table column without it | `YES` | correct |
| through a view over a `NOT NULL` column | `NO` | constraint propagates |
| `information_schema` for that view | `YES` | weaker source than `DESCRIBE` |

So `str(row[2]).upper() != "NO"` in `schema_inference.py:338-340` is sound — whenever
it yields non-nullable, that is true — but for a file scan it is always `YES` because a
table function has no catalog constraint, not because the source declared nothing. The
existing rule is correctly scoped to constraints and then relied on for declarations.

Nested members never get a `DESCRIBE` row at all. They are parsed out of the flattened
type string `STRUCT("name" VARCHAR, email VARCHAR, …)`, which carries no nullability, so
`_field_for_type` falls back to a literal (`schema_inference.py:111` for array items,
`:138` for struct members). The consequence is that `Field[Array[str | None]]`, which
the logical model expresses natively, is **unreachable from inference**.

### 2.2 Parquet declares nullability, and DuckDB already exposes it

Parquet records nullability as a repetition type per schema node — `REQUIRED`,
`OPTIONAL`, `REPEATED` — at field, list element and struct member level. DuckDB reads
it and publishes it through the `parquet_schema()` table function. On a file whose
`DESCRIBE` said `YES` for everything:

```text
parquet_schema('truthful.parquet')
  ('schema',     'REQUIRED', None,      children 3)
  ('article_id', 'REQUIRED', 'VARCHAR', None)
  ('abstract',   'OPTIONAL', 'VARCHAR', None)
  ('authors',    'REQUIRED', None,      children 1)   -- LIST
  ('list',       'REPEATED', None,      children 1)
  ('element',    'OPTIONAL', None,      children 2)   -- list item nullable
  ('name',       'REQUIRED', 'VARCHAR', None)
  ('email',      'OPTIONAL', 'VARCHAR', None)
```

All three levels are present, they genuinely differ within one file, and
`duckdb_type` arrives already in the vocabulary `_SCALAR_TYPES` consumes. Two further
properties matter:

| capability | measurement |
|---|---|
| multi-file and partitioned sources | `parquet_schema('part/*/*.parquet')` returns one row set **per file**, so per-file divergence is a comparison rather than a limitation |
| hive partition keys | DuckDB's own read of the same glob yields `id, note, day` while `parquet_schema` knows only `id, note` — the partition column exists in no file |
| null counts without a scan | `parquet_metadata(...)` reports `stats_null_count` per file, column and row group: `id 0 of 2`, `note 1 of 2` |

Arrow was evaluated as the instrument for this and measured independently:
`pq.read_schema` recovered the same declaration exactly (`round-trips exactly: True`),
which confirms the information is genuinely in the file rather than inferred. As a
*reader* it is worse:

| source | pyarrow result |
|---|---|
| JSON **top-level array** | `ArrowInvalid: JSON parse error: Column() changed from object to array in row 0` — it requires NDJSON; `read_json_auto` reads the array natively |
| NDJSON inference | marks **every** member nullable, including `name`, which is never null |
| malformed one-line CSV (authored by the fixture, appendix A) | five garbage columns, **0 rows**, and a duplicate column name where DuckDB de-duplicates with `_1` |
| Arrow type space | `timestamp[s]` where DuckDB said `DATE`; all-null column infers `null_type`; also `decimal128`, `dictionary<>`, `map<>`, `union<>`, `binary`, `duration` |

Adopting Arrow would therefore add a dependency, a second type surface, and a second
reader whose view of the file could disagree with the reader that executes — to obtain
information DuckDB already returns. It is not used.

Independently, no reader — Arrow included — can derive non-nullability from a
schema-less file, because absence of nulls in a sample proves nothing about the
population.

### 2.2a How trustworthy is a Parquet `required`?

`required` is a declaration, not a read-time verification: nothing re-checks it while
scanning. It is nevertheless difficult to violate by accident, because writers police
it themselves:

```text
pq.write_table(pa.table({"id": [1, None]}, schema=field("id", int64, nullable=False)))
  ArrowInvalid: Column 'id' is declared non-nullable but contains nulls
```

So a `required` field holding nulls means either a non-conforming writer or a corrupt
file. `stats_null_count` (§2.2) detects it per file without reading rows, more cheaply
than any guard and without the pruning caveat of §2.4 — but it reports the problem, it
does not stop the value being emitted. Decision 5 fixes the roles.

### 2.3 The framework's existing authoring guards are sufficient once inference is honest

Binding a *nullable* field was attempted three ways; all three were rejected before
any build ran:

| attempt | result |
|---|---|
| nullable expression → `PropertySlot[str]` | `TypeError: AuthorNode.email expects UnitType(name='str'), but the expression resolves to NullableType(value=UnitType(name='str'))` |
| `nullable.expression.prepend("author::")` | `AttributeError: 'NullableExpression' object has no attribute 'prepend'` |
| nullable selection as `build_key` | `TypeError: build_key must not be nullable` |
| hand-declared `Field[str]` → non-null slot and key | **accepted** |

Correcting inference (§3) alone turns the §1 incident into an authoring-time
`TypeError`. The remaining exposure is exactly the last row: a non-null **claim** that
no engine verified.

### 2.4 Runtime verification with `error()`

A guard `CASE WHEN v IS NULL THEN error(msg) ELSE v END` in lowered SQL:

- `error()` raises `InvalidInputException: Invalid Input Error: <msg>`;
- `CREATE MACRO _kg_nn(v, msg := 'unexpected NULL') AS …` works, with positional and
  named arguments, and fires from inside a `CREATE VIEW`;
- cost is within noise — 5,000,000 rows through `COPY … TO parquet`, plain and
  guarded alternating, two rounds each: 173 / 141 / 137 / 143 ms. The two `plain` runs
  differ from each other by more than plain differs from guarded, so the finding is
  "no measurable cost", not a ratio;
- the message can incorporate sibling columns, which makes it actionable:
  `Invalid Input Error: AuthorNode.email is null for build_key 8`.

It is **pruned** when the column is not consumed. Over a view containing one null:

| consumer query | guard fired |
|---|---|
| `SELECT * FROM lazy` | yes |
| `COPY (SELECT * FROM lazy) TO parquet` | yes |
| `SELECT col FROM lazy WHERE id = 2` | yes |
| `SELECT col FROM lazy WHERE id = 1` | no (row filtered — correct) |
| `SELECT count(col) FROM lazy` | yes |
| `SELECT count(*) FROM lazy` | **no** |
| `SELECT count(id) FROM lazy` | **no** |
| `SELECT max(id) FROM lazy` | **no** |

Pruning is acceptable for **emission safety** — if no consumer reads the column, no
corrupt value was produced — and disqualifying for **audit**, because the same query
either reports a violation or does not depending on a downstream module's column list,
and `error()` aborts on the first row with no count and no key list.

### 2.5 The ownership exit is currently closed

Generated files carry `# Generated by kg-build-system. Do not edit manually.`
(`rendering.py:26`). Correcting one by hand:

| action | result |
|---|---|
| `kbs generate --check` | exit 1 — `owned generated file was unexpectedly modified: …` |
| `kbs generate` | exit 1 — `Generation failed: owned generated file was unexpectedly modified: …` |

Neither path can promote the correction nor discard it. The only exits are deleting
the product and regenerating, or hand-writing the contract outside the owned package.

### 2.6 Two related gaps noticed en route

**Declared format is never checked against the file.** `InputFormat` offers
`csv | json | parquet` (`table/models.py`) and core maps them to `read_csv_auto`,
`read_json_auto`, `read_parquet` (`core.py:424`). `DataSourceConfig.__post_init__`
validates only that the location is non-empty, so a wrong `format` is accepted at
compile time and fails during execution:

```text
read_csv_auto('truthful.parquet')  -> Invalid Input Error: Error when sniffing file …
read_json_auto('t.tsv')            -> Invalid Input Error: Malformed JSON in file …
```

This is loud, which is worth saying — unlike §1 — but it is late and in DuckDB's
vocabulary, so it belongs to A5c rather than being its own work item.

Inference itself accepts ten suffixes (`schema_inference.py:31,33`: `.csv .tsv .json
.jsonl .ndjson .parquet .pq` plus `.db .ddb .duckdb`). Most are bindable by declaring the
matching format: `.tsv` parses correctly because `read_csv_auto` sniffs the delimiter, and
`.jsonl .ndjson .pq` map onto the JSON and Parquet readers. Only the **three database
suffixes have no execution reader at all** — they can be inferred into a contract that
can never be bound. A8 keeps that narrower version.

**`DECIMAL` is silently coerced to `float`.** `_SCALAR_TYPES` maps `"DECIMAL": "float"`
(`schema_inference.py:35,49`), and `_base_type` strips at the parenthesis, so
`DECIMAL(18,2)` reaches that entry. Measured, lossy:

```text
parquet_schema: ('amount', 'FIXED_LEN_BYTE_ARRAY', 'DECIMAL(18,2)')
DESCRIBE:       ('amount', 'DECIMAL(18,2)')
value:          Decimal('1234567890123456.78')   ->  cast to DOUBLE: 1234567890123456.8
```

The revision makes this *more* important, not less: `parquet_schema.duckdb_type` reports
`DECIMAL(18,2)` directly, so the tier-2 path A3 introduces flows straight through the
same lossy entry. A4 covers it.

---

## 3. Model: three levels of schema trust

The discriminator is not typed versus untyped formats. It is **whether the source
declares nullability, and whether that declaration is enforced**.

| tier | source | who declares | authority | behaviour |
|---|---|---|---|---|
| 1 | `.db` / `.ddb` / `.duckdb` relation | enforced `NOT NULL` | `DESCRIBE` | honour it exactly as today. Inference-only: no `InputFormat` selects a database reader, so such a contract cannot be bound (A8) |
| 2 | Parquet, `.pq`, single file or directory | declared, unenforced | `parquet_schema()` | honour all three levels |
| 3 | JSON, NDJSON, JSONL, CSV, TSV | nobody | `DESCRIBE` for structure only | **nullable everywhere** |

Tiers map to states one-to-one: tier 1 is `ENFORCED`, tier 2 is `DECLARED`, tier 3 is
`DEFAULTED`. Three states, not two, are therefore needed and must survive to the
generated file:

| state | meaning | renders as | verified how |
|---|---|---|---|
| `DECLARED` | the source asserts non-null | `Field[X]` | **guard at the point of use, always**; plus a statistics pre-flight count where the format provides one |
| `ENFORCED` | an upstream store guarantees it | `Field[X]` | not re-checked |
| `DEFAULTED` | the source says nothing | `Field[X \| None]` | n/a |

Statistics are a pre-flight, not the enforcement, for three reasons. They exist only for
Parquet and only when the writer emitted them, and §2.3 shows the remaining exposure is
hand-declared contracts, which overwhelmingly sit on JSON and CSV where there are none.
They describe the files inspected at one moment, while a build reads whatever exists
later — a new partition, a re-exported file, a directory that gained a day. And they
describe *physical columns only*: the §1 incident came from a derived expression, which
no file statistic can speak about. The guard travels with every build and sits where the
declared type actually applies.

For every source that can actually be bound, this collapses to a binary: Parquet →
`parquet_schema()` truth; everything else → nullable everywhere.

### 3.1 Parquet directories, hive keys, and who owns which question

`schema_inference.py:224` permits a directory source only for Parquet, `:310` reads it
with `hive_partitioning = true`, and a `layout="files"` mode exists. Per-file schemas
are no obstacle — `parquet_schema()` already returns one row set per file for a glob, so
divergence across files is a comparison and a policy choice rather than a limitation.

Hive partition keys are a real obstacle to reading the file metadata alone. Measured on
`part/day=<date>/part-0.parquet`: DuckDB's own read yields `id, note, day` while
`parquet_schema()` knows only `id, note`, because the partition column is derived from
the directory layout and exists in no file. Therefore:

> **DuckDB decides which columns exist. `parquet_schema()` decides how each is shaped.**

`DESCRIBE SELECT * FROM read_parquet(?, hive_partitioning = true)` is authoritative for
the column set; `parquet_schema()` is authoritative for nested structure and per-level
nullability; the two are joined on node path. A DuckDB column with no metadata
counterpart (a hive key) is `DEFAULTED`. A metadata node with no DuckDB counterpart is a
generation failure, because the two views of the file disagree.

The join is the work: metadata arrives as a flat Parquet node list using the three-level
list convention (`list` / `element`, grouped by `num_children`), which has to be folded
into the logical shape and matched to paths such as `authors[].email` against
`authors.list.element.email`.

---

## 4. Decisions

1. Nullability is never derived from observed values. `DESCRIBE` remains the structural
   boundary; the comment at `:322-323` is retained and corrected to say that the
   `null` column reports only *enforced* constraints and is therefore silent about what
   a file declares.
2. Where the source declares nothing, every level is nullable — fields, list items and
   struct members alike.
3. **No new dependency.** Parquet nullability comes from DuckDB's own
   `parquet_schema()` and its per-file null counts from `parquet_metadata()`.
   `read_parquet` remains the only reader, so there is one engine, one type vocabulary,
   and no second view of a file that could disagree with the one that executes.
   pyarrow was measured (§2.2) and is not adopted; see §8.
4. Types map totally and fail closed. An unrecognised DuckDB type name raises rather
   than falling through, and `DECIMAL` is rejected rather than coerced to `float` (§2.6).
   Rejecting a type is only safe while an author has somewhere else to put the column:
   export it in a mappable type, or declare that table outside a generated package.
   *Superseded in part.* The fail-closed rule stands, and so does the refusal to coerce
   `DECIMAL` — the digest gate still refuses every type with no meaning-preserving
   canonical form. What changed is the size of the mapped set: `DATE`, `TIME`,
   `TIMESTAMP` and `UUID` now digest to the canonical types `date`, `time`, `timestamp`
   and `uuid`, and the third exit assumed missing here exists as a generation-time
   declaration (A6).
5. File statistics are a **pre-flight diagnostic, never the enforcement**. Their best
   use is at generation — the one moment the author can still change the request: "you
   declared `Field[str]` for `amount`; this file reports 1 null in 4 rows." At build they
   run first, so a guard failure can be reported with a count and a file rather than as a
   bare abort. An **absent** statistic is unknown, never zero.
6. **One mechanism for keys and properties alike.** Every output expression whose
   non-nullness rests on a `DECLARED` claim is guarded at the point of use — build,
   source and target keys and property expressions are handled by the same rule in the
   same place. There is no key-specific check.
7. What differs is only the **permitted fallback after detection**, because only one of
   the two has an honest value left to emit:
   - a `DECLARED` **property** that receives null — the null *is* the honest value; it is
     what a nullable property would have emitted, it stays visible in the output, so
     publishing a finding and continuing would be coherent. **D4 chose abort instead**:
     one severity for every guard failure, no configuration knob, and no module of the
     `RejectConflictingNonNullValuesConfiguration` shape;
   - a **key** that resolves to null or degenerate — there is nothing honest to emit.
     Emitting the value collides entities, a sentinel manufactures the same collision,
     and dropping the record loses rows silently. Abort is the only option, which is why
     keys expose no knob.
   The measured case is `concat('author::', NULL)` returning the well-formed string
   `'author::'`: a satisfied declared invariant, a value that looks fine, and two entities
   merged by the next operator that groups on it.
8. Two secondary differences are cost, not design. The pruning weakness of §2.4 barely
   applies to keys because `merging.py:132` and `conflict_validation.py:215` group on
   `build_key`, `deduplication.py:109` selects distinct, `targets/neo4j/module.py:462-471`
   casts to `:ID` / `:START_ID` / `:END_ID` and `targets/file.py:158` selects every
   column; whereas `targets/meta_graph/module.py:134` runs `SELECT COUNT(*)`, the shape
   that skips a property guard — which is why the counted path of A5b exists. And
   statistics can pre-count a bare source column but never a composed expression, whether
   that expression is a key or a property.
9. Nullable properties stay nullable — a null in a nullable property is data, not a
   violation.

---

## 5. Work items

Line numbers are as of writing.

### A1 — Nullability provenance in generated output

*No behaviour change. Do first: it is what makes every later item legible.*

*Not a dependency of A5a.* A1 is a header comment, and lowering cannot read comments, so
the tri-state never needs to reach the blueprint. A5a's trigger is simply "this output
expression has a non-null static type", which after A2 already means a human or a format
asserted it: tier 3 is always nullable and tier 1 cannot be bound at all. Nothing about
`DECLARED` needs plumbing from the generator to the compiler.

| site | change |
|---|---|
| `code_generation/models.py` (near `GeneratedScalarType:60` … `GeneratedPackage:132`) | add a tri-state `Nullability` = `DECLARED` / `ENFORCED` / `DEFAULTED`; carry a per-source provenance note on `GeneratedPackage` |
| `code_generation/rendering.py:145-146`, beside the existing `# request:` and `# fingerprint:` stamps | emit one header line per source |

```python
# nullability: enforced by relation 'readings' in 'stored.duckdb' (NOT NULL)
# nullability: declared by '_truthful.parquet' (required/optional)
# nullability: not declared by 'data/articles.json' (json) — all members nullable
```

This is the only signal available to a reader who cannot edit the file, and it is what
distinguishes "the framework determined this is optional" from "the framework has no
idea".

**Cost:** header bytes feed `generation_fingerprint` (`rendering.py:29`), so every
generated package regenerates once. Batch with A2.

**Tests:** header content per tier; identical inputs give an identical fingerprint; an
existing product reports stale once and then current.

### A2 — Assume nullable for schema-less sources, at every level

*The core fix. Breaking; see A7.*

| site | change |
|---|---|
| `schema_inference.py:102` | `_field_for_type` takes `Nullability` instead of `nullable: bool` |
| `:111` | array-item recursion stops passing literal `False` |
| `:138` | struct-member recursion stops passing literal `False` |
| `:338-340` | map `DESCRIBE` output **by tier**: tier 1 → `NO` = `ENFORCED`, `YES` = `DEFAULTED`; tier 3 → `DEFAULTED` regardless of the flag; tier 2 is not decided here — A3 overrides it from `parquet_schema()`, since `DESCRIBE` reports `YES` for every file column |
| `:301-317` | the query builder already branches on suffix; decide the tier once here |
| `:322-323` | correct the comment to state the real rule |

**Tests:** JSON with nulls yields `Field[str | None]` for a struct member and
`Field[Array[str | None]]` for array items; a `.duckdb` relation with `NOT NULL` still
renders non-null; no tier-3 input can render a non-nullable nested member; the §1
binding is rejected at authoring with the `TypeError` from §2.3.

### A3 — Parquet nullability from `parquet_schema()`

*Needs A1 and A2. No new dependency.*

- Query `parquet_schema(<glob>)` for the resolved source. It returns one row per schema
  node per file: `name`, `repetition_type`, `type`, `num_children`, `duckdb_type`,
  `column_id`. Applies to a single file and to a directory alike.
- Fold the flat node list into the logical shape using the standard three-level list
  convention: a group with `num_children` owns the following subtrees; `REPEATED`
  wrappers `list` / `element` collapse to an array whose item nullability is
  `element`'s repetition type. Measured in §2.2: `authors REQUIRED`, `element OPTIONAL`,
  `name REQUIRED`, `email OPTIONAL`.
- Join to the DuckDB column set by path per §3.1. `REQUIRED` → `DECLARED`,
  `OPTIONAL` → `DEFAULTED`; a DuckDB-only column → `DEFAULTED`; a metadata-only node →
  generation failure.
- Compare per-file row sets; per D3 a divergence across a partitioned directory **fails**,
  naming both paths and both files, rather than silently taking the first file.
- Derived struct class names keyed on the member **path**, not the leaf name, so two
  unrelated structs may share a member name.
- For tier 2 this replaces the struct-member regex at `:133` and `_split_top_level` at
  `:82`: a node tree arrives instead of a string to be re-lexed.
- Execution path unchanged; `read_parquet` remains the only reader.
- Remote sources: **unverified**. `parquet_schema()` almost certainly resolves globs and
  registered filesystems the way `read_parquet` does, but that has not been measured
  here, and credentials are runtime-only today (`modules/core/credentials.py`), so remote
  inference may still need the A6 seam. Treat local sources as the supported case until
  tested.

**Tests:** required/optional nested members reach the contract; list-item nullability is
carried separately from field nullability; a hive-partitioned source yields the partition
column as `DEFAULTED`; two files with differing schemas raise; a directory source is
handled in the same pass as a single file.

### A4 — Total type mapping, and removing the silent `DECIMAL` coercion

*Independent of A3, though A3 supplies the type names it must accept.*

- `_SCALAR_TYPES` becomes total over the DuckDB type names that `DESCRIBE` and
  `parquet_schema.duckdb_type` can produce. An unrecognised name raises rather than
  falling through, so a new DuckDB type fails closed instead of silently defaulting.
- Remove `"DECIMAL": "float"` (`:49`). Per D2 a `DECIMAL` is **rejected**; how one would
  be represented is part of the deferred type decision below, not this one.
- Rejections carry the nested path (`authors.affiliation.country`), not the leaf name.
- Per D1 `DATE`, `TIMESTAMP` and `TIME` are **rejected** rather than rendered as
  `Field[str]`: `read_json_auto` types `published` as `DATE` today and inference
  silently produces a string, which invites a date into an identity key. `str` is not a
  lossy *value*, but it is a lossy *type*, and a rejection stays visible where a silent
  `Field[str]` disappears. *(Superseded: `DATE`, `TIME`, `TIMESTAMP` and `UUID` are
  canonical types now, each digested to its own canonical name rather than to `str`; the
  argument that a silent `Field[str]` is unacceptable is what decided it.)*

**What rejection removes.** `DECIMAL` plus the eleven temporal entries `DATE`, `TIME`,
`TIME WITH TIME ZONE`, `TIMESTAMP`, `TIMESTAMP WITH TIME ZONE`, `TIMESTAMP_S`,
`TIMESTAMP_MS`, `TIMESTAMP_NS` and friends — every one of which currently maps silently
to `str` or `float` (`schema_inference.py:49-61`).

**Cost.** None for this repository, because the fixture moved rather than the rule. The
reference project's date-shaped strings used to sniff as `DATE` and render as `Field[str]`,
so rejection would have failed five sites: `surveys.surveyed_on`,
`temperature.recorded_on`, `vibration.recorded_on`, and a nested `observed_on` in
`surveys.areas[].elements[].defects[]` and in `… .observations[]`. Those columns now hold
`YYYY-MM-DDTHH:MM` instants, which `read_json_auto` leaves `VARCHAR` (A7), so every column
in `reference_project/data` maps into an existing scalar. A rejected type is therefore
covered by unit tests on synthetic fixtures, not by the reference project — which is where
it belonged anyway. If a future fixture reintroduces a bare ISO date, generation fails
loudly, and that is the intended behaviour.

*(Superseded, two ways: a bare ISO date is digested as canonical `date` now rather than
refused, and the columns named above are typed by declared promotion rather than left
`VARCHAR` — see A7.)*

**Deferral — closed.** *How* a specific type is represented — `DATE`, `TIMESTAMP`, `TIME`,
`DECIMAL`, and any other DuckDB name with no total mapping into the current logical
scalars — was deliberately **not** decided here, and was deferred to one later decision
covering all specific types together. That decision has been taken:
[`DUCKDB_TYPE_ACCEPTANCE_MATRIX.md`](DUCKDB_TYPE_ACCEPTANCE_MATRIX.md) is its normative
type table and [`DUCKDB_TYPE_IMPLEMENTATION_PLAN.md`](DUCKDB_TYPE_IMPLEMENTATION_PLAN.md)
its plan. `date`, `time`, `timestamp` and `uuid` became canonical types alongside
`bool int float str`, each with a representative type for author annotations; `decimal`,
`instant`, `interval` and `binary` stay refused with a reason recorded per row, so the
`DECIMAL` coercion removed here is still removed. What this item decided for the interim —
reject, fail closed, name the column path — is unchanged and is exactly the matrix's
`reject` disposition. The author-side exit anticipated in the last sentence landed too, as
A6's generation-time `promote:` declaration, not as a runtime override.

**Tests:** one per rejected type name; a table-driven test asserting every type name
produced by a fixture is either mapped or rejected. These run on synthetic fixtures the
test writes, since no repository data reaches a rejected type any more.

### A5 — Verification in framework terms

- **A5a — null guards at lowering.** One pass over the binding's output expressions,
  which already live in a single dict in `modules/core/lowering.py:45` `lower_binding_sql`
  — `build_key` at `:49`, `source_build_key` and `target_build_key` at `:52-53`, and the
  properties alongside them; core wraps the relation at `modules/core/core.py:302-304`.
  Wrap each expression whose static type is non-null but whose non-nullness rests on a
  `DECLARED` claim. Keys and properties are not separate cases and should not read as
  separate code. Emit
  `CREATE OR REPLACE MACRO _kg_nn(v, msg := 'unexpected NULL')` at connection setup in
  `DuckDBRelationService` (`workflow/services.py`), before any view exists: macro names
  are database-scoped and `duckdb_storage="disk"` opens a fresh database per build, so
  creation must be idempotent and namespaced, matching the existing `__kg_materialized_`
  prefix convention. Messages are composed at lowering time from declaration identity
  and the row key, per §2.4. Per decision 7 and D4 **everything aborts**: a key has no
  honest value to emit, and a `DECLARED` property that receives null aborts the same
  way, so neither exposes a configuration knob. This is the only mechanism that prevents a
  corrupt value being emitted, and the only one that reaches composed expressions.
- **A5a′ — remove the existing null-key blind spot.** `conflict_validation.py:214`
  currently filters `WHERE "build_key" IS NOT NULL`, so the one operator positioned to
  notice a null-keyed record excludes it from its own findings. With A5a in place the
  filter becomes redundant; if A5a does not land first, it should at least report the
  records it skips rather than discarding them silently.
- **A5b — null-count pre-flight.** Sits in core's own source step
  (`core::table.{table}`; `core.py:202` `_source_step`, executed by `_define_source` at
  `:413`), which is the first step of every build, takes no inputs, and is the only step
  that ever touches a physical location. That placement satisfies "runs **before** the
  guarded query" by construction: every other step reaches the data only through the
  `core:data.table.{name}` role this step emits, so assembly already guarantees it
  completed before any consumer can fire a guard. No new module, step kind or role
  re-export, and the workflow graph gains no edges.

  Three consequences of placing it there:

  - view creation is lazy (`CREATE VIEW` reads nothing), so the pre-flight must issue its
    own metadata query rather than piggybacking on the `CREATE VIEW`;
  - a module executor never sees the blueprint, so `SourceRelationInstructionIR`
    (`core/ir.py`) has to carry the declared paths and their declared nullability, in the
    dotted `path_in_schema` form `parquet_metadata()` reports next to the logical path.
    The meta-graph module already ships static topology in its payload for the same
    reason;
  - `CoreModule.VERSION` goes `"1"` → `"2"`, because the payload shape changed.

  The check itself: for Parquet, `parquet_metadata().stats_null_count` per file, column
  and row group — footer metadata only. Unlike `DESCRIBE`, `path_in_schema` covers nested
  members, so `authors.list.element.email` is checkable. For JSON and CSV there is
  nothing to read and an absent statistic is **unknown**, never zero (decision 5). Per
  D5 the scanned `SUM(CASE WHEN col IS NULL THEN 1 ELSE 0 END)` aggregate is **dropped**,
  so on a non-Parquet source the step does nothing at all and A5b's entire build-time
  cost is one footer read.

  It reports and never fails. A statistic tests a claim, it does not set or enforce one
  (decision 5), so the step must not abort on a count; enforcement stays with A5a. This
  also moves A5b's centre of gravity to **generation**, the one moment the author can
  still change the request — the build-time half is the count that `error()` cannot
  produce, published the way `modules/operators/conflict_validation.py` publishes.

  Scope differs per call site: at generation every declared column is checked; at build
  only the paths a binding actually reads, which compile time knows exactly. Otherwise a
  forty-column table whose three used columns are clean fills the report with
  thirty-seven unread ones.
- **A5c — source shape check.** Same step as A5b, immediately after the view is created
  (`core.py:164` `kg_table_N`, `:424` `read_*_auto`) and **before** the A5b counts, since
  a missing column makes a null count meaningless. Compare declared fields against the
  relation's columns using metadata only, and raise naming the **declaration** and
  the **source location** before any binding step runs. Today the same condition
  surfaces as `Binder Error: Referenced column "cited" not found in FROM clause!
  Candidate bindings: "cited\nA-003", "citing"`. Placing it here also means it runs before
  any guard can fire, since `nn()` on a missing column reproduces that exact error. The
  same sniff also
  pre-empts the declared-format mismatch of §2.6, which today fails mid-execution as
  `Error when sniffing file …` or `Malformed JSON in file …`.
- **A5d — nullable concatenation diagnostic. Deliberately not implemented.**
  This item asked for an explicit `TypeError` on nullable concatenation, replacing
  `'NullableExpression' object has no attribute 'prepend'`. Implementing it made
  things worse, and the item was wrong.

  A method declared on `NullableExpression` is invisible to a type checker even
  when its body only raises. Before, `nullable.expression.prepend("author::")` was
  a Pyright error at authoring time; with the stub it type-checked clean and failed
  at build time. Verified on one receiver, `NullableExpression[str, StrExpression]`:
  the stubbed `prepend` produced no diagnostic, while the undefined `default_to`
  produced *"Cannot access attribute"*. Absence is the only form a static check can
  see — a method annotated `NoReturn` is still a legal call.

  Because `reference_project` is type-checked in `strict` mode, and the system
  spec's authoring practices require checking static contracts as well as runtime
  behaviour, trading the earliest possible signal for a friendlier runtime message
  is a net loss. The calculations and the null-policy methods therefore stay
  undefined on this family; `tests/test_source_schema_trust.py::
  NullableOperationTests` asserts their absence across the union of the concrete
  families, so an operation added later cannot quietly regress, and `nullable.py`'s
  module docstring records why the absence is load-bearing.

**Deliberate behaviour change:** guards live inside the view, so a consumer that only
reads can now fail a build that previously passed — the meta-graph's `approx_top_k`
sampling being the obvious case, since `COUNT(*)` is a shape that prunes a property guard
while `SELECT *` is not. Under D4 there is no finding-and-continue path, so one contract
can pass a build configured with only the file target and fail once the meta-graph module
is added. The mitigations all sit upstream of execution: A2 stops the claim being made in
the first place, A5b at generation shows the nulls while the request can still change, and
an author who wants the null keeps it nullable.

### A6 — Exit paths

*Not implemented. Neither remaining bullet is needed until inference reads remote
sources; the exits that do exist are out-of-band.* *(Amended: an in-band type exit now
exists at generation time — see the note at the end of this item.)*

- Edit-time credential resolver, required only if inference is to read remote sources
  at all — Parquet or otherwise. Credentials are runtime-only today
  (`modules/core/credentials.py`).

The in-band override this item once called for was implemented and then removed. A
rejected or mis-shaped column therefore has two exits, both outside the request:
export the column in a mappable type, or declare the table outside a generated
package. Hand-editing a generated file remains refused (§2.5), which is deliberate —
a generated product that no longer matches its request is not a contract anyone can
regenerate.

**Amended — the in-band exit is reinstated, at generation time.** Decision 7 of
`DUCKDB_TYPE_IMPLEMENTATION_PLAN.md` places the declared/narrowing gate where the engine
is available rather than at runtime, so `DataContractInferenceConfig` carries a top-level
`promote: dict[str, canonical_name]` — `{"recorded_on": "timestamp"}` — and the
declaration lives in the author-owned request file, never in the product (work package
WP6). Three things this does **not** reopen:

- it is a declaration, not an inference. The provider treats the promoted column as that
  canonical type for contract purposes while the reader still reports `VARCHAR`, and the
  scan applies the checked `CAST`;
- it is a **declared-only** route for every type whose only available cast narrows the
  value or its precision — `TIMESTAMP_NS`, `TIME_NS`, `HUGEINT`, `UBIGINT`, `UHUGEINT` —
  and the ingest boundary only widens otherwise. A type with no meaning-preserving
  canonical form is still refused, and scope stops at top-level columns: nested promotion
  would replace sniffing with a declared schema and move JSON from the *defaulted* tier to
  the *declared* one, which is a separate decision;
- hand-editing a generated file remains refused (§2.5). The generation fingerprint covers
  source bytes, so data that drifts away from the declaration makes the contract stale
  rather than silently wrong — which is why the gate can sit at generation and still be
  honest.

### A7 — Migration, same release as A2

Regenerate `reference_project/table/**`. Expect failures wherever `.pick` on a formerly
non-nullable member now yields a `NullableSelection`, each needing an explicit
`default_to` or `where_present`. This is the design working as intended — the null
decision moves to the binding that must own it — but it breaks downstream authors and
needs a written note, not just a version bump.

**Measured for this repository.** All **23** non-nullable `Field[...]` members in
`reference_project/table/**` are nested members and **none** is a top-level table field:
the §1 asymmetry, visible in the committed product. They are read by eighteen `.pick`
sites, but nullability propagates along the whole path (§5 of the system spec), so only
paths whose every ancestor is non-null actually change. `premises` and `surveyor` are
already nullable at top level, which is why `site_city` and the surveyor fields already
carry a `default_to` — the six picks in `bindings/site` and `bindings/survey` are
unaffected. Every affected path runs through the two projections, where each ancestor is
a non-null expanded array item (`areas[] → elements[] → defects[] → observations[]`).

Seven binding inputs break, all in the projection-fed bindings:

| input | site | failure |
|---|---|---|
| `defect_id` | `bindings/defect` `build_key` | `TypeError: build_key must not be nullable` |
| `observation_uid` | `bindings/observation` `build_key` | same |
| `title`, `condition_rating` | `DefectNode` properties | `TypeError` naming the slot type |
| `value`, `observed_by`, `observed_on` | `ObservationNode` properties | same |

`summary` reuses `title` and `observation_uid`, so it moves with them. The `expand()`
inputs — `elements`, `defects`, `observations` — need nothing, since a nullable array
legitimately yields no rows.

For a **key** the two remedies differ in consequence: `default_to` gives every null the
same value, so those records share one build key and are merged downstream, while
`where_present` drops the row. The framework does not check key uniqueness and does not
try to — see §9.2 for how the shipped migration note states this.

**D1's cost was removed by moving the fixture, not the rule.** `surveyed_on`,
`recorded_on` and both nested `observed_on` columns held bare ISO dates, which
`read_json_auto` sniffs as `DATE`; they now hold `YYYY-MM-DDTHH:MM` instants, which DuckDB
leaves `VARCHAR`. That form was chosen because a reading, an observation and a survey visit
each happen at a moment, so the data became more precise rather than evasive, and because
it still reads as a timestamp to whoever edits it next. Inference renders `Field[str]`
either way — `_SCALAR_TYPES` maps `DATE`, the `TIMESTAMP*` family and `VARCHAR` all to
`str` — so **no generated contract changes** and A7's migration is the seven binding inputs
above and nothing else. *(That last clause was true only while D1 stood; superseded below.)*

**Amended — decision 8 reverses part of this.** `DATE`, `TIME`, `TIMESTAMP` and `UUID` are
canonical types now, so `Field[str]` is no longer what inference renders either way: it
renders `Field[str]` for a `VARCHAR` column and `Field[Timestamp | None]` for a temporal one.
The reference project adopts typed temporal properties, so `surveys.surveyed_on`,
`readings/temperature.recorded_on` and `readings/mechanical/vibration.recorded_on` become
`Field[Timestamp | None]`, each with its `PropertySlot[Timestamp]` in the owning topology
node and its binding remedy (`where_present()` or `default_to(...)`) under the exact-type
rule. The two nested `observed_on` columns stay `Field[str | None]` — nested promotion is
out of scope — and `equipment.survey_period` stays a string because `2026-Q3` is a period
label, not a moment.

What the fixture move did *not* survive is its dispensability. The `YYYY-MM-DDTHH:MM`
no-seconds form is now **load-bearing**: `read_json_auto` reports a value written with
seconds as `TIMESTAMP` and one written without as `VARCHAR`, and only the A6 declaration
applies the checked `CAST`. Typing those columns is therefore a decision recorded in the
request, not an accident of how the bytes are spelled. "Fixing" the format to include
seconds would make the reader infer `TIMESTAMP` where nothing has been declared, and would
leave the promotion in the request doing nothing anyone would notice; the plan asks for a
comment in the data or the request so that stays visible.

### A8 — En-route cleanups

Independent and small.

- The three database suffixes (`.db .ddb .duckdb`) produce contracts that cannot be
  bound, because no `InputFormat` selects a database reader: either add one, or reject
  them at generation with "this source can be inferred but never bound".

---

## 6. Sequencing

```
A1 ──┬─→ A2 ──┬─→ A3
     │        └─→ A6
A5a, A5a-prime, A5b, A5c  independent of A1-A4 (A5b and A5c share core's source step,
                      A5c first; that step precedes every guard by assembly order)
A4 independent
A5d withdrawn - a static rejection already beats the runtime message it asked for
A7 ships with A2
A8 independent
Deferred: how specific types are represented — not A1-A8, one later decision (§8)
          [taken: DUCKDB_TYPE_ACCEPTANCE_MATRIX.md; A4's deferral is closed]
```

- **A1** can ship alone; it changes no behaviour.
- **A2 + A7** are the breaking batch and the actual fix. If only one thing ships, it is
  this.
- **A5a is the only item that prevents** a corrupt value reaching the graph. A5b counts,
  A5c explains — none of the others stop anything. **A5c** is the highest value per line
  among the diagnostics, because it converts a late SQL failure into a framework-term
  message regardless of what else lands. A5d was dropped: see its item for why a static
  rejection beats a better runtime message.
- **A3, A4 and A5b** are additive precision with no breaking change and no new
  dependency.

---

## 7. Resolved decisions

| # | decision | resolution | consequence |
|---|---|---|---|
| D1 | `date` / `timestamp` | **Superseded** for `date`, `time`, `timestamp` and `uuid` by [`DUCKDB_TYPE_ACCEPTANCE_MATRIX.md`](DUCKDB_TYPE_ACCEPTANCE_MATRIX.md): each is a canonical logical type now, with representative types `Date`, `Time`, `Timestamp`, `Uuid` for annotations, and each is digested rather than refused. What was decided here was: **Reject** at inference — not a logical scalar, not a silent `Field[str]`, and not `CustomDataType` either, because picking a representation was exactly what was deferred. Refusal remains the rule for every type the matrix refuses (`TIME WITH TIME ZONE`, `TIMESTAMP WITH TIME ZONE`, `BIGNUM`, …) | Was: fail-closed per decision 4; the reference fixture moved to `YYYY-MM-DDTHH:MM` instants, so nothing in `reference_project/data` reached a rejected type and no generated contract changed (A4, A7). Now: the deferral is closed by the matrix, and those top-level columns are typed by a declared temporal promotion, which makes the no-seconds format load-bearing (A7) |
| D2 | `decimal` | **Reject** outright, same basis as D1 — **and this verdict stands.** `decimal(p, s)` is still a refused type in the matrix, deferred because it needs a parameterised canonical type plus DuckDB's result-width rules, and because `DECIMAL / DECIMAL` returns `DOUBLE`, so no division operator may be offered. The silent `DECIMAL → float` coercion stays removed | Removes the last silent coercion in `_SCALAR_TYPES`. No `DECIMAL` occurs in the reference data, so nothing there needs adapting |
| D3 | per-file divergence in a partitioned directory | **Fail**, naming both paths and files | A partitioned source is only inferrable when every file agrees; unifying to a `DEFAULTED` union stays a future option |
| D4 | severity for a `DECLARED` **property** that receives nulls | **Abort**, same as a key | One severity, no configuration knob, and no findings module for A5a. A build can now fail purely because a read-only consumer was added — see A5's behaviour-change note |
| D5 | statistics absent for a `DECLARED` Parquet column | **Proceed on the guard alone**, no count | The `SUM(CASE WHEN col IS NULL …)` aggregate is deleted from A5b; unknown stays unknown and a build-time null check costs one footer read |

---

## 8. Non-goals

- Deriving nullability, types or cardinality from observed data. Statistics about null
  counts (A5b) may **test** a claim a source already made; they may never **set** one.
- **Adding pyarrow, or any second reader.** Measured (§2.2): it rejects a top-level JSON
  array DuckDB reads natively, marks every NDJSON member nullable including one never
  observed null, reproduces the malformed-CSV failure identically, and brings a type
  surface (`null_type`, `dictionary<>`, `map<>`, `union<>`, `decimal128`) the framework
  would then have to police — all to obtain what `parquet_schema()` already returns.
- Any change to the logical type model. D1 and D2 both reject rather than add a type, so
  no new logical scalar enters the IR, and `Array[T | None] | None` already expresses
  every level Parquet declares — the IR needs no new fields, only correct population.
- Choosing how a specific type is represented. `DATE`, `TIMESTAMP`, `TIME` and `DECIMAL`
  are rejected here as a stop-gap, not as a verdict: the representation question spans all
  specific types at once — custom scalars, temporal and exact-numeric semantics, which of
  them may be keys or properties, and how each maps through `CustomDataType` — and belongs
  to one later decision rather than to per-type patches in the inference table.
- Cross-source joins or lookups; `relational/planner.py` still requires one driving
  source and no lookup API exists.

*Amended by the DuckDB type acceptance work* (§7 D1/D2, §5 A4) *:* the two type-related
bullets above held nothing back permanently. `date`, `time`, `timestamp` and `uuid` have
since entered the logical type model as canonical types, closing the deferral; `decimal`,
`instant`, `interval` and `binary` did not, and are refused with a reason per row. Nothing
here was overturned about **nullability**: it is still never derived from observed values,
and the trust tiers *enforced / declared / defaulted* are unchanged.

---

## 9. Implementation notes

### 9.1 Where the implementation departs from the wording of a work item

1. **A5a — where the macro is created.** The item asks for creation "at connection
   setup in `DuckDBRelationService`". It is created by `configure_framework_macros`
   in that module, called from `_configure_duckdb` in the executor: still before any
   view exists, still idempotent, and now after `USE`, so it lands in the database
   the build actually works in. Creating it in the service constructor instead
   submits a statement to the worker thread, which blocks any connection that blocks
   on its first statement — and `tests/test_duckdb_runtime.py` has exactly such a
   connection, the one that verifies Ctrl-C interrupts a running query.
2. **A5a — a guard reads a renamed column.** A guard cannot alias its output to the
   name of the column it reads: DuckDB rejects a select item that shadows a source
   column of its own select list. A lowered binding is therefore three levels — the
   row product, a rename to `_kg_raw_*`, and the guarded select over it — which is
   also what lets a guard name its row by `build_key` in its message.
3. **A5b — what counts as a read path.** A nested reference reaches the engine as the
   outermost field plus `expand`/`struct_field` operations over it, so a read of a
   prefix counts as a read of everything beneath it: reading `evidence` puts
   `evidence.labels` into the pre-flight as well.
4. **A3 — how the declared tier is tested.** DuckDB writes every Parquet node
   `optional` whatever the source column's constraint, and §8 excludes a second
   writer, so a file declaring `required` cannot be produced inside the suite. The
   declared tier is tested against fixed `parquet_schema()` row sets in the shape
   DuckDB returns for a real file; the per-file divergence check runs on two real
   DuckDB-written files.

### 9.2 A7 — the migration note for authors

A2 makes every member of a schema-less source nullable, so a contract inferred from
JSON, NDJSON, JSONL, CSV or TSV no longer promises non-nullity anywhere. A member read
through `.pick` yields a `NullableSelection`, and a projection that publishes one
passes nullability downstream. Nothing shifts silently: each newly nullable value
fails at the binding that must own it, with a `TypeError`.

The reference project needed exactly seven inputs, all in projection-fed bindings:
`defect_id` and `observation_uid` as build keys, `title` and `condition_rating` on
`DefectNode`, and `value`, `observed_by` and `observed_on` on `ObservationNode`.

Two remedies exist and they differ in one respect worth knowing before choosing:

- **`where_present()`** drops the row.
- **`default_to(fallback)`** keeps the row and gives the null the named value.

On a **key**, `default_to` gives every null the *same* value, so those records share
one build key and any collapse or merge operator downstream treats them as one
entity. The migrated bindings in the reference project use `where_present()` for keys
and `default_to()` for properties, which reflects what the data means there: a defect
with no identifier is not the same defect as another unlabelled one, while a defect
with no title is still the same defect.

Choosing otherwise is a legitimate authoring decision and the framework does not
second-guess it. Nothing checks key uniqueness — a column can be non-distinct in the
source and stay that way — and the guard added by A5a is a **nullity** check only.
The case in §1, where `concat('author::', NULL)` yields the well-formed string
`'author::'`, passes it silently, as decision 7 already concedes. Identity is the
author's responsibility; this note states the consequence rather than trying to
enforce it.

Widening a `PropertySlot` to `T | None` is a third answer, for a graph that genuinely
has absent values. It changes the published type of the component, so it is a
topology decision rather than a migration step.

The contracts are regenerated first — `kbs generate`, then `kbs generate --check`. A
contract whose source is Parquet may gain non-null members rather than lose them,
because the declared tier (§3) now reads the file's own `required`/`optional` instead
of ignoring it.

Widening a `PropertySlot` to `T | None` is a third answer, for a graph that genuinely
has absent values. It changes the published type of the component, so it is a
topology decision rather than a migration step.

Regenerate before migrating — `kbs generate`, then `kbs generate --check`. A contract
whose source is Parquet may gain non-null members rather than lose them, because the
declared tier (§3) now reads the file's own `required`/`optional` instead of ignoring
it.

---

## Appendix A — reproduction

Everything asserted in this document comes from the script below. It is self-contained:
it writes its own fixture, needs nothing outside the directory it runs in, and prints
one labelled line per claim in the body text.

**Prerequisites.** An empty working directory; a virtual environment containing the
built wheel (`uv build --wheel`, then install the wheel) so that only what
`pip install kg-build-system` delivers is visible; and `pip install pyarrow`, which the
preamble itself needs to write the two Parquet fixtures — it is required, not optional.
Measured on python 3.12.12, duckdb 1.5.5, pyarrow 25.0.1.

**Two ordering facts the script encodes.** The ownership test edits a generated file,
so it must run last. And any previous run's generated product must be deleted first,
otherwise generation reports an ownership conflict before anything else happens — which
is itself the §2.5 defect, arriving early and confusingly.

**The malformed CSV is authored here, deliberately.** Record separators are written as
the two characters backslash-n, producing a file of one physical line. This models a
source whose record separator is wrong. It is not framework behaviour; it exists to
give A5c something to diagnose.

```python
"""Self-contained verification of every measurement in
SOURCE_SCHEMA_TRUST_AND_NULLABILITY_SPEC.md.

Run with the virtual environment's python, from any empty directory:

    python verify_spec.py

Nothing outside this directory is read.
"""

import decimal
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.json as paj
import pyarrow.parquet as pq
import kg_build_system as k

ROOT = Path.cwd()
(ROOT / "data").mkdir(exist_ok=True)

# ---------------------------------------------------------------- preamble
FIXTURE = [
    {"article_id": "A-001", "published": "2024-03-11", "abstract": "x",
     "authors": [{"name": "R. Alvarez", "email": "ra@example.org",
                  "affiliation": {"institution": "Northgate", "country": "ES"}},
                 {"name": "K. Obi", "email": None,
                  "affiliation": {"institution": "Lysander", "country": None}}],
     "keywords": ["retrieval"], "funding": [{"grant": "NG-118", "funder": None,
                                             "amount": None}]},
    {"article_id": "A-002", "published": None, "abstract": None,
     "authors": [{"name": "M. Duran", "email": "md@example.net",
                  "affiliation": {"institution": "Cobalt", "country": "PT"}}],
     "keywords": None, "funding": None},
    {"article_id": "A-003", "published": "2023-09-02", "abstract": "y",
     "authors": [{"name": "K. Obi", "email": None,
                  "affiliation": {"institution": "Lysander", "country": None}},
                 {"name": "R. Alvarez", "email": "ra@example.org",
                  "affiliation": {"institution": "Northgate", "country": "ES"}}],
     "keywords": ["graphs"], "funding": [{"grant": "CO-9", "funder": None,
                                          "amount": 120000},
                                         {"grant": "CO-10", "funder": "Cobalt",
                                          "amount": None}]},
    {"article_id": "A-004", "published": "2025-01-20", "abstract": None,
     "authors": [], "keywords": ["nulls"], "funding": []},
]
(ROOT / "data" / "articles.json").write_text(json.dumps(FIXTURE, indent=2), "utf-8")

# A deliberately corrupted csv: every record separator is the two characters
# backslash-n, so the file is one physical line.  Not framework behaviour.
(ROOT / "data" / "malformed.csv").write_text(
    "citing,cited\\nA-003,A-001\\nA-004,A-001\\n", newline=""
)

truthful = pa.schema([
    pa.field("article_id", pa.string(), nullable=False),
    pa.field("abstract", pa.string(), nullable=True),
    pa.field("authors", pa.list_(pa.struct([
        pa.field("name", pa.string(), nullable=False),
        pa.field("email", pa.string(), nullable=True)])), nullable=False),
])
pq.write_table(
    pa.table({"article_id": ["A-001"], "abstract": [None],
              "authors": [[{"name": "R.", "email": None}]]}, schema=truthful),
    "truthful.parquet",
)
pq.write_table(
    pa.table({"id": [1, 2, 3], "col": ["a", None, "c"]}), "guard.parquet"
)
(ROOT / "kb").joinpath("__init__.py").parent.mkdir(exist_ok=True)
(ROOT / "kb" / "__init__.py").write_text(
    "from kg_build_system.code_generation import generation\n"
    "from kg_build_system.code_generation.builtins import (\n"
    "    DataContractInferenceConfig,\n"
    "    InferDataContractProvider,\n"
    ")\n\n"
    "articles = generation(\n"
    "    InferDataContractProvider,\n"
    '    DataContractInferenceConfig(source="../data/articles.json"),\n'
    ")\n",
    "utf-8",
)
# The deadlock test in 2.5b edits the generated package, so any previous run's
# product must be removed first or generation reports an ownership conflict.
for stale in ((ROOT / "kb" / "articles"), (ROOT / "out"), (ROOT / "__pycache__"),
              (ROOT / "kb" / "__pycache__")):
    if stale.is_dir():
        shutil.rmtree(stale)
print(f"python {sys.version.split()[0]}  duckdb {duckdb.__version__}  "
      f"pyarrow {pa.__version__}")


def kbs(*args):
    result = subprocess.run([sys.executable, "-m", "kg_build_system.cli", *args],
                            capture_output=True, text=True, cwd=ROOT)
    return result.returncode, (result.stdout + result.stderr).strip().splitlines()


def one(label, sql, con=None):
    try:
        rows = (con or duckdb.connect()).execute(sql).fetchall()
        print(f"  {label}: {str(rows)[:130]}")
    except Exception as error:
        print(f"  {label}: {type(error).__name__}: {str(error).splitlines()[0][:120]}")


print("\n=== 2.5a generation ===")
print(f"  kbs generate -> exit {kbs('generate', '--project', '.')[0]}")
GENERATED = ROOT / "kb" / "articles" / "__init__.py"
print("  inferred member:", [line.strip() for line in GENERATED.read_text("utf-8").splitlines()
                             if "email" in line and "Field" in line])

print("\n=== 1. the incident: contract non-null, data null ===")
from kg_build_system.modules import (  # noqa: E402
    FileModule, FileModuleConfiguration, register_module,
)
from kb.articles import ArticlesTable  # noqa: E402

source = k.bind_source(target=ArticlesTable, config=k.DataSourceConfig(
    location=(ROOT / "data" / "articles.json").resolve().as_posix(),
    format=k.InputFormat.JSON))


class AuthorNode(k.Node):
    email: k.PropertySlot[str] = k.property()


author = ArticlesTable.authors.expand()
email = author.pick(lambda a: a.email)
binding = k.node_binding(
    target=AuthorNode, build_key=email.expression.prepend("author::"),
    properties=AuthorNode(email=email))
contract = k.compile(bindings=[binding], sources=[source], modules=[
    register_module(FileModule, FileModuleConfiguration("graph.jsonl"))])
report = k.build(contract, output_directory=ROOT / "out", monitor=False)
print(f"  succeeded: {report.succeeded}  failures: {report.unresolved_failures}")
for line in (ROOT / "out" / "graph.jsonl").read_text("utf-8").splitlines():
    print("   ", line)

print("\n=== 2.1 DESCRIBE calibration ===")
con = duckdb.connect()
one("literal 42", "DESCRIBE SELECT 42 AS lit", con)
con.execute("CREATE TABLE t (a INTEGER NOT NULL, b VARCHAR)")
one("stored NOT NULL table", "DESCRIBE SELECT a, b FROM t", con)
con.execute("CREATE VIEW v AS SELECT a, b FROM t")
one("through a view", "DESCRIBE SELECT a, b FROM v", con)
one("required parquet column", "DESCRIBE SELECT * FROM read_parquet('truthful.parquet')",
    con)
print("  information_schema on the view:", con.execute(
    "SELECT column_name, is_nullable FROM information_schema.columns "
    "WHERE table_name='v'").fetchall())

print("\n=== 2.2 pyarrow as an alternative reader ===")
print("  truthful.parquet recovered:", [(f.name, f.nullable)
                                        for f in pq.read_schema("truthful.parquet")])
item = pq.read_schema("truthful.parquet").field("authors").type.value_field
print("  list item nullable:", item.nullable, "| members:",
      [(f.name, f.nullable) for f in item.type])
print("  round-trips exactly:", pq.read_schema("truthful.parquet").equals(truthful))
try:
    paj.read_json("data/articles.json")
    print("  pyarrow on the top-level JSON array: READ OK")
except Exception as error:
    print(f"  pyarrow on the top-level JSON array: {type(error).__name__}: "
          f"{str(error)[:90]}")
(ROOT / "articles.ndjson").write_text(
    "".join(json.dumps(row) + "\n" for row in FIXTURE), "utf-8")
print("  pyarrow NDJSON nullability of never-null 'name':",
      [f.nullable for f in paj.read_json("articles.ndjson").schema
       .field("authors").type.value_field.type])
one("duckdb reads the same array file", "SELECT count(*) FROM read_json_auto("
    "'data/articles.json')", con)
one("duckdb on malformed csv", "DESCRIBE SELECT * FROM read_csv_auto("
    "'data/malformed.csv')", con)
try:
    table = pacsv.read_csv("data/malformed.csv")
    print(f"  pyarrow on malformed csv: columns={table.column_names} rows="
          f"{table.num_rows}")
except Exception as error:
    print(f"  pyarrow on malformed csv: {type(error).__name__}")

print("\n=== 2.2b DuckDB's own Parquet metadata functions ===")
for row in con.execute(
    "SELECT name, repetition_type, duckdb_type, num_children FROM parquet_schema("
    "'truthful.parquet') ORDER BY column_id").fetchall():
    print("  parquet_schema:", row)
print("  DESCRIBE on the same file:", [(r[0], r[2]) for r in con.execute(
    "DESCRIBE SELECT * FROM read_parquet('truthful.parquet')").fetchall()])

partition = ROOT / "part"
shutil.rmtree(partition, ignore_errors=True)
for day in ("2024-01-01", "2024-01-02"):
    folder = partition / f"day={day}"
    folder.mkdir(parents=True)
    pq.write_table(pa.table({"id": pa.array([1, 2], type=pa.int64()),
                             "note": pa.array(["a", None], type=pa.string())}),
                   folder / "part-0.parquet")
print("  parquet_schema over a glob:", con.execute(
    "SELECT DISTINCT name, repetition_type, duckdb_type FROM parquet_schema("
    "'part/*/*.parquet') ORDER BY name").fetchall())
print("  duckdb reads the same glob:", [(r[0], r[1]) for r in con.execute(
    "DESCRIBE SELECT * FROM read_parquet('part/*/*.parquet', hive_partitioning=true)"
).fetchall()])
print("  parquet_metadata stats_null_count:", con.execute(
    "SELECT DISTINCT path_in_schema, num_values, stats_null_count "
    "FROM parquet_metadata('part/*/*.parquet') ORDER BY path_in_schema").fetchall())

print("\n=== 2.2c can a required Parquet field hold nulls? ===")
try:
    pq.write_table(pa.table({"id": pa.array([1, None], type=pa.int64())},
                            schema=pa.schema([pa.field("id", pa.int64(),
                                                       nullable=False)])),
                   "violation.parquet")
    print("  write accepted a null in a required field")
except Exception as error:
    print(f"  write refused: {type(error).__name__}: {str(error)[:110]}")

print("\n=== 2.3 existing authoring guards ===")


class AuthorStruct(k.Struct):
    email: k.Field[str | None] = k.field()


class NullableArticles(k.Table):
    options = k.TableOptions(name="articles")
    authors: k.Field[k.Array[AuthorStruct] | None] = k.field()


nullable_email = NullableArticles.authors.expand().pick(lambda a: a.email)
cases = [
    ("nullable -> PropertySlot[str]", lambda: k.node_binding(
        target=AuthorNode,
        build_key=nullable_email.default_to("u").expression.prepend("a::"),
        properties=AuthorNode(email=nullable_email))),
    ("nullable .expression.prepend as build_key", lambda: k.node_binding(
        target=AuthorNode,
        build_key=nullable_email.expression.prepend("a::"),
        properties=AuthorNode(email=nullable_email.default_to("u")))),
    ("nullable selection as build_key", lambda: k.node_binding(
        target=AuthorNode,
        build_key=nullable_email,
        properties=AuthorNode(email=nullable_email.default_to("u")))),
]
for label, attempt in cases:
    try:
        attempt()
        print(f"  {label}: ACCEPTED")
    except Exception as error:
        print(f"  {label}: {type(error).__name__}: {str(error)[:120]}")


class StrictStruct(k.Struct):
    email: k.Field[str] = k.field()


class StrictArticles(k.Table):
    options = k.TableOptions(name="strict")
    authors: k.Field[k.Array[StrictStruct] | None] = k.field()


strict_email = StrictArticles.authors.expand().pick(lambda a: a.email)
try:
    k.node_binding(target=AuthorNode,
                   build_key=strict_email.expression.prepend("a::"),
                   properties=AuthorNode(email=strict_email))
    print("  hand-declared Field[str] -> non-null slot and key: ACCEPTED")
except Exception as error:
    print(f"  hand-declared Field[str]: {type(error).__name__}: {str(error)[:120]}")

print("\n=== 2.4 error() guard: viability, pruning, cost ===")
con = duckdb.connect()
con.execute("CREATE OR REPLACE MACRO _kg_nn(v, msg := 'unexpected NULL') AS "
            "CASE WHEN v IS NULL THEN error(msg) ELSE v END")
one("nn(1)", "SELECT _kg_nn(1) AS r", con)
one("nn(NULL) default message", "SELECT _kg_nn(NULL) AS r", con)
one("nn(NULL, named)", "SELECT _kg_nn(NULL, msg := 'named') AS r", con)
one("sibling column in message",
    "SELECT id, CASE WHEN col IS NULL THEN error('email is null for id ' || id) "
    "ELSE col END AS col FROM read_parquet('guard.parquet')", con)
con.execute("CREATE VIEW lazy AS SELECT id, _kg_nn(col, 'col') AS col "
            "FROM read_parquet('guard.parquet')")
for label, sql in [
    ("SELECT *", "SELECT * FROM lazy"),
    ("count(*)", "SELECT count(*) FROM lazy"),
    ("count(id)", "SELECT count(id) FROM lazy"),
    ("max(id)", "SELECT max(id) FROM lazy"),
    ("count(col)", "SELECT count(col) FROM lazy"),
    ("WHERE id = 1", "SELECT col FROM lazy WHERE id = 1"),
    ("WHERE id = 2", "SELECT col FROM lazy WHERE id = 2"),
]:
    one(label, sql, con)
con.execute("COPY (SELECT i AS id, concat('v', i) AS s FROM range(5_000_000) r(i)) "
            "TO 'clean.parquet' (FORMAT PARQUET)")
for label, sql in [
    ("plain  ", "COPY (SELECT id, s FROM read_parquet('clean.parquet')) TO 'p1.parquet' "
                "(FORMAT PARQUET)"),
    ("guarded", "COPY (SELECT id, _kg_nn(s, 's') AS s FROM read_parquet('clean.parquet')) "
                "TO 'p2.parquet' (FORMAT PARQUET)"),
    ("plain  ", "COPY (SELECT id, s FROM read_parquet('clean.parquet')) TO 'p3.parquet' "
                "(FORMAT PARQUET)"),
    ("guarded", "COPY (SELECT id, _kg_nn(s, 's') AS s FROM read_parquet('clean.parquet')) "
                "TO 'p4.parquet' (FORMAT PARQUET)"),
]:
    start = time.perf_counter()
    con.execute(sql)
    print(f"  5M rows {label}: {(time.perf_counter() - start) * 1000:.0f} ms")

print("\n=== 2.5b ownership deadlock (runs last: it edits a generated file) ===")
GENERATED.write_text(
    GENERATED.read_text("utf-8").replace("email: Field[str]", "email: Field[str | None]"),
    "utf-8",
)
print("  edited to:", [line.strip() for line in GENERATED.read_text("utf-8").splitlines()
                       if "email" in line and "Field" in line])
for argument in ("generate --check", "generate"):
    code, lines = kbs(*argument.split(), "--project", ".")
    message = lines[-1].split("ERROR")[-1].strip() if lines else ""
    print(f"  kbs {argument} -> exit {code}: {message[:95]}")

print("\n=== 2.6 declared format vs file, and DECIMAL coercion ===")
(ROOT / "t.tsv").write_text("unit_ref\tscore\nU-1\t3.5\nU-2\t4.5\n", "utf-8")
print("  read_csv_auto on a .tsv:", con.execute(
    "DESCRIBE SELECT * FROM read_csv_auto('t.tsv')").fetchall())
for label, sql in [
    ("read_csv_auto on .parquet", "SELECT * FROM read_csv_auto('truthful.parquet')"),
    ("read_json_auto on .tsv", "SELECT * FROM read_json_auto('t.tsv')"),
]:
    one(label, sql, con)
pq.write_table(
    pa.table({"amount": pa.array([decimal.Decimal("1234567890123456.78")],
                                 type=pa.decimal128(18, 2))}),
    "dec.parquet",
)
print("  parquet_schema duckdb_type:", con.execute(
    "SELECT name, duckdb_type FROM parquet_schema('dec.parquet')").fetchall())
print("  exact -> DOUBLE:", con.execute(
    "SELECT amount, CAST(amount AS DOUBLE) FROM read_parquet('dec.parquet')").fetchall())
```

### Verified output

Produced by the script above. Every line below was compared against the raw run; long
reprs are abbreviated with `...`, exception class prefixes are dropped, and `<-` marks
are commentary added here rather than program output. Timing lines are omitted — see
§2.4 for the honest reading of those numbers.

```text
python 3.12.12  duckdb 1.5.5  pyarrow 25.0.1

=== 2.5a generation ===
  kbs generate -> exit 0
  inferred member: ["email: Field[str] = field(name='email')"]        <- over-claim

=== 1. the incident: contract non-null, data null ===
  succeeded: True  failures: ()
    {... "build_key": "author::ra@example.org", "email": "ra@example.org", ...}
    {... "build_key": "author::",               "email": null,            ...}
    {... "build_key": "author::md@example.net", "email": "md@example.net", ...}
    {... "build_key": "author::",               "email": null,            ...}
    {... "build_key": "author::ra@example.org", "email": "ra@example.org", ...}

=== 2.1 DESCRIBE calibration ===
  literal 42:            [('lit', 'INTEGER', 'YES', ...)]
  stored NOT NULL table: [('a', 'INTEGER', 'NO', ...), ('b', 'VARCHAR', 'YES', ...)]
  through a view:        [('a', 'INTEGER', 'NO', ...), ('b', 'VARCHAR', 'YES', ...)]
  required parquet column: [('article_id', 'VARCHAR', 'YES', ...), ...]   <- different question
  information_schema on the view: [('a', 'YES'), ('b', 'YES')]

=== 2.2 pyarrow as an alternative reader ===
  truthful.parquet recovered: [('article_id', False), ('abstract', True), ('authors', False)]
  list item nullable: True | members: [('name', False), ('email', True)]
  round-trips exactly: True
  pyarrow on the top-level JSON array: ArrowInvalid: JSON parse error:
      Column() changed from object to array in row 0
  pyarrow NDJSON nullability of never-null 'name': [True, True, True]
  duckdb reads the same array file: [(4,)]
  duckdb on malformed csv: [('citing', ...), ('cited\\nA-003', ...), ('A-001\\nA-004', ...]
  pyarrow on malformed csv: ArrowInvalid

=== 2.2b DuckDB's own Parquet metadata functions ===
  parquet_schema: ('schema',     'REQUIRED', None,      3)
  parquet_schema: ('article_id', 'REQUIRED', 'VARCHAR', None)
  parquet_schema: ('abstract',   'OPTIONAL', 'VARCHAR', None)
  parquet_schema: ('authors',    'REQUIRED', None,      1)
  parquet_schema: ('list',       'REPEATED', None,      1)
  parquet_schema: ('element',    'OPTIONAL', None,      2)
  parquet_schema: ('name',       'REQUIRED', 'VARCHAR', None)
  parquet_schema: ('email',      'OPTIONAL', 'VARCHAR', None)
  DESCRIBE on the same file: [('article_id', 'YES'), ('abstract', 'YES'), ('authors', 'YES')]
  parquet_schema over a glob: [('id', 'OPTIONAL', 'BIGINT'), ('note', 'OPTIONAL', 'VARCHAR'),
                               ('schema', 'REQUIRED', None)]
  duckdb reads the same glob: [('id', 'BIGINT'), ('note', 'VARCHAR'), ('day', 'DATE')]
  parquet_metadata stats_null_count: [('id', 2, 0), ('note', 2, 1)]

=== 2.2c can a required Parquet field hold nulls? ===
  write refused: ArrowInvalid: Column 'id' is declared non-nullable but contains nulls

=== 2.3 existing authoring guards ===
  nullable -> PropertySlot[str]: TypeError: AuthorNode.email expects
      UnitType(name='str'), but the expression resolves to NullableType(value=UnitType(name='str'))
  nullable .expression.prepend as build_key: AttributeError:
      'NullableExpression' object has no attribute 'prepend'
  nullable selection as build_key: TypeError: build_key must not be nullable
  hand-declared Field[str] -> non-null slot and key: ACCEPTED

=== 2.4 error() guard: viability, pruning, cost ===
  nn(1): [(1,)]
  nn(NULL) default message: Invalid Input Error: unexpected NULL
  nn(NULL, named):          Invalid Input Error: named
  sibling column in message: Invalid Input Error: email is null for id 2
  SELECT *:     Invalid Input Error: col
  count(*):     [(3,)]            <- pruned
  count(id):    [(3,)]            <- pruned
  max(id):      [(3,)]            <- pruned
  count(col):   Invalid Input Error: col
  WHERE id = 1: [('a',)]          <- row filtered, correct
  WHERE id = 2: Invalid Input Error: col
  5M rows plain  : 173 ms      5M rows guarded: 141 ms
  5M rows plain  : 137 ms      5M rows guarded: 143 ms

=== 2.5b ownership deadlock (runs last: it edits a generated file) ===
  edited to: ["email: Field[str | None] = field(name='email')"]
  kbs generate --check -> exit 1: owned generated file was unexpectedly modified: ...
  kbs generate         -> exit 1: Generation failed: owned generated file was
                              unexpectedly modified: ...

=== 2.6 declared format vs file, and DECIMAL coercion ===
  read_csv_auto on a .tsv: [('unit_ref', 'VARCHAR', ...), ('score', 'DOUBLE', ...)]
  read_csv_auto on .parquet:  Invalid Input Error: Error when sniffing file "truthful.parquet".
  read_json_auto on .tsv:     Invalid Input Error: Malformed JSON in file "t.tsv", at byte 1
                              in record/value 2: unexpected character.
  parquet_schema duckdb_type: [('schema', None), ('amount', 'DECIMAL(18,2)')]
  exact -> DOUBLE: [(Decimal('1234567890123456.78'), 1234567890123456.8)]
```

The one number that needs a caveat is the cost measurement: the two `plain` runs differ
from each other by 36 ms, which is larger than the difference between plain and
guarded, so the honest statement is "no measurable cost" rather than a ratio.
