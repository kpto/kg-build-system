# Ingest

## Responsibility

The ingest boundary owns how a physical data source becomes typed contract fields, which nullability claims its format supports, and how a declared non-null claim is enforced when a build reads rows.

## Public API

### Declarations and source bindings

- `InputFormat`: `CSV = "csv"`, `JSON = "json"`, `PARQUET = "parquet"`.
- `DataSourceConfig(location: str, format: InputFormat = InputFormat.CSV, layout: str | None = None, credentials: str | None = None, version: str | None = None)` is a frozen value; `location` must be non-empty.
- `bind_source(*, target, config, options=SourceBindingOptions()) -> BoundSource`; the target must be a final `Table` or `TableGroup`.
- `resolve_bound_source(source) -> tuple[BoundTable, ...]` expands a bound group into one `BoundTable` per concrete table.
- A group binding requires `layout`, which may use only `{group_path}` and `{table_name}`.
- `Field[T]`, `field(*, name=None, description=None, annotations=())`, `Table`, `Struct`, `TableGroup` and `declared_fields(owner)` are the declaration surface used by ingest.
- `Field.access_type(owner)` is the type a read yields. A source field keeps its declared type: `Field[T]` reads present, `Field[T | None]` reads nullable. A computed field carries its expression's type.
- Reading a source field yields the selection matching its declared type; `alter_rows().drop_null()` or `default_to(...)` is the explicit narrowing. Array item nullability such as `Array[T | None]` is retained.

### Inference request

- `DataContractInferenceConfig(source: str, relation: str | None = None, mode: Literal["table", "table_group"] = "table", layout: Literal["files", "parquet_parts", "hive_partitioned_parquet"] = "files", anonymous: bool = False, override: dict[str, dict[str, Any]] = {})` is a frozen, strict `ProviderGenerationConfig`.
- `ColumnOverride(type: str | None = None, nullable: bool | None = None)` is strict, forbids unknown keys and requires at least one of `type` and `nullable`.
- `InferDataContractProvider` has `ID = "infer_data_contract"`, `VERSION = "7"`, `CONFIG_TYPE = DataContractInferenceConfig` and `async generate(context) -> GeneratedPackage`.
- `Nullability` is `DECLARED`, `ENFORCED` or `DEFAULTED`; `GeneratedField.nullability` records the claim and `GeneratedNullableType` records a nullable value shape.
- `NullabilityNote(line, sources, declarations)` is the provenance line rendered into generated headers.

### DuckDB digest gate and metadata

- `digest_for(type_name: str) -> CanonicalDigest | DeclaredOnlyDigest | RefusedDigest | None`. `None` means the name is unknown, not refused.
- `CanonicalDigest.canonical` is a canonical unit name, `"array"` or `"struct"`.
- `DeclaredOnlyDigest.canonical` and `.narrowing` name the canonical target and the measured narrowing.
- `RefusedDigest.reason` records why no meaning-preserving canonical type exists.
- `canonical_type_name(type_name: str) -> str` removes a trailing parameter list and upper-cases the name.
- `canonical_sql_type(canonical: SqlType) -> str` composes the SQL type of a canonical unit, `ArraySqlType` or `StructSqlType`; a bare container name raises `ValueError`.
- `CANONICAL_SQL_TYPES` maps `bool`, `int`, `float`, `str`, `date`, `time`, `timestamp` and `uuid` to their SQL types.
- `read_parquet_schema_rows(read: RowReader, sources) -> tuple[ParquetSchemaRow, ...]` returns one row set per file in pre-order.
- `read_declared_null_statistics(read: RowReader, sources, schema_paths) -> NullStatisticReport` reads footer statistics only.
- `NullStatisticReport.statistics`, `.unknown_paths` and `.violations` distinguish a count from an absent statistic.
- `NULL_GUARD_MACRO = "_kg_nn"` and `NULL_GUARD_MACRO_SQL` define the guard expression used by lowered bindings.

### Build contract

