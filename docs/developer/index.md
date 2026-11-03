# Developer guide

This section is for developers who change the framework, review its interfaces,
or add a language, linker, planner or executor. It describes the internal model
behind the authoring guide.

Graph authors should read the [authoring guide](../index.md). Developer docs and
author docs may cover the same subject for different readers: author docs state
what a graph author writes and observes; developer docs state the interfaces,
boundaries and design decisions the framework is built from.

## How to read this section

Read the pages in this order:

1. [Framework philosophy](philosophy.md) — the values that decide where code
   belongs: anemic models, semantics as contract, explicit boundaries, the
   toolchain, DTOs, source regeneration and transformation verbs.
2. [System design](system-design.md) — the package tree, the dependency spine,
   the kernel interfaces and the planner/executor split.
3. [Data and expressions](data-and-expressions.md) — where row sources, joins,
   projections, selections and operations live, and how the blueprint DTOs and
   source round trip work.
4. [Testing](testing.md) — the contract tests that guard each interface.

The developer docs are the canonical internal documentation. They state the
framework model, the package boundaries and the contract tests.

## Current state

The implemented tree is `kernel`, `distribution`, `generation`, `api.py` and
`cli`. The kernel type vocabulary is re-exported by the package root. Every leaf
uses `model/` and `service/`; shared mechanisms live in the package that
consumes them, for example JSON freezing in `kernel/model/internal/json.py`,
the scheduler in `kernel/service/_private/runtime.py`, and table naming and
docstring helpers in `distribution/languages/table/service/_private/`.

| Area | Implementation | Remaining limit |
| --- | --- | --- |
| Kernel | `Language`, `Linker`, `Planner`, `StepExecutor`, `Runtime`, `ResourceProvider`, `Toolchain` and `Extension` in `kernel/service/public`; the workflow and runtime values in `kernel/model/public`; canonical types in `kernel/model/public/types` | A language may publish only its layer value instead of per-declaration definitions |
| Languages | `collect`, `transcribe`, `validate`, `render` in the table, topology and binding services; annotations and expressions as supporting languages | None |
| Blueprint | `create_blueprint(...) -> GraphBlueprint`; `BlueprintLinker` implements the kernel `Linker` protocol through `service/internal/adapters/kernel_linker.py` | Public `GraphBlueprint` fields reference internal layer DTOs |
| Planning | `compile(model) -> WorkflowPlan` with the core, deduplication, merging and conflict-validation planners | The core planner depends on the DuckDB SQL emitter |
| Execution | `execute(plan, output_directory=...) -> WorkflowReport`; the kernel scheduler dispatches by exact `instruction.kind`; `DuckDbResourceProvider` owns engine services | DuckDB is the default engine |
| DTO names | `*DTO` names; graph node and edge identities carry graph names, not `symbol_id` | None |
| Source regeneration | Each language renders its own DTO; the blueprint source service delegates to the layer renderers | Python binding source is a reference, not the callable body |
| Distribution | `distribution.default` exports `DEFAULT_TOOLCHAIN` and `default_toolchain`; planners and executors are opt-in | None |
| SQL emission | The core planner emits `("sql", "duckdb")`; the DuckDB executor owns the engine boundary | DuckDB is the default SQL emitter |

## Verification

- 115 tests passed, 604 subtests.
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
