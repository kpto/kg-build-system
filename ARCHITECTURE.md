# Architecture

This file is the implementation map. The model, interfaces and design decisions
are in [docs/developer/system-design.md](docs/developer/system-design.md).

## Current tree

```text
kg_build_system/
  kernel/
    model/
      public/
        key.py           Key
        language.py      Declaration, Key, Language, Namespace,
                         ReferenceResolver, RenderContext, SourceFragment,
                         Symbol, SymbolContext, SymbolRef
        symbol.py        Declaration, Symbol, SymbolContext, SymbolRef
        workflow.py      Instruction, Step, WorkflowPlan
        runtime.py       ExecutionContext, ResourceView, StepOutcome,
                         WorkflowReport
        types/
      internal/
        json.py
        types/dto.py
      _private/
        types/
    service/
      public/
        pipeline.py      Linker, Planner, StepExecutor, Runtime, Resource,
                         ResourceProvider, Toolchain, Extension, PlanContext
        runtime.py       WorkflowRuntime
      internal/
        pipeline.py
        workflow_codec.py
      _private/
        pipeline.py
        assembly.py
        runtime.py
        workflow_codec.py
  distribution/
    model/
      public/
        refs.py          NodeRef, EdgeRef, RelationRef, FieldRef, PropertyRef,
                         SourceRef, OperationRef, Ref
        runtime.py       BuildRuntime
        paths.py
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
    modules/
      core/
      deduplication/
      merging/
      conflict_validation/
      file/
      meta_graph/
      neo4j/
      duckdb/
      python/
      runtime/
    service/              the distribution leaf's service zone
      public/create.py
      internal/{execution,relations,rendering}.py
      _private/{execution,rendering}.py
    implementations.py    language and linker implementations
  generation/
    code_generation/
  _facade.py              top-level lazy export table
  api.py                  default_toolchain, DEFAULT_TOOLCHAIN,
                          create_blueprint, compile, execute
  cli/
```

Every leaf uses the zones it needs from `model/` and `service/`:

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

`model.public` and `model.internal` import no service or private code.
`service.public` imports `model.public` and `service.internal`.
`service.internal` imports model data and uses function-local imports for
`service._private`. `service._private` may read model data and other private
service code, but not `service.public`.

A leaf contains only the zones it uses. An empty zone is deleted. The top-level
`__init__.py` delegates to `_facade.py`; every other `__init__.py` is a facade of
docstring, imports and `__all__`.

## Dependency spine

An arrow means "may import".

```text
distribution/languages -> kernel
distribution/interpreter -> distribution/languages, kernel
distribution/modules -> distribution/interpreter, distribution/languages,
                        distribution/model, distribution/service, kernel
distribution/implementations -> distribution/languages, distribution/interpreter
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
| `distribution/modules/<name>` | `kernel`, `distribution/interpreter` where it reads a blueprint, distribution languages, `distribution.model` and `distribution.service`; the core module also uses the DuckDB SQL emitter |
| `distribution/implementations.py` | `kernel`, interpreter, languages |
| `generation/code_generation` | `kernel` |
| `api.py` | `distribution`, `kernel` |
| `cli` | `generation`, `api.py` |

The kernel imports no graph, data, topology, binding, SQL, DuckDB or Python
package. Another package imports a leaf's `model.public`, `model.internal`,
`service.public` or `service.internal`; it never imports a private zone.

## The three verbs

| Verb | Input | Output |
| --- | --- | --- |
| `build` | a `Namespace` of declarations through a `Linker` | one linked model |
| `compile` | the linked model | `WorkflowPlan` |
| `execute` | the plan and an output directory | `WorkflowReport` |

`build` hands the languages and namespace to the linker. The linker discovers
declarations, derives keys with `compute_key`, transcribes symbols, resolves
references and assembles the model. `compile` groups planners by `component_id`,
assigns the component to each step and assembles the steps into one plan.
`execute` maps each executor's exact instruction kinds, lets the runtime open the
resource providers and dispatches steps through the executors.

The public API is `create_blueprint`, `compile` and `execute`. `compile` returns a
`WorkflowPlan`; `execute` takes that plan and an output directory.
