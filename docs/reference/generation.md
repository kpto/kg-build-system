# Generation

Generation turns a typed `@asset_contract` request on an asset into an owned
package of table, struct and group declarations.

Generation writes declarations; it does not read graph data at build time and it
does not run a build. The declarations it produces are ordinary public
authoring classes, and every table names the asset it was generated for with
`Table[Asset]`. The data-contract side is on
[data contracts](../concepts/data-contracts.md); the logical and physical asset
side is on [assets](../concepts/assets.md). The ingest rules for trust tiers, the
digest gate and pre-flight are on [assets and ingest](ingest.md); the workflow is
also walked through in [Install](../get-started/install.md).

## `kbs generate`

```bash
kbs generate --project .
kbs generate --project . --check
kbs generate --project . --regenerate
kbs generate --project . --watch --debounce 500
```

| Argument | Effect |
| --- | --- |
| `--project PATH` | Project directory to scan; defaults to the current directory |
| `--check` | Compare products with their requests and manifests without writing |
| `--regenerate` | Re-observe every source and regenerate every product, even current ones |
| `--watch` | Run one pass, then watch project files and regenerate on declaration changes |
| `--debounce MS` | Change debounce in milliseconds; must be greater than zero; default `300` |

`kbs generate` runs one desired-state pass over every discovered request. It
exits `0` for `CURRENT` and `CHANGED`, and `1` for `STALE` or a generation
failure. `--watch` cannot be combined with `--check` or `--regenerate`.

`--check` proves that generated products match their requests and ownership
records; it does not re-observe sources. Use `--check --regenerate` to report
source-schema drift as `STALE` without writing.

## Request model

```python
@asset_contract(
    AssetContractOptions(
        provider: type[Provider[T]],
        configuration: T,
        package: str,
    )
)
```

`@asset_contract(AssetContractOptions(...))` is a class decorator on a
module-level `Asset` subclass. It is inert: it validates the class and stores
the options as `_asset_contract`. It does not observe a source, load data, invoke
a provider or write a file. Discovery reads the decorator statically and
`generate` reads the stored request later.

| Field | Meaning |
| --- | --- |
| `provider` | A `Provider` subclass |
| `configuration` | An inline instance of that provider's `CONFIG_TYPE` |
| `package` | The dotted import package that receives the generated product |

`AssetContractOptions` accepts keyword arguments only and requires all three
fields. It raises `TypeError` when the provider is not a `Provider` subclass,
when the configuration is not the provider's `CONFIG_TYPE`, or when the
decorated class is not an `Asset` subclass. The asset name is the request
identity and the product is `<package>/<asset name>`.

```python
from kg_build_system import (
    Asset, AssetAuthority, AssetOptions, AssetSemantics,
)
from kg_build_system.generation import AssetContractOptions, asset_contract
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)


@asset_contract(AssetContractOptions(
    provider=InferDataContractProvider,
    configuration=DataContractInferenceConfig(
        source="../data/people.csv",
        mode="table",
    ),
    package="people_graph.table",
))
class People(Asset):
    options = AssetOptions(
        semantics=AssetSemantics(
            subject="people directory",
            coverage="current staff and contacts",
            authority=AssetAuthority.PRIMARY,
            basis="people export",
        ),
    )
```

The asset name is `AssetOptions.name` when set, otherwise the class name in
snake case. For `class People(Asset)` with no `name`, the product is
`people_graph/table/people/` and the package import is
`people_graph.table.people`.

| Rule | Result |
| --- | --- |
| The decorator is on a module-level `Asset` subclass | Required |
| The class has exactly one `Asset` base | Required |
| The decorator takes one inline `AssetContractOptions(...)` | Required |
| Provider and configuration are statically imported | Direct, qualified or aliased imports are accepted |
| Configuration is constructed inline with keyword arguments | Required; duplicates, stars and unpacking are refused |
| Configuration values are static literals | Strings, integers, floats, booleans, `None`, lists, tuples and dictionaries with string keys |
| Products and asset names do not collide under case folding | Required across all contracts |

A decorated class inside a function or another class, a dynamically constructed
configuration, a star import and a duplicate `AssetContractOptions` field are all
refused with a `GenerationError`.

`GenerationError` extends `ValueError`. A request defect is located at the asset
source file and line.

A module may declare several decorated assets; each produces its own product
directory. A project may declare contracts in several modules. The author-owned
asset source is never rewritten.

