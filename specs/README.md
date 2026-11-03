# Developer specs

The canonical developer documentation is [docs/developer/](../docs/developer/).
It states the current model, interfaces, source regeneration and contract tests.
This directory does not duplicate it.

- [ARCHITECTURE.md](../ARCHITECTURE.md) is the short implementation map.
- [FRAMEWORK_STATE.md](../FRAMEWORK_STATE.md) is the reviewer briefing.
- [DESIGN_ISSUES.md](../DESIGN_ISSUES.md) records the remaining design limits.

## Public and internal boundaries

| Package | Public surface | Internal surface |
| --- | --- | --- |
| `kernel` | `Language`, `Module`, `Capability`, canonical types, build and contract values | canonical type DTOs and codecs |
| `declaration/foundations/annotations` | `Annotation`, `NodeLabel`, `EdgeLabel` | annotation DTO and source rendering |
| `declaration/foundations/expressions` | expressions, selections and expression families | expression DTOs, operation specifications and source rendering |
| `declaration/languages/table` | `Table`, `Struct`, `Projection`, fields and sources | data DTOs, transcription, row-source plans and source rendering |
| `declaration/languages/topology` | `Node`, `Edge`, properties and templates | graph DTOs, transcription and source rendering |
| `declaration/languages/binding` | `node_binding`, `edge_binding`, values and options | binding DTOs, transcription and source rendering |
| `declaration/blueprint` | `GraphBlueprint`, `create_blueprint` | assembly, validation, codec and blueprint source |
| `pipeline/contract` | `WorkflowContractDTO` and its DTOs | assembly and codec |
| `pipeline/compilation` | `compile_blueprint` | module compilers, relational plans and instruction emitters |
| `pipeline/build` | `build`, `BuildRuntime`, `WorkflowReport` | runtime, engine, targets, storage and relations |
| `distribution` | supplied modules and `register_module` | module model and registration service |
| `generation/code_generation` | generation requests and commands | discovery, providers, rendering and ownership |
| `api.py` | `create_blueprint`, `compile_blueprint`, `compile`, `build` | composition only |
| `cli` | `kbs` entry point | argument parsing and command dispatch |

## Zones

Every leaf uses:

```text
pkg/
  __init__.py      facade; imports only from .public
  public/          author-facing names and thin wrappers
  internal/        cross-package DTOs, models, services and adapters
  _private/        mechanisms; imported only inside the package
```

Another package imports `pkg`, `pkg.internal` or a declared internal interface.
It never imports `pkg._private`. A foreign protocol is implemented in
`pkg/internal/adapters/<protocol>.py`.

## Dependency spine

`declaration` depends on `kernel`. `pipeline/compilation` depends on declaration
and the shared contract; `pipeline/build` depends on the shared contract. They do
not import each other.
`distribution` supplies modules. `generation` is upstream. `api.py` and `cli`
compose the systems.

See [system design](../docs/developer/system-design.md) for the full package
tree and dependency table.
