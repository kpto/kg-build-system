# Assets

An asset is one logical unit of source data, like a package. One asset may back
many tables. Open Targets is one asset: its `targets`, `diseases` and `evidence`
tables are relations extracted from that one logical source.

The asset says what the source data *is*, who publishes it, what it covers and
where a compatible reader may find it. A table says what one row looks like and
names the asset it comes from. The build resolves the two into source steps at
compile time. No file path appears in a table declaration.

## Why an asset is separate

A row shape is durable truth about the data. The location is a deployment fact.
A project that mixes them cannot answer simple questions: does this table come
from the production export or a test fixture? Which release did the build read?
Which tables belong to the same upstream package?

The asset answers those questions once:

- **Logical identity.** A relation records the asset it came from as an
  `AssetRef`, so a consumer can group tables by source package.
- **Meaning.** Subject, coverage, authority, basis, claims and limitations travel
  with the asset into the blueprint.
- **Governance.** License, owner and portable metadata are declared beside the
  data they govern.
- **Layout.** An optional description of where a relation may be found. It is
  descriptive metadata, not an access contract.
- **One place to change.** Moving a release or adding a table edits the asset's
  layout, not every table declaration.

## The model

Every asset is a subclass of `Asset` with exactly one `options = AssetOptions(...)`
assignment. The class becomes a language declaration; discovery transcribes it
into an `AssetDTO` and the blueprint carries one `AssetPartDTO`.

```python
from kg_build_system import (
    Asset, AssetAuthority, AssetGovernance, AssetLayout, AssetLicense,
    AssetOptions, AssetSemantics,
)


class OpenTargets(Asset):
    """The Open Targets Platform release."""

    options = AssetOptions(
        name="open_targets",
        website="https://platform.opentargets.org/",
        version="24.09",
        semantics=AssetSemantics(
            subject="gene-disease associations",
            coverage="curated evidence for human genes and diseases",
            authority=AssetAuthority.PRIMARY,
            basis="Open Targets Platform release",
            claims=("each association names the evidence that supports it",),
            limitations=("the release does not cover non-human organisms",),
            title="Open Targets Platform",
        ),
        governance=AssetGovernance(
            license=AssetLicense(
                "CC-BY-4.0",
                url="https://creativecommons.org/licenses/by/4.0/",
                attribution="Open Targets",
            ),
            owner="data-platform",
            metadata={"refresh": "quarterly"},
        ),
        layout=AssetLayout(
            kind="parquet",
            locator="s3://open-targets/releases/24.09",
            format="parquet",
            selector="{table}.parquet",
        ),
    )
```

`name` is optional. It defaults to the class name in snake case, so `OpenTargets`
becomes `open_targets`.

`website` is the canonical human-facing reference: the project or publisher
page a person should read. It is not a download URL, a documentation link, a
dataset card or the place rows are read from. A machine location belongs in
`layout.locator`.

`version` is a label, not a pin. It records which release you meant — a platform
release, an export date, a warehouse tag. Nothing in the build resolves,
downloads or checks it. Pin input data in the pipeline that produces the files.

`annotations` carries ordinary `Annotation` values. They are published with the
asset and interpreted by whatever planner or consumer supports them.

## Semantics

`AssetSemantics` states what the data represents and the limits of that
representation. It is required: an asset with no semantics is not a declared
asset.

| Field | Meaning |
| --- | --- |
| `subject` | What the asset is about, as a short noun phrase |
| `coverage` | Which population, period or scope the asset covers |
| `authority` | How the asset relates to the claims it supports |
| `basis` | The method or release the data is built from |
| `claims` | Statements the asset asserts that a consumer may rely on |
| `limitations` | Known gaps or qualifications |
| `title` | Human-facing title; optional |
| `description` | Longer explanation; optional |

`AssetAuthority` has four values:

| Value | Meaning |
| --- | --- |
| `AssetAuthority.PRIMARY` | The asset is the authoritative source for its subject |
| `AssetAuthority.DERIVED` | The asset is computed from other sources |
| `AssetAuthority.REFERENCE` | The asset is a lookup or reference set |
| `AssetAuthority.INFERRED` | The asset contains predictions or inference |

