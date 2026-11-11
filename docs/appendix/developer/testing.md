---
title: Testing
summary: The contract tests that guard interfaces, boundaries and the public authoring surface.
section: developer
perspective: developer
order: 50
status: normative
verified: 2026-11-10
sources:
  - tests/kernel/test_import_isolation.py
  - tests/test_architecture.py
  - tests/test_public_docstrings.py
  - tests/test_reference_build.py
  - tests/typecheck/authoring.py
---

## Interface

A contract test names a boundary and fails when the boundary changes shape. A
test that only proves one function returns an expected value is not a contract
test. The suite groups its contracts by the interface they guard:

| Group | Guards | Representative tests |
| --- | --- | --- |
| Kernel flow | `build` -> `link` -> `compile` -> `execute` with fake languages, linkers, planners, executors, providers and runtime | `tests/kernel/` |
| Pipeline identity | step ids, artifact patterns, instruction kinds, duplicate ids and unknown connection endpoints | `tests/pipeline/test_pipeline_identity.py` |
| Planner | component ownership, shared `CorePlan`, exact step kinds and planner version/runtime fields | `tests/distribution/planners/` |
| Executor | exact instruction kinds, declared resources, `StepOutcome` and skipped disrupted contexts | `tests/distribution/executors/` |
| Distribution and DTO | typed refs, DTO fields, linker order, codecs and source round trips | `tests/distribution/` |
| Reference build | the public path composes and writes real artifacts | `tests/test_reference_build.py` |
| Guards | import isolation, architecture, layout, facades and public docstrings | `tests/test_architecture.py`, `tests/test_layout.py`, `tests/test_facades.py`, `tests/test_public_docstrings.py` |
| Typecheck | the static authoring surface and its refusals | `tests/typecheck/authoring.py`, `tests/typecheck/authoring_negative.py` |

Run the checks for the area changed:

```console
uv run pytest -q
uv run pyright
cd ../kg-build-kb && python3 scripts/kb.py check && npx quartz build -d ../kg-build-system/docs
```

The document build is part of verification because the developer pages state
interfaces. A broken link or a page outside the navigation is a documentation
defect. [Install and verify](/book/part-1/02-a-first-build) gives the environment setup.

## Rules

- Kernel flow tests use fake extensions and a fake runtime. None imports the
  distribution, which proves the kernel is domain-agnostic.
- `tests/kernel/test_import_isolation.py` runs a subprocess that imports the
  kernel and asserts that no distribution package, no DuckDB module and no
  removed `pipeline` package is loaded. The architecture suite repeats the
  static form of this guard: the kernel imports no domain package.
- `compile` reads the linked model. It does not call `build`, create a blueprint
  or import the distribution. The composition root calls `create_blueprint` and
  then `compile`; the public `api.compile` shortcut creates the blueprint first.
- The four core planners share `component_id="core"` and one `CorePlan` in
  `PlanContext.shared`. They emit row-source, projection, binding and aggregate
  steps. `DuckDbSourcePlanner` has `component_id="duckdb"` and emits one
  `source.<relation>` step per compatible asset-backed relation.
- Planners in one component agree on `version` and `runtime_fields`. Duplicate
  step ids are refused. A planner declares the input and output artifact types
  of every `Step`.
- `test_core_custom_emitter.py` threads a supplied `SqlEmitter` with a custom
  operator emitter through core planning. Core imports the neutral protocol
  only, never the DuckDB module.
- An executor claims exact instruction kinds, declares the resources it reads
  and reads only the payload for those kinds. A disrupted context becomes a
  skipped outcome. An executor does not schedule, assemble or read another
  executor's payload.
- The layout guard requires a facade for every leaf, refuses an empty visibility
  zone, refuses a facade import of a missing public zone or an old shim, and
  lets private code read public model but not public service.
- The architecture guard checks the package groups and entry points, facade
  surfaces, the model/service import matrix, private-zone crossings, adapter
  files and the rule that languages do not import the interpreter and only the
  interpreter and planners read the blueprint. The zone model is stated in
  [Architecture specification](/appendix/spec/architecture).
- The facade guard permits only a docstring, imports, a literal `__all__`, a
  `TYPE_CHECKING` block and import/re-export machinery in an `__init__.py`. The
  literal export table matches the lazy groups, and every export resolves.
- The public docstring test requires an `Example` section on every public
  function and public class method, requires a developer docstring on every
  internal function, and requires facade functions to come from a public
  surface. Top-level entry points are callable wrappers from `kg_build_system.api`.
- A language DTO imports only the DTOs of the languages it depends on; it does
  not import the blueprint. A graph node or edge identity carries no
  `symbol_id`, Python module path or declaration expression. Cross-symbol fields
  use role-typed refs such as `NodeRef`, `FieldRef` and `OperationRef`.
- `workflow_plan_from_document(workflow_plan_to_document(plan))` round-trips the
  kernel workflow plan. Every language DTO and the assembled blueprint satisfy
  `from_document(to_document(value)) == value`. Unknown fields, discriminators
  and source formats are refused. There is no schema version and no migration
  path.
- The source round trip renders `GraphBlueprint` to authoring source, imports it
  in a clean namespace, calls `create_blueprint` and compares semantic models,
  not source text. The stored document shape is in
  [Documents](/appendix/reference/documents).
- The reference build compiles and executes the public path. It writes
  `graph.jsonl`, `meta_graph.json`, `meta_graph.html`, `neo4j-import/`,
  `workflow_plan.json` and `build_report.json`, and publishes no intermediate
  core records.
- `tests/typecheck/authoring.py` is the strict positive fixture for `Selection`,
  owner-derived nullability, `field`/`computed_field`, pinned projections, row
  effects, lookup, zip and unnest. `tests/typecheck/authoring_negative.py` pins
  removed names and invalid effects with inline expected diagnostics.

## Limits

- Pyright includes `kg_build_system` and the two typecheck fixtures. It excludes
  `tests/`, `reference_project/` and `legacy/`.
- `reference_project` is exercised at runtime by the reference build but is not
  typechecked. `legacy` is neither a runtime target nor a typecheck target and is
  not a compatibility suite.
- The suite reports no line or branch coverage. A test count, subtest count or
  duration is a property of the checkout, not a contract.
- The public docstring test checks that an `Example` section exists. It does not
  execute the example.
- Kernel flow tests use fakes; the reference build is the integration proof.
- The Open Targets suite belongs to another checkout and is not evidence about
  this checkout.
- A green local run is not a release gate while the repository has no CI
  workflow.

## Next

[Verification](/appendix/review/verification) — the measured state and its limits.