- `DeclaredColumnIR(name: str, logical_type: dict[str, Any])` carries a declared top-level field and its blueprint type encoding; an unknown encoding is refused.
- `DeclaredPathIR(schema_path: str, logical_path: str)` carries one claimed non-null path in `path_in_schema` form and human-readable form.
- `SourceRelationInstructionIR(relation, location, format, credential_reference=None, declaration="", declared_columns=(), declared_paths=())` is the source step's payload; `format` is `csv`, `json` or `parquet`.
- `CoreModule.VERSION = "3"`.
- `require_non_nullable`, `require_scalar` and `require_graph_property` are the graph-property checks used at binding time.
- `GenerationError` is the generation failure; authoring type errors are `TypeError`; blueprint errors are `ValueError`; build shape and format failures are `RuntimeError`.

## Internal interface

- `table.interfaces` exposes `DataSourceConfig`, `InputFormat`, `SourceBindingOptions`, `BoundSource`, `BoundTable`, `BoundTableGroup`, `bind_source`, `resolve_bound_source`, `group_tables`, `SourceIR` and the data-part codec.
- `engines.interfaces` exposes the digest gate, SQL type composition, Parquet metadata readers, the null-guard macro and the DuckDB relation service.
- `modules.core.ir` and `modules.ir` expose `SourceRelationInstructionIR`, `DeclaredColumnIR`, `DeclaredPathIR` and their codecs.
- `code_generation.interfaces` and `code_generation.builtins` expose the provider contract and `InferDataContractProvider`.

Invariants:

- `DataSourceConfig.location` is non-empty. `layout` is only used by a group binding and may interpolate only `{group_path}` and `{table_name}`.
- A bound group resolves to per-table `BoundTable` values with the same config and annotations, and the resolved location.
- `DeclaredColumnIR.logical_type` is a valid encoded logical type.
- `SourceRelationInstructionIR.format` is one of the three declared formats.
- A digest is exactly one of `canonical`, `declared_only` or `refused`; an unknown name is absent.

## IR

- `SourceIR(symbol_id, table, location, format, credential_reference=None, version=None, annotations=())` is the `data`-language source entry.
- `SourceRelationInstructionIR` is the core source-step instruction. It carries declared top-level columns and declared non-null paths.
- `DeclaredColumnIR` stores the logical type in JSON form; `DeclaredPathIR` stores both schema and logical forms.
- Generation's generated-declaration IR is in `code_generation.ir`; its nullability values are `Nullability.DECLARED`, `ENFORCED` and `DEFAULTED`.
- No ingest artifact carries a schema version. A source's `version` is opaque metadata.

## Boundaries

- Surfaces: source bindings are author-facing through `kg_build_system.table`; `table.interfaces` exposes bound-source values; the source IR is `table.ir`.
- `engines` imports `types.interfaces`, `expressions.ir`, `relational.interfaces`, `table.ir` and `_relations`; it must not import `code_generation`, `compile`, `workflow`, `modules`, `api` or `cli`.
- `code_generation` imports `types.interfaces` and `engines.interfaces` as a schema observer; it must not import `compile`, `workflow`, `modules` or `api`.
- `modules` may import the interfaces and IR of every layer; it must not be imported by `code_generation`, `table` or `engines`.
- The source reader is DuckDB: `read_csv_auto`, `read_json_auto` and `read_parquet`. No second reader observes file contents.

## Current decisions

### Source formats and trust tiers

- Inference chooses one tier per source suffix:
  - `.db`, `.ddb`, `.duckdb` — `enforced`: a `DESCRIBE` `null = NO` becomes `ENFORCED`; `YES` becomes `DEFAULTED`.
  - `.parquet`, `.pq` — `declared`: the Parquet footer supplies nullability at every level.
  - `.csv`, `.tsv`, `.json`, `.jsonl`, `.ndjson` — `defaulted`: no level carries a non-null declaration.
