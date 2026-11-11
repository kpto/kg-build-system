---
title: Appendix E · Philosophy
summary: "The mentality: state the design in meaning first, then implement it in data and bindings."
section: philosophy
order: 0
status: normative
verified: 2026-11-10
sources:
  - docs/appendix/philosophy/index.md
  - docs/book/part-2/05-meaning-and-purpose.md
  - kg_build_system/distribution/languages/graph/
---

<div class="kb-section-head">
  <p class="kb-kicker">Appendix E · Philosophy</p>
  <p class="kb-lede">Philosophy is not a stage. It is the reading order you bring to every stage: purpose before topology, topology before data, data before plan. The framework can check the structure; only you can decide whether the structure means anything.</p>
</div>

<figure class="kb-plate">
  <img src="/_assets/semantics.svg" alt="A graph purpose sits above topology, data and binding; each layer is read under the purpose, and the framework stores attachments rather than copying meaning down.">
  <figcaption>Meaning is a hierarchy of reading, not a copied field. The purpose is the root; the lower layers are implementation readings of it.</figcaption>
</figure>

## The stance

- **The graph is the product.** The plan, report and SQL are evidence that the graph was built; they are not the design.
- **Topology is the design.** A node or edge states what a record is, what it carries and which direction it points. Tables, joins and projections are how the rows arrive.
- **Semantics are a language, not a comment.** Claims, frames, limitations and the one graph purpose are published data. A description or annotation is a different channel.
- **The binding is the seam.** It is the only declaration that imports both the data shape and the graph meaning. Keep it thin; put the grain decision above it.
- **Explainability is authored.** The framework preserves what you state and checks what can be checked. It cannot infer why a node exists or whether a claim is true.

## In this section

| Page | Principle |
| --- | --- |
| [Meaning before mechanism](/appendix/philosophy/meaning-first) | Design the record before choosing the table, join or projection that produces it. |
| [One purpose, read downward](/appendix/philosophy/semantic-hierarchy) | Purpose → topology → data/binding is a hierarchy of reading, not automatic inheritance. |
| [Design in semantics](/appendix/philosophy/design-in-semantics) | Names and claims express the design; SQL verbs and staging names do not. |
| [Explainability is authored](/appendix/philosophy/explainability-is-authored) | A valid graph can be semantically empty; the framework cannot make it explainable. |
| [The binding is the seam](/appendix/philosophy/binding-is-the-seam) | Keep the design above the binding and the plumbing below it. |
| [Review top-down](/appendix/philosophy/review-top-down) | Read purpose, topology and semantics before bindings, data and plan. |
| [Anti-patterns](/appendix/philosophy/anti-patterns) | Ten smells that pass the compiler and fail the design. |

## Pages

Read [Meaning before mechanism](/appendix/philosophy/meaning-first) first. It states the order the rest of the section assumes. The pages are lenses, not additional API: each one names a decision you make in [Author](/book/part-2/index), [Pipeline](/book/part-3/index) or [Review](/appendix/review/index).

## Next

[Meaning before mechanism](/appendix/philosophy/meaning-first) — declare what a record is before deciding how it is produced.

## Decisions

| ID | Decision | Date | Status | Evidence |
| --- | --- | --- | --- | --- |
| D-023 | Add semantics and graph as value languages with one graph purpose per project. | 2026-11-06 | accepted | `tests/distribution/test_semantics_language.py` |
| D-038 | Keep author docs deep and separate from internal specs, with concept/reference paths. | 2026-11-05 | accepted | `STYLE.md`; `docs/appendix/developer/index.md` |
