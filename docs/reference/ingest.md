# Sources and ingest

A source binding turns a physical file or URI into typed rows, and the build checks the source before reading rows.

A source binding is the only build-time place a location, format, credential
reference or version appears in an author's project. The logical side is on
[data contracts](../concepts/data-contracts.md); the physical side and its rules
are on [sources](../concepts/sources.md). Types are on
[types](types.md), and generated packages are on [generation](generation.md).

## `DataSourceConfig`

```python
DataSourceConfig(
    location: str,
    format: InputFormat = InputFormat.CSV,
    layout: str | None = None,
    credentials: str | None = None,
    version: str | None = None,
)
```

`DataSourceConfig` is a frozen value. Declaring one opens no file and resolves no
credential.

| Field | Meaning | Default |
| --- | --- | --- |
| `location` | A file, directory, glob or URI | Required, non-empty |
| `format` | The reader to use | `InputFormat.CSV` |
| `layout` | How a group source derives each member's path | `None` |
| `credentials` | The name of a runtime credential entry | `None` |
| `version` | A free-text label recorded with the source | `None` |

```python
from kg_build_system import DataSourceConfig, InputFormat

config = DataSourceConfig(
    location="data/sites.json",
    format=InputFormat.JSON,
    version="registry-2026-08",
)
```

`version` is recorded verbatim in the compiled source entry. It selects no file,
pins no commit and triggers no download.

## `InputFormat`

| Member | Value | Reader | Accepts |
| --- | --- | --- | --- |
| `InputFormat.CSV` | `"csv"` | `read_csv_auto` | Delimited text; the delimiter is sniffed, so `.tsv` works under `CSV` |
| `InputFormat.JSON` | `"json"` | `read_json_auto` | JSON lines or arrays, including `.jsonl` and `.ndjson` |
| `InputFormat.PARQUET` | `"parquet"` | `read_parquet` | Parquet files or a directory of parts, including `.pq` |

The build reader is chosen by `format`, not by the file suffix. A source may be a
single file, a glob or a directory as far as its reader supports it.

!!! warning "The default format is CSV"
    Omitting `format` on a JSON or Parquet source compiles cleanly and fails when
    the source is opened. The failure names the declaration, the location and the
    declared format, before any row is consumed.

## `bind_source`

```python
bind_source(
    *,
    target: type[Table | TableGroup],
    config: DataSourceConfig,
    options: SourceBindingOptions = SourceBindingOptions(),
) -> BoundTable | BoundTableGroup
```

`bind_source` attaches a physical configuration to one final table or one table
group. The returned value is a `BoundSource`: either a `BoundTable` or a
`BoundTableGroup`.

| Parameter | Meaning |
| --- | --- |
| `target` | A final `Table` or `TableGroup` class |
| `config` | The physical location and reader settings |
| `options` | `SourceBindingOptions(annotations=())`; source-level provenance |

The returned value is one of:

| Type | Fields |
| --- | --- |
| `BoundTable(table, config, annotations=())` | One concrete table and its configuration |
| `BoundTableGroup(group, config, annotations=())` | One group and the layout that resolves its members |
| `BoundSource` | The alias `BoundTable \| BoundTableGroup` |

```python
from kg_build_system import DataSourceConfig, InputFormat, bind_source

sites_source = bind_source(
    target=SiteTable,
    config=DataSourceConfig(
        location="data/sites.json",
        format=InputFormat.JSON,
        version="registry-2026-08",
    ),
)
```

Bind at module level. Discovery finds module-level `BoundSource` values in the
project namespace, or pass the values explicitly:

```python
contract = compile(
    bindings=(site_binding,),
    sources=(sites_source,),
    modules=modules,
)
```

Rules:

| Rule | Failure |
| --- | --- |
| The target must be a final `Table` or `TableGroup` | `sources require a final Table or TableGroup` |
| `location` must be non-empty | `data sources require a non-empty location` |
| Every table a reached binding or projection reads must be bound | `no source bound for: <tables>` |
| A table may be bound only once | `source-bound table names must be unique` |
| A table and the group containing it may not both be bound | The same duplicate-source failure: the table would be bound twice |

Source annotations are recorded on the compiled source entry. The table
declaration's own annotations come first, then `SourceBindingOptions`
annotations. A group source copies its annotations to each resolved member.

