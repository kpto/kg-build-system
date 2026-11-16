---
title: Assets reference
summary: The exact asset, profile, layout, governance and contract surface, plus DuckDB location resolution.
section: reference
perspective: reference
order: 70
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/distribution/languages/asset/model/public/options.py
  - kg_build_system/distribution/languages/asset/model/public/declarations.py
  - kg_build_system/distribution/modules/duckdb/service/public/planner.py
  - kg_build_system/generation/code_generation/service/public/generation.py
  - tests/distribution/test_asset_language.py
---

## Surface

An asset is one logical unit of source data. One asset may back many source relations. An `Asset` subclass declares its profile, optional meaning, optional layout, governance and annotations; each source relation names the asset through `SourceRelation[Asset]`.

Read [Declare an asset](/book/part-2/03-source-and-rows) for the authoring path, [Asset specification](/appendix/spec/asset) for the contract, and [Assets and source data](/appendix/subjects/asset) for the subject index entry. The row shape that names the asset is on [Declare data](/book/part-2/03-source-and-rows), and the compile step that consumes it is on [Compile](/appendix/reference/compile).

## Details

```python
from kg_build_system import (
    Asset, AssetAuthority, AssetGovernance, AssetLayout, AssetLicense,
    AssetOptions, AssetProfile, Claim, Contract, Definition, Field,
    FieldDefinition, Meaning, Omitted, SourceRelation, SourceRelationOptions,
    field,
)


class OpenTargets(Asset):
    """The Open Targets Platform release."""

    options = AssetOptions(
        name="open_targets",
        website="https://platform.opentargets.org/",
        version="24.09",
        profile=AssetProfile(
            subject="gene-disease associations",
            coverage="curated evidence for human genes and diseases",
            authority=AssetAuthority.PRIMARY,
            basis="Open Targets Platform release",
        ),
        meaning=Meaning(
            claims=(Claim("Each association names its evidence."),),
        ),
        governance=AssetGovernance(license=AssetLicense("CC-BY-4.0")),
        layout=AssetLayout(
            kind="parquet",
            locator="s3://open-targets/releases/24.09",
            format="parquet",
            selector="{table}.parquet",
        ),
    )


class TargetSourceRelation(SourceRelation[OpenTargets]):
    options = SourceRelationOptions(
        name="targets",
        contract=Contract(
            definition=Definition(grain="one row per target", identity=("target_id",)),
            meaning=Meaning(claims=(Claim("One row names one target."),)),
        ),
    )
    target_id: Field[str] = field(
        definition=FieldDefinition(value="the target's stable identifier"),
        meaning=Omitted,
    )
```

**Import paths**

| Surface | Import from |
| --- | --- |
| `Asset`, `AssetOptions`, `AssetLayout`, `AssetProfile`, `AssetAuthority`, `AssetGovernance`, `AssetLicense` | `kg_build_system` |
| `Claim`, `Limitation`, `Purpose`, `Meaning` | `kg_build_system` |
| `Contract`, `Definition`, `FieldDefinition` | `kg_build_system` |
| `SourceRelation` and `SourceRelationOptions` | `kg_build_system` |
| `AssetRef` | `kg_build_system.distribution` |
| `DuckDbSourcePlanner` | `kg_build_system.distribution` or `kg_build_system.distribution.modules.duckdb` |
| `asset_generation` and `AssetGenerationOptions` | `kg_build_system.generation` |

**`Asset`**

```python
class Asset:
    options: ClassVar[AssetOptions]
```

Declare an asset by subclassing `Asset` and assigning exactly one `options = AssetOptions(...)` at class level. Discovery finds every concrete `Asset` subclass in a namespace. The class itself carries no name, key or meaning outside its options.

```python
class OpenTargets(Asset):
    options = AssetOptions(..., meaning=Omitted)
```

- The class name becomes the default logical name.
- The class is terminal: a subclass must declare its own `options`; inherited options are not accepted.
- The asset has no content model and no adapter. Source relations carry the shapes.

