---
title: Appendix E · Philosophy
summary: "The mentality: intention before mechanism, records and relations as two axes, and the binding as the fulfilment between them."
section: philosophy
order: 0
status: normative
verified: 2026-11-10
sources:
  - docs/content/appendix/philosophy/index.md
  - docs/content/book/part-2/01-meaning-and-purpose.md
  - kg_build_system/distribution/languages/graph/
---

<div class="kb-section-head">
  <p class="kb-kicker">Appendix E · Philosophy</p>
  <p class="kb-lede">Philosophy is not a stage. It is the mentality you bring to every stage: state the intention first, design the records and relations that serve it, and let the binding show how a relation fulfils a record. The framework can check the structure; only you can decide whether the structure means anything.</p>
</div>

```text
records                                 relations
what the graph asserts                  what the domain contains
  graph purpose                           relation purpose
    topology record                         projection / table
      property                                grain, fields
          ▲                                       │
          └──────────── binding ──────────────────┘
                      fulfilment
```

The two axes meet at the binding. The binding states whether the relation's grain, identity, coverage and meaning satisfy the record's purpose; it owns neither side's meaning.

## The stance

- **The graph is the product.** The plan, report and SQL are evidence that the graph was built; they are not the design.
- **Topology is the design.** A node or edge states what a record is, what it carries and which direction it points.
- **A relation is not a pipeline step.** A table or projection states what relation exists in the domain, its grain and its own purpose. A named join, filter or expansion is a derived row source, not a projection.
- **Semantics are a language, not a comment.** Purposes, claims and limitations are published data. A description or annotation is a different channel.
- **The binding is the fulfilment.** It is the only declaration that imports both the relation and the record. It states whether the relation satisfies the record's purpose, at which grain and coverage, and where it falls short.
- **Explainability is authored.** The framework preserves what you state and checks what can be checked. It cannot infer why a node exists or whether a claim is true.

## In this section

| Page | Principle |
| --- | --- |
| [Meaning before mechanism](/appendix/philosophy/meaning-first) | Design the record before choosing the table, join or projection that produces it. |
| [One purpose, read downward](/appendix/philosophy/semantic-hierarchy) | Records and relations are two axes; the binding is the fulfilment between them. |
| [Design in semantics](/appendix/philosophy/design-in-semantics) | Names and claims express the design; SQL verbs and staging names do not. |
| [Explainability is authored](/appendix/philosophy/explainability-is-authored) | A valid graph can be semantically empty; the framework cannot make it explainable. |
| [The binding is the fulfilment](/appendix/philosophy/binding-is-fulfilment) | It states whether a relation's grain, identity, coverage and meaning satisfy a record's purpose. |
| [Review top-down](/appendix/philosophy/review-top-down) | Read purpose, topology and semantics before bindings, data and plan. |
| [Anti-patterns](/appendix/philosophy/anti-patterns) | Ten smells that pass the compiler and fail the design. |

## Pages

Read [Preface: how to describe a graph](/book/intent) first. It states the mentality the rest of the section assumes. The pages are lenses, not additional API: each one names a decision you make in [Author](/book/part-2/index), [Pipeline](/book/part-3/index) or [Review](/appendix/review/index).

## Next

[Preface: how to describe a graph](/book/intent) — intention before mechanism, and the binding as fulfilment.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add semantics and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_semantics_language.py` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/content/appendix/developer/index.md` |
