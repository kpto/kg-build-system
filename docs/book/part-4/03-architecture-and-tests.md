---
title: "19. Architecture and tests"
summary: "Zones place code, the dependency spine gives it a direction, and contract tests make the interface visible before implementation is read."
section: book
perspective: book
part: IV
chapter: 19
order: 44
status: normative
verified: 2026-11-11
sources:
  - tests/test_architecture.py
  - tests/test_layout.py
  - tests/test_facades.py
  - tests/test_public_docstrings.py
  - tests/typecheck/authoring.py
---

## A change is reviewed at its boundary

A change proposes to move SQL text into the kernel so that a planner can build queries without a distribution dependency. The tests pass. The public API is untouched. A reviewer who reads only the diff sees a plausible refactor and a green build.

The change is still wrong. The kernel is defined as domain-agnostic, and SQL is a distribution concern. The boundary is not a comment in a style guide; it is the set of names another subpackage may depend on, the direction dependencies may run, and the tests that refuse an illegal edge. A reviewer who reads the interface sees the violation before reading the implementation. That is why the interface, not the code, is the review surface.

The same logic applies to the consensus module from Chapter 17. A reviewer does not need to inspect `majority` to decide whether the module belongs. The reviewer needs the responsibility, the names it adds, the dependency edges it creates, the authoring surface it changes and the tests that guard it. If those are coherent, the implementation is replaceable. If they are not, a green test suite does not rescue the design.

## Zones are a reading order

Every framework leaf uses the same layout. The layout is not a filing convention; it tells a reader what is stable, what is shared across packages and what may change without notice.

| Zone | Holds | Who may import it |
| --- | --- | --- |
| `pkg` | Facade over `model.public` and `service.public`. | Any package. |
| `pkg.model.public` | Authoring models, returned values and public DTOs. | Any package. |
| `pkg.model.internal` | Cross-package data under `dto/` and `model/`. | Any package. |
| `pkg.model._private` | Private plans, render models and engine types. | Its own package only. |
| `pkg.service.public` | Author-facing methods and thin wrappers. | Any package. |
| `pkg.service.internal` | Service interfaces, codec and assembly wrappers, adapters. | Any package. |
| `pkg.service._private` | Codecs, transcription, rendering, validation, assembly, planning, engines, runtime. | Its own package only. |

The `__init__.py` is a facade: a docstring, imports, a literal `__all__` and import/re-export machinery. It carries no service, planner, codec, validation rule, feature registry or default instance. The top-level export table in `kg_build_system/__init__.py` is lazy loading, which is import machinery rather than business logic.

Data is the lowest layer inside a package. `model.public` and `model.internal` import no service and no `_private`; `model._private` may read model data but not service behaviour. `service.public` imports `model.public` and `service.internal`, never `_private`. `service.internal` delegates to `service._private` with a function-local import, so a private implementation can import a service without creating an eager cycle. A package implements another package's protocol in a separate adapter file under `service/internal/adapters/<protocol>.py`, not inside a model or a factory.

The zones do not create a runtime sandbox. An illegal import is visible, not impossible. The value is that a reviewer can ask a precise question: does this change add a name to a public zone, add an edge to a private zone, or put mechanism where only data belongs? The answer is readable from the path before the implementation is read.

## The dependency spine is a direction, not a diagram

The spine names which package may import which. It is a tree for reading, not a complete graph; the dependency tests enforce the exact edges that exist.

| Package | May import |
| --- | --- |
| `kernel` | No framework package. |
| `languages/annotations`, `languages/expressions`, `languages/semantics` | `kernel` |
| `languages/graph` | `kernel`, semantics |
| `languages/asset` | `kernel`, annotations, semantics |
| `languages/data` | `kernel`, annotations, expressions, asset, semantics |
| `languages/topology` | `kernel`, annotations, expressions, semantics |
| `languages/binding` | `kernel`, annotations, data, topology, semantics |
| `interpreter` | `kernel`, every graph language, semantics |
| `modules/<name>` | `kernel`, `interpreter` where it reads a blueprint, languages, `distribution.model`, `distribution.service` |
| `implementations.py` | `kernel`, interpreter, languages |
| `generation/code_generation` | `kernel`, `languages/asset` |
| `api.py` | `kernel`, distribution |
| `cli` | generation, `api.py` |