## Discovery

```python
discover(project_root: str | Path) -> tuple[DiscoveredGeneration, ...]
discover_file(project_root: str | Path, source_path: str | Path) -> tuple[DiscoveredGeneration, ...]
```

Discovery parses Python source with LibCST; it does not import the author-owned
project. It scans every `.py` file beneath the project root and only parses files
whose text contains `asset_contract`. It skips directories beginning with `.`
and `__pycache__`.

`DiscoveredGeneration` carries:

| Field | Meaning |
| --- | --- |
| `request` | The statically resolved provider, configuration, package and asset identity |
| `location` | Project root, asset source path, line, column, asset name and source package |
| `product_path` | `<package>/<asset name>`, relative to the project root |
| `package_import` | The import name of the generated package, `<package>.<asset name>` |

`discover_file` refuses a source path outside the project. Discovery is also
what the watcher uses to compare changed files with the previous contract set.

`discover` raises `ValueError` when the project root is not a directory.
`discover_file` raises `ValueError` for a source path outside the project. An
invalid contract, an unreadable source file, a duplicate asset name and a
product collision raise `GenerationError`.

## Provider contract

```python
class Provider[T: ProviderGenerationConfig](ABC):
    ID: ClassVar[str]
    VERSION: ClassVar[str]
    CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]]

    @classmethod
    @abstractmethod
    async def generate(cls, context: ProviderContext[T]) -> GeneratedPackage: ...
```

A provider is a class with:

| Name | Meaning |
| --- | --- |
| `ID` | Non-empty provider identifier |
| `VERSION` | Non-empty provider version; part of the request fingerprint |
| `CONFIG_TYPE` | The exact `ProviderGenerationConfig` subclass the provider accepts |
| `generate(context)` | An async classmethod returning one `GeneratedPackage` |

`ProviderGenerationConfig` is a frozen, strict Pydantic base model. Unknown
fields are refused. The engine validates the request's static configuration into
the provider's exact `CONFIG_TYPE`; a different configuration class is a type
error.

`ProviderContext` supplies:

| Field | Meaning |
| --- | --- |
| `project_root` | The project root being generated |
| `request_path` | The author-owned asset source module |
| `request_id` | The asset name |
| `config` | The validated provider configuration |
| `resolve_provider_path(context, value)` | Resolve a provider-owned path relative to the request file |

`resolve_provider_path(context, value)` returns an observation target, not a tracked input. The path may
lie outside the project; the engine does not watch, hash or existence-check it.
A provider that observes a source schema should stamp a `source_digest` onto
`GeneratedPackage` for provenance.

A provider returns declarations, not arbitrary Python source. Rendering the same
observation twice must produce identical text; the engine proves determinism
before installing anything.

```python
from pathlib import Path
from typing import ClassVar

from kg_build_system.generation.code_generation.model.internal import (
    Provider, ProviderContext, ProviderGenerationConfig,
)
from kg_build_system.generation.code_generation.model._private.generated import (
    GeneratedAsset, GeneratedClass, GeneratedField, GeneratedFile,
    GeneratedPackage, GeneratedScalarType,
)
from kg_build_system.generation.code_generation.service.internal import (
    resolve_provider_path,
)


class ContractConfig(ProviderGenerationConfig):
    source: str


class ContractProvider(Provider[ContractConfig]):
    ID: ClassVar[str] = "contract"
    VERSION: ClassVar[str] = "1"
    CONFIG_TYPE: ClassVar[type[ProviderGenerationConfig]] = ContractConfig

    @classmethod
    async def generate(
        cls, context: ProviderContext[ContractConfig],
    ) -> GeneratedPackage:
        class_name = (
            "".join(part.title() for part in context.request_id.split("_"))
            + "Table"
        )
        field = GeneratedField("id", "id", GeneratedScalarType("str"))
        asset = context.asset
        generated_asset = (
            None if asset is None
            else GeneratedAsset(asset.module, asset.qualname)
        )
        return GeneratedPackage((
            GeneratedFile(
                Path("__init__.py"),
                (
                    GeneratedClass(
                        class_name,
                        (field,),
                        base="Table",
                        declaration_name=context.request_id,
                        asset=generated_asset,
                    ),
                ),
                (class_name,),
            ),
        ))
```

## Ownership

