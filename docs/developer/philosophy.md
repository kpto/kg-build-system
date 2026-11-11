---
title: Framework philosophy
summary: Meaning is contract, models are values, boundaries are explicit, and each transformation has one name.
section: developer
perspective: developer
order: 20
status: normative
verified: 2026-11-10
sources:
  - docs/developer/philosophy.md
  - AGENTS.md
  - kg_build_system/kernel/model/public/symbol.py
  - kg_build_system/kernel/service/public/pipeline.py
  - kg_build_system/distribution/languages/expressions/model/public/selection.py
---

## Interface

The framework is a compiler and a runtime for knowledge-graph declarations. Its design follows from four commitments: meaning is contract, data models are values, boundaries are explicit, and each transformation has one name. These commitments are not style. They decide where code lives, what an interface exposes, what a blueprint contains and what a contract test must prove.

### Anemic and amnesic models

A model is frozen data holding the facts it owns. It has no owner reference, no service object, no derived identity and no wider build context. Behaviour that needs more than those facts is a function beside the data.

A model is portable across a package boundary without a live connection or parent object; tests stay local because it is built from its fields. `GraphBlueprint` holds graph names, data names, assets and bindings, not the declaration classes or symbol-table entries behind them. A `Step` holds its ports and instruction, not its planner. A `WorkflowPlan` holds components, steps and connections, not its engine.

Identity follows the same rule. `Step` keeps `component` and `name`; `Step.id` and `step_id(step)` derive the `StepId`. An identity that crosses a planner, executor, runtime or codec boundary is a role type over `Key`: `StepId`, `OpeningId`, `ArtifactType`, `ArtifactPattern` and `InstructionKind`. A formatted string is display only and is never parsed as an identity. Direction is part of an opening identity because one name can denote an input and an output on the same step.

### Semantics as contract

A node or edge type states its meaning: what it represents, its direction, what identifies a record, which properties may be absent and where the data cannot answer the question. The build preserves those statements and publishes them for consumers.

Semantics are not a comment or implementation detail. If a meaning cannot be stated faithfully, the framework records a limit instead of inventing precision. A nullable property stays nullable, an unresolved reference fails, and a target that cannot store a type refuses it.

The blueprint is the semantic model of the graph. Topology reads as nodes, edges, labels, endpoints and properties, not Python paths, declaration expressions or symbol keys. The symbol graph is linker IR: it keys declarations, resolves references and orders transcription, and it is not the delivered model. The workflow plan carries the execution structure and records the source blueprint document under its provenance. [Identity specification](/spec/identity) states the reference and document rules.

### Explicit boundaries

A subpackage owns one responsibility. Its interface is the set of names another subpackage may use: types, protocols, functions, errors and their invariants. The interface is not `__all__`; it is the surface designed to be depended on.

Every framework leaf uses the zones it needs from the same `model` and `service` layout. Another subpackage imports `pkg.model.public`, `pkg.model.internal`, `pkg.service.public` or `pkg.service.internal`, never a private zone. A protocol implemented for another package is a separate file under `service/internal/adapters/<protocol>.py`.

Boundaries make local change possible. A join-semantics change belongs to the row-source package; it does not require editing table declarations, the planner and the authoring API. If a small feature forces edits across several subpackages, fix the boundary, not the call sites. Dependency edges are model decisions. [Architecture specification](/spec/architecture) states the zone and spine requirements.

### The toolchain

The framework has one kernel and one distribution. The kernel is a toolchain with three non-overlapping verbs:

| Verb | Input | Output |
| --- | --- | --- |
| `build` | a `Namespace` of declarations through a `Linker` | one opaque model |
| `compile` | the linked model | `WorkflowPlan` |
| `execute` | the workflow plan and an output directory | `WorkflowReport` |

`build` discovers declarations, derives a key for each, transcribes symbols, resolves references and assembles the model. The linker owns language order and root selection; the kernel never orders languages itself. `compile` groups planners by `component_id` and assembles one checkable plan. `execute` maps exact instruction kinds to executors and runs the plan through the runtime and its resources.

