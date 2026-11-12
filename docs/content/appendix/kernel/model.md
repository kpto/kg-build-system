---
title: Kernel model
summary: Canonical types, keys, declarations, symbols, workflow values and runtime results the kernel owns.
section: kernel
perspective: developer
order: 20
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/kernel/model/public/key.py
  - kg_build_system/kernel/model/public/symbol.py
  - kg_build_system/kernel/model/public/workflow.py
  - kg_build_system/kernel/model/public/runtime.py
  - kg_build_system/kernel/model/public/events.py
---

## Interface

The kernel model is a set of frozen, anaemic values. It owns the shape of an identity, a symbol, a step, a plan and a result; it never reads an instruction payload, an artifact value or a distribution model. Behaviour that needs more than the facts a value owns is a function beside it.

### Canonical types

Every language, the blueprint and the workflow plan use one type ontology owned by the kernel.

| Group | Names |
| --- | --- |
| Unit types | `BOOL`, `INT`, `FLOAT`, `STR`, `DATE`, `TIME`, `TIMESTAMP`, `UUID` (`UnitType`) |
| Containers | `ArrayType`, `StructType` |
| Absence | `NullableType`; the authoring alias `Nullable[T]` is the union `T \| None` |
| Extension | `CustomType`, `CustomDataType` |

The authoring markers `Array`, `Struct`, `Nullable`, `Shape`, `Date`, `Time`, `Timestamp` and `Uuid` are the values an author writes. A generated contract, declaration or selection uses one spelling: `Nullable[T]` and `T | None` are one canonical type, and a present selection satisfies a nullable slot.

### Key

`Key(segments: tuple[str, ...])` is a qualified name chosen by the language. `Key(("site",))` names a top-level symbol; `Key(("site", "name"))` names its child. The empty key is the root of a language's key space.

| Operation | Contract |
| --- | --- |
| `child(*segments)` | Extend the key. |
| `starts_with(other)` | Whether `other` is a prefix. |
| `matches(pattern)` | `fnmatchcase` per segment; a final `**` matches any remaining segments. |
| `to_document()` / `from_document()` | JSON array of strings. |

A key is an identity, not a content address. Two equal values with different keys remain distinct symbols unless the language computes the same key.

### Declaration and symbol

```python
@dataclass(frozen=True, slots=True)
class Declaration:
    value: Any

@dataclass(frozen=True, slots=True)
class Symbol:
    key: Key
    kind: str
    value: Any
    references: tuple[SymbolRef, ...] = ()

@dataclass(frozen=True, slots=True)
class SymbolRef:
    language: str
    key: Key
```

- A declaration carries only the value the language recognised. It has no key; `Language.compute_key` derives one.
- A symbol carries the key, kind, value and direct references. The key is unique within its language.
- `kind` states the symbol's role as the language names it. `value` is the language's own frozen representation.
- `SymbolContext` exposes the symbols transcribed before the current declaration, dependencies first. `get_symbol` and `get_value` raise `KeyError` for an unknown reference.
- The linker transcribes each reachable declaration once, and the transcribed key must equal the indexed key.

### Role references

`SymbolRef(language, key)` is the kernel's reference type. The distribution adds role-typed wrappers; they are distribution types, not kernel types.

| Role type | Names | Document |
| --- | --- | --- |
| `NodeRef` | one topology node | `[language, "node", *key]` |
| `EdgeRef` | one topology edge | `[language, "edge", *key]` |
| `RelationRef` | one relation or projection | `[language, "relation", *key]` |
| `FieldRef` | one declared field | `[language, "field", *key]` |
| `PropertyRef` | one graph property | `[language, "property", *key]` |
| `AssetRef` | one logical asset | `[language, "asset", *key]` |
| `OperationRef` | one operation specification | `[language, "operation", *key]` |

Each wraps a `SymbolRef` and exposes `.symbol`, `.key`, `.language` and `.name`; equality and hashing use the wrapped reference. A bare cross-symbol string is not a reference.

### Workflow plan

```python
@dataclass(frozen=True, slots=True)
class WorkflowPlan:
    components: tuple[Component, ...]
    steps: tuple[Step, ...]
    connections: tuple[Connection, ...] = ()
    provenance: JsonValue | None = None
```

