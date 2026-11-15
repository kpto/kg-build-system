---
title: Appendix E · Philosophy
summary: "The mentality: intention before mechanism, records and relations as two axes, and the binding as the fulfilment between them."
section: philosophy
order: 0
status: normative
verified: 2026-11-15
sources:
  - docs/content/appendix/philosophy/index.md
  - docs/content/book/intent.md
  - docs/content/appendix/developer/project-structure.md
  - AGENTS.md
  - reference_project/build.py
---

<div class="kb-section-head">
  <p class="kb-kicker">Appendix E · Philosophy</p>
  <p class="kb-lede">Philosophy is not a stage. It is the mentality you bring to every stage: state the intention first, design the records and relations that serve it, and let the binding show how a relation fulfils a record. The framework can check the structure; only you can decide whether the structure means anything.</p>
</div>

```text
records                                 relations
graph/                                  relation/
what the graph asserts                  what the domain contains
  graph purpose                           relation contract
    node, edge, property                    definition: grain, identity
      Meaning                                 Meaning: domain purpose
          ▲                                       │
          └──────────── binding ──────────────────┘
                      fulfilment
```

The two axes meet at the binding. The binding states whether the relation's grain, identity, coverage and meaning satisfy the record's purpose; it owns neither side's meaning.

## The vocabulary

| Term | What it names |
| --- | --- |
| `Meaning` | A purpose (or claims only) and the limitations that bound that purpose, attached inline to a declaration. |
| `graph/` | The record axis: the graph declaration, its nodes, edges and properties. |
| `relation/source/` | A `SourceRelation`: a domain relation the source supplies. |
| `relation/derived/` | A `DerivedRelation`: a named domain relation computed from row sources. |
| `Contract` | A relation's `Definition` (grain, identity) plus its `Meaning`. A derived relation always states one; a source relation states one when a binding reads it. |
| `FieldDefinition` | The value, unit and null meaning attached by `field(...)` or `computed_field(...)`. |
| `Stage` | A private sub-relation inside a derived-relation package; it has a definition and no contract meaning. |
| binding | The fulfilment between one relation contract and one record. |

The word *projection* survives only for the SQL and plan operator. The declaration is a `DerivedRelation`.

## The stance

- **The graph is the product.** The plan, report and SQL are evidence that the graph was built; they are not the design.
- **Topology is the design.** A node or edge states what a record is, what it carries and which direction it points.
- **A relation is a contract, not a pipeline step.** A `SourceRelation` states which domain relation a source supplies; a `DerivedRelation` states a published grain and its own domain meaning. A relation read by a binding should state a `Contract`; a private `Stage` composes inside it and is never a consumer contract.
- **A published relation is record-agnostic.** It does not name a record's properties, key or endpoints. If it does, the binding is a copy and the design has collapsed onto one axis.
- **Meaning is a language, not a comment.** Purposes, claims and limitations are published data. A description or annotation is a different channel.
- **The binding is the fulfilment.** It is the only declaration that imports both the relation and the record. It states whether the relation satisfies the record's purpose, at which grain and coverage, and where it falls short.
- **Explainability is authored.** The framework preserves what you state and checks what can be checked. It cannot infer why a node exists or whether a claim is true.

## In this section

| Page | Principle |
| --- | --- |
| [Meaning before mechanism](/appendix/philosophy/meaning-first) | Design the record before choosing the relation that produces it. |
| [Two axes, one fulfilment](/appendix/philosophy/semantic-hierarchy) | Records and relations carry their own meaning; the binding is the fulfilment between them. |
| [Design in meaning](/appendix/philosophy/design-in-meaning) | Names and claims express the design; SQL verbs and stage names do not. |
| [Explainability is authored](/appendix/philosophy/explainability-is-authored) | A valid graph can still be empty of meaning; the framework cannot make it explainable. |
| [The binding is the fulfilment](/appendix/philosophy/binding-is-fulfilment) | It states whether a relation's grain, identity, coverage and meaning satisfy a record's purpose. |
| [Review top-down](/appendix/philosophy/review-top-down) | Read purpose, topology and relation contracts before bindings, data and plan. |
| [Anti-patterns](/appendix/philosophy/anti-patterns) | Design smells that pass the compiler and fail the model. |

## Pages

Read [Preface: how to describe a graph](/book/intent) first. It states the mentality the rest of the section assumes. The pages are lenses, not additional API: each one names a decision you make in [Author](/book/part-2/index), [Pipeline](/book/part-3/index) or [Review](/appendix/review/index).

The filesystem form of the same decisions is [Project structure](/appendix/developer/project-structure): one file per public declaration, private stages, and one dependency direction.

## Next

[Preface: how to describe a graph](/book/intent) — intention before mechanism, and the binding as fulfilment.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add meaning and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_meaning_language.py` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/content/appendix/developer/index.md` |
