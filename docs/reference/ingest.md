# Assets and ingest

An asset declares one logical unit of source data. A table names that asset, and
a module planner turns a compatible layout into typed rows. The build checks the
source before reading rows.

The logical side is on [data contracts](../concepts/data-contracts.md); the
asset model, layout and source planning are on [assets](../concepts/assets.md).
Types are on [types](types.md), and generated packages are on
[generation](generation.md).

## `AssetLayout`

```python
AssetLayout(
    kind: str | None = None,
    locator: str | None = None,
    format: str | None = None,
    selector: str | None = None,
    partition_by: Sequence[str] = (),
    members: Mapping[str, str] = {},
    properties: Mapping[str, str] = {},
)
```

Layout is optional descriptive metadata on an asset. It opens no file and
resolves no credential. It is not a Hive, catalog, schema or storage-style
model; every value is an open string.

| Field | Meaning |
| --- | --- |
| `kind` | Free-text storage kind, such as `parquet` or `json` |
| `locator` | A base path, directory or URI |
| `format` | The reader format, such as `parquet`, `json` or `csv` |
| `selector` | A one-relation path template |
| `partition_by` | Semantic partition keys, in order |
| `members` | Per-relation paths keyed by relation name |
| `properties` | Portable reader hints |

```python
from kg_build_system import AssetLayout

layout = AssetLayout(
    kind="json",
    locator="data",
    format="json",
    members={"sites": "sites.json"},
)
```

The generic planner resolves one relation's location in this order:

1. `members[relation]`, when present;
2. otherwise `selector` formatted with `{table}` and `{table_path}`;
3. otherwise `locator`.

A relative member or selector result is joined to `locator`. An absolute path or
a value with a URI scheme is used as written. `{table}` is the relation's
logical name. `{table_path}` replaces dots with `/`: `readings.vibration`
becomes `readings/vibration`.

`partition_by` describes meaning, not directory names. It records that rows with
different partition values describe different physical slices.

`properties` carries portable hints. The generic planner reads
`properties["credentials"]` as the runtime credential reference. A secret is
never part of the layout.

## The generic source planner

```python
DuckDbSourcePlanner(
    *,
    formats: Sequence[str] = ("parquet", "json", "csv"),
    union_by_name: bool = False,
)
```

`DuckDbSourcePlanner` is a module planner, not an adapter and not a registry
entry. It emits one source step for each asset-backed relation the graph reads:

| Property | Value |
| --- | --- |
| `component_id` | `"duckdb"` |
| Step name | `source.<relation_name>` |
| Output | `CoreArtifactTypes.table(relation_name)` |
| Instruction kind | `("source_relation", "duckdb")` |

The step payload carries `relation`, `location`, `format`,
`credential_reference`, `declaration`, `declared_columns` and `declared_paths`.

Rules:

- One asset may produce many source steps.
- A relation is included only when a binding or projection reads it.
- A relation with no layout, an unsupported format or no resolvable location
  produces no step. If the graph reads it, compilation reports an unresolved
  plan opening.
- Two producers for one relation artifact are refused.
- `formats` restricts which layouts this planner accepts.
- `union_by_name` is accepted and currently does not change the emitted step;
  the generic planner resolves one location per relation.

`default_toolchain` adds one `DuckDbSourcePlanner` before the core planners
unless a supplied planner already reports `component_id == "duckdb"`. Another
format is supported by another ordinary module planner with its own instruction
kind. There is no adapter registry.

## Readers and formats

| `format` or `kind` | Reader | Accepts |
| --- | --- | --- |
| `parquet` | `read_parquet` | Parquet files or a directory of parts, including `.pq` |
| `json` | `read_json_auto` | JSON lines or arrays, including `.jsonl` and `.ndjson` |
| `csv` | `read_csv_auto` | Delimited text; the delimiter is sniffed, so `.tsv` works as `csv` |

The planner resolves `layout.format` first and falls back to `layout.kind`.
Values are matched exactly against the accepted set; write them in lower case.
The reader follows the declared value, not the file suffix.

!!! warning "A layout is not a reader claim"
    A layout that names no supported format produces no source step. If the graph
    reads the relation, compilation reports an unresolved plan opening. The
    failure is at plan time, not after a partial read.

## Table groups

