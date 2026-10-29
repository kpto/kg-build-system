# Framework state

This is a briefing for you as the reviewer of internal interfaces. It states the
current model, the interface map, and the decisions that still need your
attention.

## At a glance

- The framework is experimental; the API is not stable.
- Current verification: **508 passed, 6 skipped, 420 subtests**, pyright **0
  errors**, docs build **strict**.
- Every domain subpackage now has three explicit surfaces: `__init__.py` for the
  graph author, `interfaces.py` for other subpackages, and `ir.py` for
  compilation data. A contract test enforces that no subpackage imports another
  subpackage's implementation module.
- Schema versions are gone from the blueprint, the workflow contract and the
  meta-graph document. Artifacts are content-addressed.
- Workflow execution contexts no longer carry a live service. The executor
  receives its context and `ExecutionServices` as separate arguments.
- The remaining model questions are the `ComputedStruct` type-witness rule, the
  meaning of generated nullability, and whether `table` should split into
  declarations and row-source algebra.

## Authoring model

- **Fields.** `field()` declares a source-backed field; `computed_field(expr)`
  declares an expression-backed field. A source field reads as a nullable
  selection whatever its declared type; `Field[T | None]` is stripped to `T`.
  A computed field carries its expression's type.
- **Records.** `Table` is a source relation; `Struct` is a source nested record;
  `ComputedStruct` is an expression-built nested record; `Projection` is a named
  relation with a required row-source pin; `TableGroup` is a merge input, not a
  row source.
- **Selections.** `extract` reads a struct member. Value transforms are
  `default_to`, `transform_items`, `drop_null_items`, `sort`, `unique`, `concat`,
  `at`, `slice`. Row effects are one-shot through `alter_rows()`:
  `expand`, `drop_null`, `drop_if`.
- **Row sources.** `Table.row_source()` and `Projection.row_source()` start a
  relation. `where`, `union`, `join`, `group_by`, `distinct` and `order_by`
  derive one. `join` produces `{on, left, right}`; `group_by` produces
  `{by, members}`. `rows=` accepts only a row-source value.
- **Bindings.** `node_binding` and `edge_binding` take either direct expressions
  or `rows=` plus `bind=`. The callable receives a symbolic shape instance, not a
  declaration class.
- **Topology.** `Node`/`Edge` hierarchies with `Abstract*` categories,
  templates, `property()` slots, and `endpoint()` tokens for abstract sides.
- **Build.** `compile` produces a workflow contract; `build` executes it.
  Modules contribute compiler and executor steps; the core module materialises
  relations and graph records.

## Surfaces

| Package | Responsibility | Authoring (`__init__`) | Internal (`interfaces`) | IR |
| --- | --- | --- | --- | --- |
| `types` | Logical type vocabulary | markers, units, representative classes | normalization, validation, codecs | logical types |
| `annotations` | Portable annotations | `Annotation`, labels | payload and tuple helpers | `AnnotationIR` |
| `expressions` | Selections and expressions | typed selections and factories | domain model, operations, codecs | expression tree |
| `table` | Declarations and row sources | `Table`, `Struct`, `Projection`, bindings | declarations, row-source algebra, plan codecs | declarations and row plans |
| `topology` | Graph declarations | `Node`, `Edge`, templates, slots | introspection helpers, node-side base | components and properties |
| `binding` | Graph bindings | factories and values | binding model and IR codec | binding IR |
| `relational` | Relation planning | none | planner and plan values | relation plan |
| `compile` | Compilation | none | blueprint, codecs, module protocol | blueprint |
| `workflow` | Assembly and execution | `build`, `BuildRuntime`, `WorkflowReport` | workflow model, protocols, services, codec | contract IR |
| `engines` | DuckDB execution | none | lowering, SQL types, metadata, relation service | SQL type values |
| `modules` | Build stages | registration and supplied modules | module protocols | module instruction IR |
| `code_generation` | Edit-time generation | request and run surface | provider contract | generated declarations |
| `cli` | `kbs` entry point | `main` | none | none |

Shared kernel: `_frozen_json`, `_relations`, `_support`. They have no owner, no IR
and no authoring surface.

