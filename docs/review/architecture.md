---
title: Architecture
summary: A domain-agnostic kernel and a knowledge-graph distribution meet at one dependency spine.
section: review
order: 10
status: normative
verified: 2026-11-10
sources:
  - AGENTS.md
  - ARCHITECTURE.md
  - kg_build_system/kernel/
  - kg_build_system/distribution/
  - tests/test_architecture.py
subject: architecture
perspective: review
---

<!-- BEGIN GENERATED:views -->
<div class="kb-views"><span class="kb-views-subject">Kernel, distribution and contracts</span><a href="/subjects/architecture">Overview</a><a href="/review/architecture">Guide</a><a href="/spec/architecture">Spec</a><a href="/reference/api">API</a><a href="/philosophy/review-top-down">Philosophy</a><a href="/review/limits" class="active">Review</a></div>
<!-- END GENERATED:views -->

> [!lede]
> The kernel is a toolchain; the distribution is a knowledge-graph system built on it. The boundary is the review surface: graph vocabulary in the kernel is a model change, not a naming preference.

## What it is

The kernel owns reusable mechanics; the distribution owns what a graph author names and a graph build runs.

| Kernel group | Names |
| --- | --- |
| Frontend | `Language`, `Declaration`, `Symbol`, `SymbolRef`, `Key` |
| Planning | `Linker`, `Planner`, `PlanContext`, `WorkflowPlan`, `Step`, `Instruction`, `InstructionKind`, `StepId`, `OpeningId`, `ArtifactType`, `ArtifactPattern` |
| Execution | `Runtime`, `Resource`, `ResourceProvider`, `ResourceView`, `ResourceRegistry`, `PipelineEvent`, `StepOutcome`, `WorkflowReport` |
| Composition | `Toolchain` |

| Distribution piece | Supplies |
| --- | --- |
| Languages | `annotations`, `expressions`, `asset`, `data`, `topology`, `binding`, `graph`, `semantics` |
| Interpreter | blueprint assembly and typed refs |
| Modules | `core`, `deduplication`, `merging`, `conflict_validation`, `file`, `meta_graph`, `neo4j`, `duckdb`, `python`, `runtime` |
| `distribution/service` | neutral relation plan, `SqlEmitter`, execution, rendering |
| `implementations.py` | default wiring |

<figure class="kb-plate">
  <img src="/_assets/architecture.svg" alt="The kernel sits inside its boundary; languages, the interpreter, modules and the distribution service point inward, with generation, api and cli at the outer edges.">
  <figcaption>The kernel boundary and the dependency spine. An arrow points at what a layer may import. The exact interfaces are in [System design](/developer/system-design).</figcaption>
</figure>

## Rules

- **Vocabulary.** The kernel uses toolchain words; graph, blueprint, node, edge, binding, projection and asset belong to the distribution. A kernel model that needs a graph word has crossed the boundary.
- **Import direction.** Languages import the kernel; the interpreter imports languages and the kernel; modules import the interpreter, languages, `distribution.model`, `distribution.service` and the kernel; generation imports the kernel and the asset language; `api` imports the distribution and the kernel; the CLI imports generation and `api`. A new edge is a model change.
- **Kernel isolation.** The kernel imports no graph, data, topology, binding, SQL, DuckDB or generation package. `tests/kernel/test_import_isolation.py` and `tests/test_architecture.py` refuse the edge.
- **Zones.** Every leaf uses `model/{public,internal,_private}` and `service/{public,internal,_private}`. Empty zones are deleted; `__init__.py` is a facade, never business logic.
- **Visibility.** Another package imports `public` or `internal`, never `_private`. `service.internal` delegates to `_private` with a function-local import; an eager private import creates the forbidden cycle.
- **Engine neutrality.** Core planners use the neutral relation plan and injected `SqlEmitter` from `distribution/service/internal`; they never import `distribution/modules/duckdb`. A second engine is another module, not an edit to core.
- **One flow.** Languages produce declarations, the linker symbols and a model, planners a workflow plan, the runtime execution. [Compile a plan](/pipeline/plan) owns the middle of that flow.

## Evidence

`tests/kernel/test_import_isolation.py` and `tests/test_architecture.py` are the authority; the map is an inventory.

<!-- BEGIN GENERATED:code-map -->
29 leaves; empty zones are deleted. Strongest import edges:

| Import edge | Files |
| --- | ---: |
| `distribution/languages/expressions` → `kernel` | 49 |
| `distribution/modules/duckdb` → `distribution/languages/expressions` | 34 |
| `distribution/languages/data` → `distribution/languages/expressions` | 25 |
| `distribution/languages/data` → `kernel` | 25 |
| `distribution/modules/duckdb` → `distribution/languages/data` | 17 |
| `distribution/modules/duckdb` → `kernel` | 16 |
| `distribution/languages/data` → `distribution/languages/annotations` | 15 |
| `distribution/languages/topology` → `distribution/languages/annotations` | 15 |
| `distribution/languages/data` → `distribution/languages/semantics` | 14 |
| `distribution/languages/topology` → `distribution/languages/semantics` | 14 |
| `distribution/modules/core` → `distribution/service` | 14 |
| `distribution/modules/core` → `kernel` | 13 |
| `distribution/languages/binding` → `distribution/languages/data` | 12 |
| `distribution/languages/binding` → `distribution/languages/expressions` | 12 |

Kernel boundary violations: none.
<!-- END GENERATED:code-map -->

## Limits

- The kernel is not a plugin system. There is no extension registry; a toolchain is composed explicitly. [Extend the toolchain](/operate/extend) owns that contract.
- The distribution is not optional for a graph build. A custom language can run on the kernel alone; nodes, edges, bindings and the blueprint cannot.
- Zones are a source layout, not a runtime sandbox; they make an illegal import visible, not impossible.
- The map aggregates by leaf and reports its strongest edges, not every file.
- The spine is a tree for reading, not a complete graph; cross-edges are enforced one by one. [Limits](/review/limits) owns what the boundary excludes.

## Next

[Contracts](/review/contracts) — the invariants this boundary protects.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-001 | Separate a domain-agnostic toolchain kernel from the KG distribution. | 2026-11-03 | accepted | `tests/kernel/test_import_isolation.py` |
| D-002 | Use toolchain vocabulary in the kernel and domain vocabulary only in the distribution. | 2026-11-03 | accepted | `tests/test_naming.py` |
| D-010 | Give every framework leaf the same model/service zone layout. | 2026-11-03 | accepted | `tests/test_layout.py` |
| D-011 | Keep private helpers out of interface zones and break service/private cycles with function-local imports. | 2026-11-03 | accepted | `tests/test_layout.py` |
| D-030 | Consume an engine-neutral relation plan and injected `SqlEmitter`; core imports no DuckDB module. | 2026-11-05 | accepted | `tests/distribution/planners/test_core_custom_emitter.py` |
| D-031 | Build the blueprint from symbols and typed refs; group feature code into modules and type execution resources. | 2026-11-04 | accepted | `tests/distribution/test_typed_refs.py` |
| D-039 | Guard the architecture with a contract test and a reviewer briefing. | 2026-11-02 | accepted | `tests/test_architecture.py` |
