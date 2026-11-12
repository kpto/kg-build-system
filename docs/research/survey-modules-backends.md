# Survey: distribution modules, DuckDB, Neo4j, Python, runtime and frontend
Read-only source: `/home/paul/Repos/kg-build-system`. Scope:
`kg_build_system/distribution/modules/{duckdb,neo4j,python,runtime}/**`,
`kg_build_system/frontend/**`, plus the cross-module planners that emit the
DuckDB kinds the DuckDB executor owns. Paths are repo-relative. “Plan-time” =
planner `plan()`; “run-time” = executor `execute()`. **unclear** = not established.
## 1. Module map
### 1.1 Package layout

- `distribution/modules/duckdb`: source planner, executor, provider, service, SQL
  emitter, engine; public `service/public/__init__.py`, package `__init__.py`.
- `distribution/modules/neo4j`: export planner/executor, instruction DTOs, script
  renderer; public `model/public/configuration.py`, `service/public/__init__.py`.
- `distribution/modules/python`: Python step executor only.
- `distribution/modules/runtime`: storage/credential resources, outcome helpers;
  public `model/public/services.py`, `service/public/__init__.py`.
- `kg_build_system/frontend`: `frontend/__init__.py`, `frontend/monitor.py`.
Each module uses `model/public`, `model/internal`, `service/public`,
`service/internal`, `service/_private`; public modules mostly re-export private
implementations (`duckdb/service/internal/api.py:1-8`,
`neo4j/service/internal/api.py:1-6`, `python/service/internal/api.py:1-6`).
### 1.2 Planners

| Planner | Implementation | `component_id` | `version` | `runtime_fields` | Emits |
| --- | --- | --- | --- | --- | --- |
| `DuckDbSourcePlanner` | `modules/duckdb/service/public/planner.py:10-55` | `duckdb` | `1` | `()` | `("source_relation","duckdb")` |
| `RowSourcePlanner` | `modules/core/row_source/service/public/planner.py` | `core` | `4` | `()` | injected emitter kind |
| `ProjectionPlanner` | `modules/core/projection/service/public/planner.py` | `core` | `4` | `()` | injected emitter kind |
| `BindingPlanner` | `modules/core/binding/service/public/planner.py` | `core` | `4` | `()` | injected emitter kind |
| `RecordsPlanner` | `modules/core/records/service/public/planner.py` | `core` | `4` | `()` | `("aggregate","duckdb")` |
| `DeduplicationPlanner` | `modules/deduplication/service/_private/planner.py:27-68` | `deduplication` | `2` | `()` | `("deduplication","duckdb")` |
| `MergingPlanner` | `modules/merging/service/_private/planner.py:33-95` | `merging` | `2` | `()` | `("merging","duckdb")` |
| `ConflictValidationPlanner` | `modules/conflict_validation/service/_private/planner.py:36-143` | `conflict_validation` | `2` | `()` | `("conflict_findings","duckdb")`, `("conflict_report","default")` |
| `Neo4jPlanner` | `modules/neo4j/service/_private/planner.py:48-137` | `neo4j` | `2` | `(RuntimeField("relative_directory", ..., required=False),)` | `("neo4j","default")` |
| `PythonExecutor` | `modules/python/service/_private/python.py:48-82` | n/a | n/a | n/a | handles `("python","cpython")` |

`core_planners(engine=...)` returns row-source, projection, binding, records in
that order (`modules/core/service/public/functions.py:19-47`). `default_toolchain`
adds `DuckDbSourcePlanner` and core only when no supplied planner reports
`component_id == "duckdb"` / `"core"` (`kg_build_system/api.py:103-126`).
### 1.3 Executors and providers

| Object | Kinds / resources | Implementation |
| --- | --- | --- |
| `DuckDbExecutor` | `source_relation/sql/aggregate/deduplication/merging/conflict_findings` + `duckdb`; `resources=(DuckDbService,)` | `duckdb/service/_private/executor.py:45-225` |
| `PythonExecutor` | `("python","cpython")`; `resources=()` | `python/service/_private/python.py:48-82` |
| `Neo4jExecutor` | `("neo4j","default")`; `resources=(RelationService, OutputStorage)` | `neo4j/service/_private/executor.py:37-178` |
| `ConflictReportExecutor` | `("conflict_report","default")` | `conflict_validation/service/_private/executor.py` |
| `RuntimeResources` | provides `OutputStorage`, `WorkingStorage`, `TemporaryStorage`, `CredentialResolver` | `runtime/service/_private/resources.py:30-95` |
| `DuckDbResourceProvider` | provides `DuckDbService`, `RelationService` | `duckdb/service/_private/resources.py:48-104` |

Default executors: DuckDB, Python, conflict report, file, meta-graph, Neo4j
(`kg_build_system/api.py:66-73`). Default providers: `RuntimeResources()`, then
`DuckDbResourceProvider()` (`api.py:118-120`).
### 1.4 Instruction kinds and payloads

| Kind | Emitted by | Payload |
| --- | --- | --- |
| `("source_relation","duckdb")` | `DuckDbSourcePlanner` | `{relation, location, format, credential_reference, declaration, declared_columns, declared_paths}` |
| `("sql","duckdb")` | core planners via `DuckDbSqlEmitter` | `{sql, relation?}` |
| `("aggregate","duckdb")` | `RecordsPlanner` | `{relation}` |
| `("deduplication","duckdb")` | `DeduplicationPlanner` | `{relation}` |
| `("merging","duckdb")` | `MergingPlanner` | `{relation, select}` |
| `("conflict_findings","duckdb")` | `ConflictValidationPlanner` | `{component, field}` |
| `("conflict_report","default")` | `ConflictValidationPlanner` | `{fail_on_error}` |
| `("python","cpython")` | external planner | `{module, qualname}` |
| `("neo4j","default")` | `Neo4jPlanner` | `{kind: "export_component"|"write_script", ...}` + `relative_directory` |

