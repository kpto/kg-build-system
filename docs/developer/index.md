# Developer guide

This section is for developers who change the framework, review its interfaces,
or add a language, module or engine. It describes the internal model behind the
authoring guide.

Graph authors should read the [authoring guide](../index.md). Developer docs and
author docs may cover the same subject for different readers: author docs state
what a graph author writes and observes; developer docs state the interfaces,
boundaries and design decisions the framework is built from.

## How to read this section

Read the pages in this order:

1. [Framework philosophy](philosophy.md) — the values that decide where code
   belongs: anemic models, semantics as contract, explicit boundaries, the three
   systems, DTOs, source regeneration and transformation verbs.
2. [System design](system-design.md) — the package tree, the dependency
   spine, the leaf layout and the split between blueprint, compilation, contract
   and build.
3. [Data and expressions](data-and-expressions.md) — where row sources, joins,
   projections, selections and operations live, and how the blueprint DTOs and
   source round trip work.
4. [Testing](testing.md) — the contract tests that guard each interface.

The developer docs are the canonical internal documentation. They state the
framework model, the package boundaries and the contract tests.

## Current state

The implemented tree is `kernel`, `declaration`, `pipeline/{contract,
compilation, build}`, `distribution`, `generation`, `api.py` and `cli`. The
kernel type vocabulary is re-exported by the package root. Every leaf uses
`model/` and `service/`; shared mechanisms live in the package that consumes
them, for example JSON
freezing in `kernel/model/internal/json.py`, relation protocols in
`pipeline/build/service/internal/relations/protocols.py`, and table naming and
docstring helpers in `declaration/languages/table/service/_private/`.

| Area | Implementation | Remaining limit |
| --- | --- | --- |
| Kernel | Domain-agnostic protocols in `kernel/service/public`, canonical types in `kernel/model/public/types`, `Capability`, build and contract values | Capability modules are deferred; `Module` does not declare `requires`/`provides` |
| Languages | `collect`, `transcribe`, `validate`, `render` in the table, topology and binding services | None |
| Blueprint and compilation | `create_blueprint(...) -> GraphBlueprint`; `compile_blueprint(blueprint, *, modules, engine=None) -> WorkflowContractDTO`; `compile(...)` is the canonical shortcut | Public `GraphBlueprint` fields reference internal layer DTOs |
| Contract and build | `WorkflowContractDTO` owns contributions, connections and provenance; `StepDTO` owns its `InstructionDTO`; `pipeline.build.build` dispatches on `step.instruction.kind` | Some target executors still receive instruction payloads through `variables` |
| DTO names | `*DTO` names; graph node and edge identities carry graph names, not `symbol_id` | None |
| Source regeneration | Each language renders its own DTO; `blueprint_to_source` delegates to the three layer renderers | Python binding source is a reference, not the callable body |
| Distribution | `distribution.service.public` exports the supplied modules and `register_module` | None |
| SQL emission | `pipeline/compilation/service/internal/instruction` emits instructions; `pipeline/build/service/internal/engine` owns the engine boundary | DuckDB is the default SQL emitter |

## Verification

- 69 tests passed, 484 subtests.
- Pyright: 0 errors.
- Open Targets: 6 tests passed.
- `uv run mkdocs build --strict`: passes.

## What to remember

- Developer docs describe the framework's internal interfaces; author docs
  describe the authoring surface.
- The framework model is the decision. Current code is reported against it, not
  used to redefine it.
- A change to an interface is a model change and is reviewed before it is
  implemented.

Next: [Framework philosophy](philosophy.md).
