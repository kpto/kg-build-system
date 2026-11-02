# Generation

## Responsibility

`code_generation` owns edit-time generation of declaration packages from typed
requests: static discovery, provider execution, deterministic rendering,
ownership and desired-state maintenance.

## Public API

- `generation(provider, configuration)` is an inert request. The assignment name
  is the request identity; the product is the sibling package of the request
  file.
- `Generation`, `GenerationRequest`, `GenerationResult`, `GenerationSession`,
  `GenerationError`, `GenerationStatus`.
- `discover`, `discover_file`, `generate`, `watch`, `FileChange`,
  `FileChangeKind`.
- `kbs generate` (with `--check`, `--regenerate`, `--watch`, `--debounce`).
- `code_generation.builtins`: `DataContractInferenceConfig`,
  `InferDataContractProvider`, `ColumnOverride`.

## Internal interface

`code_generation.interfaces` exposes the provider contract:
`Provider`, `ProviderContext`, `ProviderGenerationConfig`,
`resolve_provider_path`, `load_provider`, `DiscoveredGeneration`,
`GenerationAction`, `GenerationActionKind`, `Nullability`.

A provider declares `ID`, `VERSION`, `CONFIG_TYPE` and async
`generate(context) -> GeneratedPackage`. A provider is loaded by dotted import
coordinates from the request; it needs no engine edit. `resolve_provider_path`
resolves an observation path relative to the request file; it is not a tracked
input.

## IR

`code_generation.ir` holds the frozen generated-declaration DTOs:
`GeneratedPackage`, `GeneratedFile`, `GeneratedClass`, `GeneratedField`,
`GeneratedMember`, `GeneratedAnnotation`, the `Generated*Type` tree and
`NullabilityNote`. Rendering owns the text; the IR states only what to render.

## Boundaries

- `code_generation` imports `types.interfaces` and `engines.interfaces` as an
  observer for type vocabulary and Parquet metadata.
- It must not import `compile`, `workflow`, `modules` or `api`; generation is an
  edit-time lane and never runs at compile or build.
- `engines` must not import `code_generation`.
- `cli` imports the generation command; `code_generation` must not import `cli`.
- The request file is author-owned; the engine writes only the product directory
  and its manifest.

## Current decisions

- **Requests are inert.** Constructing a request validates the provider/config
  pair and freezes the value. It does not observe a source, invoke a provider or
  write a file.
- **Static discovery.** Requests are found by parsing `__init__.py` without
  importing the author's package. A request must be a module-level assignment
  with an inline provider/config construction.
- **Output identity.** Request id + product path + package import are derived
  from the request file. The product directory owns a manifest; generated files
  carry an ownership header and are not hand-edited.
- **Determinism.** Rendering the same observation twice must produce identical
  bytes. The engine compares the rendered product before installing anything.
- **Desired state.** `generate` classifies current/stale, checks ownership,
  prunes files the manifest no longer owns, writes changed files atomically and
  writes the manifest last. `--check` reports without writing. `--regenerate`
  re-observes every provider.
- **Nullability.** The provider records the source tier. Rendering emits
  `Field[T | None]` for defaulted sources and `Field[T]` for enforced/declared
  sources. An override changes the claim; it does not silently change access.
- **No compile coupling.** Compilation and building never invoke generation;
  generated declarations are ordinary authoring declarations.
