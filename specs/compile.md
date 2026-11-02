# Compile

## Responsibility

The `compile` package owns the build-blueprint aggregate, its codecs and validation, the compile-time module protocol and the pipeline that lowers declarations and ordered module contributions into one workflow contract.

## Public API

- `BuildBlueprint` is a frozen, slotted compatibility aggregate:
  - `structs: tuple[Any, ...]`
  - `tables: tuple[Any, ...]`
  - `components: tuple[Any, ...]`
  - `projections: tuple[Any, ...]`
  - `bindings: tuple[Any, ...]`
  - `sources: tuple[Any, ...] = ()`
  - `modules: tuple[BlueprintModule, ...] = ()`
- `BlueprintModule(module_id, module_import, module_qualname, configuration=None)`.
- Pipeline functions:
  - `create_blueprint(*, bindings=(), sources=(), modules=(), namespace_path=None, languages=None) -> BuildBlueprint`
  - `configure_blueprint_modules(blueprint, modules) -> BuildBlueprint`
  - `create_build(*, languages, namespace) -> BuildIR`
  - `compile_build(*, build, modules=(), engine=None) -> WorkflowContractIR`
  - `compile_workflow(*, blueprint, engine=None) -> WorkflowContractIR`
  - `validate_blueprint(blueprint) -> None`
- The importable package `kg_build_system.compile` is callable through a module subclass: `kg_build_system.compile(...)` delegates to `api.compile`. `compile.models` re-exports `BuildBlueprint` and `BlueprintModule` for compatibility; their module is `kg_build_system.compile.ir`.
- The composition root `api.compile` and `api.create_blueprint` are the public authoring entry points. They append `CoreModule` after the supplied modules.

## Internal interface

`compile.interfaces` exposes:

- `BuildBlueprint`, `BlueprintModule`.
- `CompilationContext` (re-exported from `kernel.contract`): `build`, `module_id`, `configuration`, `blueprint=None`, `engine=None`.
- `ModuleCompiler` protocol: async `compile(context) -> Any`.
- `CompilableModule` protocol: `ID`, `VERSION`, `CONFIGURATION_TYPE`, async classmethod `create_compiler(context) -> ModuleCompiler`.
- `encode_blueprint(value) -> dict[str, Any]`.
- `decode_blueprint(value) -> BuildBlueprint`.
- `validate_blueprint(blueprint) -> None`.

Invariants:

- `BuildBlueprint` is frozen and its fields are tuples of IR values. It stores no declaration class, expression wrapper, binding value, connection or module instance.
- `BlueprintModule.configuration` is the serialisable registration configuration.
- `create_blueprint` lowers the default languages (`TableLanguage`, `TopologyLanguage`, `BindingLanguage`) through a `Registry`, assembles the blueprint from the `data`, `topology` and `binding` parts, records module registrations and calls `validate_blueprint`.
- `create_build` lowers an arbitrary language registry into a `BuildIR` without a blueprint.
- `compile_build` compiles modules against a custom build, assembles the workflow and returns a contract with no provenance.
- `compile_workflow` builds a `BuildIR` from the blueprint parts, compiles the blueprint's modules, assembles the workflow and returns a contract with compile provenance.

## IR

- `compile.ir` owns `BuildBlueprint` and `BlueprintModule`.
- The blueprint codec shape is:
  - `data`: the `table.ir` data part (`structs`, `tables`, `projections`, `sources`);
  - `topology`: the topology part sequence;
  - `binding`: the binding part sequence;
  - `modules`: a list of `{module_id, module_import, module_qualname, configuration}`.
- Encoding uses the component codecs; there is no schema version and no JSON-string helper. Decoding requires a mapping, known part shapes and known source/component/binding kinds.
- `validate_blueprint` requires at least one graph component and at least one graph binding. It enforces unique symbol IDs across structs, tables, components, projections, bindings and sources, and unique source-bound table names.
- Part-specific validation lives in the languages: `TableLanguage.validate` checks data invariants, `TopologyLanguage.validate` checks components and parents, and `BindingLanguage.validate` checks binding IR types and unique symbols.

