# Testing

The contract tests guard interfaces, not implementation. Each test names a
boundary and fails when the boundary changes shape. A test that only proves one
function returns the expected value is not a contract test.

The suite has five groups: kernel flow, planner, executor, distribution and
reference build. The sections below state what each group guards.

## Kernel flow

**Asserts:** `build` hands languages and a namespace to the linker; a language
discovers declarations, derives a key with `compute_key`, transcribes symbols
and exposes earlier symbols through `SymbolContext`. `compile` groups planners
by `component_id`, accepts several planners in one group only when their
versions and runtime fields agree, refuses duplicate step ids, assembles inputs
to outputs and refuses a missing producer or a cycle. `execute` maps exact
instruction kinds, refuses a duplicate kind or a kind with no executor before
any step runs, creates a fresh event bus and resource registry, subscribes the
providers and listeners, emits the pipeline lifecycle, builds one exact view per
executor and lets providers dispose their resources on finish or halt.

The tests use fake languages, linkers, planners, executors, providers and a fake
runtime. None imports the distribution. This is the proof that the kernel is
domain-agnostic and that its flow is complete without a graph.

Current coverage:

- `tests/kernel/test_kernel.py` — keys, declarations, symbols, symbol contexts,
  language ownership and identity, duplicate language names and the linker
  boundary.
- `tests/kernel/test_toolchain_flow.py` — the full `build -> compile -> execute`
  flow, duplicate step ids, unregistered instruction kinds, duplicate executor
  kinds and the workflow-plan codec round trip.
- `tests/kernel/test_runtime_resources.py` — provider resource publication on
  `PipelineStarted`, disposal on finish and halt, duplicate resource types,
  missing declared resources and the per-executor resource view.
- `tests/kernel/test_runtime_events.py` — the event lifecycle, halt events,
  listener errors, listener isolation between runs, `StepLogged` and the API
  monitor listener.
- `tests/kernel/test_extension_bundle.py` — one language, linker, planner,
  executor and provider composed into a `Toolchain`.
- `tests/kernel/test_import_isolation.py` — importing the kernel does not load a
  graph, data, topology, binding or engine package.

## Planner tests

**Asserts:** each planner receives a `GraphBlueprint`, emits the steps its
component owns and leaves every other component's records alone. The four core
planners share `component_id="core"` and one `CorePlan` in `PlanContext.shared`;
they emit row-source, projection, binding and aggregate steps. The generic
`DuckDbSourcePlanner` has `component_id="duckdb"` and emits one
`source.<relation>` step per compatible asset-backed relation.
Deduplication emits one distinct step per bound record component. Merging
respects its component scope. Conflict validation emits one findings step per
property and one deferred report step. A planner declares its `component_id`,
`version` and `runtime_fields`, and its `plan` returns `Step` values with known
input and output artifact types.

Current coverage:

- `test_core_planner.py` — source, projection, binding and aggregate planning
  across the generic source planner and the feature-scoped core planners.
- `test_duckdb_source_planner.py` — asset-table selection, layout resolution
  and `source_relation` payloads.
- `test_core_custom_emitter.py` — a non-DuckDB `SqlEmitter` threaded through
  core planning; core imports the neutral protocol only.
- `test_dedup_merge_conflict_planners.py` — the deduplication, merging and
  conflict-validation planners.
- `test_multi_planner_components.py` — several planners sharing one component,
  including the version and runtime-field checks.
- `test_plan_assembly.py` — step assembly from planned contributions.
- `test_planner_imports_no_pipeline.py` — a planner does not load the legacy
  package path.

## Executor tests

**Asserts:** an executor claims exact instruction kinds, declares the resources
it reads, reads only the payload for those kinds, returns a `StepOutcome` and
turns a disrupted context into a skipped outcome. `DuckDbExecutor` owns the
DuckDB kinds and reads a `DuckDbService` and `RelationService` from its resource
view. `FileExecutor`, `MetaGraphExecutor`, `Neo4jExecutor` and
`PythonExecutor` own their own kinds and declare their own resources. An
executor does not schedule, assemble or read another executor's payload.

Current coverage:

- `test_duckdb_executor.py` — DuckDB instruction kinds and outcomes.
- `test_duckdb_resources.py` — the DuckDB resource provider and its service.
- `test_python_executor.py` — the Python reference instruction.
- `test_toolchain_execution.py` — executor selection and report assembly through
  a toolchain.
- `test_executor_imports_no_pipeline.py` — an executor does not load the legacy
  package path.
- `targets/test_file_target.py`, `targets/test_meta_graph_target.py`,
  `targets/test_neo4j_target.py` and `targets/test_conflict_report.py` — the
  output targets.

## Distribution and DTO scope

**Asserts:** every leaf has the zones it uses; an existing zone is not an empty
marker; a facade contains only a docstring, imports and `__all__`; model
public/internal import no service or private code; service public imports no
private code; service internal has no eager private import; cross-package
imports never enter a private zone; every foreign protocol has an explicit
adapter.

