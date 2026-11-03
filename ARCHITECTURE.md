# Architecture

This file is the implementation map. The model, interfaces and design decisions
are in [docs/developer/system-design.md](docs/developer/system-design.md).

## Current tree

```text
kg_build_system/
  kernel/
    model/
      public/types/
      internal/types/
      internal/json.py
      _private/
    service/
      public/
      internal/
      _private/
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
  generation/
    code_generation/
  api.py
  cli/
```

Every leaf uses `model/` and `service/`:

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

`model.public` and `model.internal` import no service or private code.
`service.public` imports `model.public` and `service.internal`.
`service.internal` imports model data and uses function-local imports for
`service._private`. `service._private` may read model data and other private
service code, but not `service.public`.

## Dependency spine

An arrow means "may import".

```text
declaration -> kernel
pipeline/contract -> kernel
pipeline/compilation -> declaration, pipeline/contract, kernel
pipeline/build -> pipeline/contract, kernel
distribution -> kernel, declaration, pipeline/contract, pipeline/compilation, pipeline/build
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
| `distribution` | `kernel`, `declaration`, `pipeline/contract`, `pipeline/compilation`, `pipeline/build` |
| `generation/code_generation` | `kernel` |
| `api.py` | `declaration`, `pipeline`, `distribution` |
| `cli` | `generation`, `api.py` |

`pipeline/compilation` and `pipeline/build` share the contract but do not import
each other. Another package imports a leaf's `model.public`, `model.internal`,
`service.public` or `service.internal`; it never imports a private zone.
