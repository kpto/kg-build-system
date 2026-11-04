# kg-build-system

Declarative, typed, reproducible knowledge-graph builds.

The framework turns typed Python declarations into an inspectable knowledge
graph. It compiles declarations into a `WorkflowPlan`, executes the plan and
publishes the graph with the meaning declared for it.

## Package groups

| Group | Responsibility |
| --- | --- |
| `kernel/` | domain-agnostic toolchain: language, declaration, symbol, linker, planner, executor, resource, runtime, workflow plan and canonical types |
| `distribution/languages/` | the annotation, expression, data, topology and binding languages |
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
binding, projection, table, core, meta-graph, Neo4j, DuckDB and Python.

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

Current verification: 187 tests passed, 1618 subtests; pyright 0 errors.

The framework is experimental; the guide describes the current model, not a
compatibility promise.