`InstructionKind` is exact `(operation, engine)`, refuses empty segments and `/`
(`kernel/model/public/workflow.py:299-333`).
### 1.5 Neo4j identities
Export step `export.{kind}.{stem}`; output
`ArtifactType.of("neo4j","component",kind,component)` keyed `("result",)`; script
step `script` publishes `ArtifactType.of("neo4j","import_bundle")` keyed
`("result",)`; files under `nodes/` and `relationships/` named
`<readable>-<sha256(name)[:8]>.parquet`; id spaces `kg_<sha256(name)[:16]>`
(`export.py:68-98`; `planner.py:76-126`). All Neo4j steps are `deferred`.
## 2. DuckDB
### 2.1 SqlEmitter implementation
Public exports: `DuckDbExecutor`, `DuckDbResourceProvider`, `DuckDbService`,
`DuckDbSourcePlanner`, `DuckDbSqlEmitter`, `DuckDbInstructionEmitter`,
`EmissionContext`, `ExpressionEmitter`, `Operand`, `RelationQueryResult`,
`RelationRef`, `RelationService`, `expression_sql`, `relation_sql`,
`row_source_sql` (`duckdb/__init__.py:4-20`).

Protocols (`emitters/protocols.py`): `Operand` has `expression`, `logical_type`,
`sql()`; `EmissionContext` has `emit`, `parameter`, `alias_for`, `expansion`,
`with_variable`; `ExpressionEmitter` has `operator` and `emit(expression,
operands, context)`; `RowSourceEmissionContext` has `relation_for`, `shape_for`,
`source_key`, `emit_expression`; `RowSourceEmitter` has `node_type` and
`emit(plan, context)`.

`DuckDbInstructionEmitter` (`emitters/emitter.py:43-68`) has `operators` and
`row_sources` mappings. Methods:

```python
def with_operators(self, *emitters: ExpressionEmitter[SqlNode]) -> DuckDbInstructionEmitter: ...
def with_row_sources(self, *emitters: RowSourceEmitter[SqlNode]) -> DuckDbInstructionEmitter: ...
def emit_expression(self, expression: ExpressionDTO, *, aliases=None, expansions=None, relations=None, shapes=None) -> SqlNode: ...
def expression_sql(self, expression: ExpressionDTO, *, aliases=None, relations=None, shapes=None) -> str: ...
def relation_sql(self, plan: RelationPlan) -> str: ...
def emit_row_source(self, plan: RowSourcePlanDTO, relations, shapes) -> str: ...
def row_source_sql(self, plan: RowSourcePlanDTO, relations, shapes) -> str: ...
```

`DuckDbSqlEmitter` (`emitters/instruction.py:20-35`) has
`kind=("sql","duckdb")` and `instruction_emitter`. Its `emit(plan, context=None)`
renders `relation_sql(plan)`, stores `{"sql": sql}`, and adds `"relation"` only
when `context` is supplied and truthy; `DuckDbExecutor._sql` otherwise uses
`context.step.name` (`executor.py:116`). `DEFAULT_EMITTER` is a module-level
instance (`emitter.py:194`).

**Relation-plan SQL** (`emitter.py:101-162`): no scans →
`SELECT * FROM (SELECT 1) AS constant_input`; otherwise `SELECT * FROM
"relation" AS alias` with each remaining scan cross-joined. Each `Expand` adds
`CROSS JOIN UNNEST(expr) AS "expandedN"("item")` and binds its scope to
`expandedN.item`. Filters are `AND`-combined; `"present"` → `NOT (expr IS NULL)`,
`"true"` → the predicate (`emitter.py:37-40,186-191`). Outputs replace `*` with
`expr AS "name", ...`; final text uses `sqlglot .sql(dialect="duckdb")`.
Relation scans use `t0`, `t1`, …; expansions use `expanded0`, …; joins use
`_kg_left`/`_kg_right`; filter/group/order/unnest use `_kg_src`.

**Row sources** (`row_sources/*`; dispatch unknown type → `TypeError`,
`emitter.py:164-175`):

| Node | SQL |
| --- | --- |
| `RowScanDTO` | raises `ValueError("a scan is supplied by its table or projection relation")` (`scan.py:12-16`) |
| `RowFilterDTO` | `SELECT * FROM relation AS _kg_src [CROSS JOIN UNNEST...] WHERE pred`; predicate expansions cross-joined (`filter.py:22-71`) |
| `RowJoinDTO` | each side adds `TRUE AS "_kg_present"`; `on`=coalesce(keys), `left`/`right`=nullable `struct_pack`; `INNER|LEFT|RIGHT|FULL` (`join.py:15-76`) |
| `RowGroupByDTO` | inner `_kg_key_N` + `struct_pack(...) AS "_kg_member"`, null-key filter; outer `struct_pack(keys) AS "by"`, `list("_kg_member") AS "members"` (`group_by.py:15-67`) |
| `RowOrderByDTO` | `SELECT * ... ORDER BY expr [DESC]` (`order_by.py:15-30`) |
| `RowUnionDTO` | `SELECT * FROM left UNION [ALL] SELECT * FROM right` (`union.py:15-25`) |
| `RowDistinctDTO` | `SELECT DISTINCT * FROM relation` (`distinct.py:15-24`) |
| `RowUnnestDTO` | all columns except target field, plus `unnest(value) AS "field"` (`unnest.py:18-38`) |

`nullable_struct` uses `CASE WHEN _kg_present THEN struct_pack(...) END` for a
possibly absent join side (`emitters/sql.py:56-63`); the `TRUE` seed makes the
flag NULL after an outer join on the absent side.

**Expressions** (`emitters/rendering.py:91-104`): literals use `literal_sql`
(text-canonical unit/array casts; otherwise `sqlglot.exp.convert`,
`literals.py:26-51`); variables copy a bound node or raise; field refs emit
`"alias"."field"` plus `.part` segments; lookup emits a scalar subquery
`(SELECT list(struct_pack(...)) FROM relation AS _kg_lookup WHERE target = key
AND key IS NOT NULL)` and needs a planned shape; operations dispatch by
`operator.name` and unknown names raise `ValueError("DuckDB does not support
expression operator ...")` (`rendering.py:21-88`).