| Error | Trigger |
| --- | --- |
| `asset 'X' must declare options = AssetOptions(...)` | A concrete `Asset` subclass has no own `options`, or `options` is not an `AssetOptions` |
| `asset 'X' has no usable name` | The class name produces no snake-case name and `options.name` is unset |
| duplicate `asset` symbols | Two assets resolve to one logical name in one blueprint |

**`AssetOptions`**

```python
AssetOptions(
    profile: AssetProfile,
    meaning: Meaning | None = None,
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
| `profile` | What the source data represents and how it was produced | Required |
| `meaning` | Optional declaration meaning fragment | `None` |
| `name` | Logical asset name | Snake case of the class name |
| `website` | Canonical human-facing reference | `None` |
| `version` | Free-text release label | `None` |
| `layout` | Optional descriptive layout metadata | `None` |
| `governance` | License, owner and portable metadata | Empty `AssetGovernance()` |
| `annotations` | Portable annotations on the asset | `()` |

`website` is a project or publisher page. It is not a download URL, a documentation link, a dataset card or the location rows are read from. A machine location belongs in `layout.locator`.

`version` is recorded, not resolved. It selects no file, pins no commit and triggers no download.

`name` must be non-empty when supplied. `website`, `version` and the layout text fields must be non-empty when present. `annotations` is normalised to a tuple. `meaning` must be a `Meaning` value.

**`AssetProfile`**

```python
AssetProfile(
    subject: str,
    coverage: str,
    authority: AssetAuthority,
    basis: str,
    title: str | None = None,
)
```

| Field | Meaning |
| --- | --- |
| `subject` | What the asset is about |
| `coverage` | The population, period or scope it covers |
| `authority` | How the asset relates to the claims it supports |
| `basis` | The method or release the data is built from |
| `title` | Human-facing title |

`subject`, `coverage` and `basis` must be non-empty. `profile` has no `claims` or `limitations`: those are meaning units declared through `AssetOptions(meaning=...)`. See [Asset specification](/appendix/spec/asset).

**`AssetAuthority`**

| Member | Value | Meaning |
| --- | --- | --- |
| `PRIMARY` | `"primary"` | The asset is authoritative for its subject |
| `DERIVED` | `"derived"` | The asset is computed from other sources |
| `REFERENCE` | `"reference"` | The asset is a lookup or reference set |
| `INFERRED` | `"inferred"` | The asset contains predictions or inference |

**`AssetGovernance`**

```python
AssetGovernance(
    license: AssetLicense | None = None,
    owner: str | None = None,
    metadata: Mapping[str, str] = {},
)
```

`owner` is free text naming a team or organisation. `metadata` is a string mapping normalised to sorted, read-only order. `license` is either `None` or an `AssetLicense`.

**`AssetLicense`**

```python
AssetLicense(
    identifier: str,
    url: str | None = None,
    attribution: str | None = None,
)
```

`identifier` is required and non-empty. `url` and `attribution` are optional and non-empty when present.

**`AssetLayout`**

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

Layout is optional descriptive metadata, not an access contract. Declaring one opens no file, resolves no credential and proves no relation exists. It is not a Hive, catalog, schema or partition-style model; every value is an open string.

`partition_by` entries and every `members` key and value must be non-empty. `partition_by` is a tuple; `members` and `properties` are read-only mappings sorted by key.

**Location resolution**

`DuckDbSourcePlanner` resolves one relation's location as follows:

1. `members[relation_name]`, when present;
2. otherwise `selector.format(table=relation_name, table_path=relation_name.replace(".", "/"))`;
3. otherwise `locator`.

A relative member or selector result is joined to `locator` with `/`. An absolute path or a value with a URI scheme is used as written. `{table}` is the relation's logical name and `{table_path}` replaces dots with `/`.

```python
AssetLayout(
    kind="parquet",
    locator="s3://open-targets/releases/24.09",
    format="parquet",
    selector="{table_path}/{table}.parquet",
)
```

For relation `readings.vibration`, the planner reads `s3://open-targets/releases/24.09/readings/vibration/readings.vibration.parquet`.

The generic planner accepts only `parquet`, `json` and `csv`. It reads `properties["credentials"]` as the credential reference for the location. The credential value is supplied through `BuildRuntime(credentials=...)` at build time and never enters the layout, blueprint or report.

