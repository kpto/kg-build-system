---
title: Generate declarations
summary: An inert asset contract turns one observed source schema into an owned package of ordinary table declarations.
section: author
order: 90
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/generation/code_generation/model/public/contract.py
  - kg_build_system/generation/code_generation/service/_private/discovery.py
  - kg_build_system/generation/code_generation/service/_private/engine.py
  - kg_build_system/generation/code_generation/service/_private/builtins/config.py
  - reference_project/assets.py
subject: generation
perspective: guide
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Source generation and CLI</span><a href="/subjects/generation">Overview</a><a href="/author/generation" class="active">Guide</a><a href="/spec/generation">Spec</a><a href="/reference/api">API</a><a href="/philosophy/explainability-is-authored">Philosophy</a><a href="/review/limits">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> Generation is an edit-time frontend. A decorator records a request, a static scan finds it, a provider observes a schema once, and the engine writes declarations the build treats as handwritten.

## What it is

| Piece | Job |
| --- | --- |
| `@asset_contract(AssetContractOptions(...))` | An inert request on one module-level `Asset` subclass. |
| Static discovery | A LibCST scan that finds requests without importing the author module. |
| Provider | An async observer that returns one `GeneratedPackage`. |
| `.kbs-generation.json` | The ownership record for one generated product. |
| `kbs generate` | The only command that turns requests into owned source. |

`@asset_contract(AssetContractOptions(provider=..., configuration=..., package=...))` validates its options and stores them on the class. It performs no I/O, calls no provider and writes no file. The options are not `AssetOptions` fields and never enter the blueprint.

The provider protocol declares `ID`, `VERSION`, `CONFIG_TYPE` and `async generate(context) -> GeneratedPackage(files, nullability_notes, source_digest)`. The builtin `InferDataContractProvider` has `VERSION = "8"` and accepts `DataContractInferenceConfig(mode="table_group"|..., layout="files"|..., override={...})`.

## Rules

- The decorator belongs on a module-level `Asset` subclass with exactly one base. A class inside a function or another class is not a request.
- Discovery requires one inline `AssetContractOptions(...)` call with exactly three keyword fields: `provider`, `configuration` and `package`. The provider and configuration types are statically imported.
- The configuration is constructed inline with static literals. Stars, unpacking and dynamically built values are refused.
- Discovery is static LibCST; it never imports the author module. It parses only files whose text contains `asset_contract`.
- Identity is `AssetOptions.name`, otherwise the class name in snake case. The product is `<package>/<asset>` and its import is `<package>.<asset>`.
- Generation has one CLI command: `kbs generate`. `--check` is no-write: exit `0` for `CURRENT` or `CHANGED`, exit `1` for `STALE` or a failure.
- `--check --regenerate` re-observes sources and reports drift as `STALE` without writing. `--watch` excludes `--check` and `--regenerate`.
- Generated source is owned. `.kbs-generation.json` records the format version, provider identity, fingerprint, source digest and every owned file hash.
- A modified owned file refuses the pass. Unrecognized content is never overwritten, stale products are verified before pruning, and writes are atomic.
- Observation is provenance. The `DEFAULTED`, `DECLARED` and `ENFORCED` tiers feed nullability notes, statistics and manifests; they do not decide the annotation.
- Every generated source field renders `Field[T]`. Explicit value-type nullability, such as an array item, renders `Nullable[T]`.

## Example

```python
from pathlib import Path

from kg_build_system import (
    Asset, AssetAuthority, AssetLayout, AssetOptions, AssetProfile,
)
from kg_build_system.generation import AssetContractOptions, asset_contract
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig, InferDataContractProvider,
)

DATA = Path(__file__).parent / "data"


@asset_contract(
    AssetContractOptions(
        provider=InferDataContractProvider,
        configuration=DataContractInferenceConfig(
            mode="table_group",
            layout="files",
            override={
                "surveys.surveyed_on": {"type": "timestamp"},
            },
        ),
        package="reference_project.table",
    ),
)
class Estate(Asset):
    options = AssetOptions(
        name="estate",
        version="2026-08",
        profile=AssetProfile(
            subject="monitored estate records",
            coverage="sites, equipment, surveys and logger readings",
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

The product is `reference_project/table/estate/`, imported as `reference_project.table.estate`. The generated tables name `Estate` with `Table[Estate]` and use the public authoring surface, so `compile` treats them exactly like handwritten declarations.

## Limits

- Generation writes declarations; it does not read graph data, run a build or rewrite the authored asset source.
- A data-source change alone does not make a product stale. `--regenerate` is the deliberate re-observation; the source digest is provenance, not a tracked input.
- A provider returns a `GeneratedPackage`, never arbitrary Python source. The engine renders twice and requires identical text before installing anything.
- A hand-edited generated file is a conflict, not a declaration. Unowned files and directories are preserved.
- The builtin provider refuses a database input and requires `mode="table_group"` for a directory. It needs a `source=` value or the asset's layout locator.
- Observed absence never adds an optional annotation to a source-backed field. The claim reaches the manifest, header notes and pre-flight instead.
- `--watch` is a declaration watcher, not a data-source watcher. Product files and data sources trigger no pass.

## Next

[Run the walkthrough](/start/walkthrough) — follow a contract from source observation to a compiled graph.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-024 | Keep generation an inert edit-time frontend, separate from the asset model and blueprint. | 2026-11-04 | accepted | `tests/test_codegen_discovery.py` |
| D-025 | Treat observation as provenance: every generated source field renders `Field[T]`, never an optional annotation. | 2026-11-05 | accepted | `tests/test_codegen_discovery.py` |
