---
title: "12. Generating declarations"
summary: "An inert contract observes a source once and writes an owned package of ordinary declarations."
section: book
perspective: book
part: II
chapter: 12
order: 29
status: normative
verified: 2026-11-15
sources:
  - docs/content/book/part-2/09-generation.md
  - docs/content/appendix/reference/generation.md
  - docs/content/appendix/spec/generation.md
  - docs/content/appendix/reference/cli.md
---

## A source schema is a fact, not a declaration

An estate feed arrives with a schema: sites have an identifier, a name and a nested premises block; equipment has a unit reference, a site reference, a service flag and a review period. Writing the source-relation declarations by hand is mechanical, slow and easy to get subtly wrong. A field typed `str` where the feed carries a timestamp is a defect that survives review because the declaration looks ordinary.

Generation turns that mechanical observation into an explicit, repeatable step. A decorator on the asset records the intent to generate. A provider observes the source schema once and returns declarations. An engine writes them into an owned package using the same public authoring surface a person would write by hand.

The boundary is the important part. Generation is an edit-time frontend. It is not part of the build, it does not run during `compile`, and it does not run during `execute`. The declarations it writes are ordinary declarations; from the moment they exist, nothing downstream knows or cares that they were generated.

## The decorator records intent and does nothing

The request is a class decorator on an `Asset` subclass:

```python
from pathlib import Path

from kg_build_system import (
    Asset, AssetAuthority, AssetLayout, AssetOptions, AssetProfile,
)
from kg_build_system.generation import AssetGenerationOptions, asset_generation
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig, InferDataContractProvider,
)

DATA = Path(__file__).parent / "data"


@asset_generation(
    AssetGenerationOptions(
        provider=InferDataContractProvider,
        configuration=DataContractInferenceConfig(
            mode="source_relation_group",
            layout="files",
            override={
                "surveys.surveyed_on": {"type": "timestamp"},
            },
        ),
        package="reference_project.relation.source",
    ),
)
class Estate(Asset):
    options = AssetOptions(
        name="estate",
        version="2026-08",
        profile=AssetProfile(
            subject="monitored estate records",
            coverage="sites, equipment and surveys",
            authority=AssetAuthority.PRIMARY,
            basis="estate registry and telemetry export",
        ),
        layout=AssetLayout(
            kind="json",
            locator=str(DATA),
            format="json",
            members={
                "sites": "sites.json",
                "equipment": "equipment.json",
                "surveys": "surveys.json",
            },
        ),
    )
```

`@asset_generation(AssetGenerationOptions(...))` validates the class and stores the options on `_asset_generation`. It performs no I/O. It does not read a source, load data, call the provider or write a file. The decorator is inert by design: importing the author module does not trigger an observation, and no build step depends on a provider being able to reach a source.

The three options are `provider`, `configuration` and `package`. They are generation-only values. They are not fields of `AssetOptions`, they do not enter the blueprint, and they do not describe the data. An asset states what the source is; the generation request states how its source-relation declarations are produced. Merging the two would make every build depend on a generation concern.

The decorator belongs on a module-level `Asset` subclass with exactly one base. A class inside a function or another class is not a request. The asset name is `AssetOptions.name` when set, otherwise the class name in snake case. The product is `<package>/<asset name>`, and its import is `<package>.<asset name>`. For the request above the product is `reference_project/relation/source/estate/`, imported as `reference_project.relation.source.estate`.

## Discovery reads source text, not modules

`kbs generate` finds requests with a static scan. Discovery parses Python with LibCST; it does not import the author project. It scans every `.py` file beneath the project root but parses only files whose text contains `asset_generation`, and it skips directories beginning with `.` and `__pycache__`.

Static discovery is what makes the decorator's inertness useful. The tool finds a request without executing the module that holds it, so the scan is not blocked by a module that fails to import. The observation pass that follows still loads the provider and the asset; the static scan is what makes the request set knowable before that pass. It also means the accepted request shape is deliberately narrow:

- one inline `AssetGenerationOptions(...)` call with exactly the three keyword fields;
- provider and configuration types imported statically;
- configuration constructed inline with static literals;
- no star imports, no unpacking and no dynamically built values.

A request that builds its configuration at runtime is refused with a `GenerationError` located at the asset source file and line. The restriction is not hostility to dynamic code. A request that cannot be read from source cannot be compared without importing the project, and comparison is the whole job of `--check`.

## A provider observes and returns declarations

A provider is a class with four responsibilities:

| Member | Meaning |
| --- | --- |
| `ID` | A stable provider identifier. |
| `VERSION` | A stable provider version; part of the request fingerprint. |
| `CONFIG_TYPE` | The exact configuration class the provider accepts. |
| `generate(context)` | An async classmethod returning one `GeneratedPackage`. |

`ProviderContext` supplies the project root, the author-owned request path, the request identity, the validated configuration and, when the asset was loaded, the decorated asset. A provider that needs a source path resolves it relative to the request file with `resolve_provider_path(context, value)`. The returned observation target is a reference, not a tracked input; the engine does not watch, hash or existence-check it.