**`SourceRelation[Asset]`**

```python
class SourceRelation[AssetT: Asset]:
    options: ClassVar[SourceRelationOptions]

    @classmethod
    def row_source(cls) -> RelationRowSource[Self]: ...
```

A concrete source relation must name exactly one asset:

```python
class TargetSourceRelation(SourceRelation[OpenTargets]):
    options = SourceRelationOptions(contract=...)
    target_id: Field[str] = field(definition=FieldDefinition(...), meaning=Omitted)
```

`SourceRelationOptions` carries a relation `Contract` or `Omitted`, plus `name` and `annotations`. There is no asset option and no location, format, credential or version option.

| Error | Trigger |
| --- | --- |
| `X is a concrete SourceRelation without an asset; declare it as SourceRelation[Asset]` | A concrete `SourceRelation` has no parameterised asset |
| `X must name an Asset subclass: SourceRelation[Asset]` | The parameter is not an `Asset` subclass |
| `SourceRelation.options must be a SourceRelationOptions value` | `options` is not a `SourceRelationOptions` |

Every source relation in the blueprint carries an `AssetRef` such as `["asset", "asset", "open_targets"]`. Validation refuses a source relation whose asset is absent from `GraphBlueprint.assets`.

**`@asset_generation`**

```python
@asset_generation(
    AssetGenerationOptions(
        provider=InferDataContractProvider,
        configuration=DataContractInferenceConfig(...),
        package="reference_project.relation.source",
    )
)
class Estate(Asset):
    options = AssetOptions(..., meaning=Omitted)
```

`asset_generation` is a class decorator on an `Asset` subclass. It validates the class, stores the request as `_asset_generation` and does no work: it does not read a source, import a project module, invoke a provider or write a file. Discovery finds the decorated class statically and the generated product is `<package>/<asset name>`.

The decorator is external to the asset model. `AssetOptions` and `AssetDTO` have no code-generation field; an asset states its data, a contract states how its source-relation declarations are generated. Generated source relations use `SourceRelation[Asset]`.

`AssetGenerationOptions` has exactly three keyword fields: `provider`, `configuration` and `package`. See [Compile](/appendix/reference/compile) for the discovery rules, ownership record and generated product model.

**`DuckDbSourcePlanner`**

```python
DuckDbSourcePlanner(
    *,
    formats: Sequence[str] = ("parquet", "json", "csv"),
    union_by_name: bool = False,
)
```

A generic module planner for `parquet`, `json` and `csv` assets. It reads the blueprint, asks which asset-backed relations the graph actually uses and emits one step per compatible relation:

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
- A relation is included only when a binding selection, a binding row plan, a derived-relation selection or a derived-relation row plan reads it.
- A relation with no layout, an unsupported format or no resolvable location produces no step. If the graph reads it, compilation reports an unresolved plan opening.
- Two producers for one relation artifact are refused, not resolved silently.
- `formats` restricts which layouts this planner accepts.
- `union_by_name` is accepted and does not change the emitted step; the generic planner resolves one location per relation.

`default_toolchain` adds one `DuckDbSourcePlanner` before the core planners unless a supplied planner already reports `component_id == "duckdb"`.

**What to remember**

- An asset is a logical unit of source data; one asset may back many source relations.
- A source relation names its asset through `SourceRelation[Asset]`; `SourceRelationOptions` has no source fields.
- `website` is the human-facing reference; `layout.locator` is the machine location.
- Layout is optional descriptive metadata, not an access contract.
- `AssetProfile`, optional `Meaning` and `AssetGovernance` are published with the asset.
- `@asset_generation` is a generation frontend; it is not an asset field.
- The generic DuckDB source planner handles `parquet`, `json` and `csv` layouts. Another module contributes another ordinary planner; there is no adapter registry.

Related: [Declare an asset](/book/part-2/03-source-and-rows), [Asset specification](/appendix/spec/asset), [Assets and source data](/appendix/subjects/asset), [Declarations](/appendix/reference/declarations), [Compile](/appendix/reference/compile).
