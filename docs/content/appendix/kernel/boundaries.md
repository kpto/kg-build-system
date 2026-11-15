---
title: Kernel boundaries
summary: The three verbs, dependency spine, zone rules and contract tests that keep the kernel domain-agnostic.
section: kernel
perspective: developer
order: 30
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/kernel/__init__.py
  - kg_build_system/api.py
  - tests/kernel/test_import_isolation.py
  - tests/test_architecture.py
  - docs/content/appendix/developer/system-design.md
---

## Interface

The kernel is one package group with one direction of dependency. `kg_build_system.api` is the composition root: it builds the distribution's toolchain and calls the kernel verbs. The kernel supplies the verbs and the protocols; the distribution supplies the model and the implementations.

### Three verbs

| Verb | Input | Output | Contract |
| --- | --- | --- | --- |
| `build` | a `Namespace` through a `Linker` | one opaque model | Discovers declarations, computes keys, selects roots, resolves the closure, transcribes reachable declarations and assembles the model. It does not plan or execute. |
| `compile` | the linked model | `WorkflowPlan` | Calls planners in order, groups by `component_id`, publishes one `Component` per group, assigns step ids and assembles wiring. It does not build or read data. |
| `execute` | the plan and an output directory | `WorkflowReport` | Builds the exact-kind map, refuses a missing or duplicate kind before any step, opens resources and dispatches. |

`Toolchain` exposes the three verbs. `compile` does not call `build`; the composition root may create a blueprint first, but the kernel method receives the linked model. A serialised plan is self-contained because `api.compile` records the source blueprint document under `plan.provenance["blueprint"]`.

### Dependency spine

| Package | May import |
| --- | --- |
| `kernel` | No framework package. |
| `languages/annotations`, `languages/expressions`, `languages/meaning` | `kernel`. |
| `languages/graph` | `kernel`, meaning. |
| `languages/asset` | `kernel`, annotations, meaning. |
| `languages/data` | `kernel`, annotations, expressions, asset, meaning. |
| `languages/topology` | `kernel`, annotations, expressions, meaning. |
| `languages/binding` | `kernel`, annotations, data, topology, meaning. |
| `interpreter` | `kernel`, every graph language, meaning. |
| `modules/<name>` | `kernel`, `interpreter` where it reads a blueprint, languages, `distribution.model`, `distribution.service`. |
| `implementations.py` | `kernel`, interpreter, languages. |
| `generation/code_generation` | `kernel`, `languages/asset`. |
| `api.py` | `kernel`, distribution. |
| `cli` | generation, `api.py`. |

The spine is a tree for reading, not a complete graph. The dependency tests enforce the exact edge set; a new edge is a model decision proposed with its reason.

### Zones

| Zone | Holds | May be imported by |
| --- | --- | --- |
| `pkg` | facade over `model.public` and `service.public` | any package |
| `pkg.model.public` | authoring models, returned values, public DTOs | any package |
| `pkg.model.internal` | cross-package data under `dto/` and `model/` | any package |
| `pkg.model._private` | private plans, render models, engine types | its own package only |
| `pkg.service.public` | author-facing methods and thin wrappers | any package |
| `pkg.service.internal` | service interfaces, codec and assembly wrappers, adapters | any package |
| `pkg.service._private` | codecs, transcription, rendering, validation, assembly, planning, engines, runtime | its own package only |

A leaf uses only the zones it needs; an empty zone is deleted. Another package imports `public` or `internal`, never `_private`.

## Rules

- The dependency direction is one graph. A cycle or a new edge is a model change, proposed before implementation.
- The kernel imports no distribution, graph, data, topology, binding, SQL, DuckDB, Python or generation package.
- `model.public` and `model.internal` import no service and no `_private`. `model._private` may read model data but not service.
- `service.public` imports `model.public` and `service.internal`, never `_private`.
- `service.internal` delegates to `service._private` with a function-local import; it does not eagerly import a service that imports `_private`.
- An implementation of another package's protocol is a separate file under `service/internal/adapters/<protocol>.py`. It names the protocol and delegates to `_private`; it is not buried in a model or a factory.
- `api.py` is the composition root. It owns `default_toolchain`, `DEFAULT_TOOLCHAIN`, `create_blueprint`, `compile` and `execute`; the distribution supplies implementations only.
- The distribution is not optional for a graph build. A custom language can run on the kernel alone; nodes, edges, bindings and the blueprint cannot.
- The kernel changes only when the protocol set cannot carry a concept. A concept a protocol can carry belongs to a composition.

### What the framework does not decide

These are composition choices, not kernel rules:

| Concern | Carried by |
| --- | --- |
| Acquisition | A source planner and executor, a provider, or a frontend script. |
| Identifier translation | A module, or graph facts such as cross-references. |
| Orthology | A module, or graph facts such as an ortholog edge. |
| Storage engine | A neutral emitter and an executor, plus a resource provider. |
| Scheduling policy | A `Runtime` or `Linker` implementation. |
| Licence enforcement | `Resource` facts plus a filter module. |
| Incremental strategy | A planner and runtime composition. |

### Contract tests

| Test | Guards |
| --- | --- |
| `tests/kernel/test_import_isolation.py` | Importing the kernel loads no distribution package, SQL module or DuckDB. |
| `tests/test_architecture.py` | Leaf inventory, public and internal visibility, function-local private imports and the dependency spine. |
| `tests/test_layout.py` | Every leaf has a facade, zones are not empty markers and private code follows the model and service direction. |
| `tests/kernel/test_toolchain_flow.py` | A custom language, linker, planner, executor and provider run through build, compile and execute; duplicate steps and missing executors are refused. |

The tests make an illegal edge visible. They do not make it impossible in a running process.

## Limits

- Zones are a source layout, not a runtime sandbox.
- The spine is a tree for reading, not a complete graph; cross-edges are enforced one by one.
- The import tests inspect imports and loaded modules. They do not prove that every kernel name is domain-neutral.
- A custom distribution inherits this layout and spine only by adopting the same leaves and contract tests.
- The kernel boundary does not standardise build caching, remote execution or deployment. Those belong to a runtime or composition.
- A contract test states an invariant of this checkout; another distribution supplies its own tests for its own edges.

## Next

[System design](/appendix/developer/system-design) — the full internal interface, including the package tree and every protocol signature.
