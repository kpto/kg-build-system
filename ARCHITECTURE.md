# Architecture

This file is the implementation map. The model, interfaces and design decisions
are in [docs/developer/system-design.md](docs/developer/system-design.md).

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

Every leaf uses `public/`, `internal/` and `_private/`; `__init__.py` exposes the
public facade.

## Dependency spine

An arrow means "may import".

```text
declaration -> kernel
pipeline/contract -> kernel
pipeline/compilation -> declaration, pipeline/contract, kernel
pipeline/build -> pipeline/contract, kernel
distribution/modules -> kernel, declaration, pipeline/contract, pipeline/compilation, pipeline/build
generation/code_generation -> kernel
api.py -> declaration, pipeline, distribution
cli -> generation, api.py
```

The primary edges are:

| Package | May import |
| --- | --- |
| `kernel` | no framework package |
| `declaration/foundations/*` | `kernel` |
| `declaration/languages/table` | `declaration/foundations`, `kernel` |
| `declaration/languages/topology` | `declaration/foundations`, `kernel` |
| `declaration/languages/binding` | `declaration/languages/table`, `declaration/languages/topology`, `declaration/foundations`, `kernel` |
| `declaration/blueprint` | declaration languages and foundations, `kernel` |
| `pipeline/contract` | `kernel` |
| `pipeline/compilation` | `declaration`, `pipeline/contract`, `kernel` |
| `pipeline/build` | `pipeline/contract`, `kernel` |
| `distribution/modules` | `kernel`, `declaration`, `pipeline/contract`, `pipeline/compilation`, `pipeline/build` |
| `generation/code_generation` | `kernel` |
| `api.py` | `declaration`, `pipeline`, `distribution` |
| `cli` | `generation`, `api.py` |

`pipeline/compilation` and `pipeline/build` share the contract but do not import
each other. `distribution/modules` may import the build engine for execution
constants; `pipeline/build` resolves module executors dynamically from the
contract and does not import `distribution`.
