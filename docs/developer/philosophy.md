# Framework philosophy

The framework is a compiler and a runtime for knowledge-graph declarations. Its
design follows from a small set of commitments: meaning is contract, data models
are values, boundaries are explicit, and each transformation has one name.

These commitments are not stylistic preferences. They decide where code lives,
what an interface may expose, what a blueprint may contain and what a contract
test must prove.

## Anemic models

A model is frozen data holding the facts it owns. It has no owner reference, no
service object and no derived identity. Behaviour that needs more than those
facts is a function beside the data.

An anemic model is portable. It can be stored, compared, encoded and passed
across a package boundary without dragging a live connection or a parent object
with it. Tests stay local because a model can be constructed from its fields
alone.

The framework also makes models amnesic:

- a model does not know the object that created it;
- a model does not store an identity that can be derived from its content;
- a model does not carry a wider build context.

`GraphBlueprint` is a blueprint DTO: it holds graph names, data names, bindings
and sources. It does not hold the declaration classes, a symbol-table entry or
the expression objects that produced those names. A Python binding carries only
a stable `PythonRefDTO`. A `Step` holds its ports and instruction; it does not
hold the planner that contributed it. A `WorkflowPlan` holds components, steps
and connections; it does not hold the engine that will execute it.

Derived rules live beside the model. Identity functions, codecs, planners,
renderers and emitters take a model as an argument. They are not methods that
need an owner.

Pipeline identity follows the same rule. `Step` keeps `component` and `name`;
`Step.id` and `step_id(step)` derive the `StepId`. An identity that crosses a
planner, executor, runtime or codec boundary is a role type over `Key`:
`StepId`, `OpeningId`, `ArtifactType`, `ArtifactPattern` and `InstructionKind`.
A formatted string is display only and is never parsed back into an identity.
Direction is part of an opening identity because one name can denote an input
and an output on the same step.

## Semantics as contract

A node or edge type states its meaning: what it represents, its direction, what
identifies a record, which properties may be absent and where the data cannot
answer the question. The build preserves those statements and publishes them
for consumers.

Semantics are not a comment and not an implementation detail. If a meaning
cannot be stated faithfully, the framework records a limit instead of inventing
precision. A nullable property stays nullable, an unresolved reference fails,
and a target that cannot store a type refuses it.

The blueprint is the semantic model of the graph. Topology reads as nodes,
edges, labels, endpoints and properties. It does not read as Python paths,
declaration expressions or symbol keys. The symbol graph is linker IR: it exists
to key declarations, resolve references and order transcription, and it is not
the delivered model.

The workflow plan then carries the structure needed to execute the graph:
components, steps, inputs, outputs, connections and provenance.

This is why the blueprint and the workflow plan are the two serialisable
artifacts. They are the two points where meaning leaves one system and enters
another.

## Explicit boundaries

A subpackage owns one responsibility. Its interface is the set of names another
subpackage may use: types, protocols, functions, errors and their invariants. The
interface is not `__all__`; it is the surface designed to be depended on.

Every framework subpackage uses the zones it needs from the same model/service
layout:

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

- Another subpackage imports `pkg.model.public`, `pkg.model.internal`,
  `pkg.service.public` or `pkg.service.internal`. It never imports a private zone.
- `model.public` and `model.internal` import no service or private code.
  `model._private` may read model data.
- `service.public` imports `model.public` and `service.internal`.
  `service.internal` imports model data and uses function-local imports for
  `service._private`.
- `service._private` may read model data and other private service code; it does
  not import `service.public`.
- A protocol implemented for another package is a separate file under
  `service/internal/adapters/<protocol>.py`. The file names the protocol, imports
  the foreign protocol and delegates to `service._private`.
- `model.public`, `model.internal`, `service.public` and `service.internal`
  define no single-underscore helpers; dunder protocol methods remain.
- A leaf contains only the zones it uses. An empty zone is deleted.
- A dependency edge is part of the model. A cycle, or a new edge between
  packages, is proposed with its reason.

Boundaries make local change possible. A join-semantics change belongs to the
row-source package; it does not require editing table declarations, the planner
and the authoring API. If a small feature forces edits across several
subpackages, the boundary is wrong; fix the boundary, not the call sites.

## The toolchain

The framework has one kernel and one distribution. The kernel is a toolchain
with three verbs:

| Verb | Input | Output |
| --- | --- | --- |
| `build` | a `Namespace` of declarations through a `Linker` | one opaque model |
| `compile` | the linked model | `WorkflowPlan` |
| `execute` | the workflow plan and an output directory | `WorkflowReport` |

