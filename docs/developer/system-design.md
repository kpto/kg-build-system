# System design

The framework is organised around three systems and a shared kernel. Every
framework leaf uses the same model/service layout; the tree below states which
package owns which decision.

## The package tree

```text
kg_build_system/
  kernel/
    model/
      public/types/
      internal/types/
      internal/json.py
      _private/
    service/
      public/language.py
      public/module.py
      public/capability.py
      public/build.py
      public/contract.py
      public/registry.py
      internal/
      _private/
  declaration/
    foundations/annotations/
    foundations/expressions/
    languages/table/
    languages/topology/
    languages/binding/
    blueprint/
  pipeline/
    contract/
    compilation/
    build/
  distribution/
  generation/code_generation/
  api.py
  cli/
```

Every leaf contains `model/` and `service/`:

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

A leaf with no author-facing names still states that in its public model and
service surfaces; it does not invent a facade.

## Kernel

`kg_build_system.kernel` is the only domain-agnostic package. It imports no
other framework package.

The kernel holds what every system needs and cannot replace:

- the `Language` and `Module` protocols in `kernel/service/public`;
- canonical types in `kernel/model/public/types`;
- build values and the language registry mechanism;
- contract vocabulary: artifact types, inputs, outputs, steps, connections,
  execution contexts and outcomes;
- capability declarations.

```python
class Language(Protocol):
    name: str
    requires: tuple[str, ...]
    def collect(self, namespace: Namespace) -> Sequence[object]: ...
    def transcribe(self, declarations, context) -> Any: ...
    def validate(self, dto) -> None: ...
    def render(self, dto, context) -> SourceFragment: ...

class Module(Protocol):
    ID: str
    VERSION: str
    CONFIGURATION_TYPE: type
    @classmethod
    async def create_compiler(cls, context) -> Compiler | None: ...
    @classmethod
    def create_executor(cls, context) -> Executor | None: ...
```

`Language` has no `encode`/`decode`. Serialisation belongs to the DTO codec,
whose service interface uses `to_document` and `from_document`.

### Canonical types

Canonical types live in `kernel/model/public/types/`. The authoring vocabulary is
re-exported by `kg_build_system`; an author imports that name, while every layer,
the blueprint and the contract use the same type ontology.

A layer does not define its own type vocabulary. A table field, a topology
property, an expression result and a contract artifact all refer to the same
canonical types.

### Capability versus library

A **capability** is a contract declaration. The policy is that a module states
the capabilities it requires and provides, and composition checks that the
required capabilities are available. A capability names an ability, not an
implementation, a class or a live service.

The kernel defines `Capability`, but the current `Module` protocol does not
expose `requires`/`provides`; module composition does not enforce capabilities.
Capability modules are deferred.

A **library** is a replaceable implementation. The DuckDB engine, the code
generation providers and the supplied target modules are libraries. They are
selected by composition, not baked into the kernel.

The policy follows from that distinction:

- a package moves to the kernel only when every system needs it and cannot
  replace it;
- a package shared only inside one system stays in that system;
- a library is not a kernel package merely because several layers use it.

## Declaration

`declaration/` turns authoring declarations into one semantic blueprint.

| Leaf | Model | Service |
| --- | --- | --- |
| `foundations/annotations` | annotation values; `model/internal/dto` | codec and source rendering |
| `foundations/expressions` | expression and selection values; expression DTOs | construction, operation specifications, codec and source rendering |
| `languages/table` | tables, structs, projections, row sources; data DTO | field and source wrappers, transcription, codec and source rendering |
| `languages/topology` | nodes, edges, properties; graph DTO | property and endpoint wrappers, transcription, codec and source rendering |
| `languages/binding` | binding values; binding DTO | `node_binding`/`edge_binding`, transcription, codec and source rendering |
| `blueprint` | `GraphBlueprint` | `create_blueprint`, assembly, validation, codec and blueprint source |

A language collects its declarations, transcribes them to its DTO and renders
that DTO back to source. `expressions` contributes operation specifications and
expression DTOs; it is not a language and does not own a build part.

The blueprint service owns the assembly decision, not the layer decisions. It
delegates transcription and rendering to each language, then combines the
results.

## Pipeline

`pipeline/` groups the three systems that share the contract.

| System | Leaf | Responsibility |
| --- | --- | --- |
| Contract | `pipeline/contract` | `WorkflowContractDTO` in `model/public`; assembly and codec in `service/internal` and `service/_private` |
| Compilation | `pipeline/compilation` | relation plans and instruction kinds in `model/internal`; `compile_blueprint` in `service/public`; compilers and instruction emitters in `service/internal` and `service/_private` |
| Build | `pipeline/build` | `BuildRuntime` and `WorkflowReport` in `model/public`; `build` in `service/public`; runtime, engine, storage and relations in `service/_private` |

