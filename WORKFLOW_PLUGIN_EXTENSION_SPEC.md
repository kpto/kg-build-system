# Workflow Module Extension — Temporary Specification

## Status

This temporary specification records the workflow-module design under
discussion. It is not yet part of the canonical specification.

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
- Targets may consume core artifacts and publish target-owned artifacts, but
  may not change core graph semantics or make core work depend on target work.

## Workflow modules and target configuration

Workflow modules are resolved through a registry using a serialised kind.
Python module objects are never stored in a blueprint or build contract.

Modules are supplied in a uniquely ordered list. This order is module
priority: it resolves competing workflow-assembly preferences and provides
deterministic tie-breaking; it is not execution order.

A target configuration has a stable target ID and a target kind. The kind
selects the workflow-module implementation; the ID identifies this configured target
instance. Target-owned step, slot, artifact, diagnostic, and result identifiers
are namespaced by that target ID.

## Workflow data model

The workflow contract contains only immutable, serialisable definitions. The
registry resolves each `module_kind` to its Python implementation at compile
and runtime; the implementation object itself is never serialised.

```text
WorkflowModuleReference
  module_kind

TargetDefinition
  target_id
  module_kind
  configuration
  unsupported_annotation_policy

ArtifactRole
  namespace
  name

OutputSlot
  slot_id
  artifact_role

SingleInputSlot
  slot_id
  artifact_matcher

CollectionInputSlot
  slot_id
  artifact_matcher

WorkflowStep
  step_id
  module_kind
  assembly_preference: eager | deferred
  inputs
  outputs
  auxiliary: bool
  configuration

Connection
  input_slot_id
  output_slot_id

WorkflowDefinition
  steps
  connections
  beginning_step_id
  termination_step_id
```

`ArtifactRole` is semantic and has no physical-location, relation-name, or
producer identity. `OutputSlot.slot_id` identifies the producer-specific
output; it is distinct from its `artifact_role`.

Input slots deliberately have two forms. A `SingleInputSlot` resolves to one
selected compatible output slot. A `CollectionInputSlot` resolves to every
selected compatible output slot and therefore has one connection per selected
output. There is no workflow-slot `cardinality` field: cardinality already
describes values within data expressions and must not be conflated with the
number of artifact connections.

The matcher determines the candidate output slots. Assembly preference and
module priority determine which candidate a single input selects; collection
inputs retain every selected candidate. An output slot may connect to any
number of inputs.

## Steps, slots, and artifacts

Every module declares all of its steps before workflow assembly begins. A step
may depend directly on other steps, discover compatible artifact slots, have
no dependencies, expose output slots, or consume input slots.

An output slot describes one logical artifact. Artifacts may be relations,
CTEs, streams, diagnostics, external-resource handles, manifests, reports, or
other serialisable products. Logical artifacts and their physical
materialisation are distinct.

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

Assembly is global and non-greedy. The compiler puts every declared step and
slot on one table before resolving any connection. An output is a candidate
even when its producing step has not yet had its own inputs connected.

Each step declares one assembly preference:

- `eager` — resolve its input claims early;
- `deferred` — resolve its input claims late.

Connection claims are resolved in this deterministic order:

1. `eager` steps from higher-priority modules to lower-priority modules;
2. `deferred` steps from lower-priority modules to higher-priority modules.

For a compatible input, assembly prefers an open output slot. If it must use
an already-used output, it prefers the latest compatible output according to
the deterministic assembly ordering. This produces a preferred continuation
without preventing useful fan-out. Missing or unresolved equally preferred
connections are compilation diagnostics.

Once every connection is resolved, it becomes a dependency edge. The resulting
dependency graph, rather than module priority or assembly preference, defines
runtime execution order.

## Boundaries, execution, and failures

Every workflow has exactly one explicit beginning step and one explicit
termination step, using reserved boundary slots. The termination step produces
the single build result. A slotless side-effect step does not satisfy the build
completion contract merely because it executed successfully.

Compilation rejects missing or duplicate boundaries, missing connections,
ambiguous connections, cycles, unreachable steps, and steps that cannot
contribute to termination unless explicitly declared auxiliary.

Each step handler has normal and errored paths. A failed step is still
completed and passes its failure to downstream steps. A downstream step
normally propagates that failure through its errored handler, but may recover
it or produce failure-aware artifacts. Runtime never adds steps.

Cleanup is a terminal step with both normal and errored handlers. It releases
ordinary resources on success and can inspect propagated failures to clean up
partial work. The final result reports unresolved failures, recovered failures,
diagnostics, produced artifacts, and step outcomes.

## Topology annotations and target capabilities

Topology annotations are canonical graph metadata, not target configuration.
They are immutable, serialisable, namespaced entries on component and property
definitions. The core preserves them and includes them in the blueprint
fingerprint. Modules receive the compiled topology and may interpret supported
annotations.

Target configuration declares its unsupported-annotation policy: `error`,
`warning`, or `preserve`. A target may translate supported annotations into its
own workflow steps and artifacts.

## Runtime context and initial implementation

A workflow-module execution context supplies the immutable contract, resolved runtime
configuration, declared artifact inputs, and a result collector. It does not
expose authoring classes or unrestricted compiler state.

The first implementation slice is:

1. Add serialisable workflow steps, slots, artifact roles, connections,
   target definitions, and result models.
2. Implement global workflow assembly, validation, and deterministic
   scheduling.
3. Add the workflow-module registry and runtime dispatch, including failure propagation.
4. Convert the file target into a workflow module without changing its authoring
   syntax; move JSONL writing from the generic executor into that module.
5. Have the file module select core graph-record artifact roles and emit graph
   output plus a provenance manifest.
6. Add topology annotation IR and expose it to workflow-module compilation.
