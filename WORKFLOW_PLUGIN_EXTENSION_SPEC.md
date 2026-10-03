# Workflow Module Extension — Specification

## Status

This specification covers extending the system with a workflow module: what a module
declares, how it is registered and configured, which artifact types it shares with core,
and how a target interprets topology annotations. The workflow subpackage itself — its
data model, its assembly rules, its contract and its execution — is specified in
[`WORKFLOW_SUBPACKAGE_SPEC.md`](WORKFLOW_SUBPACKAGE_SPEC.md), which governs wherever the
two differ.

## Purpose and invariants

A build is an immutable, serialisable workflow assembled from ordered module
contributions. Workflow modules may contribute source acquisition, transformation,
post-processing, validation, target actions, reporting, or cleanup. These are all
workflow steps; no role receives special scheduling treatment.

- Core graph semantics remain target independent.
- The complete workflow is inspectable and frozen before runtime execution.
- Modules receive compiled definitions and runtime configuration, never authoring
  Python classes.
- Contracts retain credential references only; resolved credentials are runtime-only.
- Modules may consume core artifacts and publish module-owned artifacts. Core is a
  module contributing ordinary workflow steps; connections may make any step depend on
  any compatible producer. Modules may not change the canonical graph semantics
  represented by compiled definitions.

## Module identity, registration, and configuration

Each workflow-module class has a stable, static module ID. The ID is semantic: it is the
module's namespace for its steps, its openings, its artifact types, its runtime
configuration, and the annotations it owns. Module IDs, runtime field keys, and artifact
type namespaces are lower-case with underscores. A compiled workflow contains at most one
configured instance of a module ID.

An author supplies module registrations to `compile`; they are part of the complete
declared build intention. A registration holds a module class and serialisable,
non-secret registration configuration. The blueprint records import coordinates for that
class and the registration configuration, never a Python object. At compilation the
compiler re-imports and reconstructs each registration, verifies the class's static ID,
and rejects classes that cannot be reliably re-imported.

Compilation produces distinct module-reference configuration for execution. The module
owns that transformation: execution configuration may equal the registration
configuration and need not. At runtime the executor imports that class and delegates step
execution to it. Python class or module objects are never stored in a blueprint or a
workflow contract.

Modules are supplied in a uniquely ordered list, and that order is the author's priority
statement: the assembler derives each step's rank from it, so a step of an earlier module
runs before any step of a later one. The public API appends the mandatory core module
last, which makes core the least preferred producer without storing a numeric priority
anywhere. Core composing last also means an extension module's refined output outranks
core's, so a target that asks for a family of types is fed by the module that improved
them.

There is no target configuration or target-specific policy in the workflow model. A file
writer, database writer, source reader, validator, or cleanup provider is a workflow
module. Modules may inspect canonical topology annotations, but no central annotation
policy interprets them on their behalf.

## What the contract carries

> [WORKFLOW_SUBPACKAGE_SPEC.md](WORKFLOW_SUBPACKAGE_SPEC.md) §2, 6 — the declared data and its serialisable form.

The contract contains only immutable, serialisable definitions. The executor resolves
each compiled module reference to its Python implementation at runtime, and the
implementation object itself is never serialised.

Serialisable compilation IRs are owned by `workflow.ir`; module behaviour, assembly, and
execution use the frozen domain models in `workflow.models`. Mapping happens once when the
contract is frozen and once when execution begins. IRs are never handed to module
executors or retained by runtime contexts.

`ModuleRegistration.configuration` is compile-time input only, and must be serialisable
and non-secret. `ModuleReference.configuration` is serialisable execution configuration
produced by that module's compiler; it is not implied to be a copy of the registration
configuration, because the module owns the mapping. Runtime configuration stays separate
and is supplied only at execution.

`CompilationContext` is the single generic compile-time context, used by every module
including core. It exposes the blueprint, the module identity, and that module's
reconstructed non-secret registration configuration, and never authoring classes. Source
bindings are declarations on the blueprint and are not duplicated in the context.
Assembly priority belongs to the ordered module list and is not module configuration.

Supporting two independently configured instances of one implementation class would need
a module designed to accept multiple declared outputs or an explicit module-instance
identity; one ID means one instance. `import_module` and `class_qualname` are operational
import coordinates, not semantic namespaces. `implementation_version` is a package
version or other stable implementation fingerprint, checked at execution against the
compiled value, which rejects an incompatible runtime implementation.

