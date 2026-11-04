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
| `kernel` | canonical types; declaration, symbol, key, workflow and runtime values | `Language`, `Declaration`, `Symbol`, `SymbolRef`, `Key`, `Linker`, `Planner`, `StepExecutor`, `Runtime`, `Resource`, `ResourceProvider`, `ResourceView`, `Toolchain`, `Extension`, `WorkflowRuntime` |
| `distribution/languages/annotations` | annotation values and labels | codec and source rendering |
| `distribution/languages/expressions` | expression and selection values; expression DTOs | construction, operation specifications and source rendering |
| `distribution/languages/data` | `Table`, `Struct`, `Projection`, fields and sources; data DTOs | field and source wrappers, transcription and source rendering |
| `distribution/languages/topology` | `Node`, `Edge`, properties and templates; graph DTOs | property and endpoint wrappers, transcription and source rendering |
| `distribution/languages/binding` | binding values; binding DTOs | `node_binding`, `edge_binding`, transcription and source rendering |
| `distribution/interpreter` | `GraphBlueprint` | `create_blueprint`, `BlueprintLinker`, assembly, validation, codec and source |
| `distribution/model/public` | `BuildRuntime`, typed references and path rules | none |
| `distribution/modules/<name>` | planner and executor configuration, report values and resource models | supplied planners, executors and resource providers |
| `distribution/implementations.py` | none | language and linker implementations |
| `generation/code_generation` | generation requests, results and provider contract | generation, discovery, rendering and ownership |
| `api.py` | none | `default_toolchain`, `DEFAULT_TOOLCHAIN`, `create_blueprint`, `compile`, `execute` |
| `cli` | none | `kbs` entry point |

## Zones

Every leaf uses the zones it needs:

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

An empty zone is deleted; it is not a marker. The top-level lazy loader is
`_facade.py`.

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
on the languages and the kernel. `distribution/modules` depend on the interpreter
where they read a blueprint, the languages, `distribution/model`,
`distribution/service` and the kernel; the core module uses the DuckDB SQL
emitter. `distribution/implementations` supplies the languages and linker that
`api.py` composes. `generation` is upstream. `api.py` and `cli` compose the
systems.

The kernel imports no graph, data, topology, binding, SQL, DuckDB or Python
package.

See [system design](../docs/developer/system-design.md) for the full package
tree and dependency table.
