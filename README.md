# kg-build-system

Declarative, typed, reproducible knowledge-graph builds.

The framework turns typed Python declarations into an inspectable knowledge
graph. It compiles declarations into a `WorkflowPlan`, executes the plan and
publishes the graph with the meaning declared for it.

## Package groups

| Group | Responsibility |
| --- | --- |
| `kernel/` | domain-agnostic toolchain: language, declaration, symbol, linker, planner, executor, resource, runtime, workflow plan and canonical types |
| `distribution/languages/` | the annotation, expression, asset, data, topology and binding languages |
| `distribution/interpreter/` | `GraphBlueprint`, `BlueprintLinker` and `create_blueprint` |
| `distribution/modules/` | feature packages: core, deduplication, merging, conflict validation, file, meta-graph, Neo4j, DuckDB, Python and runtime resources |
| `distribution/implementations.py` | language and linker implementations composed by `api.py` |
| `generation/` | edit-time code generation |
| `api.py` | the composition root: `default_toolchain`, `DEFAULT_TOOLCHAIN`, `create_blueprint`, `compile` and `execute` |
| `cli/` | the `kbs` entry point |

`kg_build_system` re-exports the authoring vocabulary for the canonical types in
`kernel/model/public/types`.

The kernel vocabulary is toolchain vocabulary: language, declaration, symbol,
linker, planner, workflow plan, runtime, executor, resource and toolchain. The
distribution vocabulary is domain vocabulary: graph, blueprint, node, edge,
binding, projection, table, asset, core, meta-graph, Neo4j, DuckDB and Python.

Every framework leaf uses the zones it needs from the model/service layout:

```text
pkg/
  __init__.py          docstring, imports and __all__ only
  model/
    public/            authoring models, returned values, public DTOs
    internal/          cross-package data: dto/, model/
    _private/          private plans, render models, SQL types
  service/
    public/            authoring methods; thin wrappers
    internal/          service interfaces, codec/assembly wrappers, adapters/
    _private/          codecs, transcription, rendering, validation, assembly,
                       planning, engines, runtime
```

## Authoring model

- `Selection[T]` is the single authoring type; `NullableSelection[T]` is the
  alias `Selection[Nullable[T]]`. The compiler expression tree is private.
- A `Field[T]` declares a value type, never `T | None`. Source `Table` and
  source `Struct` reads yield `NullableSelection[T]`; computed `Projection` and
  `ComputedStruct` reads yield the type of their `computed_field` selection.
  Nested array-item nullability stays in the value type.
- `Table` and `Projection` are row-source providers. Use
  `Table.row_source()` / `Projection.row_source()`; a projection is pinned with
  `Projection(source)`.
- `field()` declares a source member and `computed_field(selection)` a computed
  member. Binding lambdas receive a typed row proxy.
- `alter_rows()` is the one-shot row-effect gate; it exposes only `drop_null`,
  `drop_if` and `expand` where they are valid. `lookup`, `zip`, `at`, `slice`,
  `extract` and the present value operations are selection methods.
- A language reports authoring references with `get_references` and transcribes
  one declaration at a time with `transcribe`; the linker resolves the closure
  before transcription.

## Source data

- An **asset** is one logical unit of source data, like a package. One asset may
  back many tables. A table names its asset with `Table[Asset]`; the relation
  carries that identity as an `AssetRef`.
- `AssetOptions` carries `website`, optional `layout`, `semantics` and
  `governance`. `AssetLayout` is optional descriptive metadata: `kind`,
  `locator`, `format`, `selector`, `partition_by`, `members` and `properties`.
  It is not an access contract.
- `DuckDbSourcePlanner` is the generic module planner for `parquet`, `json` and
  `csv` assets. There is no adapter concept in the toolchain and no adapter
  registry; another format is another ordinary module planner.
- `@asset_contract(AssetContractOptions(...))` is an inert edit-time decorator
  on an asset. Code generation is not part of `AssetOptions`, `AssetDTO` or the
  blueprint, and there are no source binding values.
- Generation observes a source and renders declarations. Observation is
  provenance: a generated source-backed field renders `Field[T]` and never adds
  absence to the declaration.

## Documentation

- Author-facing documentation starts at `docs/index.md`.
- Developer documentation starts at `docs/developer/index.md`.
- The implementation map is `ARCHITECTURE.md`.
- Reviewer state and design limits are `FRAMEWORK_STATE.md` and
  `DESIGN_ISSUES.md`.
- `specs/README.md` points at the canonical developer docs and states the model
  and service boundaries.

## Verification

```console
uv run pytest -q
uv run pyright
uv run mkdocs build --strict
```

Current verification: 259 tests passed, 1858 subtests; pyright 0 errors; the
reference build passes; the Open Targets project passes 7 tests; the strict
documentation build passes.

The framework is experimental; the guide describes the current model, not a
compatibility promise.
