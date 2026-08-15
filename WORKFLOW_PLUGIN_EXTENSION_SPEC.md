# Workflow Module Extension — Temporary Specification

## Status

This temporary specification records the workflow-module design under
discussion. It is not yet part of the canonical specification.

The initial workflow-contract and runtime-result slice is implemented. The
current implementation has serialisable module references, frozen workflow
steps/slots/connections, runtime-only step outcomes, explicit publication, a
user-facing workflow report, a file-output module, and state-aware error
handling. Recovery policy is owned by downstream modules.

## Purpose and invariants

A build is an immutable, serialisable workflow assembled from ordered module
contributions. Workflow modules may contribute source acquisition, transformation,
post-processing, validation, target actions, reporting, or cleanup. These are
all workflow steps; no role receives special scheduling treatment.

- Core graph semantics remain target independent.
- The complete workflow is inspectable and frozen before runtime execution.
- Modules receive compiled definitions and runtime configuration, never
  authoring Python classes.
- Contracts retain credential references only; resolved credentials are
  runtime-only.
- Modules may consume core artifacts and publish module-owned artifacts.
  Core is a module contributing ordinary workflow steps; connections may make
  any step depend on any compatible producer.  Modules may not change the
  canonical graph semantics represented by compiled definitions.

## Workflow modules and runtime configuration

Each workflow-module class has a stable, static module ID. The ID is semantic:
it is used as the module namespace for steps, slots, artifact roles, runtime
configuration, and annotations the module owns. A
compiled workflow may contain at most one configured instance of a module ID.

An author supplies module registrations to `compile`; they are part of the
complete declared build intention. A registration contains a module
class and serialisable, non-secret registration configuration. The blueprint
records import coordinates for that class and the registration configuration,
never a Python object. At compilation, the compiler re-imports and
reconstructs each registration, verifies the class's static ID, and rejects
classes that cannot be reliably re-imported.

Compilation produces distinct module-reference configuration for execution.
The module controls this transformation: execution configuration may equal its
registration configuration, but need not. At runtime, the executor imports
that class and delegates step execution to it. Python class or module objects
are never stored in a blueprint or build contract.

Modules are supplied in a uniquely ordered list. Earlier modules have higher
assembly priority: the order resolves competing workflow-assembly preferences
and provides deterministic tie-breaking; it is not execution order. The public
API appends the mandatory core module last, making it the lowest-priority
fallback without storing a numeric priority setting.

There is no target configuration or target-specific policy in the workflow
model. A file writer, database writer, source reader, validator, or cleanup
provider is a workflow module. Modules may inspect canonical topology
annotations, but no central annotation policy interprets them on their behalf.

## Workflow data model

The workflow contract contains only immutable, serialisable definitions. The
executor resolves each compiled module reference to its Python implementation
at runtime; the implementation object itself is never serialised.

The serialized definitions are compilation IRs owned by `workflow.ir`.
Workflow-module behavior, assembly, and runtime execution use frozen workflow
domain models from `workflow.models`. Explicit mapping occurs when a build
contract is frozen and once again when execution begins; IRs are not passed to
module executors or retained by runtime contexts.

```text
ModuleRegistrationConfiguration

ModuleRegistration
  module_class
  configuration

BlueprintModule
  module_id
  module_import
  module_qualname
  configuration

ModuleReference
  module_id
  import_module
  class_qualname
  implementation_version
  configuration

ModuleDefinition
  reference
  runtime_fields

CompilationContext
  blueprint
  settings
  overrides
  module_id
  registration_configuration

RuntimeFieldDefinition
  key
  description
  required
  value_type
  secret

ArtifactRole
  namespace
  name

OutputSlot
  slot_id
  artifact_role

SingleInputSlot
  slot_id

CollectionInputSlot
  slot_id

WorkflowStep
  step_id
  module_id
  inputs
  outputs
  payload

Connection
  input_slot_id
  output_slot_id

WorkflowDefinition
  modules
  steps
  connections

ExecutionServices
  duckdb
  output_storage
  working_storage
  temporary_storage
  credentials

ExecutorFactoryContext
  contract
  module
  runtime_configuration
  services

ExecutionContext
  contract
  module
  step
  runtime_configuration
  inputs
  services
```

`ModuleRegistration.configuration` is compile-time input only. It must be
serialisable and non-secret. `ModuleReference.configuration` is serialisable
execution configuration produced by that module's compiler. It is not a copy
of registration configuration by implication; the module owns the mapping.
Runtime configuration remains separate and is supplied only at execution.