A language DTO imports only the DTOs of the languages it depends on; it does not
import the blueprint. A graph node or edge identity contains no `symbol_id`,
Python module path or declaration expression. Endpoints and parents are graph
names. Annotation payloads are `(namespace, id, arguments)`. A Python binding
carries only a stable `PythonRefDTO(module, qualname, signature)`. Cross-symbol
fields carry role-typed refs such as `NodeRef`, `FieldRef` and `OperationRef`;
none is a bare string.

Current coverage:

- `tests/test_layout.py` — model/service zones, facade imports, empty-zone
  removal and the private/public-service import rule.
- `tests/test_architecture.py` — the package tree, facade surfaces, private
  zones, model/service import matrix and adapter files across `kernel`,
  `distribution`, `generation` and `cli`.
- `tests/test_facades.py` — every `__init__.py` contains only a docstring,
  imports, a literal `__all__`, `TYPE_CHECKING` imports and import/re-export
  machinery; the top-level lazy groups match `__all__`.
- `tests/test_naming.py` — the interface naming rules.
- `tests/distribution/test_blueprint_dto.py` — language DTO fields, graph-name
  endpoints and parents, and the public blueprint references.
- `tests/distribution/test_typed_refs.py` — role-typed references and their
  documents.
- `tests/distribution/test_asset_language.py` — asset declaration, validation,
  discovery, key, transcription, typed reference and codec round trip.
- `tests/distribution/test_blueprint_linker.py` — `BlueprintLinker` implements
  the kernel `Linker` protocol, keys declarations, resolves the authoring
  reference closure, transcribes each reachable declaration once and assembles
  one blueprint in `expressions`, `asset`, `data`, `topology`, `binding` order.
- `tests/distribution/test_expression_operations.py` — `Selection` operations,
  `extract`, one-shot row effects, `lookup`, `zip`, array operations and
  `RowSource.unnest`.

## Codec and source round trip

**Asserts:** `workflow_plan_from_document(workflow_plan_to_document(plan))`
round-trips the kernel workflow plan, including a Python instruction and an SQL
instruction. For every language DTO and for the assembled blueprint,
`from_document(to_document(value))` equals the original value. The blueprint
codec composes the language codecs. An unknown field, an unknown discriminator
or an unknown source format is refused. There is no schema version and no
migration path.

The source round trip asserts
`GraphBlueprint -> rendered authoring source -> GraphBlueprint` produces an
equivalent blueprint. The test renders through each language's source service,
imports the generated source in a clean namespace and creates a new blueprint.
It compares the semantic models, not the source text.

Current coverage:

- `tests/kernel/test_toolchain_flow.py` — the workflow-plan codec round trip.
- `tests/distribution/test_source_roundtrip.py` — the language source fragments
  and the blueprint source round trip.
- `tests/distribution/test_blueprint_source.py` — the blueprint source round
  trip.

## No `IR` and no `lower`

**Asserts:** the framework names do not use `IR` as a module or class suffix and
do not use `lower` as a transformation verb. The allowed names are `DTO` for a
serialisable artifact, `model` for an in-memory model and `plan` for an
engine-neutral plan. The allowed verbs are `discover`, `key`, `transcribe`,
`link`, `plan`, `assemble`, `emit`, `render` and `execute`. The symbol graph may
be described as linker IR in prose, but no module or class is named for it.

Current coverage: `tests/test_naming.py` checks that no framework name uses
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
- `tests/test_public_api.py` and `tests/test_authoring_api.py` — the public
  names and the authoring surface: `Selection`, owner-derived nullability,
  `field`/`computed_field`, pinned projections, row effects, lookup, zip and
  unnest.
- `tests/typecheck/authoring.py` — the authoring typecheck fixture.
- Open Targets: `cd ~/Repos/opentargets-kg && uv run pytest -q`.

## Verification

- 259 tests passed, 1858 subtests.
- Pyright: 0 errors.
- The reference build passes.
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
- Kernel flow tests use fake languages, linkers, planners, executors and
  providers; they prove the kernel works without the distribution.
- Planner and executor tests name the component and the exact instruction kinds.
- `tests/pipeline/test_pipeline_identity.py` guards the identity roles:
  ambiguous dotted ids, input/output name collision, artifact patterns,
  instruction-kind exactness, duplicate ids and unknown connection endpoints.
- A planner group may share a component; a `StepId` may not repeat.
- An executor declares its resources; the runtime owns the providers.
- The source round trip is a contract, not a convenience.
- `IR` and `lower` are not target vocabulary; the target vocabulary is `DTO`,
  `model`, `plan`, `discover`, `key`, `transcribe`, `link`, `plan`, `assemble`,
  `emit`, `render` and `execute`.
- `compile` reads a linked model; the `compile` shortcut creates the blueprint
  first.

Next: [Developer guide](index.md).