The kernel row is the load-bearing one. The kernel imports no distribution, graph, data, topology, binding, SQL, DuckDB, Python or generation package. It uses toolchain vocabulary: language, declaration, symbol, key, reference, linker, planner, workflow plan, runtime, executor, resource and toolchain. The distribution uses domain vocabulary: graph, blueprint, node, edge, binding, projection and asset. A kernel model that needs a graph word has crossed the boundary, even if the type is spelled with a neutral name.

A new edge is a model change. It may be the right change, but it is proposed with its reason before it is implemented. The reason cannot be convenience. "The planner needs the helper" is not an argument for importing a private module; it is an argument for moving the helper to an interface the planner may use, or for rethinking which package owns the decision. A cycle is refused outright.

The spine also explains why a small feature sometimes forces edits in several packages. If a join change requires editing table declarations, the planner and the authoring API, the boundary is wrong. The join belongs to the row-source package, and the planner should consume a shape that package exposes. Fixing the boundary is a different change from fixing the call sites.

## The contract-test groups

A contract test names a boundary and fails when the boundary changes shape. A test that only proves one function returns an expected value is not a contract test. The suite groups its contracts by the interface they guard.

| Group | Guards |
| --- | --- |
| Import isolation | Importing the kernel loads no distribution package, SQL module or DuckDB module. |
| Architecture | Leaf inventory, public and internal visibility, function-local private imports and the dependency spine. |
| Layout | Every leaf has a facade, empty zones are deleted and private code follows the model and service direction. |
| Facades | `__init__.py` contains import machinery only, and the export table resolves. |
| Public docstrings | Every public function and public class method has an `Example` section; internal functions have developer docstrings. |
| Reference build | The public path composes, executes and writes real artifacts. |
| Typecheck fixtures | The static authoring surface and its refusals. |

Import isolation is the sharpest test. It runs a subprocess that imports the kernel and asserts that no distribution package, no DuckDB module and no removed package is loaded. The static architecture suite repeats the guard as an import rule. The two forms answer different questions: the subprocess catches a transitive import that a static scan might miss, and the static scan names the offending edge before the code runs.

The architecture group checks the package groups and entry points, the facade surfaces, the model/service import matrix, private-zone crossings and adapter files. It also enforces two direction rules that are easy to erode: a language does not import the interpreter, and only the interpreter and planners read the blueprint. A language that reads the blueprint has stopped being a language and started assembling the model.

The layout group requires a facade for every leaf, refuses an empty visibility zone, refuses a facade import of a missing public zone or an old shim, and lets private code read public model but not public service. The facade group permits only a docstring, imports, a literal `__all__`, a `TYPE_CHECKING` block and import/re-export machinery in an `__init__.py`. The literal export table must match the lazy groups, and every export must resolve. These tests make a package boundary legible at the file level.

The public docstring group is an interface test in a different medium. It requires an `Example` section on every public function and public class method, a developer docstring on every internal function, and facade functions that come from a public surface. Top-level entry points are callable wrappers from `kg_build_system.api`. The test checks that an example exists; it does not execute the example. A wrong example can pass the docstring test and mislead a reader, which is why the API and reference appendices are reviewed as prose as well as generated surfaces.

The reference build compiles and executes the public path. It writes `graph.jsonl`, `meta_graph.json`, `meta_graph.html`, the Neo4j import bundle, `workflow_plan.json` and `build_report.json`, and publishes no intermediate core records. It is the integration proof that the default composition is wired end to end. It is not a scale benchmark and not a proof that every module is correct.

