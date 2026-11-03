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
| `kernel` | canonical types; language, workflow and runtime values | `Language`, `Linker`, `Planner`, `StepExecutor`, `Runtime`, `ResourceProvider`, `Toolchain`, `Extension`, `WorkflowRuntime` |
| `distribution/languages/annotations` | annotation values and labels | codec and source rendering |
| `distribution/languages/expressions` | expression and selection values; expression DTOs | construction, operation specifications and source rendering |
| `distribution/languages/table` | `Table`, `Struct`, `Projection`, fields and sources; data DTOs | field and source wrappers, transcription and source rendering |
| `distribution/languages/topology` | `Node`, `Edge`, properties and templates; graph DTOs | property and endpoint wrappers, transcription and source rendering |
| `distribution/languages/binding` | binding values; binding DTOs | `node_binding`, `edge_binding`, transcription and source rendering |
| `distribution/interpreter` | `GraphBlueprint` | `create_blueprint`, `BlueprintLinker`, assembly, validation, codec and source |
| `distribution/planners/*` | planner configuration and report values | supplied planners |
| `distribution/executors/*` | executor configuration, report values and execution services | supplied executors and resource providers |
| `distribution/model/public` | `BuildRuntime` and path rules | none |
| `distribution/default.py` | none | `DEFAULT_TOOLCHAIN`, `default_toolchain` |
| `generation/code_generation` | generation requests, results and provider contract | generation, discovery, rendering and ownership |
| `api.py` | none | `create_blueprint`, `compile`, `execute` |
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

`distribution/languages` depends on `kernel`. `distribution/interpreter` depends
on the languages and the kernel. `distribution/planners` and
`distribution/executors` depend on the interpreter, the languages and the
kernel; the core planner uses the DuckDB SQL emitter, and the conflict-report
executor reuses the planner's report values. `distribution/default` composes
them. `generation` is upstream. `api.py` and `cli` compose the systems.

The kernel imports no graph, table, topology, binding, SQL, DuckDB or Python
package.

See [system design](../docs/developer/system-design.md) for the full package
tree and dependency table.
