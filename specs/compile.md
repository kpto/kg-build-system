# compile

## Responsibility

The `kg_build_system.compile` package owns the build blueprint aggregate, its codecs and validation, the compile-time module protocol, and the translation of authoring declarations and ordered module contributions into one workflow contract.

## Public interface

- `BuildBlueprint` is a frozen, slotted aggregate containing only compilation IR values:
  - `structs: tuple[StructIR, ...]`
  - `tables: tuple[TableIR, ...]`
  - `components: tuple[ComponentIR, ...]`
  - `projections: tuple[ProjectionIR, ...]`
  - `bindings: tuple[BindingIR, ...]`
  - `sources: tuple[SourceIR, ...] = ()`
  - `modules: tuple[BlueprintModuleIR, ...] = ()`
- Codec functions exported by `compile.interfaces`:
  - `encode_blueprint(value: BuildBlueprint) -> dict[str, Any]`
  - `decode_blueprint(value: Mapping[str, Any]) -> BuildBlueprint`
  - `blueprint_json(value: BuildBlueprint, *, indent: int | None = None) -> str`
  - `blueprint_from_json(value: str | bytes | bytearray) -> BuildBlueprint`
  - `validate_blueprint(blueprint: BuildBlueprint) -> None`
- Compiler functions exported by `compile.interfaces`:
  - `create_blueprint(*, bindings=(), sources=(), modules=(), namespace_path=None) -> BuildBlueprint`
  - `configure_blueprint_modules(blueprint: BuildBlueprint, modules: Sequence[CompileModuleRegistration[Any]]) -> BuildBlueprint`
  - `compile_workflow(*, blueprint: BuildBlueprint) -> WorkflowContractIR`
- Compile-time module protocols in `compile.interfaces`:
  - `CompilationContext[ConfigT](blueprint, module_id, configuration)`.
  - `ModuleCompiler.compile(context: CompilationContext[Any]) -> WorkflowContribution` (async).
  - `CompilableModule` with `ID: ClassVar[str]`, `VERSION: ClassVar[str]`, `CONFIGURATION_TYPE: ClassVar[type[Any]]`, and async `create_compiler(context) -> ModuleCompiler`.
  - `CompileModuleRegistration[ConfigT]` with `module_class` and `configuration`.
- IR boundary types carried by a blueprint:
  - `StructIR` and `TableIR`: `symbol_id`, `name`, `fields: tuple[FieldIR, ...]`, optional description and annotations.
  - `FieldIR`: `name`, `logical_type`, optional description and annotations.
  - `ProjectionIR`: `symbol_id`, `name`, `fields: tuple[ProjectionFieldIR, ...]`, optional description and annotations, and a required non-null `row_source`.
  - `ComponentIR` and `PropertyIR` from `topology.ir`.
  - `NodeBindingIR` and `EdgeBindingIR`: `symbol_id`, `component`, `build_key`, `properties: tuple[tuple[str, ExpressionIR], ...]`, optional `debug_name`, annotations, `kind`, and optional `row_source`; an edge adds `source_build_key`, `target_build_key`, and optional `source_node`/`target_node`.
  - `SourceIR`: `symbol_id`, `table`, `location`, `format` (`"csv" | "json" | "parquet"`), optional `credential_reference`, optional `version`, annotations.
  - `BlueprintModuleIR`: `module_id`, `module_import`, `module_qualname`, optional `configuration` as frozen JSON.
- Codec and validation errors are `ValueError`. Compiler reconstruction raises `TypeError`, `ValueError`, `RuntimeError`, or `ModuleNotFoundError` when a module cannot be reconstructed or a matching contract cannot be produced.

## Boundaries

- Surfaces: `compile.ir` is the blueprint; `compile.interfaces` is the internal interface; the package has no author-facing surface.
- Allowed dependencies: the `interfaces` and `ir` surfaces of `types`, `annotations`, `expressions`, `table`, `topology`, `binding` and `workflow`, plus the `_frozen_json` kernel.
- `compile` may call workflow assembly and contract creation; `workflow` must not import `compile`.
- Must not import `modules`, concrete module implementations, `engines`, `code_generation`, `api`, or `cli`.
- A module compiler receives the blueprint and its own reconstructed registration configuration. It never receives authoring Python classes, a runtime connection, or executor state.
- The workflow contract is the only value handed from compilation to execution. `compile` may attach the blueprint and its fingerprint as opaque provenance; execution never reads them as instructions.