- Inference classifies a source by suffix. A build reads by the declared `DataSourceConfig.format`, not by the suffix; a mismatch fails before a row is consumed.
- `DESCRIBE` decides which top-level columns exist and what scalar each holds. For Parquet, `parquet_schema()` decides nested shape and repetition at every level.
- A DuckDB column with no Parquet footer node, such as a Hive partition key, is `DEFAULTED`.
- A footer node that DuckDB's read does not expose fails generation; the two views of the file disagree.
- Files in one partitioned source must declare the same nodes. A disagreement fails and names both files rather than choosing the first.
- When neither `DESCRIBE` nor the footer types a node or list item, generation fails; no type is guessed.
- Schema-less sources are nullable at every level: fields, array items and struct members. Absence of a declaration is never read as evidence of presence.
- The inference provider refuses `.db`, `.ddb` and `.duckdb` inputs: no `InputFormat` selects a database reader, so such a contract could be inferred but never bound. The error names `InputFormat` and says the relation can never be bound.
- The provider supports local paths and `http`, `https` and `s3` sources. `anonymous=True` applies only to S3.
- `mode="table"` reads one file or one remote object and one relation. A directory requires `mode="table_group"`. `layout != "files"` requires `mode="table_group"`. `relation` is required when a table input exposes more than one relation and is refused for table-group inference.
- `layout="files"` treats each supported file as a table. `parquet_parts` and `hive_partitioned_parquet` group Parquet files into logical tables; Hive partition directories are removed from the logical path.
- Unsupported suffixes fail generation. A directory with no supported relations fails.

### Nullability claims

- A non-null inferred field records `DECLARED` or `ENFORCED`; a nullable field records `DEFAULTED` and carries `GeneratedNullableType`.
- A Parquet `REQUIRED` node is `DECLARED`; `OPTIONAL` is `DEFAULTED`; the rule applies at field, array-item and struct-member level.
- An enforced database column with `null = NO` is `ENFORCED`; `YES` is `DEFAULTED`.
- Generated top-level nullability is rendered into the generated field annotation: `DEFAULTED` renders `Field[T | None]`, `DECLARED`/`ENFORCED` renders `Field[T]`. Source access follows that annotation. Nested member and array-item nullability stay in the value type.
- `NullabilityNote` is emitted once per source: enforced, declared, or not declared. The line names the source and, for an enforced relation, the relation.

### Digest gate

- Every DuckDB type name is classified exactly once by `DIGEST_TABLE`; aliases `JSON`, `TIMETZ` and `TIMESTAMPTZ` resolve to their reported families.
- `canonical` types digest as-is or through a widening cast: booleans, integer widths through `UINTEGER`, `FLOAT`, `DOUBLE`, `VARCHAR`, `ENUM`, `UUID`, `DATE`, `TIME`, `TIMESTAMP`, `TIMESTAMP_S`, `TIMESTAMP_MS` and the `LIST`, `ARRAY` and `STRUCT` container families.
- `declared_only` types require an author declaration because their only cast narrows: `UBIGINT`, `HUGEINT`, `UHUGEINT`, `TIME_NS`, `TIMESTAMP_NS`.
- `refused` types have no meaning-preserving canonical form: `DECIMAL`, `BIGNUM`, `BIT`, `BLOB`, `TIME WITH TIME ZONE`, `TIMESTAMP WITH TIME ZONE`, `INTERVAL`, `MAP`, `UNION`, `VARIANT`, `ROW`, untyped `NULL`, `TYPE`, `GEOMETRY` and `GEOGRAPHY`.
- An unrecognised type name is not a refusal; it is unsupported and fails generation.
- A declared-only type without an override fails generation and names the narrowing, the canonical target and the override syntax. A declared-only nested member has no override route.
- A refused type cannot be lifted by any override. `DECIMAL` is not coerced to `float`.
- Containers digest from their item or member types; a bare container has no single canonical scalar type.

### Widening