The provider returns a `GeneratedPackage` composed of files, declarations and fields, plus optional nullability notes and a source digest. It does not return arbitrary Python text. The engine validates the complete package and renders it twice, requiring identical text before installing anything. Determinism is a precondition for ownership: a file whose content changes between two renders cannot be compared by hash.

The builtin `InferDataContractProvider` has `VERSION = "8"` and accepts `DataContractInferenceConfig`. The configuration names a source, a mode (`relation` or `source_relation_group`), a layout (`files`, `parquet_parts` or `hive_partitioned_parquet`), an optional relation, anonymous S3 access and a per-column override map. A directory requires `mode="source_relation_group"`. A database input is refused because no supported asset layout selects a database reader, so a generated source relation could never get a generic source step.

The override map is a declaration-time value, not a runtime option. An entry names a full `<relation path>.<column>` path and may declare its type, its nullability, or both. It can settle a type the reader reports as text or a nullability claim the statistics contradict. It cannot lift a physical type the reader refuses.

## Ownership is what makes generated code ordinary

Every generated product contains `.kbs-generation.json`, the ownership record. It records the request identity, provider identity and version, request fingerprint, optional source digest, owned files and directories, and the hash of every owned file.

Ownership changes the status of generated code. The files are not a cache and not a build artifact; they are project source with a recorded producer. The product is current when its record matches the request fingerprint and its file hashes. A product whose record does not match is stale, and the next pass regenerates it.

The record also makes edits honest:

- A modified owned file refuses the pass. It is never accepted as a new source of truth, and the engine does not overwrite it.
- Content not recorded in the record is never overwritten or deleted. A desired path that collides with unrecognized content fails the pass.
- Obsolete owned files are verified before pruning, and owned directories are removed only when empty.
- Deleting or renaming a request removes its verified product and preserves unrecognized content.
- Writes are atomic.

Generated files carry a header naming the request and the fingerprint and saying not to edit them manually. The instruction is not a suggestion about style. A hand-edited generated file is a conflict between the request and the product; the resolution is to change the request and regenerate, or to stop owning the file.

## Check, regenerate and watch answer different questions

`kbs` has one command: `kbs generate`. `compile` and `execute` are Python calls, not console commands. The command writes declarations; it does not read graph data, compile a plan or execute a build.

```console
kbs generate --project .
kbs generate --project . --check
kbs generate --project . --regenerate
kbs generate --project . --check --regenerate
kbs generate --project . --watch --debounce 500
```

| Flag | Question it answers |
| --- | --- |
| none | Make every product match its request. |
| `--check` | Do products and ownership records match their requests, without writing? |
| `--regenerate` | What does the source say now, and write that answer? |
| `--check --regenerate` | Has the source schema drifted, without writing? |
| `--watch` | Which declaration changes should trigger a new pass? |

`--check` performs the complete comparison without mutation. It exits `0` when products are current and `1` when a product or record is missing, changed, altered or orphaned. It does not re-observe sources. `--regenerate` forces every provider to observe its source again; alone it writes the re-observed result, and with `--check` it reports schema drift as `STALE` without writing. A usage error, including a refused flag combination, exits `2`.

`--watch` cannot be combined with `--check` or `--regenerate`. It runs one pass, indexes the requests, then watches project files. A change to an author-owned asset source is rescanned; a change under a generated product is ignored; a data-source change triggers nothing, because sources are references. An invalid edit is logged and watching continues.

The separation matters because the three operations answer different questions. A check that runs often must be cheap and deterministic, so it compares declarations and records. A source observation may be slow or remote, so it is a deliberate act. A watcher reacts to declaration edits, not to the data the declarations describe.

## Observation is provenance, not a type

A provider observes nullability claims from three kinds of evidence: `DEFAULTED`, `DECLARED` and `ENFORCED`. Those claims feed nullability notes, statistics and manifests. They do not decide the rendered annotation.

Every generated source field renders `Field[T]`, taken from its value type alone. A source that declares a column non-null still renders `Field[T]`. A source that leaves it nullable still renders `Field[T]`. The observed claim reaches the header notes and the pre-flight, where a reviewer can see it; it never adds `| None` to a source-backed field.

The reason is the same asymmetry that governs nullability in the authoring surface. Source access is nullable regardless of what the file claims, so a generated source field reads as `NullableSelection[T]` exactly like a handwritten one. Adding `| None` to the field type would be redundant at best and misleading at worst: it would suggest that the declaration has chosen an optional value, when the source's absence is a property of the observation. A field type states the value; the source access states the risk.

Value-type nullability is different. An array item that is explicitly nullable, or a computed result that is explicitly nullable, belongs to the value type and renders as `Nullable[T]`. That is a statement about the value's shape, not about a source observation. The distinction is the one from the values and nullability chapter: nullability that belongs to the type is rendered; nullability that belongs to access is narrowed at use.

## Observation writes structure; the author writes the contract