The kernel holds the protocols, canonical types, workflow values, runtime values, resource view and scheduler that cannot be omitted or replaced. Generation is upstream: it produces declarations from typed requests before `build` runs, and `build`, `compile` and `execute` never invoke it. The distribution supplies the graph domain. Custom languages, linkers, planners and executors run without the default distribution.

A custom toolchain is one `Toolchain` value. Extensions contribute languages, planners and executors; a new linked model supplies its own `Linker`.

### DTOs and source regeneration

A DTO is a member of the blueprint or the workflow plan. A value outside those two artifacts is in-memory: a transcribed symbol value, a render input, a relation plan or an execution result. It is not a DTO and is not expected to deserialise.

| Kind | Example | Serialised | Owner |
| --- | --- | --- | --- |
| Blueprint DTO | `GraphBlueprint`, `DataPartDTO`, `RowJoinDTO` | yes | the interpreter and the graph languages |
| Plan DTO | `WorkflowPlan`, `Step`, `Instruction` | yes | `kernel/model/public/workflow.py` |
| In-memory model | a linked blueprint, a symbol value, a render input | no | the consuming service |
| In-memory plan | a relation plan, an engine-neutral join plan | no | a planner |
| In-memory result | a workflow report, an executor outcome | no | the runtime |

Naming follows the artifact. A serialisable model is a DTO and its module names the artifact; a DTO type carries the `DTO` suffix, while kernel workflow values keep toolchain names. A value that is not serialised is an in-memory model, plan or result. `IR` is not an internal-data synonym or a suffix; the symbol graph is linker IR in prose only.

A language transcribes declarations into symbols and renders a symbol value back to authoring source. Each language renders its own DTO; the blueprint source service delegates and assembles the fragments. The round trip `blueprint -> generated source -> blueprint` is a contract test, not a convenience. The blueprint is a semantic model, not a snapshot: two declaration spellings that mean the same thing produce the same blueprint, and the renderer emits one equivalent form. [Document shapes](/reference/documents) owns the canonical wire form.

### One authoring type, one verb

The distribution exposes one authoring value for a typed position in a row: `Selection[T]`. `NullableSelection[T]` is the alias `Selection[Nullable[T]]`. No expression family or accessor unwraps the compiler tree.

A field declaration names a value type, never `T | None`. A source `Table` or `Struct` read is nullable because the source may omit the value; a computed `Projection` output or `ComputedStruct` member follows its selection. The owner supplies nullability; the author never writes it into a field annotation. `alter_rows()` is a one-shot handle exposing only `drop_null`, `drop_if` and `expand` where they are valid. `lookup` returns a nullable array of target records; `zip` pairs arrays by position; `RowSource.unnest` expands an array as a relation's grain.

Each transformation has one name.

| Verb | Input | Output | Owner |
| --- | --- | --- | --- |
| discover | namespace | declarations | language |
| key | declaration | `Key` | language |
| transcribe | declarations and symbol context | symbols | language |
| link | languages and namespace | opaque model | linker |
| plan | model | `Step`s | planner |
| assemble | planned steps | `WorkflowPlan` | kernel |
| emit | plan | instruction payload | instruction emitter |
| render | symbol value | authoring source | language |
| execute | workflow plan | artifacts and `WorkflowReport` | runtime and executors |

`lower` names none of them.

## Rules

- A model is frozen data; behaviour is a function beside it.
- Meaning is part of the delivered contract, not a comment.
- Every dependency edge is a design decision, proposed with its reason.
- Only the blueprint and the workflow plan are serialisable artifacts.
- The symbol graph is linker IR; the blueprint is the semantic model.
- A language transcribes declarations into symbols and renders symbol values; it does not encode or decode.
- The blueprint must round-trip through generated authoring source.

## Limits

- A toolchain is the only composition unit; there is no registry.
- DuckDB is the default SQL emitter. The core planners consume an injected `SqlEmitter`, and another engine supplies another emitter and executor.
- A Python instruction is a reference, not the callable body.
- Public `GraphBlueprint` fields reference internal language DTOs that are not exported public names.
- [Limits](/review/limits) records the consumer cost of each boundary.

## Next

[Architecture subject](/subjects/architecture) — where these commitments become package boundaries and tested edges.