- Ingest widens and never narrows by itself.
- At build, every declared top-level column is cast in the per-source view to the canonical SQL type its logical type composes to: `int` to `BIGINT`, `float` to `DOUBLE`, `str` to `VARCHAR`, `bool` to `BOOLEAN`, and identity for `date`, `time`, `timestamp` and `uuid`.
- A `NullableType` casts to its base SQL type; nullability is not part of an SQL type. An array of castable items casts element-wise; a struct, a custom type and an array containing either have no canonical SQL type and are left uncast.
- The cast repeats the column's own name, so widening never renames it.
- A multi-file Parquet source is widened in its own source view before any union, so one partition's narrower physical width does not leak into another.
- A declared-only narrowing is applied only when an override declares it. The cast is checked: a value outside the target aborts the build.
- A request `type` override is a declaration, not an inference. It may target any canonical unit type for a scalar the gate maps, including a type the reader reports differently; the scan applies the checked cast.

### Generation-time declared overrides

- `override` is keyed by the full `<relation path>.<column>` path, for example `temperature.recorded_on`. A bare column name, a missing relation part, a nested member path and an unknown column are refused with the available names.
- `type` declares one canonical unit type for one whole top-level column. It cannot promote a container, cannot lift a refused type and must name a canonical unit.
- `nullable: true` declines a source-declared non-null claim: the field becomes `DEFAULTED` and leaves the statistics pre-flight.
- `nullable: false` records `DECLARED` where the source declared none and emits the header claim. The generated annotation then carries a non-null source field.
- An absent `nullable` keeps the source's own claim. An absent `type` keeps the reader's reported type.
- An override reaches exactly the relation it names and only whole top-level columns.
- Overrides live in the author-owned request. They are not part of the generated product and are not available as a runtime edit.

### Statistics pre-flight

- Statistics test a claim; they never set or enforce one.
- At generation, for a Parquet relation, declared non-null paths are checked against `parquet_metadata().stats_null_count` from file footers. A violation is logged with the source, null count, row count and schema path; generation continues. A path with no published statistic is logged as unknown, never as zero.
- At build, the check covers only Parquet declared non-null paths the build actually reads; reading a prefix covers everything below it. Unread columns are not reported.
- A build violation marks the source step `WARNING` and logs the count. It does not abort the build.
- A statistics read failure at build is logged and the build continues. The statistics step never replaces the guard.
- The generation pre-flight is per relation; one relation's declared path is never tested through another relation's files.
- Statistics cannot test composed expressions, and a non-Parquet source has no statistics.

### Guards and binding constraints

- Every binding output with a non-null logical type is guarded at the point of use: `build_key`, `source_build_key`, `target_build_key` and every property use the same rule and the same lowering path.
- A nullable binding output is not guarded. A null in a nullable property is data, not a violation.
- `_kg_nn(value, message)` aborts on the first null through DuckDB `error()`. The message names `<component>.<property>`; for a property or endpoint key it also names the row's `build_key`, while the `build_key` guard cannot include the key it is testing.
- The guard macro is created on connection setup, before any view exists. Creation is idempotent.
- There is no key-specific check and no fallback policy: every guard failure aborts. There is no configuration to downgrade, publish or continue.
- A guard is evaluated only where its output is read. A consumer that never reads the column does not fire it; enforcement is emission safety, not an audit.
- A binding property is cast to its topology-declared SQL type before the guard. Keys are not property-cast.
- A key must satisfy `require_non_nullable(require_scalar(...))`. A property must be a scalar or a flat, homogeneous array of non-null scalars. Nested structs and nested arrays are not graph properties; nullable array items must be removed with `drop_null_items()`.
- A binding property expression must match its declared property type under the current compatibility rule; see [bindings](bindings.md). Every declared property must be mapped exactly once.
- Before any row is read, the source step describes the relation and compares its columns with the declaration. A missing field fails with the declaration, the location and the available columns.
- A source whose bytes do not match its declared `InputFormat` fails during the pre-use check or at view creation, with the declaration, location and format.
