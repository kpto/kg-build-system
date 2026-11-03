# Developer specs

The canonical developer documentation is [docs/developer/](../docs/developer/).
It states the current model, interfaces, source regeneration and contract tests.
This directory does not duplicate it.

- [ARCHITECTURE.md](../ARCHITECTURE.md) is the short implementation map.
- [FRAMEWORK_STATE.md](../FRAMEWORK_STATE.md) is the reviewer briefing.
- [DESIGN_ISSUES.md](../DESIGN_ISSUES.md) records the remaining design limits.

## Model and service boundaries

| Package | Model surface | Service surface |
| --- | --- | --- |
| `kernel` | canonical types, build and contract values | `Language`, `Module`, `Capability`, registry |
| `declaration/foundations/annotations` | annotation values and labels | codec and source rendering |
| `declaration/foundations/expressions` | expression and selection values; expression DTOs | construction, operation specifications and source rendering |
| `declaration/languages/table` | `Table`, `Struct`, `Projection`, fields and sources; data DTOs | field and source wrappers, transcription and source rendering |
| `declaration/languages/topology` | `Node`, `Edge`, properties and templates; graph DTOs | property and endpoint wrappers, transcription and source rendering |
| `declaration/languages/binding` | binding values; binding DTOs | `node_binding`, `edge_binding`, transcription and source rendering |
| `declaration/blueprint` | `GraphBlueprint` | `create_blueprint`, assembly, validation, codec and source |
| `pipeline/contract` | `WorkflowContractDTO` and step DTOs | assembly and codec |
| `pipeline/compilation` | relation plans and instruction kinds | `compile_blueprint`, compilers and instruction emitters |
| `pipeline/build` | `BuildRuntime`, `WorkflowReport` | `build`, runtime, engine, storage and dispatch |
| `distribution` | module configurations and instruction DTOs | module classes, registration and compiler/executor factories |
| `generation/code_generation` | generation requests, results and provider contract | generation, discovery, rendering and ownership |
| `api.py` | none | `create_blueprint`, `compile_blueprint`, `compile`, `build` |
| `cli` | none | `kbs` entry point |

## Zones

Every leaf uses:

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

The import matrix:

- `model.public` and `model.internal` import no service or private code.
- `model._private` may import `model.public` and `model.internal`.
- `service.public` imports `model.public` and `service.internal`.
- `service.internal` imports model data and uses function-local imports for
  `service._private`.
- `service._private` may import model data and other private service code; it
  does not import `service.public`.
- Another package imports `pkg.model.public`, `pkg.model.internal`,
  `pkg.service.public` or `pkg.service.internal`. It never imports a private
  zone.
- A foreign protocol is implemented in `service/internal/adapters/<protocol>.py`.

## Dependency spine

`declaration` depends on `kernel`. `pipeline/compilation` and `pipeline/build`
depend on declaration and the shared contract, and do not import each other.
`distribution` supplies modules. `generation` is upstream. `api.py` and `cli`
compose the systems.

See [system design](../docs/developer/system-design.md) for the full package
tree and dependency table.