## Boundaries

- Surfaces: `compile.ir` is the blueprint; `compile.interfaces` is the internal interface; the package has no author-facing surface of its own beyond the compatibility callable and `compile.models`.
- Allowed dependencies: `kernel`, and the `interfaces` and `ir` surfaces of `table`, `topology`, `binding` and `workflow`.
- `compile` may call workflow assembly and contract creation; `workflow` must not import `compile`.
- Must not import concrete module implementations, `engines`, `code_generation`, `api` or `cli`.
- A module compiler receives `CompilationContext` and its own reconstructed registration configuration. It never receives authoring classes, a runtime connection or executor state.
- The workflow contract is the only value handed from compilation to execution. Compile provenance is opaque to execution.

## Current decisions

- **The blueprint is IR, not authoring state.** Every field is a tuple of frozen IR values. No declaration class, expression wrapper, binding object, connection or module instance is stored.
- **Validation is explicit at the language boundary.** `create_blueprint` validates. `encode_blueprint`, `decode_blueprint` and `configure_blueprint_modules` do not call `validate_blueprint` themselves; a caller that needs the guarantee calls it.
- **No schema version.** A blueprint is identified by its content. The decoder refuses unknown fields and never negotiates a version.
- **Blueprint invariants.** `validate_blueprint` checks the cross-part invariants listed above. The languages check their own parts before the blueprint is assembled: unique field names, unique logical table/projection names, known projection scans, acyclic projection dependencies, a row source on every projection, known source tables, unique component symbols, edge endpoints and abstract parents.
- **Compile mode: declarations.** `create_blueprint` accepts explicit `bindings` and `sources`, a `namespace_path`, or both. Namespace mode imports every module under the path, skips `build`, `node_modules` and `__pycache__`, and collects public module-level values. Explicit and discovered values are deduplicated by object identity. Declarations are resolved from the expressions and row sources the bindings and projections use.
- **Compile mode: public API.** `kg_build_system.create_blueprint(*, modules, namespace_path=None, bindings=None, sources=None)` and `kg_build_system.compile(*, modules, namespace_path=None, bindings=None, sources=None, blueprint=None, engine=None)` are the composition modes. `modules` is required and core is appended after the supplied modules. `blueprint` cannot be combined with `namespace_path`, `bindings` or `sources`. `bindings` and `sources` are supplied together. With no source mode, the caller's file directory is the namespace path.
- **Module composition.** A blueprint records each module registration as `BlueprintModule` with the module ID, import module, class qualname and frozen configuration. Compilation imports the class, reconstructs the configuration with `CONFIGURATION_TYPE(**configuration)`, calls `create_compiler` and rewrites the contribution's module reference to the loaded class's module, qualname and `VERSION`. Module IDs must be unique for workflow assembly. The pipeline does not separately verify the class's `ID` against the reference; the executor verifies the runtime ID and version.
- **Compile-time configuration.** `CompilationContext.configuration` is the reconstructed non-secret registration configuration. The module owns any difference between that configuration and the `ModuleReference.configuration` it puts in its contribution.
- **Order is preserved.** The order of `BlueprintModule` entries is the order of module contributions. Core is last in the public API. Compilation does not reorder modules before assembly.
- **Sources are carried, not completed.** The blueprint carries the source bindings it was given. `validate_blueprint` checks uniqueness, and the data language checks that a source names a declared table; a table with no source is not rejected at blueprint validation.
- **Provenance.** `compile_workflow` attaches `provenance["compile"]["blueprint_fingerprint"]`. The fingerprint is the SHA-256 of `encode_blueprint(blueprint)` with sorted keys and compact separators. The encoded binding includes `debug_name`, so `debug_name` participates in this fingerprint. `../DESIGN_ISSUES.md` item 6 says the blueprint fingerprint removes it; the current code does not.
- **No concrete module knowledge.** `compile` imports the language and module protocol surfaces, never a concrete module or engine. The composition root supplies registrations. `create_build` and `compile_build` are the custom-language path that does not require the default distribution.
