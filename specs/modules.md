# Modules

## Responsibility

The `modules` package owns the module registration surface, the core graph
records module, the operator modules and the supplied target modules.

## Public API

- From `kg_build_system.modules`: `register_module`, `ModuleRegistration`,
  `ModuleRegistrationConfiguration`, and the supplied module classes and
  configurations:
  `CollapseExactDuplicatesModule`, `MergeCompatibleFactsModule`,
  `RejectConflictingNonNullValuesModule`, `FileModule`, `MetaGraphModule`,
  `Neo4jModule`, with their configuration types.
- `register_module(module_class, configuration=None)` returns a registration.
  With no configuration it constructs `module_class.CONFIGURATION_TYPE()`.
- The module class interface is the kernel protocol:
  `ID`, `VERSION`, `CONFIGURATION_TYPE`, async `create_compiler(context)` and
  `create_executor(context)`. A compiler implements `compile(context)` and
  returns a `WorkflowContribution`; an executor implements `handle(context)`
  and `handle_disrupted(context)`.
- `CompilationContext` exposes `build`, `blueprint` (the compatibility graph
  aggregate), `module_id`, `configuration` and `engine`.
- `ExecutionContext` exposes the module definition, step, ids, variables,
  resolved runtime configuration, inputs and `services`.

## Internal interface

`modules.interfaces` exports the registration values, `Module`, `ModuleCompiler`,
`ModuleExecutor`, and `module_configuration_json`.
`modules.ir` aggregates the module instruction IR.

Supplied modules:

| Module | Role |
| --- | --- |
| `CoreModule` | materialise source, row-source, projection and binding relations; aggregate graph records |
| `FileModule` | write JSON Lines graph records |
| `MetaGraphModule` | write the meta-graph document and HTML |
| `Neo4jModule` | write a Parquet import bundle and admin script |
| `CollapseExactDuplicatesModule` | one record per component identity |
| `MergeCompatibleFactsModule` | merge parallel facts for selected components |
| `RejectConflictingNonNullValuesModule` | report conflicting non-null values |

Core artifact vocabulary is `core/graph.<kind>.<component>`,
`core/binding.<symbol>`, `core/data.table.<name>`,
`core/data.projection.<name>` and `core/data.row_source.<key>`.

## IR

`modules.ir` contains the core instruction documents (`source_relation`,
`relation`, `aggregate`) and the target instruction documents. The core
instructions keep the legacy `action`-discriminated JSON shape, but are frozen
dataclasses with explicit encode/decode. Targets own their own instruction IR
under `modules.targets.*.ir`.

## Boundaries

- `modules` may import the `interfaces`/`ir` surfaces of every domain package,
  `compile`, `workflow` and `engines`.
- `compile` and `workflow` never import a concrete module; the composition root
  and `modules` own the downward dependency.
- A module compiler receives the blueprint or build; a module executor receives
  runtime services. Neither imports authoring classes except the compatibility
  `MergeCompatibleFactsModuleConfiguration`, which resolves component classes.
- `modules.targets` may import `core` artifact vocabulary but not core
  implementation.

## Current decisions

- Module IDs and versions are part of the contract. `build` requires the exact
  `VERSION`; there is no migration path.
- Registration configuration is serialisable and non-secret; runtime fields are
  supplied by `BuildRuntime.module_configuration` and validated before any step.
- `core` is a module, not a privileged pipeline. It consumes only the blueprint
  it is handed and emits ordinary workflow steps.
- Target modules publish summaries and write their own files; they do not
  mutate graph records.
- One module contributes steps, variables and a module definition. One step
  produces artifacts; publications are outputs with no in-workflow reader.
- Custom module authoring is framework-internal: a project normally composes the
  supplied modules. A new module implements the kernel protocol and registers
  through `register_module`.