Runtime configuration values are not stored in the contract; the contract records their
definitions and execution supplies values per module ID and field key. A `secret` field
must never enter module variables, published artifacts, manifests, or fingerprints.

## Module interfaces

> [WORKFLOW_SUBPACKAGE_SPEC.md](WORKFLOW_SUBPACKAGE_SPEC.md) §7 — the executor protocol.

Ownership follows the capability boundary. `compile.interfaces` defines the compiler
protocol and the compilation context, `workflow.interfaces` defines the executor
protocol, and `modules.interfaces` combines them for public module implementations and
registrations:

```python
@dataclass(frozen=True, slots=True)
class CompilationContext[ConfigT]:
    blueprint: BuildBlueprint
    module_id: str
    configuration: ConfigT


class ModuleCompiler(Protocol):
    async def compile(self, context: CompilationContext[Any]) -> WorkflowContribution: ...


class ModuleExecutor(ABC):
    def handle(self, context: ExecutionContext) -> StepOutcome: ...
    def handle_disrupted(self, context: DisruptedExecutionContext) -> StepOutcome: ...


class Module(ABC):
    ID: ClassVar[str]
    VERSION: ClassVar[str]
    CONFIGURATION_TYPE: ClassVar[type[ModuleRegistrationConfiguration]]

    @classmethod
    async def create_compiler(cls, context: CompilationContext[Any]) -> ModuleCompiler: ...
    @classmethod
    def create_executor(cls, context: ExecutorFactoryContext) -> ModuleExecutor: ...


@dataclass(frozen=True, slots=True)
class ModuleRegistration(Generic[ConfigT]):
    module_class: type[Module]
    configuration: ConfigT
```

`compile` builds its blueprint internally, serialises registrations into blueprint module
entries, reconstructs them, calls `create_compiler`, and calls `ModuleCompiler.compile`.
The returned `WorkflowContribution` carries the serialisable module definition, the
declared steps, and the module's own `variables`. Compilation preserves contribution
order and hands expansion, connection, ambiguity refusal and completeness to the
assembler: a module states what it takes and gives out and never names a producer. Only
the resulting serialisable workflow enters the contract.

At runtime the executor validates and supplies runtime configuration, combines it with the
compiled `ModuleReference` and the module's variables, and calls `create_executor` once
per module; the returned executor handles every step of that module. It receives compiled
reference configuration, never registration configuration.

## Openings, artifacts, and publications

> [WORKFLOW_SUBPACKAGE_SPEC.md](WORKFLOW_SUBPACKAGE_SPEC.md) §2, 3 — openings and their expansion into ports.

Every module declares all of its steps before assembly begins. A declared step carries no
dependency list: connections are its only dependencies. It may take nothing, give out
nothing, or both.

An opening names one artifact type and, optionally, what the step calls it. An `Input`
naming a type with `*` in either half is an open input, and the assembler expands it into
one port per type it finds in the build, each fed by one output. That is how a module
takes a family of artifacts without knowing which steps produced them: a writer asks for
`core / graph.*` and receives one port per graph-record type the build writes. A module
learns what an open input matched only at execution, by which keys arrived in its context,
so a handler should default to empty rather than assume a match.

An artifact may be a relation, a CTE, a stream, module-owned findings, an
external-resource handle, a manifest, a report, or any other serialisable product. The
logical artifact and its physical materialisation are distinct, and an artifact type is
semantic: it carries no physical path, source location, or producer identity. A
passthrough step such as a validator consumes an artifact and declares a new opening of
the same type even when it reuses the same physical relation.

A declared opening may produce no runtime artifact when the step has nothing meaningful
to give out. Consumers therefore treat a missing artifact as a valid possibility. One
opening may feed any number of readers.

A value a module hands to the build itself is declared as a `Publication`, which sits with
the step's outputs and is exempt from the rule that every output is read. Publication is
read off that declaration; nothing is inferred from a type name. A validator may expose
its findings as an ordinary output, aggregate them into a module-owned report, and
publish that report. Whether findings gate the build is the validator's own
configuration.

## What assembly guarantees a module can rely on

> [WORKFLOW_SUBPACKAGE_SPEC.md](WORKFLOW_SUBPACKAGE_SPEC.md) §3–5 — expansion, rank, and the assembly passes.