Compilation reads a blueprint and produces a contract. Build reads a contract
and executes it. They share the contract and must not import each other.

The contract owns structure: steps, inputs, outputs, connections and provenance.
A step owns its instruction. SQL is one instruction kind, not a contract field.

## Distribution

`distribution/` contains the supplied modules and their registration.

| Surface | Contents |
| --- | --- |
| `model/public` | module configurations and supplied module declarations |
| `model/internal` | module model and instruction DTOs |
| `service/public` | supplied module classes and `register_module` |
| `service/internal` | registration and module service interfaces |
| `service/_private` | compilers, executors and module mechanisms |

A module owns a compiler and an executor. The core module is a module, not a
domain package. Registration records a module class and its frozen configuration;
it does not import the implementation at registration time and does not hold a
live service. The composition root appends the core module after the supplied
modules.

## Generation

`generation/code_generation/` is the edit-time lane. It turns typed requests into
declarations before declaration runs. It is upstream of the blueprint.

| Surface | Contents |
| --- | --- |
| `model/public` | generation requests and result models |
| `model/internal` | provider contract and discovery models |
| `model/_private` | generated render model |
| `service/public` | `generation`, `generate`, `discover`, `watch` |
| `service/internal` | provider loading and provider adapters |
| `service/_private` | discovery, rendering, ownership, watcher and engine |

Generation and compilation are separate lanes:

- generation observes a source, runs a provider and renders declarations;
- compilation imports the resulting declarations and never invokes generation;
- build never invokes generation.

A generated declaration and a handwritten declaration enter the same blueprint
and contract path. There is no generation-specific compilation path.

## Dependency spine

The tree shows the primary dependency spine. A tree cannot encode every edge;
the dependency tests enforce the rest. The spine runs outward from the kernel:
declaration depends on the kernel, pipeline depends on declaration and shares the
contract, distribution depends on pipeline, and `api.py`/`cli` compose them.
Generation is upstream and does not sit on the execution spine.

| Package | May import |
| --- | --- |
| `kernel` | no framework package |
| `declaration/foundations/*` | `kernel` |
| `declaration/languages/table` | `declaration/foundations`, `kernel` |
| `declaration/languages/topology` | `declaration/foundations`, `kernel` |
| `declaration/languages/binding` | `declaration/languages/table`, `declaration/languages/topology`, `declaration/foundations`, `kernel` |
| `declaration/blueprint` | every declaration language and foundation, `kernel` |
| `pipeline/contract` | `kernel` |
| `pipeline/compilation` | `declaration` (blueprint and DTOs), `pipeline/contract`, `kernel` |
| `pipeline/build` | `pipeline/contract`, `kernel` |
| `distribution` | `kernel`, `declaration`, `pipeline/contract`, `pipeline/compilation`, `pipeline/build` |
| `generation/code_generation` | `kernel`; engine observation is read-only |
| `api.py` | declaration, pipeline, distribution |
| `cli` | `generation`, `api.py` |

Two rules apply to every row:

- compilation and build do not import each other;
- no package imports another package's private zones.

The exact edge set is a model decision. A new edge is proposed with its reason,
not added because a call site needs it.

## Leaf layout and import matrix

| Zone | Reader | May be imported by | Holds |
| --- | --- | --- | --- |
| `pkg` | graph author | any package | facade over `model.public` and `service.public` |
| `pkg.model.public` | graph author | any package for authoring names and frozen type vocabulary | authoring models, returned values and public DTOs |
| `pkg.model.internal` | framework code | any package for cross-package data | `dto/` and `model/` data |
| `pkg.model._private` | its own package | no other package | private plans, render models and SQL types |
| `pkg.service.public` | graph author | any package for service interfaces | authoring methods and thin wrappers |
| `pkg.service.internal` | framework code | any package for service interfaces | codec and assembly wrappers, adapters |
| `pkg.service._private` | its own package | no other package | codecs, transcription, rendering, validation, assembly, planning, engines and runtime |

The import matrix is part of the layout:

| Source | May import | Must not import |
| --- | --- | --- |
| `model.public` | model data | any service or `_private` |
| `model.internal` | model data | any service or `_private` |
| `model._private` | `model.public`, `model.internal` | service |
| `service.public` | `model.public`, `service.internal` | `_private` |
| `service.internal` | model data; `service._private` with function-local imports | `service.public` |
| `service._private` | `model.public`, `model.internal`, `model._private`, `service._private` | `service.public` |

