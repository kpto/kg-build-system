# Edit-Time Generated Packages — Specification

## 1. Purpose and status

This document specifies the implemented edit-time package-generation system
for the Knowledge Graph Build System.

Generation requests are typed Python values for IDE and static-analysis
support. Discovery is static, providers run only through generation commands,
and every result is a complete importable package owned through a versioned
manifest. Runtime declaration imports and blueprint compilation do not execute
generation.

The current ownership-manifest format version is `3`.

## 2. Request model

A request is a simple module-level assignment in an author-owned
`__init__.py`:

```python
from kg_build_system.code_generation import generation
from kg_build_system.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)


complex_records = generation(
    InferDataContractProvider,
    DataContractInferenceConfig(
        source="../data/complex_records.json",
        mode="table",
    ),
)
```

The assignment name is the request ID, logical output identity, directory
name, and generated package suffix. There is no separate `name` or output-path
argument.

For the request above in `demo/table/__init__.py`, output is fixed at:

```text
demo/table/
  __init__.py                       # author-owned request
  complex_records/                  # generated package
    __init__.py
    .kbs-generation.json
```

Table-group providers may produce a nested package tree beneath the same
request root.

The runtime request object is inert:

```python
@dataclass(frozen=True)
class Generation[T: ProviderGenerationConfig]:
    provider: type[Provider[T]]
    configuration: T
```

Calling `generation(...)` validates the provider/configuration pairing and
constructs this value. It does not read dependencies, load data, invoke a
provider, or write files.

## 3. Static discovery

Discovery uses LibCST and never imports the author-owned project module.

A valid request:

- appears in a file named `__init__.py`;
- is a simple module-level assignment;
- has exactly one plain identifier target;
- uses the canonical `generation` function;
- supplies a statically resolvable provider class;
- constructs its provider configuration inline;
- uses only supported static values in configuration arguments.

Direct, qualified, and aliased imports are supported when their identities can
be resolved statically.

The following are invalid:

```python
# Outside __init__.py.
release = generation(...)

# No single stable request identity.
release, metadata = generation(...)

# Attribute targets are not package names.
requests.release = generation(...)

# Dynamic configuration cannot be discovered safely.
release = generation(Provider, make_configuration())
```

Request IDs beginning with `_` are rejected. Multiple valid requests may
appear in one author-owned `__init__.py`, provided their identities and product
paths do not collide.

Static configuration values are JSON-like scalars, lists, tuples, and
dictionaries. Provider configurations are frozen strict Pydantic models with
unknown fields rejected.

## 4. Naming and location

For a request assignment named `evidence_release`:

- request ID: `evidence_release`;
- product directory: sibling `evidence_release/`;
- package import: `<author package>.evidence_release`;
- default logical root name: `evidence_release`;
- default table-group class: `EvidenceReleaseTableGroup`;
- default single-table class: `EvidenceReleaseTable`.

The containing `__init__.py` establishes the output boundary through normal
Python package structure. Requests cannot configure absolute paths, relative
output traversal, adjacent sidecars, or another package's directory.

Logical declaration names are emitted explicitly in declaration options where
needed, so generated module layout cannot accidentally change catalog
identity.

## 5. Provider contract

Providers are ordinary implementations of the public generic `Provider`
interface. Built-in and third-party providers use the same path.

A provider declares:

- a stable provider `ID` and `VERSION`;
- its strict configuration type;
- edit-time dependencies;
- one normalized `GeneratedPackage` result.

`ProviderContext` supplies the project root, request source file, request ID,
and typed configuration. It resolves dependency paths relative to the
author-owned request file.

The engine does not identify or special-case built-in providers. Providers
interpret input data; the core owns request identity, product location,
rendering, validation, ownership, installation, check mode, and pruning.

## 6. Provider-independent output model

Providers return declarations, not arbitrary Python source:

```text
GeneratedPackage
  files: GeneratedFile...

GeneratedFile
  relative_path
  declarations: GeneratedClass...
  exports

GeneratedClass
  base
  declaration_name
  fields
  group members
```

Generated field types are normalized independently of Python rendering:

```text
GeneratedScalarType
GeneratedStructType
GeneratedArrayType
GeneratedNullableType
```

Providers may also attach normalized annotations by import identity and static
arguments.

The core rejects:

- absolute output paths;
- `..` traversal or paths escaping the product root;
- case-normalized collisions;
- file-versus-directory collisions;
- duplicate declaration import identities;
- invalid public identifiers or unsupported normalized types.

The complete desired package is rendered and parsed before filesystem
mutation.

## 7. Generated declarations

Generated structs, tables, and table groups are complete ordinary
declarations using the public authoring API:

```python
from kg_build_system import Field, Struct, Table, TableOptions, field
from kg_build_system.types import Array, Date, Time, Timestamp, Uuid


class InputDetailsStruct(Struct):
    label: Field[str] = field(name="label")


class InputTable(Table):
    options = TableOptions(name="input")
    observed_on: Field[Date | None] = field(name="observed_on")
    details: Field[InputDetailsStruct | None] = field(name="details")
    tags: Field[Array[str] | None] = field(name="tags")
```

Members are annotated with **representative types**, not with canonical type
names: a date, time, timestamp or uuid column renders as `Field[Date]`,
`Field[Time]`, `Field[Timestamp]` or `Field[Uuid]` — aliases of the stdlib
classes, exported by `kg_build_system.types` — while `bool`, `int`, `float` and
`str` render as the builtins.

That import line is emitted **whole and unconditionally** by every generated file
that declares anything, rather than derived per file from the types that file
happens to use. An un-imported annotation raises `NameError` while the class body
executes, before any framework code runs, so importing the entire representative
set makes the omission structurally impossible. Because the line carries names a
file may not use, the header also emits `# ruff: noqa: F401` (§9).

All logical members use unified `Field[T]`. Generated code does not use
`StructField`, `CollectionField`, placeholder declarations, mixins, `G_`
classes, or author-owned wrapper subclasses.

Nested table groups point directly to generated final declarations. Generated
`__init__.py` files may re-export convenient roots through `__all__`. The
author-owned request file is never rewritten.

Blueprint compilation imports these declarations exactly like handwritten
ones. It has no generation-specific declaration path.

## 8. Built-in data-contract inference

`InferDataContractProvider` produces unified table declarations from physical
schema metadata.

Its configuration is:

```python
class DataContractInferenceConfig(ProviderGenerationConfig):
    source: str
    relation: str | None = None
    mode: Literal["table", "table_group"] = "table"
    layout: Literal[
        "files", "parquet_parts", "hive_partitioned_parquet"
    ] = "files"
    anonymous: bool = False
```

Supported inputs include CSV/TSV, JSON/JSONL/NDJSON, Parquet, and supported
DuckDB-readable database relations. Remote S3 inputs are supported through the
same provider with optional anonymous access.

`mode="table"` produces one final table package. `mode="table_group"`
discovers logical relations and emits nested groups. Layout determines whether
files are independent tables, part files of one table, or Hive-partitioned
relations.

Schema inference uses DuckDB `DESCRIBE` as its schema boundary. It does not
scan values merely to guess whether a column that happened to contain no nulls
is logically required. This has an important physical-metadata consequence:

- top-level nullability is taken from the described relation;
- nested DuckDB `STRUCT` member types do not carry independent member
  nullability through `DESCRIBE`, so generated nested members are currently
  required;
- a JSON field containing only null values may be inferred as generic `JSON`;
  `JSON` is accepted and digested to canonical `str`, since `JSON` is a `VARCHAR`
  spelling and the source view applies `CAST(value AS VARCHAR)`. It is not a
  portable logical scalar in its own right and never becomes a canonical type.

Authors needing richer nested nullability must use a source format/provider
that supplies it or provide a handwritten contract. The generator must not
invent nested nullability from sampled values.

## 9. Rendering and ownership headers

The core renderer owns formatting and import generation. Every generated
Python file begins with a recognizable header containing:

- the product ownership marker;
- request ID;
- request fingerprint;
- renderer format directives, including `# ruff: noqa: F401` for the
  unconditional representative-type import of §7.

Rendered files are deterministic for the same request, provider version,
configuration, and dependency bytes. Generated source is parsed before it is
eligible for installation.

Generated files are not author-editable. A change to an owned generated file
is detected as a conflict or stale state rather than silently accepted as a
new source of truth.

## 10. Ownership manifest format 3

Every generated package contains:

```text
.kbs-generation.json
```

Format version 3 records:

```text
format_version
request_id
request_source_package
provider_import
provider_qualname
provider_version
request_fingerprint
owned_files
owned_directories
owned_file_hashes
```

Paths are normalized relative paths within the product root. Absolute and
machine-specific paths do not enter manifests or fingerprints.

`owned_file_hashes` binds each owned file to its expected generated content.
Ownership is proven by the validated manifest, relative path, ownership
header, and expected hash. Directory or filename conventions alone do not
prove ownership.

## 11. Desired-state generation

`kbs generate` processes all discovered requests as one desired-state pass:

1. statically discover and validate requests;
2. load provider and strict configuration types;
3. collect provider-declared dependencies;
4. generate normalized package trees;
5. validate paths, declarations, types, imports, and collisions;
6. render and parse all desired Python files;
7. compute fingerprints and format-3 manifests;
8. compare all desired products with disk;
9. verify ownership of obsolete and orphaned content;
10. prune only verified obsolete content;
11. atomically create or replace changed generated files;
12. run a post-install check pass to prove idempotence.

Providers, paths, ownership, and collisions are validated before mutation. An
existing unrecognized path is never overwritten. If desired output collides
with unrecognized content, the pass fails.

Writes use atomic replacement. Changed generated Python files have their owned
bytecode pruned so later imports cannot observe stale code.

## 12. Safe pruning, deletion, and rename

Only content proven to be owned may be deleted.

For an output-shape change:

- desired owned paths are created or updated;
- paths owned by the previous manifest but absent from the desired manifest
  are verified and pruned;
- unrecognized paths remain untouched;
- owned directories are removed deepest-first only when empty.

When a request disappears, its manifest becomes orphaned. The engine verifies
all recorded ownership, removes verified generated files and bytecode, removes
the manifest last, and removes the product root only if empty.

If unrecognized content remains, so does the containing directory:

```text
generated_product/
  notes.txt        # preserved
```

Renaming a request is safe deletion of the old product plus independent
creation of the new product. Unexpected modification of an owned file prevents
unsafe pruning.

## 13. Check mode

`kbs generate --check` performs the complete desired-state comparison without
mutation. It returns current only when every product and manifest matches.

It reports stale state for:

- missing or changed generated files;
- altered owned files;
- obsolete owned files;
- missing or invalid manifests;
- orphaned manifests;
- unrecognized collisions with desired output;
- invalid requests, provider output, or product collisions.

Check mode is the canonical CI and pre-compilation freshness validation.
Blueprint compilation itself does not invoke it.

## 14. Watch mode

`kbs generate --watch` maintains a complete request and dependency index.

- Changing an author-owned `__init__.py` rescans that declaration file and may
  add, update, rename, or remove products.
- Changing a provider-declared dependency regenerates only affected requests.
- An unchanged dependency save is ignored by content fingerprint.
- Events under generated products are ignored unless the path is independently
  declared as a provider dependency.
- Unrelated paths do not trigger global regeneration.

Watch diagnostics describe semantic generation actions—declaration added,
changed, deleted, or dependency changed—rather than exposing raw backend file
events. Generation errors are reported while watch mode continues.

## 15. Compilation boundary

Generation is edit-time installation. Compilation operates on importable final
declarations:

```python
from demo.table.complex_records import ComplexRecordsTable
```

`compile` does not inspect request objects, load providers, consult manifests,
or generate files. Generated declarations and handwritten declarations pass
through the same immutable blueprint schema version 2. The auxiliary
`create_blueprint` function exposes that intermediate representation without
changing the generation boundary.

This boundary keeps provider dependencies and source inspection out of runtime
builds and makes generated Python, ownership metadata, blueprint JSON, and SQL
independently inspectable artifacts.

## 16. Removed model

The following concepts are intentionally absent:

- `@generated(...)` placeholder decorators;
- generated mixins and `G_` bases;
- mutation of author-owned imports or class base lists;
- configurable generated output locations;
- adjacent single-file sidecars as the product model;
- author wrappers required to make a generated declaration final;
- MRO rules for combining generated and handwritten members.

Declaration augmentation, if introduced later, must be a separate design and
must not weaken package ownership.

## 17. Required behavioral coverage

The implementation is required to test:

- typed inert request construction;
- direct, qualified, and aliased discovery;
- rejection outside `__init__.py` and of dynamic or ambiguous assignments;
- assignment-derived product identity;
- multiple requests in one package;
- complete single-table and nested table-group products;
- unified generated `Field[T]` declarations;
- direct imports and blueprint compilation of generated finals;
- deterministic rendering, fingerprints, and idempotence;
- format-3 manifest portability and file hashes;
- missing, stale, altered, obsolete, and orphaned products;
- refusal to overwrite unrecognized content;
- safe output-shape pruning, request deletion, and rename;
- preservation of unrecognized files and directories;
- owned Python bytecode pruning;
- dependency-indexed watch updates and unchanged-save suppression;
- local, S3, part-file, and Hive-layout data-contract inference;
- end-to-end generation, compilation, and execution through the demo.

## 18. Remaining extensions

- richer provider-supplied nested nullability and constraints;
- normalized custom logical types from external schemas;
- additional schema, API, and catalog providers;
- stronger cross-request transactional rollback for filesystem failures;
- optional provenance linking generated declarations to source schema
  locations without introducing machine-specific fingerprints.