| Value | Facts |
| --- | --- |
| `Component` | `id`, `version`, `runtime_fields`; one per planner group. |
| `Step` | `component`, `name`, `inputs`, `outputs`, one `Instruction`, `assembly_preference`; `id` is `StepId(component, name)`. |
| `StepId` | component id and step name; `version` is not part of the identity. |
| `OpeningId(step, direction, name)` | one input or output port; direction is part of the key, so an input and an output may share a name. |
| `ArtifactType` | a concrete artifact key of at least two segments; no wildcard. |
| `ArtifactPattern` | the declared type an input accepts; `*` inside a segment, a final `**` for any remainder. |
| `Connection` | one resolved input opening to one output opening. |
| `Instruction` | `kind` and a JSON-compatible `payload`; the payload is opaque to the kernel. |
| `InstructionKind` | exact `(operation, engine)` pair. |

Assembly refuses a duplicate `StepId(component, name)`, a wiring with no producer and a wiring cycle. `compile` groups planners by `component_id` and publishes one component per group. `plan.provenance` is opaque to the kernel; `api.compile` records the source blueprint document under `provenance["blueprint"]`.

### Runtime and report

| Value | Facts |
| --- | --- |
| `WorkflowReport` | published artifacts, recovered failures, unresolved failures, provenance; `succeeded` is true when no unresolved failure remains. |
| `StepOutcome` | the step id, a `StepStatus`, produced artifacts and an optional `Failure`. |
| `StepStatus` | `SUCCEEDED`, `WARNING`, `FAILED`, `SKIPPED`; the first two are continuable, the last two disrupting. |
| `Artifact` | output opening name, concrete type and value; it does not store its step. |
| `PublishedArtifact` | one final artifact under its output opening. |
| `ExecutionContext` | the step, runtime configuration, inputs, the executor's `ResourceView` and a logger. |
| `DisruptedExecutionContext` | the same facts plus the disrupting upstream results. |
| `RuntimeConfiguration` | output, working and temporary directories, credentials, per-component and per-provider settings. |
| `ResourceView` | the exact resources one executor may read; `get` raises `KeyError` otherwise. |

The event values are `PipelineStarted`, `StepStarted`, `StepFinished`, `StepLogged`, `PipelineFinished` and `PipelineHalted`. `EventBus` delivers each event to every subscriber; `ResourceRegistry` holds the live resources keyed by exact type. `Resource` is the capability protocol: `close() -> None`. A resource is not a model field and is never stored in a plan.

### Opaque model

`ModelT` is opaque. `Toolchain[ModelT]` links to it, hands it to planners and never inspects it. The kernel never reads a `GraphBlueprint`, an instruction payload or an artifact value; the distribution implements the model and the executors that interpret those payloads.

## Rules

- Identity is a qualified name. A symbol is keyed by its language and key, not by a content digest.
- A declaration has no key; a symbol carries key, kind, value and references.
- A reference is `SymbolRef(language, key)`. Role types wrap it; a bare string never stands for a cross-symbol reference.
- A field declares a value type, not absence. Source access is nullable and computed access follows the selection.
- An instruction kind is exact. The kernel does not parse a payload or infer a kind from a name.
- A `Step` owns one `Instruction`; a step id is `(component, name)` with no version segment.
- An opening identity includes its direction. An input and an output with the same name on one step are distinct openings.
- Plan wiring is resolved before execution. An unresolved input or output is refused rather than discovered by an executor.
- Model values are frozen and carry no owner, service or wider context. Derived rules are functions beside the data.
- A `WorkflowPlan` is a DTO artifact of the plan; values outside the blueprint and the plan are in-memory models, not DTOs.

## Limits

- The kernel model carries no graph, node, edge, binding, projection or asset meaning. Those are distribution types.
- There is no schema version, migration path or compatibility negotiation. A change to a model value is a model change.
- The kernel does not validate that a payload matches an engine's expectations; the executor that claims the kind does.
- `WorkflowReport.provenance` is free-form. The kernel preserves it and assigns it no structure.
- Role refs and their documents are distribution contracts; the kernel defines only `SymbolRef`.
- The kernel model does not carry acquisition settings, storage layout or scheduling policy. A plan states structure, not how a deployment runs it.

## Next

[Kernel boundaries](/appendix/kernel/boundaries) — the three verbs, the dependency spine and the tests that guard them.