Each generated product contains `.kbs-generation.json`, the ownership record.
It records the request identity, provider identity and version, request
fingerprint, optional source digest, owned files and directories, and the hash
of every owned file.

- The request fingerprint covers the request configuration, configuration type,
  format version, provider identity and version, request ID and source package.
  It contains no source content and no source-content digest.
- `source_digest` is provenance only. The engine stores and replaces it without
  interpreting it; a change to the digest alone does not make a product stale.
- Ownership is proved by a validated record, a relative path, the ownership
  header in the file and the expected file hash. A filename alone proves
  nothing.
- A product whose record matches its request fingerprint and file hashes is
  current and its sources are not observed.
- An owned file that was modified is a conflict. It is never accepted as a new
  source of truth, and the pass fails rather than overwriting it.
- Content not recorded in the record is never overwritten or deleted. A desired
  path that collides with unrecognized content fails the pass.
- Obsolete owned files are verified before pruning. Owned directories are
  removed only when empty. Deleting or renaming a request removes its verified
  product and preserves unrecognized content.
- Owned Python bytecode is pruned with its source.

Generated files carry:

```text
# Generated by kg-build-system. Do not edit manually.
# request: <request id>
# fingerprint: <request fingerprint>
```

Do not edit a generated file. Change the request and regenerate. A hand-edited
file is a conflict, not a declaration.

## Check, regenerate and watch

### Check

`kbs generate --check` performs the complete comparison without mutation and
returns one of two statuses:

| Status | Meaning |
| --- | --- |
| `CURRENT` | Every product and record matches its request and file hashes |
| `STALE` | A product or record is missing, changed, altered or orphaned |

A stale result lists the affected paths as diagnostics. `--check` does not
re-observe sources and does not write. A discovery failure or provider failure
is an error, not a `STALE` result.

### Regenerate

`kbs generate --regenerate` forces every provider to observe its source again.
It is a single re-observation pass: with `--check` it reports schema drift as
`STALE` without writing, and alone it writes the re-observed result.

Source data is a reference, not a tracked input. A row-level or schema-level
change does not make a product stale on its own; `--regenerate` is how a source
change is deliberately pulled into the project.

### Watch

`kbs generate --watch` runs one complete pass, indexes the requests, and then
watches project files.

- A change to an author-owned asset source file is rescanned.
- The session reports `DECLARATION_ADDED`, `DECLARATION_CHANGED` or
  `DECLARATION_DELETED` with the source path and package import before
  regenerating.
- An unchanged save produces no action. A change that does not alter the
  discovered request set produces no regeneration.
- Changes under a generated product are ignored.
- Data-source changes trigger nothing, because sources are references.
- Watched suffixes default to `.py`, `.json`, `.toml`, `.yaml` and `.yml`;
  ignored directories include caches, virtual environments and VCS metadata.
- An invalid edit is logged and watching continues.

### Python surface

```python
import asyncio

from kg_build_system.generation.code_generation import GenerationStatus, generate

result = asyncio.run(generate(".", check=True))
if result.status is GenerationStatus.STALE:
    print("\n".join(result.diagnostics))
```

| Name | Meaning |
| --- | --- |
| `generate(project_root, *, check=False, regenerate=False)` | Run one desired-state pass |
| `GenerationResult` | `status`, changed, created, updated and deleted paths, diagnostics, actions |
| `GenerationStatus` | `CURRENT`, `CHANGED`, `STALE` |
| `GenerationSession(project_root)` | Incremental watch state; `await start()`, `await handle(changed_paths, on_action=...)` |
| `GenerationAction` | `kind`, `trigger_path`, `source_paths`, optional `declaration_id` |
| `GenerationActionKind` | `DECLARATION_ADDED`, `DECLARATION_CHANGED`, `DECLARATION_DELETED` |
| `watch(root, *, debounce=300, ...)` | Async iterator of batches of file changes |

`generate` raises `GenerationError` for a request, provider or ownership defect
and `OSError` for a filesystem failure. With `check=True`, a product that does
not match its request returns `STALE` instead of raising.

## Output model

A provider returns a `GeneratedPackage` composed of files, declarations and
fields. The engine validates and renders the complete package before any file is
written.