A workflow assembles only when every input is fed and every output is read, so a module
that writes an artifact someone must consume needs a consumer in the composition:
compiling core, or any producing module, on its own is a build failure naming the
openings nothing reads. A step may not read what it writes, and no connection may close a
cycle, so a module that wants a later stage's records declares the type it takes and lets
rank decide the writer.

Higher priority means earlier in the declared module list, and core is appended last so
extension modules outrank it. A module that needs a specific producer cannot ask for one;
it states a type that only that producer writes. Two producers of one type that differ by
nothing the declarations state leave the build incomplete, which is the author's signal to
name the type more precisely.

## Execution expectations

> [WORKFLOW_SUBPACKAGE_SPEC.md](WORKFLOW_SUBPACKAGE_SPEC.md) §7 — scheduling, disruption, and failure resolution.

There are no privileged scheduling roles. A beginning step is an ordinary step with no
inputs; a termination step is an ordinary step with no outputs; a workflow may have any
number of each. Cleanup is an ordinary step too: it declares explicit inputs on the work
or the failure-aware artifacts it needs and gets no hidden scheduling position.

Each executor has two input-state handlers. `handle` runs only when every connected
producer succeeded or warned. `handle_disrupted` runs when any connected producer failed
or was skipped, and its base implementation skips the step, so a module that wants that
policy opts in with `return super().handle_disrupted(context)`. A module may instead
recover by returning success or warning, emit failure-aware artifacts, publish a report,
or fail deliberately. A failed or skipped step still completes and passes its state
downstream; unhandled exceptions from either handler become failed outcomes. Runtime
never adds steps.

Outcomes are checked against the frozen declaration: they must answer the step they were
asked for, artifacts may appear only on declared openings, and each artifact's type must
be what that opening declares. An outcome carries a status, zero or more artifacts, and an
optional `Failure`, which describes a step that could not complete its work. Recovery is
not a fifth status: a disrupted handler recovers by returning success or warning. There is
no workflow-level diagnostic model.

Failures travel to the end of the graph because every output has a reader. Those still
active at a step that publishes are reported unresolved, the rest are recovered, and a
report succeeds when nothing is unresolved.

## Runtime services

> [WORKFLOW_SUBPACKAGE_SPEC.md](WORKFLOW_SUBPACKAGE_SPEC.md) §7 — the facilities handed to a module.

A module's context supplies the compiled module definition, the declared step, that
step's identity and its module's, the module's variables, resolved runtime
configuration, the artifacts arriving on each declared input, and the shared services.
It exposes no registration configuration, no authoring classes, and no compiler state.
Inputs are keyed by the input names the module declared, so the ports an open input grew
into arrive together. Nothing selects or re-resolves at runtime: execution uses only the
connections frozen in the contract.

Services expose an executor-owned, DuckDB-specific relation service. This is a lifecycle
boundary rather than an engine-neutral relational model: module compilers still emit
DuckDB SQL, while module executors ask the service to define lazy views or materialise
reuse boundaries, run queries, export Parquet, and register filesystems. The service
returns opaque runtime-only `RelationRef` values that always identify public views; a
materialised relation uses a private backing table hidden behind that view. The service
owns identifier handling and applies checkpoint and compression policy once per completed
step that created materialised backing. Modules never receive the unrestricted connection
or the compression configuration.

The relation service serialises execution, result fetching, filesystem registration,
export, checkpointing, and connection shutdown through one worker thread, and its public
API stays synchronous. The workflow thread waits for worker results in short
interruptible intervals; Ctrl-C interrupts the active DuckDB connection and propagates
`KeyboardInterrupt` once the worker operation settles.

The executor may back the service with a compressed or uncompressed in-memory database on
temporary storage, or an ephemeral persistent database on working storage, honouring the
runtime memory limit and thread count in either mode.

`output_storage` is the publication root supplied at runtime, and target modules write
published files beneath it using relative paths. `working_storage` is a separate root for
durable intermediate artifacts and defaults to the output root. `temporary_storage` is
disposable scratch space used only during execution and defaults to the system temporary
location. Credential resolution is a runtime service as well, and resolved secrets stay
outside the serialised contract and module variables.

## Topology annotations and module interpretation

Topology annotations are canonical graph metadata, not target configuration. They are
immutable, serialisable, namespaced entries on component and property definitions. The
core preserves them and includes them in the blueprint fingerprint. Modules receive the
compiled topology and may interpret the annotations they support.

Modules may translate annotations they understand into their own workflow steps and
artifacts. Unknown annotations remain canonical metadata; the core applies no central
unsupported-annotation policy.
