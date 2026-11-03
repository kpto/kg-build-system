# Framework state

This is the reviewer briefing. The target tree is the implementation; the old
top-level packages are deleted.

## Verification

- **61 tests**, **306 subtests**.
- Pyright: **0 errors**.
- `uv run mkdocs build --strict`: passes.
- Open Targets KG: **6 tests** pass.

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
    public/types/
    internal/types/
    internal/json.py
  declaration/
    foundations/
      annotations/
      expressions/
    languages/
      table/
      topology/
      binding/
    blueprint/
  pipeline/
    contract/
    compilation/
    build/
  distribution/
    modules/
  generation/
    code_generation/
  types/                 # authoring alias for kernel.public.types
  api.py
  cli/
```

## Pipeline

- `create_blueprint` lives in `declaration/blueprint` and returns
  `GraphBlueprint`.
- `compile_blueprint` lives in `pipeline/compilation` and returns
  `WorkflowContractDTO`.
- `compile` is the composition-root shortcut: it creates a blueprint and then
  compiles it.
- `build` lives in `pipeline/build` and dispatches on `step.instruction.kind`.
- Supplied modules and `register_module` live in `distribution`.
- Source generation is per layer; `blueprint_to_source` delegates to the table,
  topology and binding renderers.
- The contract owns contributions, connections and provenance. A step owns its
  `InstructionDTO`.

## Remaining temporary adapters and limits

- Capability modules are deferred. `Capability` exists, but `Module` does not
  declare `requires`/`provides` and composition does not enforce them.
- DuckDB is the default emitter. `DuckDbSqlEmitter` is a library, not a
  capability module.
- A Python binding stores a reference: `PythonRefDTO(module, qualname,
  signature)`, not the callable body.
- Some target executors still read `variables["instructions"]`; the build target
  adapter copies the step instruction payload into `variables`.
- Public `GraphBlueprint` fields reference internal layer DTOs. The handle is
  public; those layer DTOs are not exported public names.
- `pipeline/build` and `distribution/modules` reference each other through
  target adapters and core engine helpers.

## Documentation

- `docs/developer/` is the canonical developer guide.
- `ARCHITECTURE.md` is the short implementation map.
- `DESIGN_ISSUES.md` states the remaining design limits.
- `specs/README.md` points at the developer docs and states the boundaries.