Another package imports `pkg.model.public`, `pkg.model.internal`,
`pkg.service.public` or `pkg.service.internal`. It never imports
`pkg.model._private` or `pkg.service._private`.
`_private` may use public model data but not public service behaviour.

A public function or method is a thin wrapper over `service.internal` or
`service._private`, with a user-facing docstring and a runnable `Example:`. The
mechanism is not in `service.public`. Internal and private functions carry
developer docstrings and need no example.

A protocol implementation is a separate file under
`service/internal/adapters/<protocol>.py`. The file names the protocol, imports
the foreign protocol and delegates to `service._private`. It is not buried in a
model or factory.

No `model.public`, `model.internal`, `service.public` or `service.internal`
module defines a single-underscore helper; dunder protocol methods remain. A
codec is a service: interface in `service.internal`, implementation in
`service._private`. A DTO is a model: `model.internal/dto`, or `model.public` for
a public artifact.

## Blueprint and compile are separate

`create_blueprint` takes no modules:

```python
blueprint = create_blueprint(
    namespace_path=None,
    bindings=(),
    sources=(),
    languages=None,
)
```

`compile_blueprint` reads that blueprint and a module composition:

```python
contract = compile_blueprint(blueprint, modules=modules, engine=None)
```

`create_blueprint` returns a `GraphBlueprint`. It collects declarations, runs the
languages, assembles the layer DTOs and validates the result.

`compile_blueprint` reads a `GraphBlueprint` and returns a
`WorkflowContractDTO`. It does not assemble a blueprint and does not call the
blueprint package.

`compile(...)` is the canonical shortcut. It creates the blueprint, appends the
core module and calls `compile_blueprint`; the caller never sees the blueprint
unless they ask for it.

The separation matters because the blueprint is inspectable and reusable. A
caller may store it, render it back to source or compile it with a different
module composition. Compilation is one consumer of the blueprint, not its owner.

## Contract, step and instruction

The workflow contract is the only value handed from compilation to execution.

```python
@dataclass(frozen=True)
class InstructionDTO:
    kind: str
    payload: JsonValue

@dataclass(frozen=True)
class StepDTO:
    name: str
    inputs: tuple[InputDTO, ...]
    outputs: tuple[GivenDTO, ...]
    instruction: InstructionDTO
    assembly_preference: Literal["eager", "deferred"] = "eager"
```

- The contract owns contributions, steps, connections and provenance.
- A step owns its instruction.
- `InstructionDTO.kind` selects the executor; `payload` is opaque to the contract.
- SQL is one instruction kind. A Python instruction is a stable reference, not a
  live callable.
- A module compiler emits instructions through an `InstructionEmitter`; adding an
  instruction kind does not edit a contract field.

Compilation decomposes the blueprint into an in-memory build, runs module
compilers, emits instructions and assembles the contract. Build dispatches on
`instruction.kind` and executes steps.

## Current state and limits

The tree above is the implementation.

- 69 tests passed, 484 subtests.
- Pyright: 0 errors.
- Open Targets: 6 tests passed.

The remaining limits are:

| Limit | Current choice |
| --- | --- |
| Capability modules are deferred. | `Capability` exists in `kernel`, but `Module` does not declare `requires`/`provides`; composition does not enforce capabilities. |
| DuckDB is the default SQL emitter. | `DuckDbSqlEmitter` is the default SQL library; another engine supplies another emitter. |
| A Python binding source is a reference. | The blueprint stores `PythonRefDTO(module, qualname, signature)`, not the callable body. |
| Some target executors still adapt instructions into `variables`. | The build target adapter copies the step's instruction payload into `variables["instructions"]` before calling those executors. |
| Public `GraphBlueprint` fields reference internal layer DTOs. | `GraphBlueprint` is public; its `graph`, `data`, `bindings` and `sources` fields are typed by layer DTOs that are not exported public names. |

See [data and expressions](data-and-expressions.md) for the DTO shapes and the
source round trip.

## What to remember

- The kernel is domain-agnostic and holds only what cannot be replaced.
- Every leaf has a model side and a service side; public surfaces are
  `model.public` and `service.public`.
- Declaration produces the blueprint; compilation consumes it; build consumes
  the contract.
- Compilation and build share the contract and never import each other.
- A service adapter is an explicit file under `service/internal/adapters`.
- A step owns its instruction; SQL is one instruction kind.

Next: [Data and expressions](data-and-expressions.md).