A generated field carries no `FieldDefinition`, and a generated relation carries no
`Contract` unless the request states one. That is not an omission in the provider. A
definition states what a value is in the domain, in which unit and what its absence
denotes; a contract states a grain, an identity and a meaning. Every one of those is
an authored decision. An observation can see that a column holds text and how often
it is null; it cannot see that the text is an identifier or that a missing value
means "not surveyed".

The request is the author's only input to generation, so it is also where a contract
part is stated. Generation writes the parts the request carries and leaves the rest
absent. A generated source relation with no contract is a skeleton: it compiles and
its row shape is checked. It remains bindable, because a source relation's contract
is optional; the binding states the grain, identity and coverage it relies on, and
the absence is a review finding. Structural completeness is what generation
guarantees; contractual completeness is what the author states. A generated derived
relation is different: it is a published contract and must state one, so it is not
generated as a skeleton.

This keeps the ownership rule honest. A generated file is never hand-edited, so
nothing that the file must say can live only in the author's head. If a definition
matters, it is stated in the request and rendered into the declaration; if it does
not, the skeleton is reported and the author decides whether to state it.

## Generated source compiles like handwritten source

Generated declarations use only the public authoring surface: `Field`, `field`, `SourceRelation`, `Struct`, `SourceRelationGroup`, `SourceRelationOptions` and `SourceRelationGroupOptions`. A generated relation names its asset with `SourceRelation[Asset]` and imports the authored asset module. The renderer emits canonical scalar names as their public types: `Date`, `Time`, `Timestamp`, `Uuid`, and the builtin scalars as their Python names.

```python
from kg_build_system import Field, SourceRelation, SourceRelationOptions, field

from reference_project.asset.estate import Estate


class EquipmentSourceRelation(SourceRelation[Estate]):
    options = SourceRelationOptions(name="equipment")

    unit_ref: Field[str] = field(name="unit_ref")
    unit_name: Field[str] = field(name="unit_name")
    site_id: Field[str] = field(name="site_id")
    in_service: Field[bool] = field(name="in_service")
    survey_period: Field[str] = field(name="survey_period")
```

The excerpt looks like a relation a person would write, because it is one. There is no generation-specific compilation path. The build imports the generated class exactly as it imports a handwritten class, reads its fields and types, and plans the same source step. The generated package is a normal package with an explicit `__init__.py`; its classes are ordinary declarations. The `__init__.py` is a facade, like every other package in the project: re-exports and `__all__`, no declaration and no logic.

This is the strongest form of the ownership claim. Generated code is not a parallel model that happens to resemble the authoring API. It is the authoring API. A reviewer can read it, a type checker can check it, and a later author can depend on it without knowing which classes came from a provider.

## Generation ends before the build begins

The build does not invoke generation. `create_blueprint`, `compile` and `execute` read the declarations that exist in the project; none of them calls a provider or observes a source. A build with no network access and no source files still runs against the generated declarations, because at that point they are just declarations.

This boundary has three consequences:

1. **Reproducibility.** A build depends on source text, not on a remote schema that may change between runs. The generated files are versioned with the project.
2. **Reviewability.** The observation is recorded once, in the request and the ownership record, and the result is visible in source. A reviewer can compare the generated field types with the source and with the author's overrides.
3. **Separation of failure.** A source that is unavailable fails generation, not every build. A declaration defect fails compilation, not the observation.

The source digest is provenance, not a tracked input. The engine stores it and replaces it when a provider reports a new one, but a change to the digest alone does not make a product stale. A row-level or schema-level source change is pulled into the project by `--regenerate`, deliberately. If every data change made every product stale, a build would depend on the source's current shape, which is exactly the dependency the boundary removes.

The authored asset source is never rewritten. Generation adds and owns the product package; the generation request and the asset options stay under the author's control. A provider that needs a source path resolves it relative to the request file; the path may lie outside the project, and the engine does not track it. Observation is an act with a recorded result, not a live connection.

## A contract for the estate feed

Return to the estate asset. The request says: observe the JSON directory as a relation group, infer the relations from the files, override the survey date as a timestamp, and write the result into `reference_project.relation.source`. The asset says: this is the primary estate registry at release 2026-08, covering sites, equipment and surveys, with the registry and telemetry export as its basis.

Generation produces `reference_project/relation/source/estate/` with one module per relation, a relation group where the layout calls for one, structs for nested members, and the ownership record. Every relation names `Estate` with `SourceRelation[Estate]`. The survey date is a `Timestamp` because the override declared it, and a value that does not fit the checked cast aborts the scan.

A later schema change adds a column. `kbs generate --check` still reports the product as current, because the declaration and its ownership record match; the check does not observe the source. `kbs generate --check --regenerate` observes the source, sees the new column, and reports `STALE` without writing. `kbs generate --regenerate` writes the re-observed field. A plain `kbs generate` leaves a current product alone, because a source change is not a declaration change. The build was never involved.

The sequence is the point. Observation produces declarations. Declarations produce a blueprint. The blueprint produces work. Generation sits before the first step and does not reach into the others.

## Next

[Part III — From declarations to records](/book/part-3/index) — follow the linked model into the blueprint, the plan and the records.
