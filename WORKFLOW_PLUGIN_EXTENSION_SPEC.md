# Workflow Plugin Extension — Temporary Specification

## Status

This temporary specification records the workflow-plugin design under
discussion. It is not yet part of the canonical specification.

## Purpose and invariants

A build is an immutable, serialisable workflow assembled from ordered plugin
contributions. Plugins may contribute source acquisition, transformation,
post-processing, validation, target actions, reporting, or cleanup. These are
all workflow steps; no role receives special scheduling treatment.

- Core graph semantics remain target independent.
- The complete workflow is inspectable and frozen before runtime execution.
- Plugins receive compiled definitions and runtime configuration, never
  authoring Python classes.
- Contracts retain credential references only; resolved credentials are
  runtime-only.
- Targets may consume core artifacts and publish target-owned artifacts, but
  may not change core graph semantics or make core work depend on target work.

## Plugins and target configuration

Plugins are resolved through a registry using a serialised kind. Python plugin
objects are never stored in a blueprint or build contract.

Plugins are supplied in a uniquely ordered list. This order is plugin
priority: it resolves competing workflow-assembly preferences and provides
deterministic tie-breaking; it is not execution order.

A target configuration has a stable target ID and a target kind. The kind
selects the plugin implementation; the ID identifies this configured target
instance. Target-owned step, slot, artifact, diagnostic, and result identifiers
are namespaced by that target ID.

## Steps, slots, and artifacts

Every plugin declares all of its steps before workflow assembly begins. A step
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

An input slot connects to one compatible output slot. An output slot may
connect to many input slots, allowing fan-out and parallel work. A collection
input expands to connections for every selected output slot. Consumers such as
writers discover artifact roles rather than knowledge of processing phases.

For example, a writer can select preferred artifacts in the `core` namespace
matching `graph.intermediate_records.nodes.*`; it does not need to know which
plugin created the current continuation.

## Workflow assembly

Assembly is global and non-greedy. The compiler puts every declared step and
slot on one table before resolving any connection. An output is a candidate
even when its producing step has not yet had its own inputs connected.

Each step declares one assembly preference:

- `eager` — resolve its input claims early;
- `deferred` — resolve its input claims late.

Connection claims are resolved in this deterministic order:

1. `eager` steps from higher-priority plugins to lower-priority plugins;
2. `deferred` steps from lower-priority plugins to higher-priority plugins.

For a compatible input, assembly prefers an open output slot. If it must use
an already-used output, it prefers the latest compatible output according to
the deterministic assembly ordering. This produces a preferred continuation
without preventing useful fan-out. Missing or unresolved equally preferred
connections are compilation diagnostics.

Once every connection is resolved, it becomes a dependency edge. The resulting
dependency graph, rather than plugin priority or assembly preference, defines
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
fingerprint. Plugins receive the compiled topology and may interpret supported
annotations.

Target configuration declares its unsupported-annotation policy: `error`,
`warning`, or `preserve`. A target may translate supported annotations into its
own workflow steps and artifacts.

## Runtime context and initial implementation

A plugin execution context supplies the immutable contract, resolved runtime
configuration, declared artifact inputs, and a result collector. It does not
expose authoring classes or unrestricted compiler state.

The first implementation slice is:

1. Add serialisable workflow steps, slots, artifact roles, connections,
   target definitions, and result models.
2. Implement global workflow assembly, validation, and deterministic
   scheduling.
3. Add the plugin registry and runtime dispatch, including failure propagation.
4. Convert the file target into a plugin without changing its authoring
   syntax; move JSONL writing from the generic executor into that plugin.
5. Have the file plugin select core graph-record artifact roles and emit graph
   output plus a provenance manifest.
6. Add topology annotation IR and expose it to plugin compilation.
