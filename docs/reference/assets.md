# Assets

An asset is one logical unit of source data. One asset may back many tables. An
`Asset` subclass declares its semantics, optional layout, governance and
annotations; each table names the asset through `Table[Asset]`. See
[Assets](../concepts/assets.md) for the model.

```python
from kg_build_system import (
    Asset, AssetAuthority, AssetGovernance, AssetLayout, AssetLicense,
    AssetOptions, AssetSemantics, Field, Table, TableOptions, field,
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
        ),
        governance=AssetGovernance(license=AssetLicense("CC-BY-4.0")),
        layout=AssetLayout(
            kind="parquet",
            locator="s3://open-targets/releases/24.09",
            format="parquet",
            selector="{table}.parquet",
        ),
    )


class TargetTable(Table[OpenTargets]):
    options = TableOptions(name="targets")
    target_id: Field[str] = field()
```

## Import paths

| Surface | Import from |
| --- | --- |
| `Asset`, `AssetOptions`, `AssetLayout`, `AssetSemantics`, `AssetAuthority`, `AssetGovernance`, `AssetLicense` | `kg_build_system` |
| `Table` and `TableOptions` | `kg_build_system` |
| `AssetRef` | `kg_build_system.distribution` |
| `DuckDbSourcePlanner` | `kg_build_system.distribution` or `kg_build_system.distribution.modules.duckdb` |
| `asset_contract` and `AssetContractOptions` | `kg_build_system.generation` |

## `Asset`

```python
class Asset:
    options: ClassVar[AssetOptions]
```

Declare an asset by subclassing `Asset` and assigning exactly one
`options = AssetOptions(...)` at class level. Discovery finds every concrete
`Asset` subclass in a namespace. The class itself carries no name, key or
description outside its options.

```python
class OpenTargets(Asset):
    options = AssetOptions(...)
```

- The class name becomes the default logical name.
- The class is terminal: a subclass must declare its own `options`; inherited
  options are not accepted.
- The asset has no content model and no adapter. Tables carry the shapes.

| Error | Trigger |
| --- | --- |
| `asset 'X' must declare options = AssetOptions(...)` | A concrete `Asset` subclass has no own `options`, or `options` is not an `AssetOptions` |
| `asset 'X' has no usable name` | The class name produces no snake-case name and `options.name` is unset |
| duplicate `asset` symbols | Two assets resolve to one logical name in one blueprint |

## `AssetOptions`

```python
AssetOptions(
    semantics: AssetSemantics,
    name: str | None = None,
    website: str | None = None,
    version: str | None = None,
    layout: AssetLayout | None = None,
    governance: AssetGovernance = AssetGovernance(),
    annotations: Sequence[Annotation] = (),
)
```

| Field | Meaning | Default |
| --- | --- | --- |
| `semantics` | What the data represents and its limits | Required |
| `name` | Logical asset name | Snake case of the class name |
| `website` | Canonical human-facing reference | `None` |
| `version` | Free-text release label | `None` |
| `layout` | Optional descriptive layout metadata | `None` |
| `governance` | License, owner and portable metadata | Empty `AssetGovernance()` |
| `annotations` | Portable annotations on the asset | `()` |

`website` is a project or publisher page. It is not a download URL, a
documentation link, a dataset card or the location rows are read from. A machine
location belongs in `layout.locator`.

`version` is recorded, not resolved. It selects no file, pins no commit and
triggers no download.

`name` must be non-empty when supplied. `website`, `version` and the layout text
fields must be non-empty when present. `annotations` is normalised to a tuple.

## `AssetSemantics`

```python
AssetSemantics(
    subject: str,
    coverage: str,
    authority: AssetAuthority,
    basis: str,
    claims: Sequence[str] = (),
    limitations: Sequence[str] = (),
    title: str | None = None,
    description: str | None = None,
)
```

| Field | Meaning |
| --- | --- |
| `subject` | What the asset is about |
| `coverage` | The population, period or scope it covers |
| `authority` | How the asset relates to the claims it supports |
| `basis` | The method or release the data is built from |
| `claims` | Statements a consumer may rely on |
| `limitations` | Known gaps or qualifications |
| `title` | Human-facing title |
| `description` | Longer explanation |

`subject`, `coverage` and `basis` must be non-empty. Every entry in `claims` and
`limitations` must be non-empty.

### `AssetAuthority`

| Member | Value | Meaning |
| --- | --- | --- |
| `PRIMARY` | `"primary"` | The asset is authoritative for its subject |
| `DERIVED` | `"derived"` | The asset is computed from other sources |
| `REFERENCE` | `"reference"` | The asset is a lookup or reference set |
| `INFERRED` | `"inferred"` | The asset contains predictions or inference |

## `AssetGovernance`

```python
AssetGovernance(
    license: AssetLicense | None = None,
    owner: str | None = None,
    metadata: Mapping[str, str] = {},
)
```

`owner` is free text naming a team or organisation. `metadata` is a string
mapping normalised to sorted, read-only order. `license` is either `None` or an
`AssetLicense`.

### `AssetLicense`

```python
AssetLicense(
    identifier: str,
    url: str | None = None,
    attribution: str | None = None,
)
```

`identifier` is required and non-empty. `url` and `attribution` are optional and
non-empty when present.

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

| Field | Meaning |
| --- | --- |
| `kind` | Free-text storage kind, such as `parquet` or `json` |
| `locator` | Base path, directory or URI |
| `format` | Reader format, such as `parquet`, `json` or `csv` |
| `selector` | One-relation path template |
| `partition_by` | Semantic partition keys, in order |
| `members` | Per-relation paths keyed by relation name; relative values join `locator` |
| `properties` | Portable reader hints |

