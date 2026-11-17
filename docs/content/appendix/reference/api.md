---
title: API surface
summary: The lazy facade, its generated import groups, and the modules behind the public names.
section: reference
order: 10
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/__init__.py
  - kg_build_system/api.py
  - kg_build_system/kernel/__init__.py
  - kg_build_system/distribution/__init__.py
  - kg_build_system/generation/__init__.py
---

`kg_build_system` is the facade you import. It is lazy: importing the package loads neither a language nor the composition root. Names are declared literally in `__all__`, mapped to their defining modules by `_GROUPS`, and loaded on first access by `__getattr__`.

## Surface

| Import | Use |
| --- | --- |
| `kg_build_system` | Authoring names, `compile`, `create_blueprint`, `execute`, `GraphBlueprint`, `BuildRuntime`, `WorkflowReport`. |
| `kg_build_system.kernel` | Kernel protocols, workflow values and the `Toolchain` composition value: `Language`, `Linker`, `Planner`, `StepExecutor`, `Runtime`, `WorkflowRuntime`, `Toolchain`, `WorkflowPlan`, `Step`, `Instruction`, `Key`, `SymbolRef`, `RuntimeConfiguration`. |
| `kg_build_system.distribution` | Planners and executors, plus `GraphBlueprint`, `create_blueprint` and typed references. |
| `kg_build_system.generation` | Generation names: `asset_generation`, discovery, `generate`, `watch`, sessions, results and errors. |

The canonical path is `create_blueprint` → `compile` → `execute`: create an immutable `GraphBlueprint`, compile it to a `WorkflowPlan`, then execute it to a `WorkflowReport`. `BuildRuntime` carries execution settings; `WorkflowReport` carries the published artifacts and failures. See [Documents](/appendix/reference/documents) for the plan and report shapes, and [CLI](/appendix/reference/cli) for the console command that writes declarations before this path.

This table is the **default facade**. The kernel protocols are exported from `kg_build_system.kernel`; a custom language, planner or executor is a value passed to a `Toolchain`; a provider is added to the runtime. None is a name in this table. See [Extend the toolchain](/book/part-4/01-the-kernel-and-extension) and [SPEC-013](/appendix/spec/extension). `SqlEmitter` is a distribution service protocol, not a facade name or a kernel protocol: core planners consume it, and a new engine supplies an implementation.

## Details

<!-- BEGIN GENERATED:api -->
| Defining module | Public names |
| --- | --- |
| `kg_build_system.api` | `DEFAULT_TOOLCHAIN`, `compile`, `create_blueprint`, `default_languages`, `default_toolchain`, `execute` |
| `kg_build_system.distribution.interpreter` | `GraphBlueprint` |
| `kg_build_system.distribution.languages.annotations` | `Annotation`, `EdgeLabel`, `NodeLabel` |
| `kg_build_system.distribution.languages.asset` | `Asset`, `AssetAuthority`, `AssetGovernance`, `AssetLayout`, `AssetLicense`, `AssetOptions`, `AssetProfile` |
| `kg_build_system.distribution.languages.binding` | `BindingOptions`, `EdgeBinding`, `EdgeValues`, `NodeBinding`, `NodeValues`, `edge_binding`, `node_binding` |
| `kg_build_system.distribution.languages.data` | `ComputedStruct`, `Contract`, `Definition`, `DerivedRowSource`, `DeclaredValue`, `Field`, `FieldDefinition`, `GroupByKeys`, `Grain`, `NullableComputedField`, `OrderByKey`, `RelationOperation`, `RelationOperationSpec`, `ScalarValue`, `JoinHow`, `DerivedRelation`, `DerivedRelationOptions`, `RelationRowSource`, `RowSource`, `Stage`, `StageOptions`, `StageRowSource`, `Struct`, `StructOptions`, `StructOptionsTemplate`, `StructTemplate`, `SourceRelation`, `SourceRelationGroup`, `SourceRelationGroupOptions`, `SourceRelationOptions`, `computed_field`, `field` |
| `kg_build_system.distribution.languages.expressions` | `ArrayRowEffects`, `NullableArrayRowEffects`, `NullableRowEffects`, `NullableSelection`, `Pair`, `RowEffects`, `Selection`, `LiteralValue`, `DEFAULT_OPERATIONS`, `ArgumentSpec`, `Operation`, `OperationHandle`, `OperationRegistry`, `OperationSpec`, `ParameterSpec`, `RowEffectSpec`, `all_of`, `any_of`, `value_expression` |
| `kg_build_system.distribution.languages.graph` | `Graph`, `GraphOptions` |
| `kg_build_system.distribution.languages.meaning` | `Claim`, `Limitation`, `Meaning`, `Omitted`, `Purpose`, `is_omitted` |
| `kg_build_system.distribution.languages.topology` | `AbstractEdge`, `AbstractNode`, `Edge`, `EdgeOptions`, `EdgeOptionsTemplate`, `EdgeRoot`, `EdgeTemplate`, `Endpoint`, `Node`, `NodeOptions`, `NodeOptionsTemplate`, `NodeTemplate`, `PropertySlot`, `endpoint`, `property` |
| `kg_build_system.distribution.model.public.manifest` | `Blueprint`, `Workflow` |
| `kg_build_system.distribution.model.public.runtime` | `BuildRuntime` |
| `kg_build_system.kernel.model.public.runtime` | `Logger`, `WorkflowReport` |
| `kg_build_system.kernel.model.public.types` | `Array`, `ArrayType`, `CustomDataType`, `Date`, `Nullable`, `NullableType`, `Shape`, `Time`, `Timestamp`, `Uuid`, `BOOL`, `INT`, `FLOAT`, `STR`, `DATE`, `TIME`, `TIMESTAMP`, `UUID` |
| `kg_build_system.kernel.model.public.workflow` | `JsonValue`, `WorkflowPlan` |
<!-- END GENERATED:api -->

The block above is generated from `_GROUPS` and names each defining module. Import the name from `kg_build_system`; the module path is evidence, not the authoring import. Do not edit the block by hand.

The lazy loader is small and literal:

- `__all__` is a list of public names, not a computed scan.
- `_GROUPS` maps each defining module suffix to the names it owns.
- `__getattr__` imports that one module, reads the attribute, caches it on the package module with `setattr`, and returns it.
- `__dir__` returns the sorted `__all__`.

Importing `kg_build_system` therefore does not create `DEFAULT_TOOLCHAIN`; that value is built when the `api` group is first loaded. Importing a submodule directly, such as `kg_build_system.api`, does import that module and its composition root.

A public signature names language DTOs. `GraphBlueprint` is the public handle, but its `graph`, `data`, `assets`, `bindings`, `operations` and `graph_declaration` fields are `GraphPartDTO`, `DataPartDTO`, `AssetPartDTO`, `BindingDTO`, `ExpressionsPartDTO` and `GraphDeclarationDTO`. Those DTO types are not exported by the facade. This is a known limit of the signature: treat the fields as read-only and pass the blueprint back to `compile` rather than rebuilding it from the DTO classes.

For the vocabulary around these names, use [Glossary](/appendix/reference/glossary). For the step from a blueprint to a plan, use [Blueprint](/book/part-3/01-linking-and-blueprint).
