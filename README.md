# kg-build-system

Declarative, typed, reproducible knowledge-graph builds.

The framework turns typed Python declarations into an inspectable knowledge
graph. It compiles declarations into a frozen workflow contract, executes the
contract and publishes the graph with the meaning declared for it.

## Package groups

| Group | Responsibility |
| --- | --- |
| `kernel/` | domain-agnostic protocols, canonical types, build values and contract vocabulary |
| `declaration/` | annotation and expression foundations, the `table`, `topology` and `binding` languages, and `GraphBlueprint` |
| `pipeline/contract/` | the `WorkflowContractDTO`, assembly and codec |
| `pipeline/compilation/` | `compile_blueprint`, module compilers, relational plans and instruction emitters |
| `pipeline/build/` | contract execution, runtime, engine, storage and relations |
| `distribution/` | supplied modules and `register_module` |
| `generation/` | edit-time code generation |
| `api.py` | the composition root: `create_blueprint`, `compile_blueprint`, `compile` and `build` |
| `cli/` | the `kbs` entry point |

`kg_build_system.types` is the authoring alias for the canonical types in
`kernel/model/public/types`.

Every framework leaf uses the model/service layout:

```text
pkg/
  __init__.py          imports only model.public and service.public
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

The framework is experimental; the guide describes the current model, not a
compatibility promise.