The operator registry composes 25 emitters at import (`operators/registry.py:41-86`):
`add`, `subtract`, `equals`, `and`, `or`, `not`, `concat`, `append`, `replace`,
`to_string`, `before_separator`, `after_separator`, `array_at`, `array_slice`,
`transform_items`, `drop_null_items`, `sort`, `distinct`, `join`,
`struct_field`, `expand`, `drop_null`, `drop_if`, `coalesce`, `zip`. Key SQL:
`+ - = AND OR`; `concat`/`append` both `concat(...)`; `replace(...)`;
`array_to_string` for `join`; `list_extract`/`list_slice`; `list_sort`,
`list_distinct`, `list_transform`, `list_filter`; `string_split` and
`array_to_string` for separator ops; `struct_field` → `expr."name"`; `zip` uses
`list_transform`/`range`/`struct_pack` and returns NULL on unequal lengths.
`expand` returns `context.expansion(expansion_scope(expression))`; unplanned
scope raises. `drop_null`/`drop_if` are SQL identity functions returning the
first operand; their row effect is planned as `Filter(mode="present"|"true")`
(`operators/drop_null.py:22-31`, `drop_if.py:22-29`,
`core/.../planning/emission.py:225-327`).

`expansion_scope` (`emitters/planning.py:30-58`): direct field →
`(relation, field, *path)`; `struct_field(expand(x), name=...)` appends `name`;
otherwise `("expression", sha256(json)[:])`. Emitter invariants: registries
reject duplicate operator/node types at import; only this package imports
`sqlglot`; `alias_for` raises rather than falling back; lookup needs a shape;
literals cast only `TEXT_CANONICAL_UNIT_NAMES`.
### 2.2 Source planner

```python
class DuckDbSourcePlanner:
    component_id = "duckdb"
    version = "1"
    runtime_fields: tuple[RuntimeField, ...] = ()
    def __init__(self, *, formats: Sequence[str] = ("parquet","json","csv"), union_by_name: bool = False) -> None: ...
    def plan(self, blueprint: GraphBlueprint, context: PlanContext) -> Sequence[Step]: ...
```

Logic is `source_steps(blueprint, *, formats=SUPPORTED_FORMATS)`
(`_private/planner.py:82-114`). `SUPPORTED_FORMATS = {"parquet","json","csv"}`.
It iterates `asset_tables(blueprint)` — only asset-backed relations the graph
reads, sorted by relation name (`distribution/service/_private/asset_tables.py:158-197`).
It skips no layout, unsupported format, format excluded by `formats`, or no
resolvable location. Each step:
`component="duckdb"`, `name=f"source.{relation_name}"`, no inputs, output
`CoreArtifactTypes.table(relation_name)`, payload via `_payload`.

Format = `layout.format or layout.kind`, exact lower-case match.

