---
title: Pipeline
summary: Link declarations into symbols, assemble the semantic blueprint, compile a workflow plan and execute it.
section: pipeline
order: 0
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/kernel/service/_private/pipeline.py
  - kg_build_system/distribution/interpreter/
  - docs/developer/system-design.md
---

<div class="kb-section-head">
  <p class="kb-kicker">03 · Pipeline</p>
  <p class="kb-lede">Three verbs, one direction. <strong>Link</strong> turns declarations into a model. <strong>Compile</strong> turns the model into a plan without reading data. <strong>Execute</strong> runs the plan through exact instruction kinds.</p>
</div>

<figure class="kb-plate">
  <img src="/_assets/artifacts.svg" alt="Declarations become a symbol graph, then a blueprint, then a workflow plan, then a report.">
  <figcaption>Each artifact has one owner and one job. The symbol graph is linker working state; it is not delivered.</figcaption>
</figure>

## In this section

| Page | Stage | Question |
| --- | --- | --- |
| [Link declarations](/pipeline/link) | build | Which declarations are reached, keyed, ordered and transcribed? |
| [Assemble the blueprint](/pipeline/blueprint) | build | What is the semantic model, and what does it guarantee? |
| [Compile a plan](/pipeline/plan) | compile | How do planners become components, steps and connections? |
| [Execute a plan](/pipeline/execute) | execute | How do resources, events and executors produce a report? |

## Pages

Each page states one stage, its inputs and outputs, the refusals it owns and the limits it leaves to the next stage. Read [Link declarations](/pipeline/link) first; the blueprint is what linking produces.

## Next

[Link declarations](/pipeline/link) — discovery, keys, closure and symbol order.
