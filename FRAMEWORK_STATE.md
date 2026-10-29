# Framework state

This is a briefing for you as the reviewer of internal interfaces. It is not a
specification and not a history. It states the current model, the interface map,
the spec corpus, and the decisions that need your attention.

## At a glance

- The framework is experimental; the API is not stable.
- Current verification: **504 passed, 6 skipped, 422 subtests**, pyright **0
  errors**, docs build **strict**.
- Author-facing documentation is in `docs/`. Internal interface specs are still
  at the repository root; they have not yet been aggregated.
- The code and the stated model disagree in two places that matter: schema
  versions still exist, and `table` still owns both declarations and the
  row-source algebra.
- The authoring model is coherent and tested. Two model questions remain: how a
  `ComputedStruct` behaves when it types a source field, and whether generated
  nullability is a contract claim or only a generation-time note.
- The internal boundaries are not yet at the standard described in `AGENTS.md`.

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

## Internal interface map

```text
types -> (none)
annotations -> _frozen_json
expressions -> types, _frozen_json
topology -> types, annotations, expressions, _support
table -> types, annotations, expressions, _support
relational -> expressions
binding -> types, annotations, expressions, table, topology
compile -> types, annotations, expressions, table, topology, binding, workflow
engines -> types, expressions, table, relational
workflow -> engines
modules -> types, annotations, expressions, table, topology, binding,
            relational, engines, compile, workflow
code_generation -> types, engines
cli -> code_generation
```

| Package | Responsibility | Interface problem |
| --- | --- | --- |
| `types` | Logical types, authoring markers, normalization, codecs | Exports `Nullable` and many internals at root; docs call `Nullable` internal |
| `expressions` | Selections and bindable expressions over an expression IR | Authoring wrappers and the expression IR live together; consumers bind to `expressions.ir` |
| `table` | Declarations **and** row-source algebra | Two responsibilities; `table.rows` is imported directly by six packages |
| `relational` | Product-level relation planning | Exposes only `lower_product`; `engines` imports `relational.ir`/`planner` directly |
| `binding` | Graph-binding authoring values | Imports `topology.models._NodeSideBase`; factory types are split from the IR |
| `compile` | Blueprint, codecs, validation, compilation | Hides the module compiler protocol; `BuildBlueprint` embeds `workflow.ir`; schema version 4 |
| `topology` | Node/edge declarations, properties, endpoints | `topology.ir` is the real cross-package interface |
| `workflow` | Workflow model, assembly, contract, execution | Hides `ModuleExecutor` and `WorkflowContractIR`; imports `engines.duckdb`; context holds services |
| `modules` | Module contract and built-ins | Imports private compile/workflow/engine modules; authors must import private modules |
| `engines` | DuckDB lowering and type mapping | `engines/__init__` exports nothing; `workflow` and `code_generation` bind to `engines.duckdb` |
| `code_generation` | Edit-time generated declaration packages | Depends on the runtime DuckDB engine; not in author docs |
| `annotations` | Frozen annotations and labels | Consumers import `annotations.ir`, not the package interface |
| `cli` | `kbs` entry point | Has no library interface; only generation is wired |

Cross-cutting findings:

- **The IR is the real interface and no package owns it.** The compiled model is
  stitched from `annotations.ir`, `types.ir`, `expressions.ir`, `table.ir`,
  `topology.ir`, `binding.ir`, `workflow.ir` and `relational.ir`. Any IR change
  touches `compile` and every consumer.
- **`__init__` is not the interface.** `compile` omits the module compiler
  protocol, `workflow` omits the executor and contract types, `engines` exports
  nothing.
- **One private cross-package import:** `binding` imports
  `topology.models._NodeSideBase`.
- **Undeclared edges:** `workflow -> engines.duckdb`,
  `code_generation -> engines.duckdb`, and the composition root imports
  `compile.compiler` and `modules.core`.
- **Shared kernel:** `_frozen_json` and `_support` are top-level private modules
  used across packages without a declared interface.
- **`table` still has two responsibilities:** declarations and row-source
  algebra. `table.rows` is a de facto interface used by binding, compile,
  engines and modules.
- **Schema versions remain:** blueprint 4 and workflow contract 2. `AGENTS.md`
  says the framework has none. The code is behind the model here.
- **Anaemic-model exception:** workflow execution contexts carry
  `ExecutionServices`, a service object inside frozen data.
- **Import-time coupling:** importing `kg_build_system` pulls the DuckDB stack
  through `workflow -> engines.duckdb`.

## Spec corpus

The internal interfaces are specified in `specs/`, indexed by `specs/README.md`.
The former root specs have been aggregated into that set; plans, changelogs and
superseded notes are gone.

The specs state the current code interface. `FRAMEWORK_STATE.md` records the
known interface conflicts and the decisions that need attention; the specs do
not resolve them.

## Decisions for you

1. **Schema versions.** Remove `BLUEPRINT_SCHEMA_VERSION`,
   `WORKFLOW_CONTRACT_SCHEMA_VERSION`, the meta-graph version and the generation
   format version, or keep them and change the stated model. `AGENTS.md` says the
   framework has none.
2. **`table` split.** Keep declarations and row sources together, or give the
   row-source algebra its own package and interface. Six packages currently
   depend on `table.rows`.
3. **IR ownership.** Decide whether the IR is the interface and give it one
   owner and one exported surface, or keep per-package `.ir` modules as the
   dependency surface. The current answer is accidental.
4. **Extension protocols.** Export `ModuleCompiler`, `ModuleExecutor` and
   `WorkflowContractIR` from their packages so module and workflow extensions do
   not import private modules.
5. **DuckDB edges.** `workflow` and `code_generation` import `engines.duckdb`.
   Decide whether the engine is an interface dependency or whether the shared
   pieces move behind an engine-neutral interface.
6. **Generated shapes.** `join`/`group_by` result shapes are `Any` at edit time;
   fields are typed at runtime. Decide whether to accept that or generate typed
   shapes.
7. **Aggregates and computed structs.** `group_by` has no count/sum/having;
   `ComputedStruct` has no public constructor. Both are known limits.
8. **`ComputedStruct` as a field type.** Its member expressions are type
   witnesses when it types a source field; reads come from the carrier. Decide
   whether that is the intended model or whether a computed struct must not type
   a source-backed field.
9. **Contract durability.** `build` requires the exact module `VERSION`; there
   is no compatibility or migration path. Decide whether that is the intended
   limit or whether contracts need a version policy.
## Documentation

The author-facing guide is in `docs/` and now includes a `Why this framework`
page: semantics as contract, explicit assumptions, typed authoring, reproducible
builds, separation of meaning and execution, honest limits and the author /
consumer perspective.

The docs state the current behavior: the row-source algebra and joined/grouped
projections, `ComputedStruct` as a type witness on a carrier, generated
nullability as a source claim rather than a non-null field type, attribute
docstrings on computed fields, non-null group keys, text-only join `equals`,
exact module-version contract durability, and module-level rather than
binding-level producer conflicts.

They also cover templates, custom scalars, topology order and reachability, the
row-source guarantees, module authoring status, build and output limits, source
and binding nuances, patterns, debugging errors and the API/glossary.

The internal interface map, the spec set and the decisions that need attention
stay in `specs/` and this file.

## Verification

```console
uv run pytest -q
uv run pyright
uv run mkdocs build --strict
```