A `TableGroup` is a catalog of final tables and nested groups. It binds nothing.
Each member table names its own asset:

```python
from kg_build_system import (
    Asset, AssetAuthority, AssetOptions, AssetSemantics, Field, Table,
    TableGroup, TableGroupOptions, field,
)


class Estate(Asset):
    options = AssetOptions(
        semantics=AssetSemantics(
            subject="monitored estate",
            coverage="sites and readings",
            authority=AssetAuthority.PRIMARY,
            basis="estate export",
        ),
    )


class TemperatureTable(Table[Estate]):
    station_id: Field[str] = field()


class VibrationTable(Table[Estate]):
    device_id: Field[str] = field()


class MechanicalTableGroup(TableGroup):
    options = TableGroupOptions(name="mechanical")
    vibration = VibrationTable


class ReadingsTableGroup(TableGroup):
    options = TableGroupOptions(name="readings")
    temperature = TemperatureTable
    mechanical = MechanicalTableGroup
```

A group may contain tables from more than one asset. Members that no reached
binding or projection reads are dropped: they do not enter the blueprint and
produce no source step.

| Error | Trigger |
| --- | --- |
| `table groups must declare at least one member` | The group has no table or group member |
| `table groups may contain only final Table or TableGroup declarations` | A member is not a final table or group |
| `table groups may not contain a cycle` | A group contains itself, directly or through nested groups |
| `a table group may include a final table only once` | The same table is reached through two catalog paths |
| `a table group has duplicate catalog paths` | Two members resolve to the same catalog path |

## Locations and credentials

A local location is a path. Prefer an absolute path, or one built from
`Path(__file__).parent`, so the build does not depend on the process's current
directory.

An object store is a URI with a scheme. A private store names a runtime
credential in `properties`:

```python
AssetLayout(
    kind="parquet",
    locator="s3://estate-registry/2026-08",
    format="parquet",
    members={"sites": "sites.parquet"},
    properties={"credentials": "estate_lake"},
)
```

The layout carries the credential name, never the value. Supply the value
through `BuildRuntime(credentials=...)`; the workflow plan and the report contain
no secret. The value is a JSON object whose `filesystem_options` are handed to
the filesystem for the URI's scheme. Unknown keys are refused, and a credentialed
location without a scheme fails.

## Generated nullability

A generated package records the source's observed nullability claim as
provenance. Every generated source-backed field renders `Field[T]`; source
access is a `NullableSelection[T]` because the owner is a source `Table` or
`Struct`. The claim feeds the statistics pre-flight and the manifest notes, and
it never adds absence to the rendered field.

### Trust tiers

The built-in inference provider chooses one tier from the source suffix:

| Source suffix | Tier | Claim |
| --- | --- | --- |
| `.parquet`, `.pq` | Declared | The Parquet footer supplies `required` or `optional` at every level |
| `.csv`, `.tsv`, `.json`, `.jsonl`, `.ndjson` | Defaulted | No level declares non-nullability; all members are nullable |
| `.db`, `.ddb`, `.duckdb` | Enforced | A catalog `NOT NULL` constraint is enforced |

The `Nullability` values are `DECLARED`, `ENFORCED` and `DEFAULTED`. A source
with no non-null claim records `DEFAULTED`; a Parquet `REQUIRED` field records
`DECLARED`; an enforced catalog constraint records `ENFORCED`. The tier is
provenance: it selects the pre-flight and the header note, not the rendered
field.

The built-in provider refuses database inputs because no supported asset layout
format selects a database reader: a generated table could never get a generic
source step. Export the relation to `parquet`, `json` or `csv`, contribute a
module planner for the database, or declare the table outside a generated
package. The enforced tier still exists for a provider that can observe an
enforced catalog.

### What is rendered

- Every generated source field renders `Field[T]` from its value type.
- Source access is `NullableSelection[T]` for every tier; the declaration does
  not encode the observed claim.
- Nested member and array-item nullability stay in the value type, as in
  `Field[Array[Nullable[str]]]`.
- Every generated table declares its asset: `class SitesTable(Table[Estate])`.
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
is a `DataContractInferenceConfig` value inside the asset's
`@asset_contract(AssetContractOptions(...))` decorator, not a generated
declaration and not a runtime option in the compiled workflow plan.