## Table groups and layout

A `TableGroup` names a hierarchy of final tables and nested groups. It is a
catalog and a source-binding convenience, not a shape and not a row source.

```python
from kg_build_system import (
    DataSourceConfig, Field, InputFormat, Table, TableGroup, TableGroupOptions,
    bind_source, field,
)


class TemperatureTable(Table):
    station_id: Field[str] = field()


class VibrationTable(Table):
    device_id: Field[str] = field()


class MechanicalTableGroup(TableGroup):
    options = TableGroupOptions(name="mechanical")
    vibration = VibrationTable


class ReadingsTableGroup(TableGroup):
    options = TableGroupOptions(name="readings")
    temperature = TemperatureTable
    mechanical = MechanicalTableGroup


readings_source = bind_source(
    target=ReadingsTableGroup,
    config=DataSourceConfig(
        location="data",
        format=InputFormat.JSON,
        layout="{group_path}/{table_name}.json",
    ),
)
```

`{group_path}` is the chain of group names above the table, joined with `/`; each
name comes from `TableGroupOptions(name=...)` or the class name without
`TableGroup`. `{table_name}` is the table's own logical name. Those are the only
placeholders.

| Table | `{group_path}` | `{table_name}` | Location |
| --- | --- | --- | --- |
| `temperature` | `readings` | `temperature` | `data/readings/temperature.json` |
| `vibration` | `readings/mechanical` | `vibration` | `data/readings/mechanical/vibration.json` |

Rules:

- A group source requires `layout`; without one it fails with `group sources
  require DataSourceConfig.layout to resolve each table`.
- A layout may use only `{group_path}` and `{table_name}`; anything else fails
  with `group source layouts may use only {group_path} and {table_name}`.
- Members must be final tables or other groups. A table appears once, catalog
  paths are unique, and groups contain no cycle.
- A group with no members is refused with `table groups must declare at least
  one member`.
- The layout resolves the whole group because binding the group binds every
  member. Members that no reached binding or projection reads are then dropped
  from the blueprint and have no recorded source.
- A group source does not join, merge or widen anything. Each member keeps its
  own rows and its own shape.

Use a table source when each table has its own location or naming does not follow
a rule. Use a group source when a family shares a format and a naming rule.

## Locations and credentials

A local location is a path. Prefer an absolute path, or one built from
`Path(__file__).parent`, so the build does not depend on the process's current
directory. A relative path resolves against that directory.

An object store is a URI with a scheme. A private store names a runtime
credential:

```python
lake_source = bind_source(
    target=SitesTable,
    config=DataSourceConfig(
        location="s3://estate-registry/2026-08/sites.parquet",
        format=InputFormat.PARQUET,
        credentials="estate_lake",
    ),
)
```

The declaration carries the credential name, never the value. Supply the value
through `BuildRuntime(credentials=...)`; the contract and the report contain no
secret. The value is a JSON object whose `filesystem_options` are handed to the
filesystem for the URI's scheme. Unknown keys are refused, and a credentialed
location without a scheme fails with `credentialed source locations require a URI
scheme`.

## Generated nullability

A generated package records the source's nullability claim in the rendered field
and in provenance. A `DEFAULTED` field is nullable; a `DECLARED` or `ENFORCED`
field is non-null.

### Trust tiers

The built-in inference provider chooses one tier from the source suffix:

| Source suffix | Tier | Claim |
| --- | --- | --- |
| `.parquet`, `.pq` | Declared | The Parquet footer supplies `required` or `optional` at every level |
| `.csv`, `.tsv`, `.json`, `.jsonl`, `.ndjson` | Defaulted | No level declares non-nullability; all members are nullable |
| `.db`, `.ddb`, `.duckdb` | Enforced | A catalog `NOT NULL` constraint is enforced |

The `Nullability` values are `DECLARED`, `ENFORCED` and `DEFAULTED`. A nullable
field records `DEFAULTED`; a Parquet `REQUIRED` field records `DECLARED`; an
enforced catalog constraint records `ENFORCED`.

The built-in provider refuses database inputs because no `InputFormat` selects a
database reader: a generated contract could never be bound. Export the relation
to Parquet, or declare the table outside a generated package. The enforced tier
still exists for a provider that can observe an enforced catalog.

### What is rendered

