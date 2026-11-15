---
title: Extension specification
summary: The kernel protocol set is the extension surface; contributions are ordinary objects composed into a toolchain or runtime.
section: spec
perspective: spec
subject: extension
spec: SPEC-013
order: 130
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/kernel/service/public/pipeline.py
  - kg_build_system/kernel/model/public/language.py
  - kg_build_system/api.py
  - kg_build_system/distribution/service/internal/emission.py
  - kg_build_system/distribution/modules/python/service/_private/python.py
evidence:
  - tests/kernel/test_toolchain_flow.py
  - tests/distribution/planners/test_core_custom_emitter.py
  - tests/test_architecture.py
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Extending the toolchain</span><a href="/appendix/subjects/extension">Overview</a><a href="/book/part-2/06-extension">Guide</a><a href="/appendix/spec/extension" class="active">Spec</a><a href="/appendix/reference/api">API</a><a href="/appendix/philosophy/design-in-meaning">Philosophy</a><a href="/appendix/review/architecture">Review</a></div>
<!-- END GENERATED:views -->

## Requirement

- **R1.** A contribution MUST be an ordinary object passed explicitly to the composition that owns it: a language, linker, planner, or executor to `Toolchain` or `default_toolchain`; a `ResourceProvider` to the runtime. No `Extension` class, extension registry, plugin entry point, or discovery-by-name path may exist.
- **R2.** `Toolchain` MUST compose `languages`, `linker`, `planners`, `executors`, and `runtime`. `default_toolchain` MUST accept planners and executors and MUST add the generic source planner unless a supplied planner claims `duckdb`, and the core planners unless one claims `core`.
- **R3.** A `Language` MUST implement `discover_declarations`, `compute_key`, `get_kind`, `get_identity`, `get_references`, `transcribe`, and `render`. The linker MUST call `transcribe` once per reachable declaration.
- **R4.** A `Planner` MUST declare `component_id`, `version`, and `runtime_fields`, and `plan(model, context)` MUST return a sequence of steps. Planners that share a component MUST agree on version and runtime fields.
- **R5.** A `StepExecutor` MUST declare the exact `kinds` it handles, MUST declare the `resources` it reads, and MUST return a `StepOutcome` from `execute`. Its `ResourceView` MUST contain exactly the declared types; any other lookup MUST raise `KeyError`.
- **R6.** Instruction dispatch MUST compare `InstructionKind` exactly. Prefix matching, wildcard kinds, and family dispatch MUST NOT exist.
- **R7.** A `ResourceProvider` MUST receive events through `on_event`, MUST publish resources on `PipelineStarted`, and MUST dispose them on `PipelineFinished` or `PipelineHalted`.
- **R8.** A custom engine MUST implement the neutral `SqlEmitter` protocol. Core planners MUST consume that protocol and MUST NOT import a DuckDB module.
- **R9.** The Python executor SHOULD run only trusted targets: `("python", "cpython")` imports `{module, qualname}` in the host process and provides no isolation, timeout, or retry.

## Evidence

| Evidence | Proves |
| --- | --- |
| `tests/kernel/test_toolchain_flow.py` | A custom language, linker, planner, executor, and resource provider run through build, compile, and execute; duplicate steps and missing executors are refused. |
| `tests/distribution/planners/test_core_custom_emitter.py` | Core planners accept a supplied `SqlEmitter` and emit through its instruction emitter. |
| `tests/test_architecture.py` | The kernel and core import boundaries hold, including the refusal of domain and DuckDB imports. |

## API

| Name | Kind | Contract |
| --- | --- | --- |
| `Toolchain` | composition value | Languages, linker, planners, executors, and runtime in one explicit value. |
| `default_toolchain` | factory | Adds the default source and core planners only when no supplied planner claims their component. |
| `Language` | protocol | Seven-method frontend; `transcribe` is the per-declaration path. |
| `Planner` | protocol | One component identity, version, runtime fields, and `plan`. |
| `StepExecutor` | protocol | Exact instruction kinds, declared resources, and `execute`. |
| `ResourceProvider` | protocol | Event listener that opens and disposes live resources. |
| `InstructionKind` | role type | Exact `(operation, engine)` dispatch key. |
| `SqlEmitter` | protocol | Engine-neutral relation and row-source emission. |
| `PythonExecutor` | built-in executor | `("python", "cpython")` with a `{module, qualname}` payload. |

> [!note] Worked example
> [A consensus module](/book/part-4/01-the-kernel-and-extension#a-consensus-module-composed) composes a `Planner` and a `StepExecutor` into a `Toolchain`. It is a composed module, not a shipped default.

## Limits

- There is no per-step timeout, retry, cancellation, or memory quota. A Python target runs in the host process.
- A new language must implement the whole language surface; a helper may batch internally, but the linker still calls `transcribe` per declaration.
- Execution uses one exact-kind map. Two executors claiming one kind, or a plan kind with no executor, are refused before any step runs.
- A listener observes events and cannot change scheduling, resources, or the report.
- `default_toolchain` supplies one graph distribution. A custom distribution composes its own languages, linker, and planners.
- A custom engine supplies the neutral emitter; the kernel does not inspect SQL or engine objects.

## Rationale

Explicit composition keeps a build readable as the objects a project actually supplies. The kernel owns protocols, while the distribution owns graph meaning, so a new engine or language changes the toolchain rather than the definition of a step. That is the same authored-boundary stance as [binding is the fulfilment](/appendix/philosophy/binding-is-fulfilment): the connection is named, never inferred.

## Next

[Extension subject](/appendix/subjects/extension) — the subject index entry for toolchain composition and engine boundaries.
