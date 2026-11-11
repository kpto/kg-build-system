---
title: "Part III — From declarations to records"
summary: "How one declaration becomes a checked plan, a run and a set of published records."
section: book
perspective: meta
part: III
order: 30
status: normative
verified: 2026-11-11
sources:
  - docs/index.md
  - docs/book/part-3/01-linking-and-blueprint.md
  - docs/appendix/reference/documents.md
---

## In this part

Part II ended with declarations an author can write: a node, a source relation, a binding that says how one becomes the other. Part III follows those declarations through the three stages that turn them into records. Linking keys the declarations and assembles the semantic blueprint. Planning asks a planner composition what work the blueprint requires. Execution opens the resources, runs the work and publishes the result.

The running example is the `site` declaration in the reference estate project. `SiteNode` is a graph component, `SitesTable` is a relation over the `estate` asset, and `site_binding` populates the node from the table. That one thread is small enough to follow through every artifact: the declaration, its symbol, the blueprint node, the plan's source-binding-aggregate-write chain and the published site records.

The chapters do not treat the artifacts as interchangeable. Each one states what its artifact owns, what it refuses and what it deliberately leaves to the next stage. Chapters 12 to 14 follow the pipeline; 15 and 16 turn from producing records to judging them and shipping the bundle. The point is not to memorise document shapes. It is to see where a build decides what exists, where it decides what will run, and where it discovers what the data actually is.

<figure class="kb-plate">
  <img src="/_assets/artifacts.svg" alt="Declarations become a symbol graph, then a blueprint, then a workflow plan, then a report.">
  <figcaption>Each artifact has one owner and one job. The symbol graph is linker working state; it is not delivered.</figcaption>
</figure>

## Chapters

| Chapter | Question |
| --- | --- |
| [12. Linking and the blueprint](/book/part-3/01-linking-and-blueprint) | Which declarations become symbols, and what semantic model is delivered? |
| [13. Planning the work](/book/part-3/02-planning) | How does one blueprint become components, steps and checked wiring? |
| [14. Executing and publishing](/book/part-3/03-execution-and-outputs) | How does a plan become records, resources and a report? |
| [15. Quality, failures and debugging](/book/part-3/04-quality-and-failure) | Which records should reach a target, and how does a failed run explain itself? |
| [16. Shipping a build](/book/part-3/05-shipping) | What must travel with a run so another person can reproduce and judge it? |

## Next

[12. Linking and the blueprint](/book/part-3/01-linking-and-blueprint) — start with the stage that decides what the build contains.
