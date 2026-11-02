# Overview

## Responsibility

The framework turns typed Python declarations, graph bindings and physical source bindings into an immutable workflow contract, then executes that contract to produce graph artifacts.

## Public API

- `kg_build_system` lazily exports the authoring vocabulary:
  - declarations: `Table`, `Struct`, `ComputedStruct`, `Projection`, `TableGroup`, `Field`, `field`, `computed_field`, `projection_field`, `bind_source`, `DataSourceConfig`, `InputFormat`;
  - expressions and selections: `value_expression`, `ValueSelection`, `NullableSelection`, `ArraySelection`, `StructSelection`, the typed expression families and `all_of`/`any_of`;
  - topology: `Node`, `Edge`, `AbstractNode`, `AbstractEdge`, the templates and options, `property`, `PropertySlot`, `Endpoint`, `endpoint`;
  - bindings: `node_binding`, `edge_binding`, `NodeValues`, `EdgeValues`, `BindingOptions`;
  - types: `Array`, `Nullable`, `NullableType`, `ArrayType`, `CustomDataType`, `Shape`, `Date`, `Time`, `Timestamp`, `Uuid`;
  - workflow: `build`, `BuildRuntime`, `WorkflowReport`.
- Composition functions:
  - `create_blueprint(*, modules, namespace_path=None, bindings=None, sources=None) -> BuildBlueprint`
  - `compile(*, modules, namespace_path=None, bindings=None, sources=None, blueprint=None, engine=None) -> WorkflowContractIR`
  - `build(contract, runtime=None, *, output_directory=Path("build"), working_directory=Path("_workdir"), temporary_directory=None, monitor=None) -> WorkflowReport`
- `modules` is required by the public API; the core module is appended after the supplied modules. `bindings` and `sources` are supplied together. `blueprint` is exclusive with the other inputs. With no explicit input, the calling file's directory is the namespace path.
- `kg_build_system.compile` is the composition function. The importable package `kg_build_system.compile` remains available for `BuildBlueprint` and `compile.models`; importing the package replaces its module class with a callable that delegates to the composition function.

## Internal interface

- `kernel` is the shared root and has no `interfaces.py` or `ir.py`; `kernel.__init__` is its internal interface:
  - `Language(name, requires)` with `collect(namespace)`, `lower(declarations, context)`, `validate(ir)`, `encode(ir)`, `decode(value)`;
  - `Namespace.values()` and `LanguageContext.part(name)`;
  - `Module(ID, VERSION, CONFIGURATION_TYPE)` with async `create_compiler(context)` and `create_executor(context)`; `ModuleCompiler.compile(context)` and `ModuleExecutor.handle(context)`/`handle_disrupted(context)`;
  - `BuildIR.parts`, `BuildIR.part(name)`, `BuildIR.part_as(name, type)`; `Build` wraps one `BuildIR`;
  - `Registry(languages)` validates unique names and known dependencies, orders languages by `requires`, and builds one named part per language;
  - `CompilationContext(build, module_id, configuration, blueprint=None, engine=None)`;
  - contract values: `ArtifactType`, `Input`, `Output`, `Publication`, `WorkflowStep`, `ModuleReference`, `RuntimeFieldDefinition`, `ModuleDefinition`, `WorkflowContribution`, `TakenInput`, `StepStatus`, `Failure`, `Artifact`, `StepOutcome`, continuable/disrupting inputs, defined steps and contributions, `Connection`, execution contexts, `PublishedArtifact`, `type_matches`.
- Languages contributed by domain packages:
  - `data` (`TableLanguage`): tables, structs, projections and bound sources;
  - `topology` (`TopologyLanguage`): node and edge components;
  - `binding` (`BindingLanguage`): node and edge bindings; it requires `data` and `topology`.
- `expressions` contributes operation specifications to expression construction; it is not a language.
- `modules.core` is a module, not a domain package: it compiles the blueprint into source, row-source, projection, binding and aggregation steps, and executes their instructions.
- `engines` owns lowering from engine-neutral plans to SQL and owns the DuckDB relation service. `code_generation` uses the same engine metadata as an observer only.

