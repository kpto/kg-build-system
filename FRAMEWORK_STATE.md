# Framework state

This is the reviewer briefing. The toolchain kernel and the distribution are the
implementation.

## Verification

- **455 tests**, **2065 subtests**.
- Pyright: **0 errors**.
- `./docs/build.sh`: passes.
- The reference build passes.
- Open Targets KG: **7 tests** pass.

```console
uv run pytest -q
uv run pyright
./docs/check.sh && ./docs/build.sh
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
    languages/{annotations,expressions,semantics,graph,asset,data,topology,binding}
    interpreter/
    modules/{core,deduplication,merging,conflict_validation,file,meta_graph,neo4j,duckdb,python,runtime}
    service/             the distribution leaf's service zone
    implementations.py
  generation/code_generation/
  __init__.py            lazy export table; literal __all__
  api.py
  cli/
```

Every leaf uses the zones it needs from `model/public`, `model/internal`,
`model/_private`, `service/public`, `service/internal` and `service/_private`.
An empty zone is deleted. `__init__.py` is a docstring, imports and `__all__`
only; the top-level lazy export table and `__getattr__` live in
`kg_build_system/__init__.py`.

## Toolchain

- `build` hands languages and a namespace to the `Linker`. The linker discovers
  declarations, derives keys with `compute_key`, reads direct references from
  authoring values with `get_references`, resolves the closure before
  transcription, orders the reachable declarations and transcribes each one with
  `transcribe`.
- A `Declaration` has no key; a `Symbol` carries its key, kind, value and
  references. `SymbolRef(language, key)` is the only cross-symbol identity.
- `Selection[T]` is the single authoring type; `NullableSelection[T]` is
  `Selection[Nullable[T]]`. A `Field[T]` declares a value type, never `T | None`;
  `SourceRelation`/`Struct` reads are nullable and computed `DerivedRelation`/
  `ComputedStruct` reads follow their selection. `alter_rows()` is the one-shot
  row-effect gate; `lookup`, `zip` and `RowSource.unnest` complete the value and
  grain surface.
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
  `default_toolchain` adds the generic DuckDB source planner, the four core
  planners, the default executors and the runtime providers. Core planners live
  under `modules/core/<feature>/service/public/planner.py`; shared planning is
  under `core/service/_private/planning/`.
- Core consumes the neutral relation plan and `SqlEmitter` protocol from
  `distribution/service/internal`; DuckDB implements the protocol. Core imports
  no DuckDB module.
- An asset is one logical unit of source data and may back many tables; a table
  names its asset with `SourceRelation[Asset]`. `AssetOptions` carries a required
  `AssetProfile`, optional `Meaning`, website, optional layout and governance.
  `AssetLayout` is optional descriptive metadata, not an access contract.
- Source generation is per language; the interpreter source service renders the
  graph declaration first, then delegates to the asset, topology, data and
  binding renderers.
- Generation is an edit-time frontend: `@asset_generation(AssetGenerationOptions(...))`
  is an inert decorator on an asset, not an asset field or blueprint value.
  Observation is provenance; a generated source-backed field renders `Field[T]`.
- The workflow plan owns components, steps, connections and provenance. A step
  owns its instruction.

## Remaining limits

[docs/content/appendix/review/limits.md](docs/content/appendix/review/limits.md), published at `/appendix/review/limits`,
is the canonical classified table. Each row names its kind — model rule,
replaceable default, current algorithm, not implemented, interface limit or
empirical — and its extension point or model reason. Verification status stays
in the section above; this page does not duplicate the table.

## Documentation

- The book starts at [docs/content/book/index.md](docs/content/book/index.md).
- Developer interfaces start at [docs/content/appendix/developer/index.md](docs/content/appendix/developer/index.md).
- The kernel surface is at [docs/content/appendix/kernel/index.md](docs/content/appendix/kernel/index.md).
- `ARCHITECTURE.md` is the short implementation map.
- `DESIGN_ISSUES.md` points at the canonical limits table and lists the model
  rules.
- `specs/README.md` points at the developer docs and states the model/service
  boundaries.
