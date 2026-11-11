---
title: Kernel
summary: The kernel protocols and model that form the extension surface beneath the default graph distribution.
section: kernel
perspective: meta
order: 0
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/kernel/__init__.py
  - kg_build_system/kernel/service/public/pipeline.py
  - kg_build_system/kernel/model/public/workflow.py
  - docs/developer/system-design.md
  - tests/kernel/test_toolchain_flow.py
---

<div class="kb-section-head">
  <p class="kb-kicker">Layer 1 · Extension surface</p>
  <p class="kb-lede">The kernel is the extension surface. The default graph distribution is one composition of it.</p>
</div>

## In this section

The kernel is a domain-agnostic toolchain with three verbs: it links language declarations into an opaque model, compiles that model into a workflow plan, and executes the plan through exact instruction-kind executors. It imports no distribution, graph, SQL, DuckDB, Python or generation package.

The default graph distribution — the blueprint, the graph languages, the interpreter, the core planners, the source planner and the file, meta-graph and Neo4j modules — is one composition of the kernel protocols. It is replaceable. A new source, declaration syntax, derivation, storage engine or lifecycle resource is another composition, not a framework change.

> **"Not in the default distribution" is not "not in the framework."**
> The default distribution is one composition of the kernel protocols.
> A new source, syntax, derivation, engine or lifecycle resource is another
> composition, not a framework change.

### Terms

| Term | Meaning |
| --- | --- |
| Authoring surface | What a graph author writes: `Table`, `Field`, `Selection`, `Node`, `Edge`, bindings and semantics. It guards declarations. |
| Extension surface | The kernel protocols: `Language`, `Linker`, `Planner`, `StepExecutor`, `ResourceProvider` and `Runtime`. |
| Default distribution | One composition of the extension surface: the graph languages, blueprint, core planners, DuckDB source and targets. It is replaceable. |
| Model rule | A deliberate semantic constraint; changing it is a model change, not a new composition. Example: a graph property is scalar, so a nested object is reified. |

| Page | States | Read when |
| --- | --- | --- |
| [Kernel protocols](/kernel/protocols) | The six protocols, their supporting values and the cost of each extension. | Implementing or reviewing an extension. |
| [Kernel model](/kernel/model) | Canonical types, keys, declarations, symbols, workflow values and runtime results. | Reading an artifact value or a plan. |
| [Kernel boundaries](/kernel/boundaries) | The three verbs, the dependency spine, the zones and the tests that guard them. | Proposing a cross-package change. |

## Pages

Read [Kernel protocols](/kernel/protocols) first: it names the objects a composition supplies. [Kernel model](/kernel/model) states the values those objects exchange. [Kernel boundaries](/kernel/boundaries) states the dependency direction and the contract tests that enforce it.

Related surfaces:

- [Framework](/framework/index) — the default graph distribution as a whole.
- [Extend the toolchain](/operate/extend) — the task guide, with a worked module example.
- [Extension specification](/spec/extension) — the requirements for composition.
- [System design](/developer/system-design) — the full internal interface, including every signature.

## Next

[Kernel protocols](/kernel/protocols) — the six protocols a composition implements.
