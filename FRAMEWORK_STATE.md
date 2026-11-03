# Framework state

This is the reviewer briefing. The toolchain kernel and the distribution are the
implementation.

## Verification

- **115 tests**, **604 subtests**.
- Pyright: **0 errors**.
- `uv run mkdocs build --strict`: passes.
- Open Targets KG: **7 tests** pass.

```console
uv run pytest -q
uv run pyright
uv run mkdocs build --strict
cd ~/Repos/opentargets-kg && uv run pytest -q
```

## Current tree

```text
kg_build_system/
  kernel/
    model/
      public/
        language.py
        workflow.py
        runtime.py
        types/
      internal/
      _private/
    service/
      public/
        pipeline.py
        runtime.py
      internal/
      _private/
  distribution/
    model/public/
    languages/{annotations,expressions,table,topology,binding}
    interpreter/
    planners/{core,deduplication,merging,conflict_validation}
    executors/
      model/ service/     the executor leaf's own zones
      runtime/
      duckdb/
      python/
      file/
      meta_graph/
      neo4j/
      conflict_validation/
    service/             the distribution leaf's service zone
    default.py
  generation/code_generation/
  api.py
  cli/
```

Every leaf uses `model/public`, `model/internal`, `model/_private`,
`service/public`, `service/internal` and `service/_private`. `__init__.py`
imports only `model.public` and `service.public`.

## Toolchain

- `build` orders languages, transcribes and validates their layers and calls
  `linker.link(layers)`.
- `compile` calls every planner, assigns each planner's `component_id` to its
  steps and assembles a `WorkflowPlan`.
- `execute` maps exact instruction kinds, creates services and calls the runtime.
- `create_blueprint` lives in `distribution/interpreter` and returns
  `GraphBlueprint`.
- `compile` is the composition-root shortcut: it creates a blueprint when none is
  supplied and returns a `WorkflowPlan`.
- `execute` lives in `api.py` and dispatches on `step.instruction.kind`.
- Supplied planners and executors live in `distribution`; `default_toolchain`
  adds the core planner and the default executors.
- Source generation is per language; the interpreter source service delegates to
  the table, topology and binding renderers.
- The workflow plan owns components, steps, connections and provenance. A step
  owns its instruction.

## Remaining limits

- A toolchain is the only composition unit. There is no registry.
- DuckDB is the default SQL emitter. `DuckDbSqlEmitter` is a library, not part
  of the kernel.
- A Python instruction is a reference: `("python", "cpython")` carries
  `{module, qualname}`, not a live callable.
- Public `GraphBlueprint` fields reference internal layer DTOs. The handle is
  public; those layer DTOs are not exported public names.
- A language may publish only its layer value instead of per-declaration
  definitions.

## Documentation

- `docs/developer/` is the canonical developer guide.
- `ARCHITECTURE.md` is the short implementation map.
- `DESIGN_ISSUES.md` states the remaining design limits.
- `specs/README.md` points at the developer docs and states the model/service
  boundaries.