`CompilationContext` is the single generic compile-time context used by every
module, including the built-in core module. Source bindings are declarations
on `BuildBlueprint`; they are not duplicated in the context. A module derives
effective sources by applying serialisable source overrides to
`blueprint.sources`. The context exposes the blueprint, compilation settings,
overrides, module identity, and that module's reconstructed, non-secret
registration configuration. It never exposes authoring classes. Assembly
priority belongs to the ordered module list and is not module configuration.

`module_id` identifies one configured module in a workflow. Supporting two
independently configured instances of the same implementation requires either
a module designed to accept multiple declared outputs or a future explicit
module-instance-ID model; it is not implicit in the initial design.

`import_module` and `class_qualname` are operational import coordinates, not
semantic namespaces. `implementation_version` is a package version or other
stable implementation fingerprint used to reject an incompatible runtime
implementation.

Runtime configuration field values are not stored in the contract. The
contract records their definitions, and runtime supplies values as a mapping
by module ID and field key. `secret` fields must never enter workflow payloads,
published artifacts, manifests, or fingerprints.

`ArtifactRole` is semantic and has no physical-location, relation-name, or
producer identity. `OutputSlot.slot_id` identifies the producer-specific
output; it is distinct from its `artifact_role`.

Input slots deliberately have two forms. A `SingleInputSlot` resolves to one
selected compatible output slot. A `CollectionInputSlot` resolves to every
selected compatible output slot and therefore has one connection per selected
output. There is no workflow-slot `cardinality` field: cardinality already
describes values within data expressions and must not be conflated with the
number of artifact connections. An output slot may connect to any number of
inputs.

Each workflow module supplies candidate predicates for its own input slots as
part of its compile-only step drafts. A predicate receives only compiled
definitions and the complete declared slot table, and determines whether a
declared output slot is a candidate for a declared input slot. It is
deterministic, pure, and synchronous: it cannot inspect runtime configuration,
resolved credentials, physical artifacts, or execution state. The contract
retains resolved connections, not Python predicate objects.

Compile-only step drafts carry assembly preference, while the ordered module
list supplies assembly priority. Together they determine which candidate a
single input selects; collection inputs retain every candidate selected by
their module's predicate. Both values are discarded after connections are
resolved and therefore do not enter the serialized workflow IR or its
fingerprint.

## Workflow-module interface

Modules use abstract base classes for registration and lifecycle ownership.
Compiler and executor capabilities remain narrow protocols:

```python
@dataclass
class ModuleRegistrationConfiguration(ABC): ...


@dataclass
class ModuleRegistration[T](ABC):
    module_class: type
    configuration: T


class ModuleCompiler(Protocol):
    async def compile(
        self, context: CompilationContext,
    ) -> ModuleCompilationResult: ...


class ModuleExecutor(Protocol):
    async def handle(
        self, context: ExecutionContext,
    ) -> StepOutcome: ...

    async def handle_disrupted(
        self, context: DisruptedExecutionContext,
    ) -> StepOutcome: ...


class Module(ABC):
    ID: ClassVar[str]

    @classmethod
    async def create_compiler(
        cls, context: CompilationContext,
    ) -> ModuleCompiler: ...

    @classmethod
    async def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor: ...
```

`compile` creates its blueprint internally and serialises registrations into
blueprint module entries. It then reconstructs them, calls `create_compiler`,
and calls `ModuleCompiler.compile`. The resulting `ModuleCompilationResult` contains a
serialisable module definition, step drafts, and candidate predicates. The
compiler retains only serialisable definitions and resolved connections in the
contract, and owns selection, connection creation, and graph validation.

At runtime, the executor validates and supplies runtime configuration, combines
it with the compiled `ModuleReference`, and calls `create_executor` with a
generic `ExecutorFactoryContext`. The returned `ModuleExecutor` receives an
`ExecutionContext` for each step. It receives compiled reference configuration,
not registration configuration.

## Steps, slots, and artifacts

Every module declares all of its steps before workflow assembly begins. A
compile-only step draft may declare candidate predicates for its input slots.
A serialised workflow step has no direct dependency list: connections are its
only dependencies. It may have no inputs, expose output slots, consume input
slots, or both consume and produce slots.

An output slot describes one logical artifact. Artifacts may be relations,
CTEs, streams, module-owned findings, external-resource handles, manifests,
reports, or other serialisable products. Logical artifacts and their physical
materialisation are distinct.