Layout is optional descriptive metadata, not an access contract. Declaring one
opens no file, resolves no credential and proves no relation exists. It is not a
Hive, catalog, schema or partition-style model; every value is an open string.

`partition_by` entries and every `members` key and value must be non-empty.
`partition_by` is a tuple; `members` and `properties` are read-only mappings
sorted by key.

### Location resolution

`DuckDbSourcePlanner` resolves one relation's location as follows:

1. `members[relation_name]`, when present;
2. otherwise `selector.format(table=relation_name, table_path=relation_name.replace(".", "/"))`;
3. otherwise `locator`.

A relative member or selector result is joined to `locator` with `/`. An
absolute path or a value with a URI scheme is used as written. `{table}` is the
relation's logical name and `{table_path}` replaces dots with `/`.

```python
AssetLayout(
    kind="parquet",
    locator="s3://open-targets/releases/24.09",
    format="parquet",
    selector="{table_path}/{table}.parquet",
)
```

For relation `readings.vibration`, the planner reads
`s3://open-targets/releases/24.09/readings/vibration/readings.vibration.parquet`.

The generic planner accepts only `parquet`, `json` and `csv`. It reads
`properties["credentials"]` as the credential reference for the location. The
credential value is supplied through `BuildRuntime(credentials=...)` at build
time and never enters the layout, blueprint or report.

## `Table[Asset]`

```python
class Table[AssetT: Asset]:
    options: ClassVar[TableOptions]

    @classmethod
    def row_source(cls) -> RelationRowSource[Self]: ...
```

A concrete table must name exactly one asset:

```python
class TargetTable(Table[OpenTargets]):
    target_id: Field[str] = field()
```

`TableOptions` has only `name`, `description` and `annotations`. There is no
asset option and no location, format, credential or version option.

| Error | Trigger |
| --- | --- |
| `X is a concrete Table without an asset; declare it as Table[Asset]` | A concrete `Table` has no parameterised asset |
| `X must name an Asset subclass: Table[Asset]` | The parameter is not an `Asset` subclass |
| `Table.options must be a TableOptions value` | `options` is not a `TableOptions` |

Every relation in the blueprint carries an `AssetRef` such as
`["asset", "asset", "open_targets"]`. Validation refuses a relation whose asset
is absent from `GraphBlueprint.assets`.

## `@asset_contract`

```python
@asset_contract(
    AssetContractOptions(
        provider=InferDataContractProvider,
        configuration=DataContractInferenceConfig(...),
        package="reference_project.table",
    )
)
class Estate(Asset):
    options = AssetOptions(...)
```

`asset_contract` is a class decorator on an `Asset` subclass. It validates the
class, stores the request as `_asset_contract` and does no work: it does not
read a source, import a project module, invoke a provider or write a file.
Discovery finds the decorated class statically and the generated product is
`<package>/<asset name>`.

The decorator is external to the asset model. `AssetOptions` and `AssetDTO` have
no code-generation field; an asset states its data, a contract states how its
table declarations are generated. Generated tables use `Table[Asset]`.

`AssetContractOptions` has exactly three keyword fields: `provider`,
`configuration` and `package`. See [Generation](generation.md) for the discovery
rules, ownership record and generated product model.

## `DuckDbSourcePlanner`

```python
DuckDbSourcePlanner(
    *,
    formats: Sequence[str] = ("parquet", "json", "csv"),
    union_by_name: bool = False,
)
```

A generic module planner for `parquet`, `json` and `csv` assets. It reads the
blueprint, asks which asset-backed relations the graph actually uses and emits
one step per compatible relation:

| Property | Value |
| --- | --- |
| `component_id` | `"duckdb"` |
| `version` | `"1"` |
| `runtime_fields` | `()` |
| Step name | `source.<relation_name>` |
| Output | `CoreArtifactTypes.table(relation_name)` |
| Instruction kind | `("source_relation", "duckdb")` |

The instruction payload carries:

| Field | Meaning |
| --- | --- |
| `relation` | The plan relation name, such as `kg_table_0` |
| `location` | The resolved location |
| `format` | The resolved `format` or `kind` |
| `credential_reference` | `layout.properties["credentials"]` or `None` |
| `declaration` | The relation's logical name |
| `declared_columns` | The declared columns and logical types |
| `declared_paths` | The non-null Parquet paths to pre-flight |

Rules:

- One asset may produce many source steps.
- A relation is included only when a binding expression, a binding row plan, a
  projection expression or a projection row plan reads it.
- A relation with no layout, an unsupported format or no resolvable location
  produces no step. If the graph reads it, compilation reports an unresolved
  plan opening.
- Two producers for one relation artifact are refused, not resolved silently.
- `formats` restricts which layouts this planner accepts.
- `union_by_name` is accepted and currently does not change the emitted step;
  the generic planner resolves one location per relation.

`default_toolchain` adds one `DuckDbSourcePlanner` before the core planners
unless a supplied planner already reports `component_id == "duckdb"`.

## What to remember

- An asset is a logical unit of source data; one asset may back many tables.
- A table names its asset through `Table[Asset]`; `TableOptions` has no source
  fields.
- `website` is the human-facing reference; `layout.locator` is the machine
  location.
- Layout is optional descriptive metadata, not an access contract.
- `AssetSemantics` and `AssetGovernance` are published with the asset.
- `@asset_contract` is a generation frontend; it is not an asset field.
- The generic DuckDB source planner handles `parquet`, `json` and `csv` layouts.
  Another module contributes another ordinary planner; there is no adapter
  registry.

Related: [Assets](../concepts/assets.md),
[Assets and ingest](ingest.md),
[Generation](generation.md),
[Declarations](declarations.md),
[Planners and executors](planners-and-executors.md).