- A `DEFAULTED` field renders `Field[T | None]` and reads as nullable.
- A `DECLARED` or `ENFORCED` field renders `Field[T]` and reads as non-null.
- Nested member and array-item nullability stay in the value type.
- The header records one note per source, or per relation in a group:

| Tier | Header line |
| --- | --- |
| Enforced | `nullability: enforced by relation '<relation>' in <file> (NOT NULL)` |
| Declared | `nullability: declared by <file> (required/optional)` |
| Defaulted | `nullability: not declared by <file> - all members nullable` |

The source digest in `.kbs-generation.json` is provenance only. It is not a
tracked input, and a change to it alone does not make a generated product stale.

### Overrides

An override settles a source's claim or type for one whole top-level column. It
is request-time configuration, not a generated declaration and not a runtime
option in the compiled contract.

```python
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig, InferDataContractProvider,
)
from kg_build_system.generation.code_generation import generation

readings = generation(
    InferDataContractProvider,
    DataContractInferenceConfig(
        source="../data/readings.parquet",
        override={
            "readings.recorded_on": {"type": "timestamp"},
            "readings.quality": {"nullable": False},
        },
    ),
)
```

| Override entry | Effect |
| --- | --- |
| `{"type": "<canonical unit>"}` | Declares the whole column's canonical type; the scan applies a checked cast |
| `{"nullable": True}` | Declines a source non-null claim; the field records `DEFAULTED`, renders `Field[T \| None]`, and leaves the pre-flight |
| `{"nullable": False}` | Asserts a non-null claim; the field records `DECLARED`, renders `Field[T]`, and enters the pre-flight |
| Absent `nullable` | Keeps the source's own claim |
| Absent `type` | Keeps the reader's reported type |

Keys are the full `<relation path>.<column>` path. A bare column name, a missing
relation part, a path that reaches inside a column, and an unknown column are
refused with the available names. `type` must name a canonical unit type, cannot
promote a container and cannot lift a refused physical type. An override never
reads values to decide a claim; the checked cast or the build guard tests the
declaration against the data.