A declared output slot may produce no runtime artifact when the step has
nothing meaningful to publish. The slot remains part of the frozen workflow;
its connected consumers receive no artifact for that connection. Modules must
therefore treat an empty runtime input as a valid possibility.

Each output slot has a producer-specific slot ID and one artifact role. The
slot ID says which step produced it; the role says what it represents:

```text
slot:
  namespace: core
  name: normalise.Target.records

artifact:
  namespace: core
  role: graph.intermediate_records.nodes.Target
```

Compact identifiers render namespaces consistently:

```text
core::normalise.Target.records
core::graph.intermediate_records.nodes.Target
```

An artifact role is a semantic description, not a physical path, source
location, or producer identity. A passthrough step such as validation consumes
an artifact and produces a new slot with the same role, even when it reuses the
same physical relation or CTE.

A single input slot connects to one compatible output slot. An output slot may
connect to many input slots, allowing fan-out and parallel work. A collection
input expands to connections for every selected output slot. Consumers such as
writers discover artifact roles rather than knowledge of processing phases.

For example, a writer can select preferred artifacts in the `core` namespace
matching `graph.intermediate_records.nodes.*`; it does not need to know which
module created the current continuation.

## Workflow assembly

Assembly is global and non-greedy. The compiler first asks every resolved
module to declare its serialisable steps and slots from compiled definitions.
It then puts every declared step and slot on one table before evaluating
module candidate predicates or resolving any connection. An output is a
candidate even when its producing step has not yet had its own inputs
connected.

Each compile-only step draft declares one assembly preference:

- `eager` — resolve its input claims early;
- `deferred` — resolve its input claims late.

Connection claims are resolved in this deterministic order:

1. `eager` steps from higher-priority modules to lower-priority modules;
2. `deferred` steps from lower-priority modules to higher-priority modules.

Higher priority means earlier in the declared module list. The public API
places core last so extension modules can claim and continue core artifacts
without a special priority value or compiler-owned core bootstrap path.

For a candidate input/output pair, assembly prefers an open output slot. If it
must use an already-used output, it prefers the latest compatible output according to
the deterministic assembly ordering. This produces a preferred continuation
without preventing useful fan-out. Missing or unresolved equally preferred
connections are compilation errors.

Once every connection is resolved, it becomes a dependency edge. Module
priority and assembly preference are discarded. The resulting dependency graph
alone defines runtime execution order.

## Execution and failures

There are no privileged scheduling roles. A beginning step is an ordinary step
with no input slots. A termination step is an ordinary step with no output
slots. A workflow may have multiple beginnings and multiple terminations.

The workflow protocol provides the standard result-publication convention. A
module marks an output for inclusion in the user-facing workflow result with a
workflow publication role:

```text
workflow::publication.<module_id>.<name>
```

`WorkflowArtifactRoles` owns the `published` constructor and `is_published`
predicate. The executor collects every emitted artifact with this role directly
into the workflow result without inspecting its value. Publication is generic:
the workflow has no special diagnostic, validation, target, or report payload
type, and no core publication step.

The executor completes a build when every declared step has reached an
outcome. The user-facing result contains explicitly published artifacts,
recovered failures, unresolved failures, and compact provenance. A no-output
side-effect step is therefore a sink, not an implicit single build result.

Compilation rejects missing connections, ambiguous connections, and cycles.
Cleanup is also an ordinary step: it must have explicit input connections to
the work or failure-aware artifacts it needs, and it has no hidden scheduling
priority.

Each executor has two abstract input-state handlers. `handle` receives an
`ExecutionContext` only when every connected producer succeeded or warned.
`handle_disrupted` receives a `DisruptedExecutionContext` when any connected
producer failed or was skipped. Its abstract base implementation returns a
skipped outcome, so a module must explicitly opt into that policy with
`return await super().handle_disrupted(context)`. A module may instead recover
by returning success or warning, emit failure-aware artifacts, publish a
report, or fail intentionally.

A failed or skipped step is still completed and passes its state to downstream
steps. The executor catches unhandled exceptions from either handler and turns
them into failed outcomes with `Failure` details. Runtime never adds steps.

Runtime artifacts and step outcomes are runtime-only models. Slots and
artifact roles remain serialised workflow semantics and do not dictate physical
materialisation. Internal execution detail is not part of the user-facing
workflow result.

### Runtime outcomes and published results

The runtime model records every completed step as a `StepOutcome`. An outcome
has a status, zero or more declared output artifacts, optional failure
information. Modules return outcomes rather than untyped values; the executor
validates that every produced artifact belongs to one of that step's declared
output slots and has the declared artifact role.