| Name | Shape |
| --- | --- |
| `GeneratedPackage(files, nullability_notes=(), source_digest=None)` | One complete desired product |
| `GeneratedFile(relative_path, declarations=(), exports=())` | One `.py` file and its exported names |
| `GeneratedClass(name, fields=(), members=(), description=None, base=None, declaration_name=None, asset=None)` | A table, struct or group declaration; a table carries a `GeneratedAsset` |
| `GeneratedField(python_name, external_name, value_type, description=None, annotations=(), nullability=Nullability.DEFAULTED, ...)` | One `Field[T] = field(...)` member |
| `GeneratedMember(python_name, declaration_name)` | One named member of a generated table group |
| `GeneratedAnnotation(import_module, class_name, arguments={})` | One annotation on a generated field |
| `GeneratedAsset(module, qualname)` | The authored asset a generated table names as its generic argument |

`GeneratedField` also carries optional `schema_path` and `logical_path` values
for source-path provenance; an ordinary provider leaves them empty. `nullability`
records the source claim and decides the rendered field: `DEFAULTED` renders
`Field[T | None]`, while `DECLARED` or `ENFORCED` renders `Field[T]`. The
rendered declaration therefore decides how the field reads.

A value type is one of:

| Name | Shape |
| --- | --- |
| `GeneratedScalarType(name)` | A canonical scalar name: `bool`, `int`, `float`, `str`, `date`, `time`, `timestamp` or `uuid` |
| `GeneratedStructType(declaration_name, in_file=None)` | A reference to a generated struct; `in_file` binds it to a declaring file |
| `GeneratedArrayType(item)` | An `Array[T]` value |
| `GeneratedNullableType(value)` | A nullable value shape |

`Nullability` is `DECLARED`, `ENFORCED` or `DEFAULTED`. `NullabilityNote(line,
sources=(), declarations=())` is one provenance line rendered into the header of
the files it describes.

Rendering rules:

- A generated path is a relative `.py` path with no `..` and no absolute path.
  Case-normalized path collisions are refused.
- A file may not declare the same class twice.
- A generated reference resolves inside its own file first, then to another file
  that declares the name uniquely. A dangling name and an ambiguous unbound name
  are refused.
- A file that would import two different declarations under one name is refused
  rather than silently shadowing one.
- Every package directory receives an explicit `__init__.py`, and every rendered
  file is parsed before installation.
- A `DEFAULTED` source renders `Field[T | None]`; an `ENFORCED` or `DECLARED`
  non-null source renders `Field[T]`. Array-item and nested-member nullability
  stay in the value type.
- Canonical `date`, `time`, `timestamp` and `uuid` render as `Date`, `Time`,
  `Timestamp` and `Uuid`; the builtin scalars use their Python names. Every file
  that declares anything imports the whole representative set.
- A generated table carries a `GeneratedAsset`; the renderer emits
  `Table[Asset]` and imports the authored asset module.
- Generated declarations use only the public authoring surface: `Field`,
  `field`, `Table`, `Struct`, `TableGroup`, `TableOptions` and
  `TableGroupOptions`.
- Generated code has no generation-specific compilation path. It is imported by
  `compile` exactly like handwritten declarations.

## Built-in inference provider

```python
InferDataContractProvider
ID = "infer_data_contract"
VERSION = "7"
CONFIG_TYPE = DataContractInferenceConfig
```

`DataContractInferenceConfig` is a frozen, strict `ProviderGenerationConfig`:

| Field | Meaning | Default |
| --- | --- | --- |
| `source` | Local path or `http`, `https` or `s3` source | `None`; falls back to the asset's `AssetLayout.locator` |
| `relation` | Relation to infer | `None` |
| `mode` | `"table"` or `"table_group"` | `"table"` |
| `layout` | `"files"`, `"parquet_parts"` or `"hive_partitioned_parquet"` | `"files"` |
| `anonymous` | Anonymous S3 access | `False` |
| `override` | Per-column type or nullability declarations | `{}` |

Rules:

- `source` names one input. When it is omitted, the provider uses the
  decorated asset's `AssetLayout.locator`; a contract with neither is refused.
- `mode="table"` reads one file or one remote object and one relation. A
  directory requires `mode="table_group"`. A relative `source` resolves against
  the asset source file, not the process's working directory.
- `relation` is required when a table input exposes more than one relation and is
  refused for table-group inference.
- `layout` other than `"files"` requires `mode="table_group"`.
- `layout="files"` treats each supported file as a table. `parquet_parts` and
  `hive_partitioned_parquet` group Parquet files into logical tables; Hive
  partition directories are removed from the logical path.
