# Edit-Time Generated Packages — Specification

## 1. Purpose and status

This document specifies the implemented edit-time package-generation system
for the Knowledge Graph Build System.

Generation requests are typed Python values for IDE and static-analysis
support. Discovery is static, providers run only through generation commands,
and every result is a complete importable package owned through a versioned
manifest. Runtime declaration imports and blueprint compilation do not execute
generation.

The current ownership-manifest format version is `6`. As of that version the
system tracks references, not data: see the decision record in section 19.

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
constructs this value. It does not observe sources, load data, invoke a
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
- one normalized `GeneratedPackage` result.

`ProviderContext` supplies the project root, request source file, request ID,
and typed configuration. `resolve_path` resolves a provider path relative to
the author-owned request file and assigns it no semantics: the resolved path
is an observation target, not a tracked input. It may live outside the
project, and the engine neither watches, hashes, nor existence-checks it.

A provider that observes a source schema should record a digest of what it
observed in `GeneratedPackage.source_digest`. The engine stores that value in
the manifest as provenance and never interprets it; computing it should cost
metadata (footer schema rows, a sniffed column list), never the source's
data bytes.

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
- duplicate declarations within one file, and dangling or ambiguous
  generated references;
- invalid public identifiers or unsupported normalized types.

The complete desired package is rendered and parsed before filesystem
mutation.

Generated references carry identity, not just a name: a struct reference may
bind to the file declaring its target, so identity is ``(name, file)`` and
several files declaring same-named records is ordinary. An unbound reference
resolves the way Python resolves names for a handwritten author: a
declaration in the same file wins, and any other reference needs the name to
be unique across the package to be imported. A name no file declares dangles
and an unbound name several files declare is ambiguous for an import; both
are refused rather than guessed, so an import is never bound to the wrong
declaration. The rendered class name is display only — the built-in provider
emits shortest-honest names that repeat freely across files (section 8).

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
    override: dict[str, dict] = {}