The typecheck fixtures guard the authoring surface. The positive fixture exercises `Selection`, owner-derived nullability, `field` and `computed_field`, pinned projections, row effects, `lookup`, `zip` and row-source `unnest`. The negative fixture pins removed names and invalid effects with inline expected diagnostics. Pyright analyses `kg_build_system` and the two fixtures; it excludes `tests/`, `reference_project/` and `legacy/`.

Each group answers a different reviewer question. Import isolation and architecture ask whether one package may depend on another. Layout and facades ask whether a file sits in the right zone and whether a facade is only a facade. Public docstrings ask whether the authoring surface is documented. The reference build asks whether the default composition still runs. The typecheck fixtures ask whether the static surface still refuses the wrong authoring. A change that needs a new contract test is naming a new boundary; a change that only adds a unit test is not.

The suite also groups kernel flow tests, pipeline identity, planners, executors and distribution DTOs. Those groups guard the verbs and the values inside the boundary. The seven groups above guard the boundary itself.

## What a green build proves

A green run proves that the named refusals still exist, that the public path still composes, that the static types hold on the analysed subset, and that the documentation links resolve in the checked build. It is real evidence, and it is narrower than it looks.

It does not prove that the design is right. A module can honour every protocol and still compute the wrong relation. It does not prove that a kernel name is domain-neutral; the import tests inspect imports and loaded modules, not the meaning of every name. It does not prove that a public example runs, that a docstring is accurate or that a page states the current interface. It does not prove scale, performance, data quality or the correctness of a target's output. It does not prove that a custom distribution inherits these rules; another distribution supplies its own edges and its own tests.

The static type result has a scope. Pyright covers the package and two authoring fixtures, not all of `tests/`, not `reference_project/` and not `legacy/`. The reference project is exercised at runtime but not typechecked. The suite reports no line or branch coverage, so a high test count is not a coverage claim. Test count, subtest count and duration belong to the checkout; the pass/fail result and the measured error count are the stable claims.

The repository has no CI configuration. Every check is a command a person runs. That makes a green build a local measurement, not a release gate. It also means a documented limit can be removed in code while the docs still state it; that mismatch is a review defect, not something a green run detects.

## The interface is the review surface

An interface is the set of names another subpackage may use: types, protocols, functions, errors and their invariants. It is not `__all__`. It is the surface designed to be depended on, and it is reviewed through `docs/appendix/developer/` for internal readers and `docs/` for graph authors. The two surfaces may cover the same subject for different readers; they are not alternates.

A developer doc states names, signatures, invariants, allowed dependencies and the authoring surface. Implementation detail is out of scope. When the code and the developer doc disagree, the doc is the decision and one of them changes. A plan or a changelog is a change report, not a specification.

This is why a change that crosses a subpackage boundary is proposed as an interface change before it is implemented. The proposal fits on one screen: the responsibility, the interface delta, the dependency delta, the authoring delta, the deletions, the contract tests and the verification. If the interface delta does not explain the change, the change is not ready. The reviewer supervises interfaces; implementation is replaceable behind them. An implementation detail is sampled only when it suggests that the interface or the responsibility is wrong.

The discipline has a practical payoff. A new planner that claims an existing component is reviewed as a component change: does it agree on version and runtime fields, does it emit duplicate step ids, does it read the model it is given? A new executor is reviewed as an exact-kind change: which kind does it claim, which resources does it declare, what does it do with a disrupted context? A new language is reviewed as a seven-method surface plus a renderer and a round-trip test. None of those reviews requires reading the whole implementation, and none of them is satisfied by a test that only covers the happy path.

The consensus module is a good example of the limit. Its interface is small enough to review: one component, one exact kind, one input pattern, one publication, no resources. Its contract tests pin five claims. A reviewer can approve the interface and still reject the design if a vote belongs elsewhere. The architecture makes the interface visible; it does not make the design decision.

## Next

[20. Limits and evidence](/book/part-4/04-limits-and-evidence) — classify what the composition refuses, and read the evidence behind the claim.
