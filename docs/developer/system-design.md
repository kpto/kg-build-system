# System design

The framework is organised around three systems and a shared kernel. The tree
below is the implemented layout; it states which package owns which decision.

## The package tree

```text
kg_build_system/
  kernel/
    public/types/
    public/language.py
    public/module.py
    public/capability.py
    public/build.py
    public/contract.py
    internal/types/
    internal/json.py
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
      compiler/
      relational/
      instruction/
    build/
      runtime/
      engine/
      targets/
      storage/
      relations/
  distribution/
    modules/
  generation/
    code_generation/
  api.py
  cli/
```

Every leaf has `__init__.py`, `public/`, `internal/` and `_private/`. A leaf with
nothing author-facing still has a `public/` that states that; it does not invent a
facade.

## Kernel

`kg_build_system.kernel` is the only domain-agnostic package. It imports no
other framework package.

The kernel holds what every system needs and cannot replace:

- the `Language` and `Module` protocols;
- canonical types;
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

`Language` has no `encode`/`decode`. Serialisation belongs to the DTO codec, which
names its artifact with `to_document` and `from_document`.

### Canonical types

Canonical types live in `kernel/public/types/`. The authoring alias is
`kg_build_system.types`; an author imports that name, while every layer, the
blueprint and the contract use the same type ontology.

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

| Leaf | Responsibility |
| --- | --- |
| `foundations/annotations` | annotation values and annotation DTOs |
| `foundations/expressions` | expression and selection authoring, operation specifications and expression DTOs |
| `languages/table` | tables, structs, projections, row sources and the data DTO |
| `languages/topology` | nodes, edges, properties and the graph DTO |
| `languages/binding` | node and edge bindings and the binding DTO |
| `blueprint` | assembles layer DTOs into `GraphBlueprint` and renders blueprint source |

A language collects its declarations, transcribes them to its DTO and renders
that DTO back to source. `expressions` contributes operation specifications and
expression DTOs; it is not a language and does not own a build part.

The blueprint package owns the assembly decision, not the layer decisions. It
delegates transcription and rendering to each language, then combines the
results.

## Pipeline

`pipeline/` groups the three systems that share the contract.

| System | Leaf | Responsibility |
| --- | --- | --- |
| Contract | `pipeline/contract` | the `WorkflowContractDTO`, steps, instructions, connections and provenance |
| Compilation | `pipeline/compilation/compiler` | module compilers and blueprint decomposition |
| Compilation | `pipeline/compilation/relational` | engine-neutral relation plans |
| Compilation | `pipeline/compilation/instruction` | instruction emission |
| Build | `pipeline/build/runtime` | step execution and failure propagation |
| Build | `pipeline/build/engine` | SQL and engine-specific emission |
| Build | `pipeline/build/targets` | target outputs |
| Build | `pipeline/build/storage` | working and output storage |
| Build | `pipeline/build/relations` | relation services |

Compilation reads a blueprint and produces a contract. Build reads a contract
and executes it. They share the contract and must not import each other.

The contract owns structure: steps, inputs, outputs, connections and provenance.
A step owns its instruction. SQL is one instruction kind, not a contract field.

## Distribution

`distribution/modules/` contains the supplied modules and their registration.
`kg_build_system.distribution` exports the supplied module classes and
`register_module`. A module owns a compiler and an executor. The core module is a
module, not a domain package.

Registration records a module class and its frozen configuration. It does not
import the implementation at registration time and does not hold a live service.
The composition root appends the core module after the supplied modules.

## Generation

`generation/code_generation/` is the edit-time lane. It turns typed requests into
declarations before declaration runs. It is upstream of the blueprint.

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
| `distribution/modules` | `kernel`, `declaration`, `pipeline/contract`, `pipeline/compilation`, `pipeline/build` |
| `generation/code_generation` | `kernel`; engine observation is read-only |
| `api.py` | declaration, pipeline, distribution |
| `cli` | `generation`, `api.py` |

Two rules apply to every row:

- compilation and build do not import each other;
- no package imports another package's `_private`.

The exact edge set is a model decision. A new edge is proposed with its reason,
not added because a call site needs it.

## Leaf layout

Every leaf uses the same four-part layout.

| Zone | Reader | May be imported by | Holds |
| --- | --- | --- | --- |
| `pkg` | graph author | any package | facade over `public` |
| `pkg.public` | graph author | any package for authoring names and frozen type vocabulary | declarations, values and thin wrappers |
| `pkg.internal` | framework code | any package | DTOs, models, services and cross-package protocols |
| `pkg.internal.adapters` | framework code | the package that owns the protocol | one file per foreign protocol |
| `pkg._private` | its own package | no other package | mechanisms |

`internal/` contains these sub-zones where applicable:

| Sub-zone | Contents |
| --- | --- |
| `dto/` | serialisable members of the blueprint or contract |
| `model/` | in-memory frozen models |
| `service/` | transcription, rendering, planning and other transformations |
| `adapters/` | implementations of a foreign protocol |

A public function or method is a thin wrapper over `_private` or `internal`, with
a user-facing docstring and a runnable `Example:`. The mechanism is not in
`public`. Internal and private functions carry developer docstrings and need no
example.

A protocol implementation is a separate file under `internal/adapters/<protocol>.py`.
The file names the protocol, imports the foreign protocol and delegates to
`_private`. It is not buried in a model or factory.

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

- 61 tests passed, 306 subtests.
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
- Declaration produces the blueprint; compilation consumes it; build consumes
  the contract.
- Compilation and build share the contract and never import each other.
- A leaf has `public`, `internal` and `_private`; a foreign protocol has an
  explicit adapter.
- A step owns its instruction; SQL is one instruction kind.

Next: [Data and expressions](data-and-expressions.md).
