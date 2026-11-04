# Developer guide

This section is for developers who change the framework, review its interfaces,
or add a language, linker, planner, executor or resource. It describes the
internal model behind the authoring guide.

Graph authors should read the [authoring guide](../index.md). Developer docs and
author docs may cover the same subject for different readers: author docs state
what a graph author writes and observes; developer docs state the interfaces,
boundaries and design decisions the framework is built from.

## How to read this section

Read the pages in this order:

1. [Framework philosophy](philosophy.md) — the values that decide where code
   belongs: anemic models, semantics as contract, explicit boundaries, the
   toolchain, DTOs, source regeneration and transformation verbs.
2. [System design](system-design.md) — the package tree, the module layout, the
   kernel interfaces, declarations and symbols, the blueprint and the
   planner/executor/resource split.
3. [Data and expressions](data-and-expressions.md) — where row sources, joins,
   projections, selections and operations live, and how the blueprint DTOs,
   typed references and source round trip work.
4. [Testing](testing.md) — the contract tests that guard each interface.

The developer docs are the canonical internal documentation. They state the
framework model, the package boundaries and the contract tests.

## Current state

The implemented tree is `kernel`, `distribution`, `frontend`, `generation`,
`api.py` and `cli`. The kernel type vocabulary is re-exported by the package
root. Every leaf uses the zones it needs from `model/` and `service/`; shared
mechanisms live in the package that consumes them, for example JSON freezing in
`kernel/model/internal/json.py`, the scheduler in
`kernel/service/_private/runtime.py`, the pipeline event model in
`kernel/model/public/events.py`, frontend monitors in `frontend/monitor.py`, and
naming and docstring helpers in
`distribution/languages/data/service/_private/`.

| Area | Implementation | Remaining limit |
| --- | --- | --- |
| Kernel | `Language`, `Declaration`, `Symbol`, `SymbolRef`, `Key`, `Linker`, `Planner`, `StepExecutor`, `Runtime`, `Resource`, `ResourceProvider`, `ResourceView`, `Toolchain` in `kernel/service/public`; the workflow, runtime and event values in `kernel/model/public`; canonical types in `kernel/model/public/types` | A toolchain is the only composition unit |
| Languages | `discover_declarations`, `compute_key`, `get_kind`, `owns`, `get_identity`, `get_references`, `transcribe_many` and `render` in the expressions, asset, data, topology and binding services; annotations remain inline | Custom operations outside the static registry are not symbol declarations |
| Blueprint | `create_blueprint(...) -> GraphBlueprint`; `BlueprintLinker` implements the kernel `Linker` protocol through `service/internal/adapters/kernel_linker.py`; typed references in `distribution/model/public/refs.py` | Public `GraphBlueprint` fields reference internal language DTOs |
| Planning | `compile(model) -> WorkflowPlan`; the generic `DuckDbSourcePlanner` has `component_id="duckdb"` and the core module has four planners sharing `component_id="core"`, plus deduplication, merging and conflict-validation planners | The core planners depend on the DuckDB SQL emitter |
| Execution | `execute(plan, output_directory=..., monitor=...) -> WorkflowReport`; the kernel emits `PipelineEvent`s and dispatches by exact `instruction.kind`; providers subscribe to the run and publish resources on `PipelineStarted`; `DuckDbResourceProvider`, `DuckDbService` and `RuntimeResources` own the live resources | DuckDB is the default engine |
| Frontend | `Monitor`, `NullMonitor`, `ConsoleMonitor` and `resolve_monitor` in `frontend/monitor.py`; `api.execute(monitor=...)` subscribes the selected listener | `rich` is optional and loaded lazily |
| DTO names | `*DTO` names; cross-symbol fields carry role-typed refs such as `NodeRef` and `FieldRef`, never a bare name or `symbol_id` | None |
| Source regeneration | Each language renders its own DTO; the blueprint source service delegates to the language renderers | Python binding source is a reference, not the callable body |
| Distribution | `kg_build_system.api` exports `DEFAULT_TOOLCHAIN` and `default_toolchain`; the distribution supplies implementations; planners and executors are opt-in | None |
| SQL emission | The core planners emit `("sql", "duckdb")`; the DuckDB module owns the executor, resource provider and emitter | DuckDB is the default SQL emitter |

## Verification

- 228 tests passed, 1753 subtests.
- Pyright: 0 errors.
- `uv run mkdocs build --strict`: passes.
- Open Targets: 7 tests passed.

## What to remember

- Developer docs describe the framework's internal interfaces; author docs
  describe the authoring surface.
- The framework model is the decision. Current code is reported against it, not
  used to redefine it.
- A change to an interface is a model change and is reviewed before it is
  implemented.

Next: [Framework philosophy](philosophy.md).
