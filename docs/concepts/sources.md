# Sources

A table declaration describes the shape of a row. It says nothing about where
those rows live. A **source** supplies the location, and binding one to a table
is the only place a path, a URI or a credential appears in an author's project.

That separation is the point. The shape is portable truth about the data; the
source is a deployment detail that can change without changing a single field,
a projection or a binding.

## Binding a source

`bind_source` takes the declaration to bind and a `DataSourceConfig`. It returns
a `BoundSource` — either a bound table or a bound group — which compilation
consumes.

```python
from kg_build_system import DataSourceConfig, InputFormat, bind_source

from estate.table.sites import SitesTable

sites_source = bind_source(
    target=SitesTable,
    config=DataSourceConfig(
        location="data/sites.json",
        format=InputFormat.JSON,
        version="registry-2026-08",
    ),
)
```

Bind at module level. Discovery finds module-level `BoundSource` values
in the project namespace, or you can pass them explicitly with the bindings:

```python
contract = compile(bindings=(site_binding,), sources=(sites_source,), modules=modules)
```

Rules enforced at declaration time:

| Rule | What you see if it is broken |
| --- | --- |
| every table a binding or reached projection reads must be bound | `no source bound for: sites` |
| a table may be bound once | `source-bound table names must be unique` |
| a source must target a final `Table` or `TableGroup` | `sources require a final Table or TableGroup` |

`Read` follows the whole reachable plan: a binding's expressions and row source,
then every projection those reference, in turn. A table that no reached binding
or projection reads is not required, even if it is declared or appears in a
group source.

The source binding is the physical fact, not the table declaration: the
declaration stays the same when the location moves, and only the binding changes.

## `DataSourceConfig`

| Field | Meaning | Default |
| --- | --- | --- |
| `location` | a file, a directory, a glob or a URI | required |
| `format` | which reader to use | `InputFormat.CSV` |
| `layout` | how to derive each member's path, for a group source only | `None` |
| `credentials` | the name of a runtime credential entry | `None` |
| `version` | a free-text label recorded with the source | `None` |

The config is a frozen value: no file is opened when you declare one, and two
sources with equal fields are interchangeable.

## Choosing the format

`InputFormat` has three members, and each selects one reader: `CSV` reads
delimited text, `JSON` reads JSON lines or arrays, and `PARQUET` reads Parquet.
The CSV reader sniffs the delimiter. At build time the declared format decides,
not the file name.

That is deliberate: a wrong format is a loud failure rather than a quiet
misread. Several spellings work under the right reader — `.tsv` parses as
`CSV` because the delimiter is sniffed, `.jsonl` and `.ndjson` parse as `JSON`,
and `.pq` parses as `PARQUET`.

A location may be a single file, a glob or a directory, as far as the reader
supports it — Parquet accepts a directory of parts, and the file readers accept
a glob.

!!! warning "The default format is CSV"
    Omitting `format` on a JSON or Parquet source compiles cleanly and fails when
    that source is opened. Because the check happens before any row is consumed,
    you get a framework message naming the declaration, the location and the
    declared format, rather than a reader error.

## A single table

For one table, `location` alone says what to read: it points at the table's own
file, glob or directory, and `layout` plays no part.

```python
equipment_source = bind_source(
    target=EquipmentTable,
    config=DataSourceConfig(
        location="data/equipment.json",
        format=InputFormat.JSON,
    ),
)
```

Use this when each table has its own chosen location, or when the locations do
not follow a rule.

## A group source

A table group is a hierarchy of final tables. Binding the group binds every
member table, and `layout` says how to turn a member's place in the hierarchy
into a path.

```python
from kg_build_system import TableGroup, TableGroupOptions


class ReadingsTableGroup(TableGroup):
    options = TableGroupOptions(name="readings")
    temperature = TemperatureTable
    mechanical = MechanicalTableGroup
```

```python
readings_source = bind_source(
    target=ReadingsTableGroup,
    config=DataSourceConfig(
        location="data",
        format=InputFormat.JSON,
        layout="{group_path}/{table_name}.json",
    ),
)
```

Given a `MechanicalTableGroup` named `mechanical` containing a `vibration` table,
that one layout resolves:

| Table | `{group_path}` | `{table_name}` | Location |
| --- | --- | --- | --- |
| `temperature` | `readings` | `temperature` | `data/readings/temperature.json` |
| `vibration` | `readings/mechanical` | `vibration` | `data/readings/mechanical/vibration.json` |