A limitation is a fact about the data, not a build error. Recording it lets a
consumer decide whether the asset answers its question; inventing precision is
the only wrong answer.

## Governance

`AssetGovernance` carries portable ownership and licensing facts:

```python
AssetGovernance(
    license=AssetLicense("CC-BY-4.0", url="...", attribution="Open Targets"),
    owner="data-platform",
    metadata={"refresh": "quarterly"},
)
```

`AssetLicense(identifier, url, attribution)` names the license; `identifier` is
required and `url` and `attribution` are optional. `owner` is a free-text team
or organisation. `metadata` is a string-to-string mapping for facts a tool may
read, such as a refresh cadence or a review policy.

## Layout

`AssetLayout` is optional descriptive metadata about where a compatible reader
may find the asset's relations. It is general: every value is an open string,
not a Hive, catalog, schema or partition-style vocabulary.

| Field | Meaning |
| --- | --- |
| `kind` | A free-text description of the storage kind, such as `parquet` |
| `locator` | A base path, directory or URI |
| `format` | The reader format, such as `parquet`, `json` or `csv` |
| `selector` | A template for one relation, using `{table}` and `{table_path}` |
| `partition_by` | Semantic partition keys, in order |
| `members` | Optional per-relation relative paths |
| `properties` | Portable reader hints, such as a credential reference |

Layout is not an access contract. Declaring one opens no file, resolves no
credential and proves no table exists. It tells a planner how to construct a
location if the planner supports the declared `kind` or `format`.

The generic DuckDB source planner resolves a relation in this order:

1. `members[relation]`, when the relation is named there;
2. otherwise `selector` formatted with `{table}` and `{table_path}`;
3. otherwise `locator`.

A relative member or selector result is joined to `locator`; an absolute path or
a value with a URI scheme is used as written. `{table}` is the relation's
logical name. `{table_path}` is that name with dots replaced by `/`, so
`readings.vibration` becomes `readings/vibration`.

`partition_by` describes meaning, not a path template. It lets a consumer know
that two rows with different partition values describe different physical
slices; it does not generate Hive directory names.

`properties` is where a portable hint belongs. The generic planner reads
`properties["credentials"]` as the runtime credential reference for the
location. The secret itself is supplied to the build at runtime and never enters
the layout, the blueprint or the report.

## Tables name their asset

A table names its asset through a generic parameter:

```python
from kg_build_system import Field, Table, TableOptions, field

from estate.assets import OpenTargets


class TargetTable(Table[OpenTargets]):
    """One gene-disease target relation."""

    options = TableOptions(name="targets")
    target_id: Field[str] = field()
    approved_symbol: Field[str] = field()
```

`TableOptions` has only `name`, `description` and `annotations`. It has no
location, format, credential or asset field; the asset is part of the class
base. A concrete `Table` without an asset parameter is refused when the class is
created.

`TableGroup` is still a named catalog of tables. It does not bind anything: each
member table names its own asset, and a group may contain tables from more than
one asset.

## Examples

### One Parquet asset, many tables

A release stores each relation as its own Parquet object under one prefix. The
asset declares the prefix once; the tables name the asset and nothing else.

```python
from kg_build_system import Asset, AssetAuthority, AssetLayout, AssetOptions, AssetSemantics


class OpenTargets(Asset):
    options = AssetOptions(
        semantics=AssetSemantics(
            subject="gene-disease associations",
            coverage="curated human evidence",
            authority=AssetAuthority.PRIMARY,
            basis="Open Targets Platform release",
        ),
        layout=AssetLayout(
            kind="parquet",
            locator="s3://open-targets/releases/24.09",
            format="parquet",
            selector="{table}.parquet",
            partition_by=("release",),
        ),
    )
```

Every table in the package is `Table[OpenTargets]`. The planner emits one source
step per relation the graph reads: `source.targets`, `source.diseases`,
`source.evidence`. One asset, many steps.

