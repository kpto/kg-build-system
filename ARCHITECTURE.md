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
                         AssetRef, OperationRef, Ref
        runtime.py       BuildRuntime
        paths.py
    languages/
      annotations/
      expressions/
      asset/
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
  __init__.py             top-level lazy export table and __getattr__
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
`__init__.py` holds the lazy export table, `__getattr__` and a literal `__all__`;
every leaf `__init__.py` is a facade of docstring, imports and `__all__`.

## Dependency spine

An arrow means "may import".

```text
distribution/languages -> kernel
distribution/interpreter -> distribution/languages, kernel
distribution/modules -> distribution/interpreter, distribution/languages,
                        distribution/model, distribution/service, kernel
generation/code_generation -> distribution/languages.asset, kernel
distribution/implementations -> distribution/languages, distribution/interpreter
api.py -> distribution, kernel
cli -> generation, api.py
```

The primary edges are:

| Package | May import |
| --- | --- |
| `kernel` | no framework package |
| `distribution/languages/annotations` | `kernel` |
| `distribution/languages/expressions` | `kernel` |
| `distribution/languages/asset` | `kernel`, annotations |
| `distribution/languages/data` | `kernel`, annotations, expressions, asset |
| `distribution/languages/topology` | `kernel`, annotations, expressions |
| `distribution/languages/binding` | `kernel`, annotations, data, topology |
| `distribution/interpreter` | `kernel`, every graph language |
| `distribution/modules/<name>` | `kernel`, `distribution/interpreter` where it reads a blueprint, distribution languages, `distribution.model` and `distribution.service`; the core module uses the neutral relation plan and `SqlEmitter` protocol, not the DuckDB module |
| `distribution/implementations.py` | `kernel`, interpreter, languages |
| `generation/code_generation` | `kernel`, `distribution.languages.asset` |
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

Core planners live under
`distribution/modules/core/<feature>/service/public/planner.py` with each
feature's implementation under `service/_private/`. Shared planning
stays in `core/service/_private/planning/`. Core consumes the neutral relation
plan and `SqlEmitter` protocol from `distribution/service/internal`; DuckDB
implements the protocol, and core imports no DuckDB module.

## Authoring model

`Selection[T]` is the single authoring type; `NullableSelection[T]` is
`Selection[Nullable[T]]`. A `Field[T]` declares a value type and never encodes
absence. A source `Table` or source `Struct` read yields `NullableSelection[T]`; a
computed `Projection` or `ComputedStruct` read yields the type of its
`computed_field` selection. `Table` and `Projection` are row-source providers:
use `Table.row_source()` / `Projection.row_source()`, and pin a projection with
`Projection(source)`. `alter_rows()` is the one-shot row-effect gate;
`lookup`, `zip` and `RowSource.unnest` complete the relation and array surface.
A language reports authoring references with `get_references` and transcribes
per declaration with `transcribe`.
