# Authoring API reference

The reference states the exact author-facing signature, arguments, errors and
examples for the kg-build-system authoring API.

Use a concept page to learn what a declaration means, then use the matching
reference page for the exact name, argument and failure. The reference states
the rules; it does not repeat the explanation of why the model works that way.

## Reference pages

| Reference page | What it covers | Concept page |
| --- | --- | --- |
| [Declarations](declarations.md) | Fields, `Table[Asset]`, `Struct`, `ComputedStruct`, `TableGroup`, `StructTemplate` and options | [Data contracts](../concepts/data-contracts.md) |
| [Assets](assets.md) | `Asset`, options, layout, semantics, governance, `Table[Asset]`, `@asset_contract` and the generic source planner | [Assets](../concepts/assets.md) |
| [Expressions and selections](expressions.md) | Selections, `extract`, null policy, row effects, array and value operations, literals and Boolean composition | [Expressions](../concepts/expressions.md) |
| [Row sources](row-sources.md) | `row_source()`, `where`, `union`, `join`, `group_by`, `distinct`, `order_by` and generated shapes | [Row sources and grain](../concepts/row-sources.md) |
| [Projections](projections.md) | Pinning a source, `computed_field`, outputs and dependencies | [Projections](../concepts/projections.md) |
| [Topology declarations](topology.md) | `Node`, `Edge`, properties, categories, templates and endpoints | [Topology](../concepts/topology.md) |
| [Bindings](bindings.md) | `node_binding`, `edge_binding`, keys, properties and endpoint tokens | [Bindings](../concepts/bindings.md) |
| [Semantics](semantics.md) | `Annotation`, labels and descriptions | [Semantics and annotations](../concepts/semantics.md) |
| [Types](types.md) | Canonical types, nullability, property shapes and key rules | [Types and nullability](../concepts/types.md) |
| [Assets and ingest](ingest.md) | `AssetLayout`, the generic source planner, source checks and trust rules | [Assets](../concepts/assets.md) |
| [Generation](generation.md) | `@asset_contract`, generated packages and source nullability claims | [Data contracts](../concepts/data-contracts.md) |
| [Compile and execute](compile.md) | `create_blueprint`, `compile`, `execute`, runtime and report | [Compile, execute and outputs](../concepts/build-and-outputs.md) |
| [Planners and executors](planners-and-executors.md) | supplied planners and executors, configuration, kinds and composition | [Planners and executors](../concepts/planners-and-executors.md) |
| [Glossary](glossary.md) | The vocabulary used across the guide | [How a build works](../concepts/index.md) |

## How to read a signature

- Signatures use Python type syntax. Single-letter names such as `T`, `S` and
  `R` are type parameters; a default shown after `=` applies when the argument
  is omitted.
- A parameter marked `*` is keyword-only.
- `refused` means the framework raises at declaration, compile or build time;
  the error tables on each page give the message and the trigger.
- `Value` means a row-source value such as `SiteTable.row_source()`, not the
  declaration class `SiteTable`.
- A field declaration names a value type, never absence. A source `Table` or
  source `Struct` read is a `NullableSelection[T]`; a `Projection` output or
  `ComputedStruct` member follows its `computed_field` selection. The reference
  says when an operation removes or preserves a null.

## Import paths

| Surface | Import from |
| --- | --- |
| Declarations, selections, row sources and projections | `kg_build_system` |
| `compile`, `create_blueprint` and `execute` | `kg_build_system` |
| `BuildRuntime` and `WorkflowReport` | `kg_build_system` (also `kg_build_system.distribution`) |
| `WorkflowPlan`, `Step`, `StepId`, `OpeningId`, `ArtifactType`, `ArtifactPattern`, `InstructionKind` and the kernel protocols | `kg_build_system.kernel` |
| Representative types and canonical logical types | `kg_build_system` |
| Supplied planners and executors | `kg_build_system.distribution` |
| Generation contracts and commands | `kg_build_system.generation` |

## What to remember

- Read the concept page for meaning; read the reference page for the exact
  interface.
- Every declaration and selection is a typed authoring construct, not a schema
  document or a dictionary.
- Errors are quoted so they can be matched against the message the framework
  emits.

Start with [Declarations](declarations.md) for row shapes and [Assets](assets.md) for the logical source they name.
