# kg-build-system

Declarative, typed, reproducible knowledge-graph builds.

The framework turns typed Python declarations into an inspectable knowledge
graph. It compiles declarations into a `WorkflowPlan`, executes the plan and
publishes the graph with the meaning declared for it.

## Start a project

`templates/project/` is the topic-neutral project template: the four declaration
layers, one layer directive per directory, a conformance fixture, and the
philosophy gate. `kbs init` will copy it into a new project.

A project states its composition in `manifest.py` as declarative `Blueprint` and
`Workflow` values; importing it builds nothing. The CLI finds them by type:

```console
cd templates/project
uv run pytest
uv run kbs blueprint --project project
uv run kbs workflow --project project
uv run kbs run --project project
```

`create_blueprint`, `compile` and `execute` remain the Python entry points for
tests and embedding.

## Package groups

| Group | Responsibility |
| --- | --- |
| `kernel/` | domain-agnostic toolchain: language, declaration, symbol, linker, planner, executor, resource, runtime, workflow plan and canonical types |
| `distribution/languages/` | the annotations, expressions, meaning, asset, data, topology, binding and graph languages |
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
binding, source relation, derived relation, asset, core, meta-graph, Neo4j, DuckDB and Python.

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

## Extension is expected

The default distribution is one composition of the kernel, not the framework's
boundary. A project extends it before it changes the kernel:

- **Value operation**: an `OperationSpec` plus a typed `Operation` handle in
  `expression/`; an engine emitter in `modules/`; the expressions language is
  composed with the operation set in `manifest.py`.
- **Relation operation**: a `RelationOperationSpec` plus a `RelationOperation`
  and a `RowSourceEmitter` in `modules/`; its output is plan-local until a
  `Stage`/`DerivedRelation` publishes it with a matching grain.
- **Source adapter**: a source planner and executor in `modules/`; it decodes
  and preserves the source schema, null assumptions, grain and identity.
- **Planner and executor module**: a new pass over records or a new artifact,
  composed in `manifest.py`.

The six kernel protocols — `Language`, `Linker`, `Planner`, `StepExecutor`,
`ResourceProvider` and `Runtime` — are for a different composition. The exact
surfaces are in
[docs/content/appendix/reference/extension.md](docs/content/appendix/reference/extension.md).
The template carries a runnable value operation, input adapter and relation
operation in `templates/project/`.

## Project notebook and console

`kgkit` is the project operation and notebook surface, integrated into the
`kg_build_system` distribution. It is reached through `kbs`:

```console
uv run kbs notebook init
uv run kbs console
```

The console is its own page and server. It embeds the design viewer by URL
(`viewer_url` in `kgkit/config.json`, usually `kbs view --embed`) and exchanges
snapshots over the embed bridge; it does not bundle or serve a second design
viewer. `kbs view` remains the separate design viewer. The notebook
(`kgkit/records/`) holds revisions, the event chain, findings, change designs,
evaluations, documents and captured views. A revision closes a resolved design
set; `revision_facts` supplies the graph facts and the designs it links.
Project-specific `ops/` and `eval/` commands run as JSON commands from the
manifest config.

See [Project notebook and console](docs/content/appendix/reference/kgkit.md).

## Authoring model

- `Selection[T]` is the single authoring type; `NullableSelection[T]` is the
  alias `Selection[Nullable[T]]`. The compiler expression tree is private.
- A `Field[T]` declares a value type, never `T | None`. `SourceRelation` and
  `Struct` reads yield `NullableSelection[T]`; `DerivedRelation` and
  `ComputedStruct` reads yield the type of their `computed_field` selection.
  Nested array-item nullability stays in the value type.
- `SourceRelation` and `DerivedRelation` are published row-source providers. Use
  `SourceRelation.row_source()` / `DerivedRelation.row_source()`; a derived
  relation is pinned with `DerivedRelation(source)`, and a `Stage(source)` is its
  private sub-relation.
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
  back many source relations. A source relation names its asset with
  `SourceRelation[Asset]`; the relation carries that identity as an `AssetRef`.
- `AssetOptions` carries `website`, optional `layout`, `meaning` and
  `governance`. `AssetLayout` is optional descriptive metadata: `kind`,
  `locator`, `format`, `selector`, `partition_by`, `members` and `properties`.
  It is not an access contract.
- `DuckDbSourcePlanner` is the generic module planner for `parquet`, `json` and
  `csv` assets. There is no adapter concept in the toolchain and no adapter
  registry; another format is another ordinary module planner.
- `@asset_generation(AssetGenerationOptions(...))` is an inert edit-time decorator
  on an asset. Code generation is not part of `AssetOptions`, `AssetDTO` or the
  blueprint, and there are no source binding values.
- Generation observes a source and renders declarations. Observation is
  provenance: a generated source-backed field renders `Field[T]` and never adds
  absence to the declaration.

## Documentation

- The book starts at `docs/content/index.md` and `docs/content/book/index.md`.
- Exact appendices start at `docs/content/appendix/index.md`.
- The extension surface starts at `docs/content/appendix/kernel/index.md`; the default graph
  composition starts at `docs/content/appendix/framework/index.md`.
- Developer documentation starts at `docs/content/appendix/developer/index.md`.
- The content and its builder are both under `docs/`:
  `./docs/build.sh`.
- The implementation map is `ARCHITECTURE.md`.
- Reviewer state and design limits are `FRAMEWORK_STATE.md` and
  `DESIGN_ISSUES.md`.
- `specs/README.md` points at the canonical developer docs and states the model
  and service boundaries.

## Verification

```console
uv run pytest -q
uv run pyright
./docs/check.sh && ./docs/build.sh
```

Current verification: 455 tests passed, 2065 subtests; pyright 0 errors; the reference build passes; the Open Targets project is external; the
Quartz documentation build passes.

The framework is experimental; the guide describes the current model, not a
compatibility promise.
