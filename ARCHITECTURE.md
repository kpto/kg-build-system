# Architecture

This file is the implementation map. The model, interfaces and design decisions
are in [docs/developer/system-design.md](docs/developer/system-design.md).

## Current tree

```text
kg_build_system/
  kernel/
    model/
      public/
        language.py      Definition, Layer, Language, Namespace
        workflow.py      Instruction, Step, WorkflowPlan
        runtime.py       ExecutionContext, StepOutcome, WorkflowReport
        types/
      internal/
        json.py
        types/dto.py
      _private/
        types/
    service/
      public/
        pipeline.py      Linker, Planner, StepExecutor, Runtime,
                         ResourceProvider, Toolchain, Extension, PlanContext
        runtime.py       WorkflowRuntime
      internal/
        pipeline.py
        workflow_codec.py
      _private/
        ordering.py
        pipeline.py
        assembly.py
        runtime.py
        workflow_codec.py
  distribution/
    model/public/
      paths.py
      runtime.py         BuildRuntime
    languages/
      annotations/
      expressions/
      data/
      topology/
      binding/
    interpreter/
      model/public/graph_blueprint.py
      service/public/create.py
      service/internal/adapters/kernel_linker.py
      service/_private/
    planners/
      core/
      deduplication/
      merging/
      conflict_validation/
    executors/
      model/
        public/
        internal/
      service/
        public/
        internal/
        _private/
      runtime/
      duckdb/
      python/
      file/
      meta_graph/
      neo4j/
      conflict_validation/
    service/              the distribution leaf's service zone
      public/create.py
      internal/rendering.py
      _private/rendering.py
    default.py           DEFAULT_TOOLCHAIN / default_toolchain
  generation/
    code_generation/
  api.py                 create_blueprint, compile, execute
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
distribution/languages -> kernel
distribution/interpreter -> distribution/languages, kernel
distribution/planners -> distribution/interpreter, distribution/languages, kernel
distribution/executors -> distribution/model, distribution/languages, kernel
distribution/default -> distribution/planners, distribution/executors, distribution/interpreter
generation/code_generation -> kernel
api.py -> distribution, kernel
cli -> generation, api.py
```

The primary edges are:

| Package | May import |
| --- | --- |
| `kernel` | no framework package |
| `distribution/languages/annotations` | `kernel` |
| `distribution/languages/expressions` | `kernel` |
| `distribution/languages/data` | `kernel`, annotations, expressions |
| `distribution/languages/topology` | `kernel`, annotations, expressions |
| `distribution/languages/binding` | `kernel`, annotations, data, topology |
| `distribution/interpreter` | `kernel`, every graph language |
| `distribution/planners/*` | `kernel`, `distribution/interpreter`, distribution languages; the core planner also uses the DuckDB SQL emitter |
| `distribution/executors/*` | `kernel`, distribution model, distribution languages; the conflict-report executor reuses the planner's report values |
| `distribution/default.py` | `kernel`, interpreters, planners, executors |
| `generation/code_generation` | `kernel` |
| `api.py` | `distribution`, `kernel` |
| `cli` | `generation`, `api.py` |

The kernel imports no graph, data, topology, binding, SQL, DuckDB or Python
package. Another package imports a leaf's `model.public`, `model.internal`,
`service.public` or `service.internal`; it never imports a private zone.

## The three verbs

| Verb | Input | Output |
| --- | --- | --- |
| `build` | a `Namespace` of declarations | one linked model |
| `compile` | the linked model | `WorkflowPlan` |
| `execute` | the plan and an output directory | `WorkflowReport` |

`build` orders languages by `requires`, transcribes and validates each layer and
calls `linker.link(layers)`. `compile` calls every planner, assigns its
`component_id` to each step and assembles the steps into one plan. `execute`
maps each executor's exact instruction kinds, creates services and calls the
runtime.

The public API is `create_blueprint`, `compile` and `execute`. `compile` returns a
`WorkflowPlan`; `execute` takes that plan and an output directory.
