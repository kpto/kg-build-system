# Testing

The contract tests guard interfaces, not implementation. Each test names a
boundary and fails when the boundary changes shape. A test that only proves one
function returns the expected value is not a contract test.

The suite has five layers: kernel flow, planner, executor, distribution and
reference build. The sections below state what each layer guards.

## Kernel flow

**Asserts:** `build` orders languages by `requires`, rejects duplicate names,
unknown dependencies and cycles, transcribes in dependency order and links the
layers. `compile` assigns each planner's `component_id`, refuses duplicate
component and step ids, assembles inputs to outputs and refuses a missing
producer or a cycle. `execute` maps exact instruction kinds, refuses a duplicate
kind or a kind with no executor before any step runs, and always closes the
services.

The tests use fake languages, linkers, planners, executors, resources and a fake
runtime. None imports the distribution. This is the proof that the kernel is
domain-agnostic and that its flow is complete without a graph.

Current coverage:

- `tests/kernel/test_kernel.py` — language ordering, dependency reads, duplicate
  names, unknown dependencies, cycles and the read-only definition index.
- `tests/kernel/test_toolchain_flow.py` — the full `build -> compile -> execute`
  flow, duplicate step ids, unregistered instruction kinds, duplicate executor
  kinds, service closing and the workflow-plan codec round trip.
- `tests/kernel/test_extension_bundle.py` — one `Extension` composed into a
  `Toolchain` with a fake language, linker, planner, executor and resources.
- `tests/kernel/test_import_isolation.py` — importing the kernel does not load a
  graph, data, topology, binding or engine package.

## Planner tests

**Asserts:** each planner receives a `GraphBlueprint`, emits the steps its
component owns and leaves every other component's records alone. Core emits
source, row-source, projection, binding and aggregate steps. Deduplication emits
one distinct step per bound record component. Merging respects its component
scope. Conflict validation emits one findings step per property and one deferred
report step. A planner declares its `component_id`, `version` and
`runtime_fields`, and its `plan` returns `Step` values with known input and output
artifact types.

Current coverage:

- `tests/distribution/planners/test_core_planner.py` — core source,
  projection, binding and aggregate planning.
- `tests/distribution/planners/test_core_custom_emitter.py` — a custom SQL
  emitter threaded through core planning.
- `tests/distribution/planners/test_dedup_merge_conflict_planners.py` — the
  deduplication, merging and conflict-validation planners.
- `tests/distribution/planners/test_plan_assembly.py` — step assembly from planned
  contributions.
- `tests/distribution/planners/test_planner_imports_no_pipeline.py` — a planner
  does not load the legacy package path.

## Executor tests

**Asserts:** an executor claims exact instruction kinds, reads only the payload
for those kinds, returns a `StepOutcome` and turns a disrupted context into a
skipped outcome. `DuckDbExecutor` owns the DuckDB kinds and its resource provider
creates relations, working storage, temporary storage, credentials and the engine
session. `FileExecutor`, `MetaGraphExecutor`, `Neo4jExecutor` and
`PythonExecutor` own their own kinds. An executor does not schedule, assemble or
read another executor's payload.

Current coverage:

- `tests/distribution/executors/test_duckdb_executor.py` — DuckDB instruction
  kinds and outcomes.
- `tests/distribution/executors/test_duckdb_resources.py` — the resource provider
  and its services.
- `tests/distribution/executors/test_python_executor.py` — the Python reference
  instruction.
- `tests/distribution/executors/test_toolchain_execution.py` — executor selection
  and report assembly through a toolchain.
- `tests/distribution/executors/test_executor_imports_no_pipeline.py` — an
  executor does not load the legacy package path.

## Distribution and DTO scope

**Asserts:** every leaf has `model/public`, `model/internal`, `service/public`,
`service/internal` and `service/_private`; a facade imports only `model.public`
and `service.public`; model public/internal import no service or private code;
service public imports no private code; service internal has no eager private
import; cross-package imports never enter a private zone; every foreign protocol
has an explicit adapter.

A layer DTO imports only the DTOs of the layers it depends on; it does not import
the blueprint. A graph node or edge identity contains no `symbol_id`, Python
module path or declaration expression. Endpoints and parents are graph names.
Annotation payloads are `(namespace, id, arguments)`. A Python binding carries
only a stable `PythonRefDTO(module, qualname, signature)`.

Current coverage:

- `tests/test_layout.py` — model/service directories, facade imports and the
  private/public-service import rule.