## IR

- `BuildIR` is an immutable mapping of language name to one lowered part. The default parts are `data` (`DataIR`), `topology` (`tuple[ComponentIR, ...]`) and `binding` (`tuple[BindingIR, ...]`).
- `BuildBlueprint` is the compatibility aggregate assembled from the three parts: structs, tables, components, projections, bindings, sources and module references.
- `WorkflowContractIR` is the executable contract: workflow IR, `workflow_fingerprint` and optional provenance. It carries no schema version.
- Each domain package owns its IR slice: `types.ir`, `annotations.ir`, `expressions.ir`, `table.ir`, `topology.ir`, `binding.ir`, `relational.ir`, `workflow.ir`, `compile.ir`, `modules.ir`, `code_generation.ir`, `engines.ir`.

## Boundaries

Allowed package edges:

```text
types -> (none)
annotations -> (none)
expressions -> types, _frozen_json
topology -> types, annotations, expressions, _frozen_json, kernel
table -> types, annotations, expressions, _support, _frozen_json, kernel
relational -> expressions, table
binding -> types, annotations, expressions, table, topology, _frozen_json
compile -> kernel, table, topology, binding, workflow
engines -> types, expressions, relational, table, _relations, _frozen_json
workflow -> kernel, engines, _relations, _frozen_json
modules -> kernel, types, annotations, expressions, table, topology, binding,
            relational, engines, compile, workflow, _frozen_json
code_generation -> types, engines
cli -> code_generation
kernel -> (none)
```

- `_frozen_json`, `_relations` and `_support` are shared kernel modules with no owner, no IR and no authoring surface.
- Another package imports a declared interface surface, never a private implementation module. Nested package `__init__` files are the exception for the `modules.core` vocabulary used by the composition root.
- `workflow` never imports `compile`; the dependency is `compile -> workflow`. `compile` never imports concrete modules or engines. `code_generation` never imports `compile`, `workflow`, `modules` or `api`. `cli` imports only `code_generation`.
- IR values contain no declaration classes, expression wrappers, binding values, connections, module instances or live services.

## Current decisions

- The framework is experimental. The API is not stable; breaking changes are expected. There is no schema negotiation or migration path; artifacts are content-addressed and a contract is identified by its fingerprint.
- **Two phases.** `compile` validates declarations and freezes one workflow contract. `build` executes that contract in dependency order, propagates failed or skipped inputs and verifies each returned artifact against its declared output type.
- **Three composition modes.** Namespace discovery, explicit bindings plus sources, or a prebuilt blueprint. `api.create_blueprint` and `api.compile` compose the core module last.
- **The kernel is domain-agnostic.** It knows languages, parts, modules, steps, artifacts and connections. It knows no table, topology, expression, graph or SQL vocabulary.
- **The languages lower once.** Each language turns declarations into one named part; the registry orders languages by `requires`; the blueprint is assembled from the parts, not from authoring state.
- **One file per operation.** Each expression operation has one `expressions/operations/<name>.py` specification and one `engines/duckdb/operators/<name>.py` lowering. Adding a custom operation is one spec plus one lowerer; no dispatcher branch is edited.
- **The core module is mandatory.** It materialises source, row-source, projection and binding relations and aggregates graph records. Supplied target and operator modules consume those artifacts.
- **One relational engine supplies the facts.** DuckDB scans, widens and returns values against the canonical type vocabulary; targets may narrow what they store and refuse at compile rather than coerce.
- **Compatibility is explicit.** The effective API also supports unpinned `Projection` with `projection_field`, `where_present`, `rows=TableClass`, `compile.models`, `workflow.models` and `modules.interfaces`. These are compatibility obligations; where they conflict with the clean model the conflict is recorded in `../DESIGN_ISSUES.md`.
- **Two review surfaces.** Author-facing semantics live in `../docs/`; internal interfaces live here. They may cover the same subject for different readers.