- `anonymous=True` applies only to S3.
- A database input is refused: no supported asset layout format selects a
  database reader, so a table derived from it could never get a generic source
  step. Export the relation to `parquet`, `json` or `csv`, contribute a module
  planner for the database, or declare the table outside a generated package.
- An unsupported suffix, a directory with no supported relations, and a source
  that does not exist fail generation.
- Table classes derive from the relation or asset name; struct classes derive
  from member paths and group classes from group paths. Logical declaration
  names are emitted in `TableOptions` or `TableGroupOptions`.

Trust tiers and generated nullability are on [assets and
ingest](ingest.md#generated-nullability); the digest gate is on [assets and
ingest](ingest.md#digest-gate).

## Override contract

`override` is a declaration-time value for the built-in inference provider. It
is carried in `DataContractInferenceConfig` inside the asset's
`@asset_contract(AssetContractOptions(...))`, not in a generated file and not as
a runtime option in the compiled workflow plan.

```python
from kg_build_system import (
    Asset, AssetAuthority, AssetOptions, AssetSemantics,
)
from kg_build_system.generation import AssetContractOptions, asset_contract
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)


@asset_contract(AssetContractOptions(
    provider=InferDataContractProvider,
    configuration=DataContractInferenceConfig(
        source="../data/readings.parquet",
        override={
            "readings.recorded_on": {"type": "timestamp"},
            "readings.quality": {"nullable": False},
        },
    ),
    package="estate.table",
))
class Readings(Asset):
    options = AssetOptions(
        semantics=AssetSemantics(
            subject="logger readings",
            coverage="mechanical and temperature sensors",
            authority=AssetAuthority.PRIMARY,
            basis="telemetry export",
        ),
    )
```

Each entry is a `ColumnOverride`:

| Field | Meaning |
| --- | --- |
| `type` | The canonical unit type the whole top-level column means to hold |
| `nullable` | `True` declines a source non-null claim; `False` asserts one |

An entry must declare at least one of `type` and `nullable`. Unknown keys are
refused.

Rules:

- Keys are the full `<relation path>.<column>` path. For a table group, the
  relation path includes nested group paths.
- An override reaches exactly the relation it names and only whole top-level
  columns. A bare column name, a missing relation part, a path inside a column,
  and an unknown column are refused with the available names.
- `type` must name a canonical unit type. It cannot promote a container, cannot
  lift a refused physical type, and does not change a container's item or member
  types.
- A declared-only physical type becomes digestible when `type` declares it; the
  scan then applies a checked cast, which aborts on a value that does not fit.
- `nullable: true` declines a source non-null claim and makes the field
  `DEFAULTED`; it leaves the Parquet null-statistics pre-flight and renders
  `Field[T | None]`.
- `nullable: false` asserts non-nullability and makes the field `DECLARED`; it
  enters the pre-flight and renders a non-null `Field[T]`.
- The claim decides the rendered field: `DEFAULTED` renders
  `Field[T | None]`; `DECLARED` or `ENFORCED` renders `Field[T]`.
- An absent `nullable` keeps the source's own claim. An absent `type` keeps the
  reader's reported type.
- An override never reads values to decide a claim. The build guard or the
  checked scan cast tests the declaration against the data.

An override can declare a type the reader reports as text, such as a timestamp,
and can settle a Parquet footer claim that the statistics contradict. It cannot
turn `DECIMAL` into `float` or otherwise lift a refusal.

## What to remember

- A request is an inert `@asset_contract(AssetContractOptions(...))` decorator
  on a module-level `Asset`; the asset name defines the generated package.
- A provider is a typed class with `ID`, `VERSION`, `CONFIG_TYPE` and an async
  `generate(context)` returning declarations.
- Discovery parses asset contracts without importing the project; ownership is
  proved by the manifest, header and hashes.
- `--check` compares products with their contracts; `--regenerate` re-observes
  sources; `--watch` regenerates on declaration changes and ignores data changes.
- Generated declarations are ordinary `Table`, `Struct` and `TableGroup`
  classes, and each generated table uses `Table[Asset]`.
- An override is a whole-column declaration in the contract. `nullable: true`
  renders `Field[T | None]`; `nullable: false` renders `Field[T]`.

See [assets and ingest](ingest.md) for physical rules, [types](types.md) for
the vocabulary, and the [Glossary](glossary.md) for terms.