`{group_path}` is the chain of group names above the table — each group's
`options.name`, or its class name without `TableGroup` — joined with `/`.
`{table_name}` is the table's own name. Those are the only placeholders: anything
else fails with `group source layouts may use only {group_path} and {table_name}`.

Further rules:

- A group source without a layout is refused at compile with `group sources
  require DataSourceConfig.layout to resolve each table`.
- A table may appear only once in a group, two tables may not share a catalog
  path, and groups may not contain a cycle.
- The layout must resolve every member of the group, because binding the group
  resolves the whole family. Members that no reached binding or projection reads
  are then dropped: they do not enter the blueprint and no source is recorded for
  them.

A group source does **not** join, merge or widen anything. It only names
locations; each member table keeps its own rows and its own shape.

## One source per table, or one per group

| Use a table source when | Use a group source when |
| --- | --- |
| each table has its own location | members share a format and a naming rule |
| locations are chosen individually | the hierarchy already mirrors the directory tree |
| one table is read from an unusual place | you want one change to move the whole family |

Binding a table and also the group containing it is an error: the table would be
bound twice. Pick one level per family.

## Local files and object stores

A local location is a path. Prefer an absolute path, or build one from
`Path(__file__).parent`, so the build does not depend on where the process was
started; a relative path resolves against the process's current directory.

An object store is a URI with a scheme, and a private store needs a credential
reference:

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

The declaration carries the *name* of the credential, never the secret. The
value is supplied at build time:

```python
from kg_build_system import BuildRuntime, build

report = build(
    contract,
    runtime=BuildRuntime(credentials={
        "estate_lake": '{"filesystem_options": {"key": "...", "secret": "..."}}',
    }),
    output_directory="build",
)
```

The credential value is a JSON object whose `filesystem_options` are handed to
the filesystem implementation for the URI's scheme; unknown keys are refused. A
credentialed location must have a scheme, and a bare path with a credential
fails with `credentialed source locations require a URI scheme`. The filesystem
is configured when that source is read, not when the contract is compiled, so
the frozen contract stays free of secrets.

## Versions

`version` is a free-text label recorded verbatim in the source entry of the
compiled contract, next to the location and the format. Nothing in the build
interprets it: it does not select a file, pin a commit or trigger a download.

Use it to name the snapshot you meant — `registry-2026-08`, a warehouse release
tag, an export date — so whoever reads the contract can see which vintage of the
data it described.

## Keeping acquisition out of declarations

The two layers are separate on purpose:

- `table/` holds table and struct declarations: fields, types, descriptions,
  annotations. A generated table package contains no path and must not be
  edited; regenerate it from the request instead.
- The module that binds sources holds every location, format, credential
  reference and version.

```text
request ──generate──> table/ (shape only) ──bind_source──> sources.py (location only)
```

Changing where a file lives edits the source binding, and no table, projection
or binding changes. Changing a column edits the table declaration, and every
binding that reads that column is checked against it. Neither edit can hide
inside the other.

Source-level provenance belongs on the bound source, using
`SourceBindingOptions(annotations=...)`; it describes where the rows came from,
not what a row means. The compiled source entry carries the table declaration's
own annotations first, then the source binding's annotations. A group source's
annotations are copied to each resolved member. Annotations themselves are
covered on [annotations and descriptions](annotations.md).

## What the build checks before reading rows

Compilation records the declared fields alongside the location. When the build
starts that source, before any row is consumed, it compares the two:

- a field the contract declares but the source does not expose fails with
  `declared field(s) 'opened_on' are absent from '<location>' for '<table>';
  the source exposes ...`
- a source whose bytes do not match the declared format fails with `the source
  at '<location>' for '<table>' cannot be read as the declared 'json' format`
- a null that reaches a non-null graph property or key fails at the point of
  use, naming the property and the row key — see
  [types](types.md#nullability-on-access).

This ordering is what makes a source defect readable: by the time a binding
runs, the table is known to have the declared columns, in the declared format.

## What to remember

- A source binding is the only place a location, format or credential appears.
- Bind at module level; discovery finds `BoundSource` values in the package.
- A group source maps a table's place in the hierarchy to a path. It does not
  join, merge or change the rows.
- `version` is a label, not a pin. Pin input data in your own pipeline.
- A source defect surfaces before any row is consumed, so read the first
  failure rather than the last.

Next: [Expressions](expressions.md) turns these typed rows into values.
