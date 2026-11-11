---
title: Generation specification
summary: An inert contract observes one schema once and writes an owned declaration package.
section: spec
perspective: spec
subject: generation
spec: SPEC-008
order: 80
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/generation/code_generation/model/public/contract.py
  - kg_build_system/generation/code_generation/service/_private/discovery.py
  - kg_build_system/generation/code_generation/service/_private/engine.py
  - kg_build_system/generation/code_generation/model/internal/providers.py
  - kg_build_system/generation/code_generation/service/_private/builtins/provider.py
evidence:
  - tests/test_codegen_discovery.py
  - tests/test_reference_build.py
  - docs/appendix/reference/generation.md
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Source generation and CLI</span><a href="/appendix/subjects/generation">Overview</a><a href="/book/part-2/06-generation">Guide</a><a href="/appendix/spec/generation" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/explainability-is-authored">Philosophy</a><a href="/appendix/review/limits">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** `@asset_contract(AssetContractOptions(...))` MUST be inert. It MUST validate and store the request without reading a source, invoking a provider, or writing a file.
- **R2.** The decorator MUST sit on a module-level `Asset` subclass with exactly one base, and its options MUST name exactly `provider`, `configuration`, and `package`.
- **R3.** Discovery MUST be a static LibCST scan. It MUST NOT import the author module, and it MUST parse only files whose text contains `asset_contract`.
- **R4.** A provider MUST declare `ID`, `VERSION`, and `CONFIG_TYPE`, and MUST implement async `generate(context)` returning one `GeneratedPackage`.
- **R5.** `InferDataContractProvider` MUST keep `VERSION = "8"` and MUST accept `DataContractInferenceConfig` as its configuration type.
- **R6.** The product MUST be `<package>/<asset>`, where the asset name is `AssetOptions.name` or the class name in snake case. Its import MUST be `<package>.<asset>`.
- **R7.** The generated product MUST be owned through `.kbs-generation.json`. A modified owned file MUST refuse the pass, and unrecognized content MUST NOT be overwritten.
- **R8.** `--check` MUST write nothing and MUST exit `0` for `CURRENT` or `CHANGED` and `1` for `STALE` or a failure. `--regenerate` MUST re-observe every source.
- **R9.** `--watch` MUST NOT be combined with `--check` or `--regenerate`.
- **R10.** Observation MUST be provenance: every generated source field MUST render `Field[T]`, and the build MUST NOT invoke generation.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/test_codegen_discovery.py` | Inert decorator, static discovery, provider identity, and ownership refusal. |
| `tests/test_reference_build.py` | Generated source compiles as ordinary handwritten declarations. |
| `docs/appendix/reference/generation.md` | The CLI flags, provider protocol, and request model. |

## API

| Public name | Role |
| --- | --- |
| `asset_contract` | Records a generation request on an asset class. |
| `AssetContractOptions` | Provider, configuration, and package for one request. |
| `Provider` | Typed provider base with identity and async generation. |
| `ProviderGenerationConfig` | Frozen, strict configuration base. |
| `ProviderContext` | Project, request path, asset identity, and validated config. |
| `GeneratedPackage` | Files, nullability notes, and source digest returned by a provider. |
| `InferDataContractProvider` | Builtin schema-observation provider, version `8`. |
| `DataContractInferenceConfig` | Builtin mode, layout, source, and override configuration. |
| `discover` / `discover_file` | Static request discovery for a project or one file. |
| `generate` / `watch` | Desired-state pass and declaration watcher. |
| `GenerationStatus` | `CURRENT`, `CHANGED`, or `STALE`. |
| `GenerationError` | Refusal for a defective request or ownership conflict. |

## Limits

- Generation writes declarations. It does not read graph data, run a build, or rewrite the authored asset source.
- A data-source change alone does not make a product stale. `--regenerate` is the deliberate re-observation; the source digest is provenance.
- A provider returns a `GeneratedPackage`, never arbitrary Python source. A hand-edited generated file is a conflict, not a declaration.
- The builtin provider refuses a database input and requires a directory input to use `mode="table_group"`.
- Observed absence never adds an optional annotation to a source-backed field. The claim reaches the manifest and pre-flight instead.
- `--watch` watches declarations, not data sources. Product files and data sources trigger no pass.

## Rationale

Generation is an upstream frontend, so the [build boundary](/appendix/review/contracts) stays intact: observation ends where authored declarations begin. The inert decorator keeps intent readable in source while ownership makes every written file accountable. Treating observation as provenance keeps uncertainty visible to a reviewer instead of silently widening the model.

## Next

Read the [generation subject](/appendix/subjects/generation) for the authoring-level view.
