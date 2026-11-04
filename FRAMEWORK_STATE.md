# Framework state

This is the reviewer briefing. The toolchain kernel and the distribution are the
implementation.

## Verification

- **177 tests**, **1611 subtests**.
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
        key.py
        language.py
        symbol.py
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
    languages/{annotations,expressions,data,topology,binding}
    interpreter/
    modules/{core,deduplication,merging,conflict_validation,file,meta_graph,neo4j,duckdb,python,runtime}
    service/             the distribution leaf's service zone
    implementations.py
  generation/code_generation/
  _facade.py
  api.py
  cli/
```

Every leaf uses the zones it needs from `model/public`, `model/internal`,
`model/_private`, `service/public`, `service/internal` and `service/_private`.
An empty zone is deleted. `__init__.py` is a docstring, imports and `__all__`
only; the top-level lazy loader is `_facade.py`.

## Toolchain

- `build` hands languages and a namespace to the `Linker`. The linker discovers
  declarations, derives keys with `compute_key`, transcribes symbols, resolves
  references, orders them and assembles the model.
- A `Declaration` has no key; a `Symbol` carries its key, kind, value and
  references. `SymbolRef(language, key)` is the only cross-symbol identity.
- `compile` groups planners by `component_id`; several planners may share a
  component when their `version` and `runtime_fields` agree. It assigns the
  component to each step and assembles a `WorkflowPlan`.
- `PlanContext.shared` carries per-compile state; the core planners share
  `"core.plan"`.
- `execute` maps exact instruction kinds, and the runtime opens providers, merges
  resources, builds one view per executor and closes providers in reverse order.
- `create_blueprint` lives in `distribution/interpreter` and returns
  `GraphBlueprint`.
- `compile` is the composition-root shortcut: it creates a blueprint when none is
  supplied and returns a `WorkflowPlan`.
- `execute` lives in `api.py` and dispatches on `step.instruction.kind`.
- Supplied planners, executors and resources live in `distribution/modules`;
  `default_toolchain` adds the five core planners, the default executors and the
  runtime providers.
- Source generation is per language; the interpreter source service delegates to
  the data, topology and binding renderers.
- The workflow plan owns components, steps, connections and provenance. A step
  owns its instruction.

## Remaining limits

- A toolchain is the only composition unit. There is no registry.
- DuckDB is the default SQL emitter. `DuckDbSqlEmitter` is a library, not part
  of the kernel.
- A Python instruction is a reference: `("python", "cpython")` carries
  `{module, qualname}`, not a live callable.
- Public `GraphBlueprint` fields reference internal language DTOs. The handle is
  public; those language DTOs are not exported public names.
- A repeated struct graph name takes its qualified Python name as an extra key
  segment.

## Documentation

- `docs/developer/` is the canonical developer guide.
- `ARCHITECTURE.md` is the short implementation map.
- `DESIGN_ISSUES.md` states the remaining design limits.
- `specs/README.md` points at the developer docs and states the model/service
  boundaries.