- `tests/test_architecture.py` — the package tree, facade surfaces, private
  zones, model/service import matrix and adapter files across `kernel`,
  `distribution`, `generation` and `cli`.
- `tests/test_naming.py` — the interface naming rules.
- `tests/distribution/test_blueprint_dto.py` — layer DTO fields, graph-name
  endpoints and parents, and the public blueprint references.
- `tests/distribution/test_blueprint_linker.py` — `BlueprintLinker` implements
  the kernel `Linker` protocol and links the language layers into one blueprint.

## Codec and source round trip

**Asserts:** `workflow_plan_from_document(workflow_plan_to_document(plan))`
round-trips the kernel workflow plan, including a Python instruction and an SQL
instruction. For every layer DTO and for the assembled blueprint,
`from_document(to_document(value))` equals the original value. The blueprint
codec composes the layer codecs. An unknown field, an unknown discriminator or an
unknown source format is refused. There is no schema version and no migration
path.

The source round trip asserts
`GraphBlueprint -> rendered authoring source -> GraphBlueprint` produces an
equivalent blueprint. The test renders through each layer's source service,
imports the generated source in a clean namespace and creates a new blueprint.
It compares the semantic models, not the source text.

Current coverage:

- `tests/kernel/test_toolchain_flow.py` — the workflow-plan codec round trip.
- `tests/distribution/test_source_roundtrip.py` — the layer source fragments and
  the blueprint source round trip.
- `tests/distribution/test_blueprint_source.py` — the blueprint source round
  trip.

## No `IR` and no `lower`

**Asserts:** the framework names do not use `IR` as a module or class suffix and
do not use `lower` as a transformation verb. The allowed names are `DTO` for a
serialisable artifact, `model` for an in-memory model and `plan` for an
engine-neutral plan. The allowed verbs are `collect`, `transcribe`, `link`,
`plan`, `assemble`, `emit`, `render` and `execute`.

Current coverage: `tests/test_naming.py` checks that no framework definition uses
the `IR` suffix or the `lower` verb, that DTO classes live in DTO modules and that
plans and generated models are not DTOs.

## Compile does not build

**Asserts:** `Toolchain.compile` reads the linked model and does not call
`build`, create a blueprint or import the distribution. The composition root is
what calls `create_blueprint` and then `compile`.

Current coverage: `tests/kernel/test_toolchain_flow.py` compiles a model built by
fake languages and a fake linker, and `tests/kernel/test_import_isolation.py`
proves the kernel does not load a distribution package. The public
`api.compile` shortcut creates a blueprint and then calls the toolchain; that is
its contract.

## Reference build and Open Targets

**Asserts:** the reference project builds graph records, a meta-graph and a Neo4j
bundle through the public API, with the same planner and executor composition the
authoring guide documents. The Open Targets project builds against the same
interfaces.

Current coverage:

- `tests/test_reference_build.py` — the reference build writes `graph.jsonl`,
  `meta_graph.json`, `meta_graph.html` and `neo4j-import/`.
- `tests/test_public_api.py` and `tests/test_old_authoring_api.py` — the public
  names and the authoring surface.
- `tests/typecheck/authoring.py` — the authoring typecheck fixture.
- Open Targets: `cd ~/Repos/opentargets-kg && uv run pytest -q`.

## Verification

- 115 tests passed, 604 subtests.
- Pyright: 0 errors.
- Open Targets: 7 tests passed.
- `uv run mkdocs build --strict`: passes.

Run the checks for the area changed:

```console
uv run pytest -q
uv run pyright
uv run mkdocs build --strict
```

The document build is part of the verification because the developer guide states
interfaces. A broken link or a page outside the navigation is a documentation
defect.

Do not rebuild the graph or regenerate artifacts unless the change requires it.

## What to remember

- A contract test asserts an interface or a boundary, not a return value.
- Kernel flow tests use fake languages, linkers, planners and executors; they
  prove the kernel works without the distribution.
- Planner and executor tests name the component and the exact instruction kinds.
- The source round trip is a contract, not a convenience.
- `IR` and `lower` are not target vocabulary; the target vocabulary is `DTO`,
  `model`, `plan`, `collect`, `transcribe`, `link`, `plan`, `assemble`, `emit`,
  `render` and `execute`.
- `compile` reads a linked model; the `compile` shortcut creates the blueprint
  first.

Next: [Developer guide](index.md).
