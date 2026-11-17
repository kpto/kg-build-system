---
title: Appendix G · Framework reference
summary: The graph distribution built on the kernel, its book chapters, and the default composition it supplies.
section: framework
perspective: meta
order: 0
status: normative
verified: 2026-11-10
sources:
  - docs/content/appendix/developer/system-design.md
  - kg_build_system/api.py
  - kg_build_system/distribution/implementations.py
---

<div class="kb-section-head">
  <p class="kb-kicker">Appendix G · Framework reference</p>
  <p class="kb-lede">The graph domain built on the kernel: authoring, blueprint, languages, planners, execution, targets, generation and CLI.</p>
</div>

## In this section

The framework is the graph distribution that runs on the domain-agnostic [kernel](/appendix/kernel/index). It contains the authoring surface, the blueprint, the graph languages, the core planners, DuckDB, the file, meta-graph and Neo4j targets, generation and the CLI.

The default distribution is one composition of the kernel protocols, not the framework's boundary. A new source, language, module or engine composes a different `Toolchain`; a new provider is added to the runtime. The book describes that composition and the object that replaces each part.

## Pages

| Page | Covers |
| --- | --- |
| [Part I — The build](/book/part-1/index) | Install, run the estate build, place declarations in a project. |
| [Part II — Authoring](/book/part-2/index) | Asset, relations, values, grain, records, bindings and meaning. |
| [Part III — Records](/book/part-3/index) | Link declarations, assemble the blueprint, plan the work, execute and ship. |
| [Part IV — Extending](/book/part-4/index) | Kernel, default distribution, architecture, tests, limits and evidence. |
| [Review](/appendix/review/index) | Architecture, invariants, limits, decisions, verification and drift. |
| [Developer](/appendix/developer/index) | Kernel interfaces, boundaries, DTOs and contract tests. |
| [Reference](/appendix/reference/index) | API surface, CLI, documents, failures and the glossary. |

### What is one composition

| Role | Default composition | Extension point |
| --- | --- | --- |
| Source | `DuckDbSourcePlanner` | Another source planner |
| Core planners | `RowSourcePlanner`, `ProjectionPlanner`, `BindingPlanner`, `RecordsPlanner` | Another planner group |
| Targets | `FilePlanner`, `MetaGraphPlanner`, `Neo4jPlanner` | Another output module |
| Emitter | `DuckDbSqlEmitter` | Another `SqlEmitter` |
| Provider | `DuckDbResourceProvider` | Another `ResourceProvider` |

Every row is a replaceable default. [Limits](/appendix/review/limits) classifies the composition's boundaries and names the object that replaces each one.

Project-local extension is the expected first move: a value operation in `expression/`, a relation operation, source adapter or planner/executor module in `modules/`, composed in `manifest.py`. The [Extension reference](/appendix/reference/extension) states the surfaces and the kernel protocols that remain for a different composition.

## Next

[Start](/book/part-1/index) — install the package and run the estate build.