A relation whose file name does not follow the selector is named in `members`:

```python
layout = AssetLayout(
    kind="parquet",
    locator="s3://open-targets/releases/24.09",
    format="parquet",
    selector="{table}.parquet",
    members={"targets": "targets/by_id.parquet"},
)
```

### A local JSON asset

The reference project reads a handful of JSON documents from one directory. One
asset covers all of them.

```python
from pathlib import Path

from kg_build_system import Asset, AssetAuthority, AssetLayout, AssetOptions, AssetSemantics

DATA = Path(__file__).parent / "data"


class Estate(Asset):
    """The monitored estate: sites, equipment, surveys and readings."""

    options = AssetOptions(
        name="estate",
        version="2026-08",
        semantics=AssetSemantics(
            subject="monitored estate records",
            coverage="sites, equipment, surveys and logger readings",
            authority=AssetAuthority.PRIMARY,
            basis="estate registry and telemetry export",
            limitations=("nullability is not declared by the JSON documents",),
        ),
        layout=AssetLayout(
            kind="json",
            locator=str(DATA),
            format="json",
            members={
                "sites": "sites.json",
                "equipment": "equipment.json",
                "surveys": "surveys.json",
                "temperature": "readings/temperature.json",
                "vibration": "readings/mechanical/vibration.json",
            },
        ),
    )
```

```python
from kg_build_system import Field, Table, field

from estate.assets import Estate


class SiteTable(Table[Estate]):
    site_id: Field[str] = field()
    name: Field[str] = field()
```

The `members` mapping is the path table. Moving the whole directory edits
`locator`; adding a table edits `members` and declares the new table.

## How source steps are planned

There is no adapter concept in the toolchain and no adapter registry. A module
contributes an ordinary planner that emits relation-producing steps for the
assets it understands. The word *adapter* is prose for such a step, not a type
in the model.

The generic planner is `DuckDbSourcePlanner`, supplied by the DuckDB module and
added by `default_toolchain` before the core planners. It handles assets whose
layout resolves to `parquet`, `json` or `csv` and emits one
`source.<relation>` step per relation the graph reads, with instruction kind
`("source_relation", "duckdb")`.

- One asset may produce many source steps.
- A relation with no compatible layout produces no step. If the graph reads that
  relation, compilation reports an unresolved plan opening.
- Two producers for one relation artifact are refused rather than resolved
  silently.
- Another format, such as Avro or a database table, is supported by another
  module planner with its own instruction kind. It does not edit the asset model
  or register an adapter.

## Decisions you make

- **Put the canonical reference in `website`.** A project page, not the object
  store prefix; the prefix belongs in `locator`.
- **Treat `version` as a label.** Record the release you meant; pin downloads
  upstream.
- **Declare the semantics honestly.** State the subject and the limits; do not
  turn a sample into a promise.
- **Prefer one asset per upstream package.** If two relations always ship
  together and share governance, they belong to one asset.
- **Keep layout optional.** An asset without a layout is still a complete
  logical declaration; it simply has no generic source step.
- **Name credentials, never inline them.** The reference is a layout property;
  the secret is supplied at build time.

## Limits

- An asset declares no content model and no adapter. Tables carry the shapes.
- There is no code-generation field. Generation is a separate frontend attached
  with `@asset_contract(AssetContractOptions(...))`; the request is inert and
  does not enter `AssetOptions` or the blueprint.
- Layout is descriptive, not an access contract. A planner may ignore an asset
  whose observed rules it does not support.
- One asset may back many tables; a table names exactly one asset.
- `website` and `locator` answer different questions. A website never selects
  rows.
- Asset annotations and governance are published; a consumer decides what they
  mean.

## Next steps

Continue with [expressions](expressions.md) to turn typed rows into values, or
go back to [data contracts](data-contracts.md) for the table declarations that
name an asset.

## Reference

For every asset option, layout rule, planner argument and error, see the
[assets reference](../reference/assets.md) and the
[assets and ingest reference](../reference/ingest.md).