The full request model is on [Generation](generation.md#request-model), the
built-in provider is on [Generation](generation.md#built-in-inference-provider),
and the override contract is on [Generation](generation.md#override-contract).

## Digest gate

The generation digest gate maps each DuckDB type it understands to a canonical
type with one of three dispositions:

| Disposition | Meaning | Author action |
| --- | --- | --- |
| `canonical` | Accepted as reported or through the automatic widening cast | None |
| `declared_only` | The only cast narrows the value or its precision | Declare the type in `override` |
| `refused` | No meaning-preserving canonical type exists | Export a supported type, or handwrite the table |

- `declared_only` examples are `UBIGINT`, `HUGEINT`, `UHUGEINT`, `TIME_NS` and
  `TIMESTAMP_NS`. The override makes the cast explicit; the cast is checked and a
  value that does not fit aborts the build.
- A declared-only nested member has no override route, because an override
  reaches top-level columns only. Export it in a mappable type or handwrite the
  contract.
- `refused` examples are `DECIMAL`, `BIGNUM`, `BIT`, `BLOB`, `TIME WITH TIME
  ZONE`, `TIMESTAMP WITH TIME ZONE`, `INTERVAL`, `MAP`, `UNION`, `VARIANT`,
  `ROW`, untyped `NULL`, `TYPE`, `GEOMETRY` and `GEOGRAPHY`. No override lifts a
  refusal; `DECIMAL` is not coerced to `float`.
- A container is digested from its item or member types. It is not a scalar and
  cannot be promoted as one.
- A type name outside the gate is unsupported, not refused. Generation fails
  rather than accepting it by default.

The complete DuckDB mapping and the reason each refused type is refused are on
[types](types.md#duckdb-dispositions).

## Widening

The ingest boundary widens and never narrows by itself. At build, each declared
top-level column is cast in its per-source view to the canonical SQL type:

| Canonical | SQL type |
| --- | --- |
| `bool` | `BOOLEAN` |
| `int` | `BIGINT` |
| `float` | `DOUBLE` |
| `str` | `VARCHAR` |
| `date` | `DATE` |
| `time` | `TIME` |
| `timestamp` | `TIMESTAMP` |
| `uuid` | `UUID` |

Further rules:

- A nullable type casts to its base type; nullability is not part of an SQL type.
- An array of castable items casts element-wise. A struct, a custom type, and an
  array containing either have no canonical SQL type and are left uncast.
- The cast repeats the column's own name, so widening never renames a column.
- A multi-file Parquet source is widened in its own source view before any union,
  so one partition's narrower physical width does not leak into another.
- A declared-only narrowing is applied only when an override declares it. The
  cast is checked: a value outside the target range aborts the build.
- A request `type` override is a declaration, not an inference. It may target any
  canonical unit type for a scalar the gate maps, including a type the reader
  reports differently; the scan applies the checked cast.

## Statistics pre-flight

A statistic tests a claim; it never sets or enforces one. The pre-flight is
Parquet-only and reads file footers, never rows.

At generation, the declared non-null top-level fields of a relation are checked
against `parquet_metadata().stats_null_count`:

- A violation is logged with the source, null count, row count and schema path.
  Generation continues.
- A path with no published statistic is logged as unknown, never as zero.
- The check is per relation; one relation's declared path is never tested through
  another relation's files.

At build, the check covers only the declared non-null Parquet paths the build
actually reads. Reading a prefix covers every path below it, so an unread column
is not reported.

- A violation marks the source step `WARNING` and logs the count. It does not
  abort the build.
- A failure to read the statistics is logged, and the build continues.
- The pre-flight never replaces the guard.

Statistics cannot test a composed expression. A non-Parquet source has no
statistics, so its claims are tested only by the guard at the point of use.

## Guards

Every binding output with a non-null logical type is guarded where it is
delivered: `build_key`, `source_build_key`, `target_build_key` and every
non-null property. A nullable output is not guarded; a null there is data, not a
violation.

- A null aborts the build on the first value read.
- A property or endpoint-key message names `<component>.<property>` and the row's
  `build_key`. A `build_key` message names the component and states that the key
  is declared non-null, not the key value.
- The guard is evaluated only where its output is read. A consumer that never
  reads the column does not fire it; this is emission safety, not an audit.
- A property is cast to its topology-declared type before the guard. Keys are
  not property-cast.
- There is no configuration to downgrade, publish or continue past a guard
  failure.
- A key must already be a non-null scalar expression; the binding factory refuses
  a nullable or composite key before the build runs.

## What the build checks before reading rows

Compilation records the declared fields with the location. When the build starts
a source, before any row is consumed, it describes the scan and compares the two:

| Defect | Failure |
| --- | --- |
| A declared field the source does not expose | `declared field(s) '<name>' are absent from '<location>' for '<table>'; the source exposes ...` |
| Bytes that do not match the declared format | `the source at '<location>' for '<table>' cannot be read as the declared '<format>' format` |

Only after those checks does a binding read rows. A null that reaches a non-null
property or key then fails at the guard, naming the property and the row key.

## Limits

- `version` is a label, not a pin. Pin input data in your own pipeline.
- A source binding stores a credential reference; the secret is runtime input
  and never enters the contract or report.
- A group source maps hierarchy to paths. It does not join, merge, widen or
  change rows.
- A group layout may use only two placeholders, `{group_path}` and
  `{table_name}`; resolved paths are joined to `location`.
- The build reader follows `format`, not the suffix. A mismatch fails before any
  row is consumed.
- A table may have one source, and a family may be bound at one level only.
- Generation classifies a source by suffix; a schema change enters a generated
  package only through `kbs generate --regenerate` or a request edit.
- A database input has an enforced tier in the model, but the built-in provider
  refuses it because no `InputFormat` can bind it. Export it to a supported
  format or handwrite the declaration.

## What to remember

- A source binding is the only build-time place a location, format, credential
  or version appears.
- A group source resolves paths; it never changes rows.
- The digest gate widens canonical types, requires an override for a
  declared-only type, and refuses a type with no canonical meaning.
- Generated nullability decides the field type: `DEFAULTED` renders
  `Field[T | None]`; `DECLARED` or `ENFORCED` renders `Field[T]`.
- A Parquet pre-flight reports nulls; the guard enforces non-nullability at the
  point of use.
- A source defect surfaces before any row is consumed.

Next: [Generation](generation.md) covers the requests that produce table
contracts. See also [types](types.md) and the [Glossary](glossary.md).
