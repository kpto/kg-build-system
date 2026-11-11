---
title: Developer guide
summary: The internal model developers review, from kernel protocols to distribution boundaries.
section: developer
perspective: developer
order: 10
status: normative
verified: 2026-11-10
sources:
  - docs/developer/index.md
  - AGENTS.md
  - ARCHITECTURE.md
  - FRAMEWORK_STATE.md
---

## In this section

The developer section is the internal interface guide: the model, boundaries and contract tests a framework reviewer may depend on.

## Interface

The developer section states the framework's internal interfaces for the reader who changes the framework, reviews an interface, or adds a language, linker, planner, executor or resource. It assumes the authoring surface and explains the model beneath it.

Author pages and developer pages can cover one subject for different readers. An author page states what an author writes and observes. A developer page states the names, signatures, invariants, allowed dependencies and boundaries a framework reviewer may depend on.

## Pages

| Page | States |
| --- | --- |
| [Framework philosophy](/developer/philosophy) | The commitments that decide where code belongs and what an interface may expose. |
| [System design](/developer/system-design) | The package tree, kernel protocols, linker, blueprint, plan, runtime, zones and dependency spine. |
| [Data and expressions](/developer/data-and-expressions) | The DTOs, typed refs, row-source plan, neutral emission boundary and source round trip. |
| [Testing](/developer/testing) | The contract-test groups, commands, guards and the gaps the suite leaves. |

### Kernel and distribution

The kernel is domain-agnostic. It owns the toolchain vocabulary and the protocols that cannot be omitted or replaced; it imports no graph, data, topology, binding, SQL, DuckDB, Python or generation package.

| Group | Names |
| --- | --- |
| Frontend | `Language`, `Declaration`, `Symbol`, `SymbolRef`, `Key`, `Namespace`, `ReferenceResolver`, `RenderContext`, `SourceFragment` |
| Linking and planning | `Linker`, `SymbolContext`, `PlanContext`, `Planner`, `Component`, `WorkflowPlan`, `Step`, `Instruction`, `InstructionKind`, `StepId`, `OpeningId`, `ArtifactType`, `ArtifactPattern` |
| Execution | `Runtime`, `Resource`, `ResourceProvider`, `ResourceView`, `ResourceRegistry`, `PipelineEvent`, `EventBus`, `StepOutcome`, `WorkflowReport`, `RuntimeConfiguration` |
| Composition | `Toolchain`, `WorkflowRuntime` |

The distribution owns the graph domain: `GraphBlueprint`, the graph languages, the interpreter, the modules that plan and execute graph, file, meta-graph and Neo4j work, and the resources those executors read. The kernel model is opaque; the distribution implements it.

The toolchain has three verbs:

| Verb | Input | Output |
| --- | --- | --- |
| `build` | a `Namespace` of declarations through a `Linker` | one opaque model |
| `compile` | the linked model | `WorkflowPlan` |
| `execute` | the workflow plan and an output directory | `WorkflowReport` |

## Rules

- **The model is the decision.** Code is reported against the model; it does not redefine it. An interface change is a model change, stated before implementation and reviewed through this section. [Contracts](/review/contracts) owns the invariants.
- **State the interface.** A developer page names the public and internal names, their signatures and invariants, the allowed dependency edges and the authoring surface. Implementation route is out of scope.
- **Keep the vocabulary split.** Language, declaration, symbol, linker, planner, workflow plan, step, executor, resource and toolchain are kernel words. Graph, blueprint, node, edge, binding, projection, table, asset and operation are distribution words.
- **Use one verb per transformation.** A language discovers, keys, transcribes and renders; a linker links; a planner plans; assembly assembles; an emitter emits; the runtime executes. `lower` names none of them.
- **Name the artifact.** A serialisable member of the blueprint or the workflow plan is a DTO. A value outside those artifacts is an in-memory model, plan or result.
- **Bound the section.** This section documents the framework, not the graph a project builds. A graph author's rule belongs in the authoring pages; a framework interface belongs here. [Architecture specification](/spec/architecture) states the package boundary that makes the split enforceable.

## Limits

- A developer page states interfaces and invariants, not a tutorial, a change report or a migration guide.
- The pages describe the model at `verified: 2026-11-10`; a source change after that date is drift, not a silent revision.
- Counts and measured behaviour belong to [Limits](/review/limits), not to an interface page.
- A toolchain is the only composition unit. There is no registry and no single extension interface to implement.
- The distribution is not optional for a graph build. A custom language can run on the kernel alone; nodes, edges, bindings and the blueprint cannot.
- The kernel boundary is enforced by import tests, which make an illegal edge visible rather than impossible in a running process.

## Next

[Architecture specification](/spec/architecture) — the normative boundary for the kernel, distribution and dependency spine.