```

`override` replaces what the reader reports for one relation's whole
top-level column. Keys are the column's FULL path — the relation path inside
the source and the column name:

```python
override={
    "temperature.recorded_on": {"type": "timestamp"},
    "evidence_orphanet.directionOnTarget": {"nullable": True},
}
```

A bare column name is refused: the same name can appear in many relations of
one source, and an override reaches exactly the relation it names. `type`
declares the canonical unit type the column means to hold (decision 9's
promotion; the source view applies the checked cast). `nullable` settles a
nullability claim — `true` declines a source-declared non-nullability (a
Parquet footer `REQUIRED` whose statistics report nulls), which also drops
the column from the statistics pre-flight and the build guard; `false`
asserts one the guard will test; absence keeps the source's own claim.
Values are plain dictionaries because discovery reads the request file
without executing it; an entry must declare at least one of `type` and
`nullable`, and scope stops at whole top-level columns — reaching inside a
column would replace sniffing with a declared schema and is a separate
decision, as with nested promotion.

Derived `Struct` records are named from the member path alone — the
`timeseries` column yields `TimeseriesStruct` in its table's own file, and a
nested member extends the path (`OntologySourcesStruct`), never a parent or
table prefix. Six relations with a `timeseries` struct column render six
identical class names in six files, exactly as handwritten Python would:
each table's references bind to their own file, so the names never have to be
globally unique. Names are display, not identity — identity is the class
object, module-qualified in the IR, and file-bound references at render time
guarantee an import never binds the wrong declaration (section 6).

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

Rendered files are deterministic for the same request, provider version, and
configuration; source data contributes nothing to them beyond what the
provider observed at generation time. Generated source is parsed before it is
eligible for installation.

Generated files are not author-editable. A change to an owned generated file
is detected as a conflict or stale state rather than silently accepted as a
new source of truth.

## 10. Ownership manifest format 6

Every generated package contains:

```text
.kbs-generation.json
```

Format version 6 records:

```text
format_version
request_id
request_source_package
provider_import
provider_qualname
provider_version
request_fingerprint
source_digest
owned_files
owned_directories
owned_file_hashes
```

`request_fingerprint` is the authoring identity of the request — its
configuration, identity, provider import, provider version, and format
version. No source content, and no digest of source content, enters it.
`source_digest` is the optional observation stamp described in section 5:
provenance only, never a staleness trigger.

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
3. take a product whose manifest still matches its request fingerprint and
   owned-file hashes as current without observing its sources, unless
   `--regenerate` forces re-observation of every request;
4. generate normalized package trees for the remaining requests;
5. validate paths, declarations, types, imports, and collisions;
6. render and parse all desired Python files;
7. compute fingerprints and format-6 manifests;
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

Because sources are references rather than tracked inputs, `--check` proves
that products match their requests and manifests — it cannot and does not
prove that contracts match the current shape of a source. `--regenerate`
added to check mode does that: every provider re-observes its source, and a
schema change that would alter the contract is reported as stale without
anything being written.

## 14. Watch mode

`kbs generate --watch` maintains a complete request index.

- Changing an author-owned `__init__.py` rescans that declaration file and may
  add, update, rename, or remove products.
- Changes to data sources trigger nothing. A source is a reference, not a
  tracked input, so no file watch, content hash, or staleness trigger exists
  for it; pulling a source schema change into the project is a deliberate
  `--regenerate` pass.
- Events under generated products are ignored.
- Unrelated paths do not trigger global regeneration.

Watch diagnostics describe semantic generation actions—declaration added,
changed, or deleted—rather than exposing raw backend file events. Generation
errors are reported while watch mode continues.

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

This boundary keeps provider observation and source inspection out of runtime
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
- MRO rules for combining generated and handwritten members;
- provider-declared dependency file sets, data-byte fingerprinting, and
  data-path watch triggers (removed with manifest format 6, section 19).

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
- local-first and file-bound generated reference resolution, refusal of
  dangling and ambiguous references, and shared declaration names across
  files importing as distinct declarations;
- format-6 manifest portability and file hashes;
- missing, stale, altered, obsolete, and orphaned products;
- refusal to overwrite unrecognized content;
- safe output-shape pruning, request deletion, and rename;
- preservation of unrecognized files and directories;
- owned Python bytecode pruning;
- steady-state passes observing no source at all, and `--regenerate`
  re-observing;
- source data changes, row-level or schema-level, never triggering watch
  regeneration or plain `--check` staleness, while `--check --regenerate`
  reports schema drift;
- sources outside the project directory being ordinary generation inputs;
- the manifest `source_digest` tracking observed schema, not observed values;
- local, S3, part-file, and Hive-layout data-contract inference;
- end-to-end generation, compilation, and execution through the demo.

## 18. Remaining extensions

- richer provider-supplied nested nullability and constraints;
- normalized custom logical types from external schemas;
- additional schema, API, and catalog providers;
- stronger cross-request transactional rollback for filesystem failures;
- optional provenance linking generated declarations to source schema
  locations without introducing machine-specific fingerprints;
- import aliasing at namespace merges, so one file may deliberately bind two
  same-named declarations from different modules (references currently refuse
  such a reference as ambiguous rather than aliasing it — section 6).

## 19. Decision record — references, not data

Manifest format 6 removed provider-declared dependencies. It replaces "which
files' bytes is this product a function of?" with "which request produced
this snapshot, and what did that request observe?"

### The decision

A generation source — a Parquet directory, a JSON file, an S3 prefix — is a
reference carried by the request, never a tracked build input. The engine
tracks authoring artifacts only: request files, provider identity, rendered
products, and manifests. It does not enumerate, open, hash, existence-check,
watch, or root-constrain a provider's sources. Providers observe their sources
on demand and stamp the observed schema's digest into the manifest as
provenance.

### Why

The dependency mechanism imported the build-system premise that a generated
product is a pure function of tracked file contents. For observation-based
providers that premise is ill-typed, and its costs were structural:

- content hashing conflated row identity with schema identity. A row-level
  change rewrote every product file to record a new fingerprint, although the
  contract describes schema, not values;
- hashing the whole dataset to describe its columns prices a product at
  dataset size rather than schema size;
- file watching is bounded to one project tree and one suffix list, so the
  mechanism under-triggered (formats outside the list, sources outside the
  root) while over-triggering inside it;
- "did the input change in a way that matters?" is provider-specific —
  a Parquet footer tree, a Hive layout's partition keys, a sniffer's bounded
  sample — and cannot be answered by a format-agnostic file index;
- remote sources had to be excused from the entire mechanism because they
  have no local paths, which showed the Path-shaped interface could not
  represent the provider's actual relationship to its source;
- the enforcement of contract fidelity was never in code generation.
  `SOURCE_SCHEMA_TRUST_AND_NULLABILITY_SPEC.md` puts it at runtime ingest:
  widening-only, checked promotion casts, and a build that fails on the first
  value that does not fit. Byte-level dependency tracking was a redundant
  tripwire whose failure mode — a silently stale contract — cannot corrupt a
  build.

### Consequences, accepted

- `--check` proves products match their requests and manifests, not the
  current world; `--check --regenerate` re-observes sources and reports schema
  drift without writing.
- A source schema change enters the project only through a deliberate
  `--regenerate` pass or a request edit. Row-level change never invalidates
  anything.
- Sources may live anywhere the process can read: outside the project root
  is now ordinary, and local and remote sources differ only in transport.
- The determinism guard compares two renders of one observation rather than
  two observations, which also removes a race against a mutating dataset.
- Products embed the request fingerprint, so the fingerprint inputs changing
  (including `FORMAT_VERSION`) rewrites product files; this was the
  established behavior and format 6 is such a change.

### Digest mechanics

The built-in inference provider records, per relation, the described columns
with their reported types and tiered nullability, the Parquet node shapes when
present, and the source count and Hive flag. `source_digest` is the SHA-256
of those facts. File names, paths, sizes, byte offsets, and values are
deliberately excluded: the digest moves when the observed schema moves and
not when its data does. The engine stores and replaces the digest without
interpretation; only the provider that wrote it compares old against new,
during a regeneration pass.