```text
StepStatus = succeeded | warning | failed | skipped

Failure
  message
  module_id
  step_id
  exception_type

Artifact
  slot_id
  role
  value                         # runtime-only physical value

StepOutcome
  step_id
  module_id
  status
  artifacts
  failure

PublishedArtifact
  role
  value

WorkflowReport
  published_artifacts
  recovered_failures
  unresolved_failures
  provenance
```

There is no workflow-level diagnostic model. A validation module may expose
its findings as a private output slot, aggregate them into a module-owned
report, and publish that report if it has useful content. Whether findings
become a gate failure is the validator's configuration and lifecycle decision.
`Failure` describes a step that could not complete its work. Recovery is not a
fifth step state: a disrupted handler recovers by returning success or warning.

The runtime execution context supplies the immutable contract, compiled module
definition/reference, resolved runtime configuration, declared artifact inputs,
and execution services. Runtime values, artifacts, and outcomes never enter
the serialised workflow contract.

## Topology annotations and module interpretation

Topology annotations are canonical graph metadata, not target configuration.
They are immutable, serialisable, namespaced entries on component and property
definitions. The core preserves them and includes them in the blueprint
fingerprint. Modules receive the compiled topology and may interpret supported
annotations.

Modules may translate annotations they understand into their own workflow
steps and artifacts. Unknown annotations remain canonical metadata; the core
does not apply a central unsupported-annotation policy.

## Runtime context and initial implementation

A workflow-module execution context supplies the immutable contract, the
module's compiled definition and reference configuration, the current declared
step, resolved runtime configuration, declared artifact inputs, and generic
runtime services. It does not expose registration configuration, authoring
classes, or unrestricted compiler state. Runtime configuration is structured
as `module_id -> field key -> value`. Candidate predicates are never invoked at
runtime: execution uses only the connections frozen in the contract.

Runtime inputs preserve a producer's state even if its declared output slot
has no artifact. A continuable input has a `succeeded` or `warning` state; a
disrupting input has a `failed` or `skipped` state and optional failure details.
For collection slots the execution context contains one input contribution per
connected output slot. The executor calls `handle` only if every contribution
across every input slot is continuable; otherwise it calls `handle_disrupted`.

Runtime services expose the DuckDB connection directly. DuckDB is the initial
execution engine and modules are expected to push relational work into it;
there is deliberately no premature relation-service abstraction. Relation
artifacts may therefore carry executor-local DuckDB relation names. A target
module may use DuckDB directly to write an output file or database product.

`output_storage` is the publication root supplied at runtime. Target modules
write published files beneath it using relative paths. `working_storage` is a
separate root for durable intermediate artifacts and defaults to the output
root. `temporary_storage` is disposable scratch space used only during
execution and defaults to the system temporary location. Credential resolution is also a runtime service; resolved secrets
remain outside the serialised contract and workflow payloads.

The first implementation slice is:

1. Add serialisable module references, runtime-field definitions, workflow
   steps, slots, artifact roles, connections, and result models.
2. Implement global workflow assembly, validation, and deterministic
   scheduling.
3. Add registration-based compilation, module import resolution, and runtime
   dispatch; add failure propagation in a later extension.
4. Convert the file target into a workflow module without changing its authoring
   syntax; move JSONL writing from the generic executor into that module.
5. Have the file module select core graph-record artifact roles and publish its
   graph-output result.
6. Add topology annotation IR and expose it to workflow-module compilation.

Implemented additions to this slice:

- JSONL writing is owned by `FileModule`, which publishes its output result.
- Runtime workflow models are owned by `workflow.models`; module lifecycle
  interfaces are owned by `workflow.interfaces`; `modules` contains concrete
  module implementations only.
- `CompilationContext`, `ExecutorFactoryContext`, and `ExecutionContext` are
  generic contexts shared by every module; core has no context or lifecycle
  privilege.
- Runtime execution services expose DuckDB directly alongside distinct durable
  working storage and disposable temporary storage.
- `WorkflowArtifactRoles` is the neutral publication vocabulary; the executor
  directly collects matching declared artifacts into `WorkflowReport`, which
  exposes those values, failures, and compact provenance without interpreting
  module-specific artifact payloads.
- Validators may use private finding slots and a module-owned aggregation step
  to publish one optional validation report and apply configured gate policy.
- Workflow compilation IRs and workflow domain models are distinct; module
  implementations use domain models, and runtime contexts do not expose the
  serialized build contract.