## Current decisions

- **The blueprint is IR, not authoring state.** Every field of `BuildBlueprint` is a frozen IR value. No declaration class, expression wrapper, binding object, connection, or module instance is stored.
- **Validation is mandatory at both ends.** `blueprint_json` validates before encoding; `decode_blueprint` validates after decoding. `create_blueprint`, `configure_blueprint_modules`, and `compile_workflow` validate before use.
- **No schema version.** A blueprint is identified by its content; the decoder rejects unknown fields and never negotiates a version.
- **Codec shape.** Encoding emits `structs`, `tables`, `components`, `projections`, `bindings`, `sources`, and `modules`. JSON is sorted by key and compact unless an indent is requested. Decoding requires a mapping, non-empty strings where the schema requires text, arrays where it requires arrays, known component kinds, known binding kinds, known source formats, and a row source on every projection.
- **Blueprint invariants.** Validation requires at least one graph component and at least one graph binding, and enforces:
  - unique symbol IDs across structs, tables, components, projections, bindings, and sources;
  - unique struct names within a module, unique table names, unique component names, unique projection names, unique logical source names across tables and projections, and unique module IDs;
  - unique field names per declaration and unique property names per component;
  - an edge declares both endpoints and names known components; a node declares neither;
  - a parent names a known abstract component of the same kind, and the parent chain is acyclic;
  - every `RowScanIR` names a known table or projection; every field reference names a known logical source and a known top-level field;
  - `expand` has one array argument and returns its item type; join keys have equal scalar logical types; `group_by` has at least one uniquely named identifier key with a scalar expression; `order_by` has at least one key; projection dependencies are acyclic;
  - source-bound table names are unique and name a declared table;
  - a binding targets a concrete component of its own kind; an abstract target is rejected;
  - an edge binding's supplied endpoint is a concrete node that equals or descends from the declared endpoint;
  - a binding maps every declared component property exactly once with a compatible logical type;
  - binding keys are non-null scalar expressions.
- **Compile mode: declarations.** `compile.compiler.create_blueprint` accepts explicit `bindings` and `sources`, a `namespace_path`, or both. Namespace mode imports every module under the path and collects module-level `NodeBinding`, `EdgeBinding`, and `BoundSource` values. Explicit and discovered values are deduplicated by object identity. Declarations are resolved from the expressions and row sources the bindings and projections actually use; unrelated declarations do not enter the blueprint.
- **Compile mode: public API.** `kg_build_system.create_blueprint(*, modules, namespace_path=None, bindings=None, sources=None)` and `kg_build_system.compile(*, modules, namespace_path=None, bindings=None, sources=None, blueprint=None)` are the composition modes. `modules` is required and core is appended after the supplied modules. `blueprint` cannot be combined with `namespace_path`, `bindings`, or `sources`. `bindings` and `sources` are supplied together. With no source mode, the caller's file directory is the namespace path.
- **Module composition.** A blueprint records each module registration as `BlueprintModuleIR` with the module ID, import module, class qualname, and frozen registration configuration. Compilation imports the class, reconstructs the configuration with `CONFIGURATION_TYPE(**configuration)`, verifies the static ID, calls `create_compiler`, and requires the returned contribution's module ID to match. The contribution reference is then rewritten to the actual import module, class qualname, and `VERSION`. Module IDs must be unique. A module class must declare a non-empty string `ID`; a class defined inside a function (`"<locals>"` in its qualname) is rejected.
- **Compile-time configuration.** `CompilationContext.configuration` is the reconstructed non-secret registration configuration. The module owns any difference between that configuration and the `ModuleReference.configuration` it puts in its contribution.
- **Order is preserved.** The order of `BlueprintModuleIR` entries is the order of module contributions. Core is last in the public API. Compilation does not reorder modules before assembly.
- **Sources are complete.** Compilation requires every table named by the blueprint to have a bound source. A missing binding is a `ValueError` naming the tables.
- **Provenance.** `compile_workflow` attaches `provenance["compile"]` containing the encoded blueprint and a `blueprint_fingerprint`. The fingerprint is the SHA-256 of the canonical encoded blueprint with binding `debug_name` values removed, so a debug rename does not change it. The workflow contract's own `workflow_fingerprint` covers only the workflow IR.
- **No concrete module knowledge.** `compile` imports the module protocol and the declaration IR and authoring packages, never a concrete module or engine. The composition root supplies registrations.