`build` discovers declarations, derives a key for each, transcribes symbols,
resolves references and assembles the model. The linker owns language order and
root selection; the kernel never orders languages itself.

The **kernel** is shared by every system. It holds the protocols, canonical
types, workflow values, runtime values, resource view and the scheduler that
cannot be omitted or replaced.

**Generation** is upstream. It produces declarations from typed requests before
`build` runs. `build`, `compile` and `execute` never invoke generation.

**Distribution** supplies the graph domain. It owns the languages that read
declarations, the `BlueprintLinker` that assembles a `GraphBlueprint`, the
modules that plan and execute graph, file, meta-graph and Neo4j work, and the
resources those executors read. A custom language, linker, planner and executor
compile and execute without the default distribution.

A custom toolchain is one `Toolchain` value. Extensions contribute languages,
planners and executors; a new linked model supplies its own `Linker`. There is
no registry and no single framework interface to implement.

## DTO versus in-memory

A DTO is a member of the blueprint or the workflow plan. A value outside those
two artifacts is in-memory: a transcribed symbol value, a render input or an
execution result. It is not a DTO and is not expected to deserialise.

| Kind | Example | Serialised | Owner |
| --- | --- | --- | --- |
| Blueprint DTO | `GraphBlueprint`, `DataPartDTO`, `RowJoinDTO` | yes | `distribution/interpreter` and the graph languages |
| Plan DTO | `WorkflowPlan`, `Step`, `Instruction` | yes | `kernel/model/public/workflow.py` |
| In-memory model | a linked blueprint, a symbol value, a render input | no | the consuming service |
| In-memory plan | a relation plan, an engine-neutral join plan | no | a planner |
| In-memory result | a workflow report, an executor outcome | no | the runtime |

A language DTO does not know the blueprint. It knows only the DTOs of the
languages it depends on. The interpreter assembles the language DTOs into one
semantic model.

Naming follows the artifact:

- a serialisable model is a DTO, and its module names the artifact:
  `blueprint_dto.py`, `workflow.py`;
- a type in a DTO module carries the `DTO` suffix, while the kernel's public
  workflow values keep their toolchain names (`Step`, `WorkflowPlan`);
- a model that is not serialised is an in-memory `model` or an engine-neutral
  `plan`, not a DTO.

`IR` is not a synonym for internal data. It is not a module or class suffix in
the framework model; the symbol graph is described as linker IR in prose only.

## Source regeneration

A language transcribes declarations into symbols and renders a symbol value back
to authoring source. Transcribe and render are the two directions of the same
language.

Source generation is the responsibility of the language that owns the DTO:

- each language has a transcription service and a source service;
- a language renders its own DTO using its dependency languages' renderers;
- the blueprint source service delegates to each language and assembles the
  fragments;
- the interpreter does not render data, topology or binding source itself.

The blueprint must regenerate equivalent authoring source. The round trip

```text
blueprint -> generated source -> blueprint
```

is a contract test, not a convenience. It proves that the blueprint contains
enough semantic information to reconstruct the declarations that would produce
the same blueprint.

The blueprint is not a snapshot of the declarations that produced it. It is a
semantic model. Two different declaration spellings that mean the same thing
should produce the same blueprint; the renderer emits one equivalent authoring
form, not the original text.

## One verb per transformation

Each transformation has one name. The verbs describe a direction, not a package
or a class.

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

Do not use `lower` for any of them. The framework uses `discover`, `key`,
`transcribe`, `link`, `plan`, `assemble`, `emit`, `render` and `execute`.

## Current state and limits

The framework is implemented: the toolchain builds a `GraphBlueprint`, compiles
it into a `WorkflowPlan`, and executes it with the supplied planners, executors
and resources. Source generation is per language.

The remaining limits are:

- a toolchain is the only composition unit; there is no registry;
- DuckDB is the default SQL emitter;
- a Python instruction is a reference, not the callable body;
- public `GraphBlueprint` fields reference internal language DTOs;
- the core planners depend on the DuckDB SQL emitter.

Verification: 187 tests passed, 1618 subtests; pyright 0 errors; the Open Targets
project passes 7 tests against the API.

See [system design](system-design.md) for the layout and [testing](testing.md)
for the contract tests.

## What to remember

- A model is frozen data; behaviour is a function beside it.
- Meaning is part of the delivered contract, not a comment.
- Every dependency edge is a design decision.
- Only the blueprint and the workflow plan are serialisable artifacts.
- The symbol graph is linker IR; the blueprint is the semantic model.
- A language transcribes declarations into symbols and renders symbol values; it
  does not encode or decode.
- The blueprint must round-trip through generated authoring source.

Next: [System design](system-design.md).
