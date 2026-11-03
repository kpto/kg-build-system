# Sources

A source binds a table declaration to the physical place where its rows live.

A table says what a row looks like; it does not say whether the rows are in a JSON
file, a Parquet directory or an object store. Keeping the two apart is what lets a
file move without changing a field, a projection or a binding. The source is where
a build's location, format and credential reference appear, and it is attached
after the row shape is declared.

## Why sources are separate

The shape is durable truth about the data. The location is a deployment fact. A
pipeline that mixes them cannot answer simple questions: does this table come from
the production export or the test fixture? Which snapshot did the build read?

A source binding gives each table one answer. It is recorded in the compiled
contract next to the table's declared fields, so a reviewer can see what was read
without opening the build code. A path change edits the source module only.

## The model

`bind_source` takes a target and a `DataSourceConfig` and returns a `BoundSource`.
The target is a final `Table` or a `TableGroup`. The config carries five facts:

- **Location**: a file, a directory, a glob or a URI.
- **Format**: the reader to use, one of CSV, JSON or Parquet.
- **Layout**: how to derive a path for each member of a group source.
- **Credentials**: the name of a runtime credential entry, never the secret.
- **Version**: a free-text label recorded with the source.

The config is a frozen value. Declaring one opens no file, so a project can be
imported and compiled without its data being present.

Bind sources at module level. Discovery finds module-level `BoundSource` values in
the project, or you can pass them explicitly when compiling. Compilation follows
the bindings and the projections they reach; only tables that a reached binding
or projection reads must be bound. A table that is declared but never read needs
no source.

## Example: the survey files

The three survey tables have one file each:

```python
from estate.table import DefectTable, SiteTable, UnitTable
from kg_build_system import DataSourceConfig, InputFormat, bind_source

sites_source = bind_source(
    target=SiteTable,
    config=DataSourceConfig(
        location="data/survey/sites.json",
        format=InputFormat.JSON,
        version="survey-2026-08",
    ),
)

units_source = bind_source(
    target=UnitTable,
    config=DataSourceConfig(
        location="data/survey/units.json",
        format=InputFormat.JSON,
        version="survey-2026-08",
    ),
)

defects_source = bind_source(
    target=DefectTable,
    config=DataSourceConfig(
        location="data/survey/defects.json",
        format=InputFormat.JSON,
        version="survey-2026-08",
    ),
)
```

The declarations did not change. The survey tables still have the same fields;
only their physical locations were supplied.

## Choosing a format

`InputFormat.CSV`, `InputFormat.JSON` and `InputFormat.PARQUET` each select one
reader. The declared format decides, not the file name. That is deliberate: a
wrong format becomes a clear failure instead of a quiet misread. A CSV reader
sniffs the delimiter, so a tab-separated file reads as CSV; `.jsonl` and
`.ndjson` read as JSON; `.pq` reads as Parquet.

The default is CSV. Set `format` explicitly on a JSON or Parquet source. A missing
format compiles cleanly and fails when the source is opened, before any row is
consumed.

## When a family shares a layout

A `TableGroup` names a family of concrete tables and nested groups. One group
binding covers the whole family when the files follow one rule:

```python
from estate.table import DefectTable, SiteTable, UnitTable
from kg_build_system import (
    DataSourceConfig, InputFormat, TableGroup, TableGroupOptions, bind_source,
)


class SurveyTableGroup(TableGroup):
    """The survey relations, one file per table."""

    options = TableGroupOptions(name="survey")
    sites = SiteTable
    units = UnitTable
    defects = DefectTable


survey_sources = bind_source(
    target=SurveyTableGroup,
    config=DataSourceConfig(
        location="data",
        format=InputFormat.JSON,
        layout="{group_path}/{table_name}.json",
    ),
)
```

The layout resolves `data/survey/sites.json`, `data/survey/units.json` and
`data/survey/defects.json`. `{group_path}` is the chain of group names above the
table, and `{table_name}` is the table's own name. Those are the only
placeholders.

A group source names locations; it does not join, merge or widen the rows. Each
member keeps its own shape and its own grain. Members that no reached binding or
projection reads are dropped: they do not enter the blueprint. A table may appear
only once in a group, and groups may not contain a cycle. Use a group source when
the hierarchy already mirrors the directory tree or when one change should move
the whole family. Use table sources when locations are chosen individually.

Pick one level for a family. Binding a table and the group that contains it binds
the table twice.

## Credentials and versions

Object stores use a URI with a scheme. The declaration carries the *name* of a
credential, and the value is supplied to the build at runtime. The same site table
can come from an object store instead of a local file:

```python
lake_sites_source = bind_source(
    target=SiteTable,
    config=DataSourceConfig(
        location="s3://estate-registry/2026-08/sites.parquet",
        format=InputFormat.PARQUET,
        credentials="estate_lake",
    ),
)
```

The filesystem is configured when the source is read, not when the workflow plan
is compiled, so the frozen plan stays free of secrets. The credential value is a
JSON object whose `filesystem_options` are passed to the filesystem for the URI's
scheme.

`version` is a label, not a pin. It records which snapshot you meant —
`survey-2026-08`, a warehouse release tag, an export date — so the workflow plan
can be read later. Nothing in the build resolves it, downloads it or checks it. Pin input
data in the pipeline that produces the files.

## Decisions you make

- **Choose the format explicitly.** The CSV default is a trap for JSON and
  Parquet sources.
- **Prefer a stable path.** Use an absolute path or build one from
  `Path(__file__).parent`; a relative path resolves against the process's current
  directory.
- **Keep acquisition out of declarations.** A generated table package contains no
  path. Generated files must not be edited; regenerate them from the request
  instead.
- **Name credentials, never inline them.** A credentialed location needs a URI
  scheme, and the secret belongs in the build runtime.
- **Put provenance on the binding.** `SourceBindingOptions(annotations=...)`
  describes where the rows came from, not what a row means.

## Limits

- A source never changes a shape. It does not add, drop or rename a field; the
  declaration does that.
- A group source requires a layout; its single config supplies one format for
  every member.
- A group layout may use only `{group_path}` and `{table_name}`, and must resolve
  every member of the group.
- Every table a reached binding or projection reads must be bound, and each table
  may be bound once.
- A source can be a single file, a glob or a directory as far as its reader
  supports it.
- Before any row is consumed, the build checks that the declared fields exist at
  the location and that the bytes match the declared format. A null that reaches
  a non-null property or key fails at the point of use.

## Next steps

Continue with [expressions](expressions.md) to turn these typed rows into values.

## Reference

For every source option, format, layout placeholder and credential detail, see
the [sources and ingest reference](../reference/ingest.md).
