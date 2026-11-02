# Architecture

This is the implementation contract for the clean reimplementation. The legacy
tree is at `legacy/kg_build_system`; it is reference only.

## Kernel

`kg_build_system.kernel` is the only domain-agnostic package. It imports no
other framework package.

| Name | Responsibility |
| --- | --- |
| `Language` | collect authoring declarations, lower them to one named IR part, validate, encode/decode |
| `Module` | compile against the frozen build, execute contract steps |
| `BuildIR` | immutable named parts, one per language |
| `Registry` | validate names and language dependencies, order languages, compose modules and engine |
| `Build` | run languages, freeze `BuildIR`, run module compilers, assemble the contract |
| `CompilationContext` | build, module id, configuration, blueprint view, engine |
| `contract` | artifact types, steps, contributions, execution contexts, outcomes |

The kernel owns no table, topology, expression, SQL or graph knowledge.

## Surfaces

Every package states three surfaces:

- `__init__.py` — public API: domain model, authoring names, methods.
- `interfaces.py` — internal API: domain values, protocols, functions.
- `ir.py` — IR: DTOs and their serialise/deserialise functions.

Models are frozen data. Behaviour lives in functions or services beside them.
No model holds a live process, connection or engine.

## Packages

| Package | Public | Internal | IR |
| --- | --- | --- | --- |
| `kernel` | protocols, build pipeline | contract values | contract IR where needed |
| `types` | markers, units, representative classes | logical type algebra, normalization | type DTOs + codec |
| `expressions` | expression and selection API | operation specs, selection primitives | expression DTOs + codec |
| `table` | `Table`, `Struct`, `Projection`, `Field`, sources | declaration access, row-source algebra | data DTOs + row-source plan |
| `topology` | `Node`, `Edge`, categories, templates, properties | declaration access, endpoint rules | component DTOs |
| `binding` | `node_binding`, `edge_binding`, values | binding model, validation | binding DTOs |
| `relational` | none | engine-neutral plans, planner | relation plan DTOs |
| `engines` | none | engine protocol | engine type DTOs |
| `compile` | compatibility surface | pipeline, blueprint assembly | `BuildBlueprint` |
| `workflow` | `build`, runtime, report | contract assembly, executor, services | workflow contract IR |
| `modules` | registration, supplied modules | module protocol | module instruction DTOs |
| `code_generation` | request/run surface | provider contract | generated declaration DTOs |

## Languages

- `table` is the `data` language. It collects `Table`, `Struct`, `Projection`
  classes and `BoundSource` values.
- `topology` is the `topology` language. It collects `Node` and `Edge` classes.
- `binding` is the `binding` language. It requires `data` and `topology`.
- `expressions` contributes operation specs, not declarations.

`BuildBlueprint` is a compatibility aggregate assembled from the `data`,
`topology` and `binding` parts. Modules may read `context.blueprint` (legacy) or
`context.build.part(...)` (kernel).

## Operations

Each operation has one file in `expressions/operations/` and one lowering file in
the engine. An operation spec states name, arity, parameters, result type and row
effect. The expression IR stores only name, arguments, parameters and logical
type. The engine registry is keyed by the same name. A custom operation is one
spec plus one lowerer; no dispatcher edits.

## Compatibility (Open Targets KG)

The effective API includes the older authoring forms:

- `Projection` without a pin and `projection_field(...)`.
- `pick(...)`, `where_present()`, `drop_null_items()`, `expand()`, `.append(...)`.
- `node_binding(rows=TableClass, ...)` as well as a row-source value.
- `value_expression`, `Nullable`, `NullableType`, `ArrayType`, `STR`, `FLOAT`.
- `BuildBlueprint` at `compile.models`.
- `workflow.models` and `modules.interfaces` module contract names.
- `code_generation.generation` and `code_generation.builtins`.

These are compatibility obligations, not the preferred model. Where they conflict
with the cleaner model, the conflict is recorded in `DESIGN_ISSUES.md`.