```python
from kg_build_system import (
    Asset, AssetAuthority, AssetOptions, AssetSemantics,
)
from kg_build_system.generation import AssetContractOptions, asset_contract
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig, InferDataContractProvider,
)


@asset_contract(AssetContractOptions(
    provider=InferDataContractProvider,
    configuration=DataContractInferenceConfig(
        mode="table_group",
        override={
            "readings.temperature.recorded_on": {"type": "timestamp"},
            "readings.quality": {"nullable": False},
        },
    ),
    package="estate.table",
))
class Estate(Asset):
    options = AssetOptions(
        semantics=AssetSemantics(
            subject="monitored estate",
            coverage="sites and readings",
            authority=AssetAuthority.PRIMARY,
            basis="estate export",
        ),
    )
```

| Override entry | Effect |
| --- | --- |
| `{"type": "<canonical unit>"}` | Declares the whole column's canonical type; the scan applies a checked cast |
| `{"nullable": True}` | Declines a source non-null claim; the field records `DEFAULTED`, still renders `Field[T]`, and leaves the pre-flight |
| `{"nullable": False}` | Asserts a non-null claim; the field records `DECLARED`, still renders `Field[T]`, and enters the pre-flight |
| Absent `nullable` | Keeps the source's own claim |
| Absent `type` | Keeps the reader's reported type |

Keys are the full `<relation path>.<column>` path. A bare column name, a missing
relation part, a path that reaches inside a column, and an unknown column are
refused with the available names. `type` must name a canonical unit type, cannot
promote a container and cannot lift a refused physical type. An override never
reads values to decide a claim; the checked cast or the build guard tests the
declaration against the data.

The request model is on [Generation](generation.md#request-model), the built-in
provider is on [Generation](generation.md#built-in-inference-provider), and the
override contract is on [Generation](generation.md#override-contract).

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
  table.
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
top-level column is cast in its per-relation source view to the canonical SQL
type:

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
- A multi-file Parquet relation is widened in its own source view before any
  union, so one partition's narrower physical width does not leak into another.
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
- A key must already be a present scalar selection; the binding factory refuses
  a nullable or composite key before the build runs.

## What the build checks before reading rows

The source step carries the declared columns and their logical types. When the
build starts a source, before any row is consumed, it describes the scan and
compares the two:

| Defect | Failure |
| --- | --- |
| A declared field the source does not expose | `declared field(s) '<name>' are absent from '<location>' for '<table>'; the source exposes ...` |
| Bytes that do not match the declared format | `the source at '<location>' for '<table>' cannot be read as the declared '<format>' format` |

Only after those checks does a binding read rows. A null that reaches a non-null
property or key then fails at the guard, naming the property and the row key.

## Limits

- `version` is a label, not a pin. Pin input data in your own pipeline.
- Layout is optional descriptive metadata, not an access contract. A relation
  without a compatible layout has no generic source step.
- The layout stores a credential reference; the secret is runtime input and never
  enters the workflow plan or report.
- One asset may back many tables; a table names exactly one asset.
- A group is a catalog. It does not bind, join, merge, widen or change rows.
- The generic planner follows `format` or `kind`, not the suffix. Values are
  matched exactly against `parquet`, `json` and `csv`.
- Generation classifies a source by suffix; a schema change enters a generated
  package only through `kbs generate --regenerate` or a request edit.
- A database input has an enforced tier in the model, but the built-in provider
  refuses it because no supported layout format can select a database reader.
  Export it to a supported format, contribute a module planner, or handwrite the
  declaration.

## What to remember

- An asset is the logical source package; a layout is optional metadata.
- `DuckDbSourcePlanner` handles `parquet`, `json` and `csv`; another module
  contributes another ordinary planner.
- A group resolves relations; it never changes rows.
- The digest gate widens canonical types, requires an override for a
  declared-only type, and refuses a type with no canonical meaning.
- Observed nullability is provenance: every generated source field renders
  `Field[T]` and reads as nullable because it belongs to a source.
- A Parquet pre-flight reports nulls; the guard enforces non-nullability at the
  point of use.
- A source defect surfaces before any row is consumed.

Next: [Generation](generation.md) covers the requests that produce table
contracts. See also [types](types.md) and the [Glossary](glossary.md).