Location (`_private/planner.py:20-45`): `layout.members[relation_name]`, else
`layout.selector.format(table=relation_name, table_path=relation_name.replace(".","/"))`,
else `layout.locator`. A relative result (no URI scheme, not starting `/`, `\`,
`~`) is joined to `locator` with one `/`; absolute/schemed values are used as
written.

Payload (`_private/planner.py:48-79`): `relation` (`kg_table_0`, …), `location`,
`format`, `credential_reference` (`layout.properties.get("credentials")`),
`declaration` (logical relation name), `declared_columns`
(`[{name, logical_type}]`), `declared_paths` (`[{schema_path, logical_path}]`).

`union_by_name` is stored but never passed to `source_steps`; it has no effect
(`service/public/planner.py:33-40,55`). Docs say this explicitly
(`docs/reference/assets.md:350-353`, `docs/reference/ingest.md:101-102`).

`declared_read_paths` (`_private/reading.py:114-172`) walks binding and
projection expressions, records field reads, and keeps non-null contract paths
the build reaches. `declared_non_null_paths` (`reading.py:75-111`) adds Parquet’s
`("list","element")` wrapper for array levels and recurses into struct types via
a snake-case conversion of the struct qualname (`_snake_name`); a name mismatch
would stop recursion (**unclear** whether generated structs can mismatch).
### 2.3 Source reading SQL
`source_spec(payload) -> SourceSpec` validates fields (`readers.py:130-152`);
`SourceSpec` = `relation`, `location`, `format`, `credential_reference`,
`declaration`, `declared_columns`, `declared_paths` (`readers.py:58-68`).
`source_scan` emits exactly `read_csv_auto('<loc>')`, `read_json_auto('<loc>')`
or `read_parquet('<loc>')` (`readers.py:155-159`); only single quotes are
escaped. No options, glob list, `union_by_name`, `filename`, Hive partitioning or
reader parameters; `layout.partition_by` is unused.

`open_source` (`readers.py:294-324`): (1) if `credential_reference`, resolve via
`CredentialResolver`, parse `DuckDbSourceCredentialOptions`
(`filesystem_options: dict[str, JsonValue]`, pydantic frozen, extra forbid,
strict), require a URI scheme, build `fsspec.filesystem(protocol, **options)`
and `relations.register_filesystem(...)` (`readers.py:269-291`); (2) build the
scan; (3) if `declared_columns`, run `DESCRIBE SELECT * FROM <scan>` and raise
`RuntimeError` naming source/declaration/exposed columns for missing top-level
names (`readers.py:187-217`) — types are not compared; (4) `SELECT <widened
columns>` or `SELECT *` (`readers.py:311-314`); (5) `relations.view(spec.relation,
sql)`, wrapping errors as `RuntimeError` with source context (`315-322`);
(6) parquet + declared paths → footer null-stat pre-flight; return
`(relation, warned)`.

Widening (`readers.py:162-184`): `Nullable` unwrapped; `Unit` → canonical SQL
type (`bool` BOOLEAN, `int` BIGINT, `float` DOUBLE, `str` VARCHAR, `date` DATE,
`time` TIME, `timestamp` TIMESTAMP, `uuid` UUID); `Array` → `<item>[]`;
`Struct`/other → no cast.

Null pre-flight (`readers.py:220-258`; `engine/parquet_metadata.py:60-93`): only
`parquet` + `declared_paths`; sums `num_values`/`stats_null_count` per
`path_in_schema` from `parquet_metadata(?)`; absent statistics go to
`unknown_paths`, never zero; violations warn and make the source step `WARNING`;
statistics read errors warn and are ignored. `read_parquet_schema_rows` uses
`parquet_schema(?)` ordered by file/column id and returns 7-tuples
(`parquet_metadata.py:35-57`).
### 2.4 Executor semantics
`DuckDbExecutor.execute` dispatches on exact kind and always calls
`service.engine.finish_step()` in `finally` (`executor.py:58-88`). A disrupted
context returns `skipped(context)` but still reaches `finish_step`; an unknown
kind raises `ValueError` and also reaches `finish_step`.

| Kind | Behavior |
| --- | --- |
| `source_relation` | `source_spec` → `open_source`; `succeeded(..., status=WARNING if warned else SUCCEEDED)` (`executor.py:90-104`) |
| `sql` | requires non-empty `sql`; relation = payload `relation` or step name; `materialize(relation, sql)` (`106-122`) |
| `aggregate` | requires `relation`; every artifact in every input group → `SELECT * FROM <ref> UNION ALL ...`; `view(relation, union_sql)` (`124-146`) |
| `deduplication` | requires `relation`; first artifact; none → SUCCEEDED with no artifact; else `SELECT DISTINCT * FROM <ref>` materialized (`148-167`) |
| `merging` | requires `relation` + `select`; first artifact; none → SUCCEEDED with no artifact; else `SELECT {select} FROM <ref> GROUP BY "build_key"` (`169-194`) |
| `conflict_findings` | requires `component` + `field`; first artifact; none → SUCCEEDED with no artifact; else `count(DISTINCT field)` grouped by build key with `FILTER (WHERE field IS NOT NULL) > 1`; emits `ConflictingNonNullValueFinding`s (`196-225`) |

`_first_relation` (`executor.py:37-42`) walks `context.inputs.values()` in input
order and returns the first artifact; it ignores the declared input name.
### 2.5 Connection and resource lifecycle
`DuckDbResourceProvider` (`resources.py:48-104`): on `PipelineStarted`,
`_settings(configuration)` → ensure `working_directory` →
`mkdtemp(prefix=".kg-build-duckdb-", dir=working_directory)` →
`open_engine(settings, dir)` → `DuckDbService(engine)` → register
`DuckDbService` and `service.relations` as `RelationService`. On
`PipelineFinished`/`PipelineHalted`, close services in reverse order. Repeated
starts accumulate engines; a duplicate resource add fails.

`_settings` (`resources.py:23-45`) reads `provider_configuration["duckdb"]`:
`storage` (`"memory"` default; `"memory"|"disk"`), `threads` (`None` or positive
int; bool rejected), `memory_limit` (`None` or str), `compression` (`bool`,
default `True`). Unknown keys ignored; validation repeats in the engine.

`open_engine(settings, storage_directory)` (`engine/session.py:120-150`) imports
`duckdb` (missing → `RuntimeError("DuckDB is required to execute workflows")`),
creates the storage directory even for memory, then: `memory` →
`duckdb.connect()`, `ATTACH ':memory:' AS kg_build_memory [ (COMPRESS) ]`, `USE
kg_build_memory`; `disk` → `duckdb.connect(storage_directory/"kg_build.duckdb")`,
with `PRAGMA force_compression='uncompressed'` when `compression` is false;
`threads` → `SET threads = ?`; `memory_limit` → `SET memory_limit = ?` (empty
raises); all → `SET temp_directory = <abs storage dir>`, `SET TimeZone='UTC'`,
and `configure_framework_macros` creating
`_kg_nn(v, msg := 'unexpected NULL') AS CASE WHEN v IS NULL THEN error(msg) ELSE
v END`. It reads effective `memory_limit`/`threads` from `duckdb_settings()` and
`current_setting('TimeZone')`, then builds
`DuckDBRelationService(connection, checkpoint_on_step=settings.compression or
settings.storage == "disk")`. Setup errors close the connection and re-raise.

`EngineSession` fields (`session.py:29-37`): `relations`, `time_zone`,
`memory_limit`, `threads`, `storage_directory`. `close()` closes relations then
`rmtree(storage_directory, ignore_errors=True)`; idempotent. `finish_step()`
delegates to relations. `engine_session(...)` closes in `finally`.

`DuckDBRelationService` (`engine/service.py:47-159`) serializes all DB work through
one `ThreadPoolExecutor(max_workers=1, thread_name_prefix="kg-build-duckdb")`:

```python
def __init__(self, connection: Any, *, checkpoint_on_step: bool) -> None: ...
def reference(self, value: object) -> str: ...
def view(self, name: str, query: str) -> RelationRef: ...
def materialize(self, name: str, query: str, parameters: Sequence[object] = ()) -> RelationRef: ...
def query(self, query: str, parameters: Sequence[object] = ()) -> RelationQueryResult: ...
def export_parquet(self, query: str, destination: Path, *, compression: str = "zstd") -> None: ...
def register_filesystem(self, filesystem: object) -> None: ...
def finish_step(self) -> None: ...
def close(self) -> None: ...
```

`_run` refuses after close; `KeyboardInterrupt` calls `connection.interrupt()`,
waits and re-raises; `_wait` polls `future.result(timeout=0.05)`. `reference`
requires `RelationRef`. `view` = `CREATE VIEW "name" AS query` (no `OR
REPLACE`). `materialize` = `CREATE TABLE "__kg_materialized_<name>" AS query`
then `CREATE VIEW "name" AS SELECT * FROM "__kg_materialized_<name>"`; marks
dirty. `query` allows only first keywords
`DESCRIBE|EXPLAIN|SELECT|SHOW|SUMMARIZE|VALUES|WITH` and returns a
description-only `_DuckDBQueryResult`; `fetchone/fetchall/fetchmany` submit later
on the same connection. `export_parquet` = `COPY (query) TO '<abs>' (FORMAT
PARQUET, COMPRESSION <UPPER>)`. `finish_step` runs `CHECKPOINT` only when dirty
and `checkpoint_on_step`. `close` closes on the worker, marks closed, and shuts
the worker down even on error.
### 2.6 DuckDB limits and failure modes
- One engine/worker per run; no timeout, row cap, chunk size, retry or cancellation
  except `KeyboardInterrupt`. `CREATE TABLE AS` materializes whole relations;
  `query` returns a lazy fetch handle. No `OR REPLACE`: reused relation names fail.
- `_require_query` checks only the first keyword; it cannot prove a `WITH` is
  read-only. `query()`/`fetch*()` are separate submissions; a second statement
  before fetching can change the result (**unclear** if promised otherwise).
- `open_engine` failure after `mkdtemp` leaks the private storage directory
  (`resources.py:91-97`, `session.py:125-137`); a `finish_step` failure in
  `finally` masks the original exception; `aggregate` with no inputs fails on
  empty union SQL; dedup/merge/findings with no input return SUCCEEDED with no
  artifact.
- Source `DESCRIBE` checks only top-level names; null-stat violations warn and
  `_kg_nn` aborts later at the binding; `layout.partition_by`, non-`credentials`
  properties and `union_by_name` are unused.
## 3. Neo4j
### 3.1 Direction and planner
Export-only. Reads graph-record relations from DuckDB, writes Parquet with
Neo4j bulk-import headers, and writes a standalone Python script that runs
external `neo4j-admin database import`. No Neo4j driver is imported; no Cypher,
live connection, transaction, read-back or verification exists in the framework.
The generated script is the only ingest path.

```python
class Neo4jPlanner:
    component_id = "neo4j"
    version = "2"
    runtime_fields = (RuntimeField("relative_directory", "Optional runtime replacement for the Neo4j import-bundle directory.", required=False),)
    def __init__(self, configuration: Neo4jConfiguration | None = None) -> None: ...
    def plan(self, model: GraphBlueprint, context: PlanContext) -> tuple[Step, ...]: ...
```

`_graph_record_components` selects graph-order components (nodes then edges) with
at least one binding (`planner.py:36-45`). `component_imports` sorts by
`(kind, name)` and validates labels/properties (`export.py:164-204`). One export
step per component, then one deferred `script` step consuming
`ArtifactPattern.of("neo4j","component","**")` (`planner.py:73-105`). Export
inputs use `CoreArtifactTypes.graph_records(kind, component)` under name
`records`.
### 3.2 Export and graph semantics
`validate_properties` (`export.py:135-161`):

- Reserved names: `build_key`, `source_build_key`, `target_build_key`,
  `_kg_binding_symbol` (`export.py:47-49`).
- Property names containing `: { } \r \n` are refused (`_HEADER_CONTROL`).
- Scalar allowed: `bool`, `int`, `float`, `str`, `date`, `time`, `timestamp`.
- Arrays allowed: non-nullable items of `bool`, `int`, `float`, `str`.
- `uuid`, custom scalars, structs, temporal arrays, nullable array items and
  nested containers are refused at plan time with a message naming
  component/property/type.
- Node labels containing `;` raise (“must have a single Neo4j label”); edge
  labels are not checked for `;` (`export.py:100-106`).

`export_component` (`export.py:244-291`): requires exactly one `records`
artifact (`RuntimeError` if 0 or >1); validates its graph-record identity;
references the relation; resolves `bundle_path / relative_path`; creates parents;
calls `export_parquet(select_sql(...))`; counts rows by
`SELECT count(*) FROM read_parquet(?)`; returns
`Neo4jComponentExport(kind, component, relative_path, rows)`.

`select_sql` (`export.py:207-233`): node headers are
`CAST("build_key" AS VARCHAR) AS "build_key:ID(<space>)"`, then properties, then
`'<label>' AS ":LABEL"`; edge headers are `CAST("build_key" AS VARCHAR) AS
"build_key"`, `CAST("source_build_key" AS VARCHAR) AS ":START_ID(<space>)"`,
`CAST("target_build_key" AS VARCHAR) AS ":END_ID(<space>)"`, then properties,
then `'<label>' AS ":TYPE"`.

Graph semantics: one node row per node, identity = build-key string in that
node’s id space; `build_key` is **not** emitted as a node property; one constant
label per node file. One relationship row per edge; `build_key` **is** emitted
as a relationship property; `:START_ID`/`:END_ID` are build-key strings in the
endpoint node id spaces; one constant `:TYPE` per edge file; direction follows
source → target. No deduplication/merge; duplicate IDs are left to the importer.
Endpoint node components must be selected/bound, else plan-time `ValueError`
(`export.py:188-195`).

`component_stem` sanitizes to `[A-Za-z0-9._-]`, strips leading/trailing `._-`,
falls back to the kind, and appends `sha256(name)[:8]` (`export.py:68-72`).
`id_space` is `kg_` + `sha256(name)[:16]` (`export.py:75-77`).
### 3.3 Script, transactions, batching, constraints
`render_import_script(*, node_paths, relationship_paths, default_database) -> str`
(`script.py:8-175`) writes stdlib-only Python storing relative paths/default DB as
literals, locating `neo4j-admin` via `--neo4j-admin`, `NEO4J_ADMIN`,
`--neo4j-home`/`NEO4J_HOME`, `shutil.which`, then known OS/Neo4j Desktop
locations (`script.py:36-124`). CLI: positional database, `--neo4j-admin`,
`--neo4j-home`, `--dry-run`, `--print-command`, `--verbose`, repeatable
`--admin-arg`; it verifies files/refuses no nodes (`145-153`) and runs
`neo4j-admin database import full <db> --input-type=parquet --id-type=string
--nodes=<abs> ... --relationships=<abs> ...` (`154-165`). It prints the command;
`--print-command` exits 0; otherwise `subprocess.run(..., check=False)` returns
the exit code (`167-170`). `_write_script` (`executor.py:114-178`) validates every
input is a `Neo4jComponentExport`, rejects unexpected/duplicate/missing exports,
writes UTF-8/LF, chmods on POSIX, and publishes `{directory, script, nodes,
edges, node_files, relationship_files}`.
Transaction model: none; no open/commit/rollback/retry. Batching: none; one
Parquet per component, no chunk/batch-size/incremental setting. Constraints/
indexes: none; no Cypher, `CREATE CONSTRAINT` or `CREATE INDEX`. Import mode:
`full` only; no overwrite/filter/bad-row flags. Connection/auth: none; local admin
tool only. Configuration: only `relative_directory`, `script_name`,
`default_database`; no batch/timeout/retry/constraint options.
### 3.4 Neo4j failure modes
Plan-time `ValueError` for unsupported property types, reserved properties,
header-control characters, `;` in node labels, and unbound endpoint node
components (`export.py:100-106,139-159,188-195`). Run-time `RuntimeError` for
0/>1 record artifacts, artifact identity mismatch, unexpected export path,
duplicate export or missing export (`export.py:251-270`, `executor.py:133-146`);
`TypeError` for a non-`Neo4jComponentExport` script input (`executor.py:128-131`).
Unsafe output paths raise `ValueError` (`executor.py:82-85`). At import time the
script raises `parser.error` for missing files or no node files, and
`FileNotFoundError` for a missing `neo4j-admin`; an external import failure only
returns its exit code because `check=False` (`script.py:120-170`).

**Unclear/external:** whether `full` requires the target DB stopped/empty
(normal Neo4j behavior, not asserted here); whether `;` in an edge `:TYPE` means
multiple types (not rejected for edges); whether `relative_directory="."` is
intended (validator allows it; bundle resolves to the output root).
## 4. Python steps
### 4.1 Payload, loading, invocation

```python
class PythonExecutor:
    kinds = (InstructionKind("python","cpython"),)
    resources: tuple[type, ...] = ()
    def execute(self, context, instruction) -> StepOutcome: ...
```

`execute` (`python.py:54-82`): disrupted → `skipped`; payload must be an object;
`module`/`qualname` non-empty strings; `_load` imports the module and walks
`qualname.split(".")` with `getattr`; `_invoke` runs; a `StepOutcome` passes
through, otherwise `succeeded(context, result)`. `_invoke` (`26-45`): if
`target.execute` is callable, call `(context, instruction)`; else target must be
callable; `inspect.signature` failure → `target(context)`; try
`bind(context, instruction)` → call two args; on `TypeError`, `bind(context)` →
call one. One/two-argument callables work; zero-argument callables fail and
propagate; `*args`/defaulted second args take two; keyword-only `instruction` takes
one; `.execute` wins over calling the object; the executor ignores `signature`
(`PythonRefDTO` elsewhere has module/qualname/signature but is not required).
### 4.2 Isolation and error handling
- No isolation: in-process import and call. No subprocess, sandbox, venv,
  seccomp, timeout, memory limit, cancellation, retry or crash recovery.
- Import side effects happen at first execution; modules are cached across steps.
- Module/qualname is not checked against a registry or allowlist.
- `PythonExecutor` catches nothing. The kernel catches `Exception` and records a
  `FAILED` outcome with `Failure(message, step_id, exception_type)`
  (`kernel/service/_private/runtime.py:425-445`); `BaseException` aborts the run.
- If `bus.failure` is set (a listener/monitor failed), the runtime re-raises it
  instead of recording the step failure (`runtime.py:430-434`).
- A returned `StepOutcome` is runtime-validated: step id, failure presence,
  unique/declared output names, artifact types; missing declared outputs are
  allowed (`runtime.py:355-400`).
### 4.3 Not supported
- No runtime-resource access: `resources=()` means an empty `ResourceView`;
  `context.resources.get(X)` raises `KeyError` for every resource. A Python step
  cannot query DuckDB relations, use output/temporary storage or resolve
  credentials through the declared mechanism.
- No async/await (returns a coroutine artifact); no streaming/generators; no
  zero-arg target; no reload/per-step module isolation; no timeout/retry/quota.
- Only `StepOutcome` or first-output wrapping. A plain return value attaches only
  to the first declared output (`runtime/service/_private/outcome.py:26-41`); no
  outputs → value dropped; multiple outputs → later outputs empty.
- Docs coverage is thin: `docs/reference/planners-and-executors.md:291` only
  lists the kind; the calling convention, empty resource view and isolation are
  undocumented.
## 5. Runtime resources
### 5.1 Protocols and implementations
`runtime/model/public/services.py` defines `WorkflowLogger` (`debug/info/warning/
error(message, *args)`), `WorkingStorage` and `OutputStorage` (`child(
relative_path: PurePosixPath) -> Path`), `TemporaryStorage` (`root: Path`) and
`CredentialResolver` (`resolve(reference) -> str`). Implementations:
`NullWorkflowLogger` (no-op), `LocalWorkingStorage` (`root`; `child` joins parts),
`LocalTemporaryStorage` (`root` only), `MappingCredentialResolver`
(`credentials`; unknown reference → `KeyError`) (`storage/*`, `services.py:28-41`).

`runtime/service/public/functions.py`: `output_name(given) -> Key`,
`succeeded(context, value, *, status=SUCCEEDED) -> StepOutcome`,
`skipped(context) -> StepOutcome`, `instruction_payload(instruction) -> Mapping`.
`DEFAULT_OUTPUT_NAME = Key(("output",))`; `succeeded` attaches only the first
declared output (`outcome.py:18-41`). `instruction_payload` thaws frozen JSON and
requires a mapping, else `TypeError` (`outcome.py:52-59`).
### 5.2 `RuntimeResources` lifecycle
On `PipelineStarted` (`resources.py:63-88`): create output dir; create working
dir; create temporary parent if configured; `mkdtemp(prefix=".kg-build-temp-",
dir=... )`; append temp root; add `OutputStorage -> LocalWorkingStorage(output)`,
`WorkingStorage -> LocalWorkingStorage(working)`,
`TemporaryStorage -> LocalTemporaryStorage(temp)`,
`CredentialResolver -> MappingCredentialResolver(configuration.credentials)`.
On `PipelineFinished`/`PipelineHalted`: remove all temp roots with
`rmtree(ignore_errors=True)`; output/working are retained. Repeated finishes are
safe because the list is cleared.
### 5.3 Registry, views, merging, ordering
`ResourceRegistry` (`kernel/model/public/events.py:21-82`): exact-type keys;
duplicate `add` raises `ValueError` with the fully qualified type; `get` raises
`KeyError` when missing; `snapshot()` is a shallow dict copy.

`WorkflowRuntime.execute` (`kernel/service/_private/runtime.py:627-674`): new bus;
subscribe providers in passed order; subscribe frontend listeners after providers;
new registry; emit `PipelineStarted`; `views = _executor_views(executors,
resources.snapshot())`; reject unknown component configuration ids; schedule and
execute; emit `PipelineFinished`; on any `BaseException`, emit `PipelineHalted`
and re-raise.

`_executor_views` (`runtime.py:93-112`): one view per executor instance (`id`),
built from exactly `executor.resources`; any declared type absent from the merged
snapshot raises `ValueError` before scheduling; `ResourceView.get` raises
`KeyError` for undeclared types even if another executor has them
(`kernel/model/public/runtime.py:63-95`).

Merging is only the registry snapshot: all providers merged, then filtered per
executor; duplicate exact types are errors; resources added after the snapshot
are invisible; unused supplied executors must still have their resources; one
executor instance handling several kinds shares one view; `PythonExecutor` gets
an empty view; `Neo4jExecutor` needs DuckDB’s `RelationService` and
`OutputStorage`.

Ordering: default providers are `RuntimeResources()` then
`DuckDbResourceProvider()`. Open: dirs first, then DuckDB private storage under
`working_directory`. Close: temp root removal first, then DuckDB close/storage
removal. Default is benign because DuckDB storage is under working, not temp.
`EventBus.emit` delivers in subscription order, stops at the first error, records
it in `bus.failure`, and re-raises (`events.py:239-259`). Provider errors abort
the run; halt delivery errors are swallowed.
### 5.4 Runtime failure modes
Duplicate provider resource types → `ValueError` during `PipelineStarted`
(`events.py:52-58`); a missing declared resource → `ValueError` before scheduling
(`runtime.py:103-109`); duplicate executor kinds / plan kinds without an executor
→ `ValueError` (`kernel/service/_private/pipeline.py:88-104`); unknown component
ids or bad runtime fields → `ValueError`/`TypeError` (`runtime.py:255-283,648-652`).
A step `Exception` → `FAILED`; `BaseException` propagates (`runtime.py:425-445`).
A finish-time listener/provider failure attempts `PipelineHalted`, re-raises, and
may lose a built report (`runtime.py:667-671`); undeclared reads → `KeyError`
(`kernel/model/public/runtime.py:63-95`).

Frontend: `NullMonitor` no-op; `ConsoleMonitor` writes text via `rich` if present
else `print`; `resolve_monitor(True) -> ConsoleMonitor`, `False/None -> None`,
otherwise returns the supplied object unchanged (`frontend/monitor.py:152-170`).
Monitors are listeners, not resource owners; a monitor error is a pipeline
failure.
## 6. Configuration objects

| Object | Fields | Notes |
| --- | --- | --- |
| `DuckDbSettings` | `storage: Literal["memory","disk"]="memory"`, `threads: int|None=None`, `memory_limit: str|None=None`, `compression: bool=True` | `engine/session.py:19-26`; from `provider_configuration["duckdb"]` |
| `DuckDbSourcePlanner(...)` | `formats=("parquet","json","csv")`, `union_by_name=False` | `service/public/planner.py:33-40`; `union_by_name` unused |
| `DuckDbSourceCredentialOptions` | `filesystem_options: dict[str, JsonValue]` | pydantic frozen, extra forbid, strict (`readers.py:71-77`) |
| `EngineSession` | `relations`, `time_zone`, `memory_limit`, `threads`, `storage_directory: Path|None` | effective engine values, not user config |
| `DuckDbInstructionEmitter` | `operators`, `row_sources` | default global registries |
| `DuckDbSqlEmitter` | `kind=("sql","duckdb")`, `instruction_emitter` | frozen/slots |
| `Neo4jConfiguration` | `relative_directory="neo4j-import"`, `script_name="import_neo4j.py"`, `default_database="neo4j"` | `neo4j/model/public/configuration.py:10-45` |
| `Neo4jPlanner` runtime field | `RuntimeField("relative_directory", ..., required=False)`, default `value_type="string"` | `planner.py:53-59` |
| `RuntimeConfiguration` | `output_directory`, `working_directory`, `temporary_directory=None`, `credentials={}`, `component_configuration={}`, `provider_configuration={}` | `kernel/model/public/runtime.py:27-60` |
| `BuildRuntime` | `credentials`, `component_configuration`, `provider_configuration`, `output_directory`, `working_directory`, `temporary_directory`, `duckdb_storage`, `duckdb_threads`, `duckdb_memory_limit`, `duckdb_compression` | `distribution/model/public/runtime.py:16-108` |
| Python | none | only payload `{module, qualname}` |
| Frontend | `resolve_monitor(value: Monitor|bool|None)` | no config fields |

Validation: `DuckDbSettings` is checked in both provider `_settings` and engine
`_configure_duckdb`: `threads` bool/<1 rejected; `memory_limit` must be a
non-empty string at engine time; `compression` bool. `Neo4jConfiguration`
validates path safety, one-component `.py` script name, non-empty database
(`configuration.py:31-45`). `relative_directory="."` is allowed (Path parts empty)
and resolves the bundle to the output root (**unclear** if intended).
`script_name=".py"` also passes the single-part + suffix check (minor edge case).

`BuildRuntime.to_configuration()` always writes
`provider_configuration["duckdb"]` with `storage`, `threads`, `memory_limit`,
`compression`; it merges other duckdb keys from the supplied provider config but
overwrites those four with the `duckdb_*` fields
(`distribution/model/public/runtime.py:90-100`). Thus passing only
`provider_configuration={"duckdb": {...}}` through `BuildRuntime` does not set
those four; direct `RuntimeConfiguration` construction does.
## 7. Consolidated invariants
- **DuckDB:** one service/relation view per run; relation ops serialized on one
  worker; `reference` requires `RelationRef`; queries read-only by first keyword;
  identifiers quoted; source locations single-quoted/escaped; TimeZone UTC;
  `_kg_nn` before views; `finish_step` after every attempt; `CHECKPOINT` only when
  dirty + policy. Planning: one source step per used asset-backed table; exact
  lower-case formats; `members`→`selector`→`locator`; `union_by_name` no-op.
  Execution: source view casts declared columns; missing top-level names fail
  before rows; null stats warn only; aggregate = UNION ALL; dedup = DISTINCT *;
  merge = GROUP BY build_key; findings = count distinct non-null.
- **Neo4j:** offline export only; one export per bound component; exactly one
  record artifact each; node ID = build key; constant label/type; endpoint IDs in
  node spaces; no transactions/batches/constraints; external `neo4j-admin full`.
- **Python:** in-process import/call; no isolation; empty resource view; optional
  `.execute`; one/two argument forms; plain value → first output only.
- **Runtime:** fresh bus/registry per run; providers open on start and close on
  finish/halt; one view per executor from a merged snapshot; duplicate exact
  resource types and duplicate kinds refused; monitors subscribe after providers.
## 8. Surprising, ambiguous and doc/code disagreements
1. **`union_by_name` is a documented no-op** — stored but never passed to
   `source_steps` (`duckdb/service/public/planner.py:33-40,55`); docs acknowledge
   (`docs/reference/assets.md:350-353`, `docs/reference/ingest.md:101-102`).
2. **`modules/__init__.py` says core has five planners** — docstring
   `distribution/modules/__init__.py:4`; code/docs define four
   (`docs/reference/planners-and-executors.md:37-45`).
3. **`sql_types.py` cites a missing `DUCKDB_TYPE_ACCEPTANCE_MATRIX.md`**
   (`duckdb/model/public/sql_types.py:3`); the same table also lives separately
   in `generation/code_generation/service/_private/builtins/mapping.py:63-176`.
4. **TIMESTAMPTZ refusal rationale is stale** — it says materialising an instant
   is machine-dependent “until that setting is pinned”
   (`sql_types.py:191-196`), but every session pins `TimeZone='UTC'`
   (`engine/session.py:16,101`); the refusal remains.
5. **`BuildRuntime` overwrites explicit duckdb provider settings** —
   `to_configuration()` merges then overwrites
   `storage/threads/memory_limit/compression` from `duckdb_*`
   (`distribution/model/public/runtime.py:90-100`), while docs present both
   surfaces (`docs/reference/compile.md:180-224`).
6. **“Core is always present” is conditional** —
   `docs/concepts/planners-and-executors.md:60-64` says always; `default_toolchain`
   adds it only when no supplied planner reports `component_id=="core"`
   (`kg_build_system/api.py:103-112`).
7. **Neo4j export secretly depends on DuckDB** — `Neo4jExecutor.resources=
   (RelationService, OutputStorage)` and `export_component` calls
   `reference/query/export_parquet` (`neo4j/.../executor.py:41`,
   `export.py:272-284`); without `DuckDbResourceProvider` view construction fails.
   Docs describe the bundle as standalone at import time
   (`docs/concepts/build-and-outputs.md:221-225`) but not the export dependency.
8. **Python steps cannot use runtime resources** — `resources=()`
   (`python.py:52`) means an empty view; docs require executors to declare what
   they read (`docs/reference/planners-and-executors.md:128-132`) but do not warn
   about the supplied Python executor.
9. **Python calling conventions are undocumented** — `.execute` preference,
   one-argument fallback, zero-argument failure and ignored `signature` exist only
   in code (`python.py:26-45`); docs only describe `(module, qualname)` references
   (`docs/developer/data-and-expressions.md:365-366`).
10. **`drop_null`/`drop_if` emitters are identity functions** — they return the
    first operand (`operators/drop_null.py:22-31`, `drop_if.py:22-29`); row
    effects are planned as `Filter(mode="present"|"true")`
    (`core/.../planning/emission.py:225-327`).
11. **Dedup/merge/findings silently drop missing input** — no input artifact →
    `StepOutcome(step_id, SUCCEEDED)` with no artifact
    (`executor.py:160-162,186-188,203-205`); `_first_relation` also ignores
    input names (`executor.py:37-42`).
12. **DuckDB query results are cursor-like** — `query()` returns only a
    description; `fetch*` executes later on the same connection
    (`engine/service.py:115-126,162-181`); current callers fetch immediately.
13. **Source-planner “read” docs vs code** — docs say a relation is included only
    when a binding/projection selection or row plan reads it
    (`docs/reference/assets.md:145-148`); code scans all bindings and all
    projections (`distribution/service/_private/asset_tables.py:149-163`). If an
    unreferenced projection remains, it may be included (**unclear** whether the
    blueprint prunes it).
14. **Node vs edge `build_key` asymmetry** — node build key becomes an ID header,
    not a property (`export.py:212-216`); edge build key is a plain property plus
    endpoint IDs (`export.py:218-224`); not called out in the Neo4j docs.
15. **Node labels reject `;`, edge types do not** — `annotation_label` checks only
    nodes (`export.py:100-106`); an edge `:TYPE` value with `;` passes through
    (**unclear** how `neo4j-admin` reads it).
16. **`relative_directory="."` and `script_name=".py"` pass validation** —
    `validate_relative_path` accepts `.` and the Neo4j bundle resolves to the
    output root (`distribution/model/public/paths.py:7-15`,
    `neo4j/.../executor.py:104-107`); the script-name check is single component +
    `.py` suffix (`configuration.py:36-40`). Likely unintended edge cases.
17. **No Neo4j transaction/batching/constraint layer** — docs describe the bundle
    and `neo4j-admin` invocation (`docs/concepts/build-and-outputs.md:221-225`,
    `docs/reference/planners-and-executors.md:248-281`) but not the absence of
    transactions/batches/constraints or the `check=False` behavior
    (`script.py:154-170`).
18. **“All three” vs six DuckDB kinds** — `docs/developer/system-design.md:727`
    says “all three” after listing source/sql/aggregate; the `kinds` tuple has six
    (`executor.py:48-55`); ambiguous prose.
19. **Custom `formats` cannot add a reader** — the constructor filters layouts,
    but `_SCAN_FUNCTIONS` is fixed and `source_spec` rejects non-csv/json/parquet
    (`readers.py:35-39,132-134`); docs say another format needs another planner
    (`docs/reference/assets.md:116-119,154-155`).
20. **`layout.partition_by` is semantic only** — docs say it describes meaning,
    not directory names (`docs/reference/ingest.md:62-63`); code never uses it.