## Dependency graph

```text
types -> (none)
annotations -> _frozen_json
expressions -> types, _frozen_json
topology -> types, annotations, expressions, _support
table -> types, annotations, expressions, _support
relational -> expressions, _relations
binding -> types, annotations, expressions, table, topology
compile -> types, annotations, expressions, table, topology, binding, workflow
engines -> types, expressions, relational, table, _relations
workflow -> engines, _relations
modules -> types, annotations, expressions, table, topology, binding,
            relational, engines, compile, workflow
code_generation -> types, engines
cli -> code_generation
```

Cross-package imports target `interfaces` or `ir`, never an implementation
module. The contract test walks every relative import and fails on a private
target. Nested package `__init__` files are the only exception, for the
`modules.core` vocabulary the composition root uses.

## What changed in the interface model

- **One surface per audience.** Authoring names are no longer mixed with
  compilation models. `Nullable`, `Binding`, `BuildBlueprint`,
  `WorkflowContractIR`, `ExpressionNode`, `FieldMetadata`, `RowSemantics` and the
  protocol classes moved out of the authoring facades.
- **Protocols are explicit.** `ModuleCompiler`, `CompilableModule`,
  `CompilationContext`, `ModuleExecutor` and `ExecutableModule` are reachable
  through `compile.interfaces` and `workflow.interfaces`.
- **The IR is owned per package.** `compile.ir` owns the blueprint; every
  package owns its own IR slice. No `.ir` value imports an authoring class.
- **IR is anaemic.** `RowScanIR.filters`, `struct_type_key`,
  `walk_expression_ir`, `RowSemantics.effects`, `from_effects`,
  `OperationExpression.with_arguments` and `Annotation.serialise` became
  functions beside the data.
- **Execution context is data.** `ExecutionContext` and its siblings no longer
  hold `ExecutionServices`; the runtime passes services to the executor.
- **DuckDB is behind the engine interface.** The relation service and macro
  setup moved from `workflow` to `engines`. `workflow.services` states protocols
  and in-process storage only.
- **No schema versions.** Blueprint, workflow contract and meta-graph document
  no longer carry one; unknown JSON fields are refused instead.

## Decisions still open

1. **`table` split.** The package still owns both declarations and the row-source
   algebra. `table.interfaces` exposes both, and six packages depend on it.
   Decide whether to split `row-source` into its own subpackage. The split is a
   model change: the row-source plan helpers read declared field metadata.
2. **`ComputedStruct` as a field type.** Its member expressions are type
   witnesses when it types a source field; member reads come from the carrier.
   Decide whether that is intended or whether a computed struct must not type a
   source-backed field.
3. **Generated nullability.** A generated package records source nullability in
   its header and digest, but top-level source access stays nullable and the
   blueprint stores only the value type. Decide whether generation should make a
   contract claim or remain a note.
4. **Contract durability.** `build` requires the exact module `VERSION`; there is
   no compatibility or migration path. Decide whether that is the intended limit.
5. **Aggregates and computed structs.** `group_by` collects rows but has no
   `count`/`sum`/`having`. `ComputedStruct` has no public constructor. Both are
   known limits, not hidden gaps.
6. **Generated shapes.** `join`/`group_by` result shapes are `Any` at edit time
   and typed at runtime. Decide whether that is acceptable or whether generated
   shapes should be typed.
7. **Relation reuse.** No compile-time reuse rule exists; non-scan plans are
   materialised once and shared by their consumers. The open question is whether
   reuse should be a compile-time fan-out rule.

## Documentation

The author-facing guide is in `docs/`, structured as Get started, Concepts,
How-to guides and Reference. `philosophy.md` carries the values; each concept
page is paired with a precise reference page. The guide states the current
behavior, including the former contradictions: the row-source algebra and
joined/grouped projections, `ComputedStruct` as a type witness on a carrier,
generated nullability as a source claim, non-null group keys, text-only join
`equals`, exact module-version durability, and module-level producer conflicts.

The internal interface map and the spec set stay in `specs/`.

## Verification

```console
uv run pytest -q
uv run pyright
uv run mkdocs build --strict
```
