---
title: Contents
summary: The four parts of the book, the chapter order, and the appendices for exact lookup.
section: book
perspective: meta
order: 0
status: normative
verified: 2026-11-11
sources:
  - docs/index.md
  - docs/book/part-1/index.md
  - docs/book/part-4/index.md
---

## In this book

The book follows one monitored-estate graph from an empty environment to a
reviewed, published result. It is written to be read in order. The same example
returns in every part, and an idea may be explained more than once when a later
chapter needs it.

The four parts answer four questions:

1. What is a build, and how do you run one?
2. How do you author the declarations a build consumes?
3. How do declarations become a checked plan and published records?
4. How do you extend the machine, and how do you review a change to it?

Exact signatures, normative requirements and error catalogues are appendices.
They are not the book's argument; they are the place to check a name or a
requirement after the argument is clear.

## Parts

### Part I — The build

| Chapter | Question |
| --- | --- |
| [1. The build](/book/part-1/01-the-build) | What does a build produce, and why are there three artifacts? |
| [2. A first build](/book/part-1/02-a-first-build) | What happens when the reference estate build runs? |
| [3. A project](/book/part-1/03-a-project) | Where do declarations live, and what can a build see? |

### Part II — Authoring a graph

| Chapter | Question |
| --- | --- |
| [4. Meaning and purpose](/book/part-2/01-meaning-and-purpose) | What does the graph claim, and under which purpose is the claim read? |
| [5. Topology](/book/part-2/02-topology) | Which record kinds, properties, directions and categories does the design assert? |
| [6. Source and rows](/book/part-2/03-source-and-rows) | Which source do the rows represent, and what shape does one row have? |
| [7. Values and nullability](/book/part-2/04-values-and-nullability) | What does a field read return, and who decides that a value may be absent? |
| [8. Grain and projections](/book/part-2/05-grain-and-projections) | What is one row after a filter, a join, a group or an expansion? |
| [9. Binding as implementation detail](/book/part-2/06-binding) | How does a row source populate the record the design already declared? |
| [10. Generating declarations](/book/part-2/07-generation) | How is a declaration package generated without taking over the model? |

### Part III — From declarations to records

| Chapter | Question |
| --- | --- |
| [11. Linking and the blueprint](/book/part-3/01-linking-and-blueprint) | Which declarations become symbols, and what semantic model is delivered? |
| [12. Planning the work](/book/part-3/02-planning) | How does one blueprint become components, steps and checked wiring? |
| [13. Executing and publishing](/book/part-3/03-execution-and-outputs) | How does a plan become records, resources and a report? |
| [14. Quality, failures and debugging](/book/part-3/04-quality-and-failure) | Which records should reach a target, and how does a failed run explain itself? |
| [15. Shipping a build](/book/part-3/05-shipping) | What must travel with a run so another person can reproduce and judge it? |

### Part IV — Extending and reviewing

| Chapter | Question |
| --- | --- |
| [16. The kernel and the extension surface](/book/part-4/01-the-kernel-and-extension) | What must a composition provide before it can add a capability? |
| [17. The default distribution](/book/part-4/02-the-default-distribution) | Which parts of the shipped graph system are choices, and which are model rules? |
| [18. Architecture and tests](/book/part-4/03-architecture-and-tests) | What makes a boundary reviewable before the implementation is read? |
| [19. Limits and evidence](/book/part-4/04-limits-and-evidence) | When is a missing capability a limit, and what evidence supports the claim? |

## How to read

Read the book in order the first time. The estate example accumulates decisions:
chapter 6 assumes the design from chapter 5, chapter 9 assumes the grain from
chapter 8, and chapter 11 assumes the binding from chapter 9.

For a task, the parts also work as routes:

| If you need to | Start at |
| --- | --- |
| Install and run the reference build | [2. A first build](/book/part-1/02-a-first-build) |
| Add a source, table or value | [6. Source and rows](/book/part-2/03-source-and-rows) |
| Fix a duplicated or multiplied row | [8. Grain and projections](/book/part-2/05-grain-and-projections) |
| Add a node or edge | [5. Topology](/book/part-2/02-topology) |
| Populate a record from rows | [9. Binding as implementation detail](/book/part-2/06-binding) |
| Add a capability | [16. The kernel and the extension surface](/book/part-4/01-the-kernel-and-extension) |
| Judge a change | [18. Architecture and tests](/book/part-4/03-architecture-and-tests) |

The appendices hold the exact material: [specifications](/appendix/spec/index),
[reference](/appendix/reference/index), [developer interfaces](/appendix/developer/index),
[review evidence](/appendix/review/index), [philosophy](/appendix/philosophy/index),
[kernel reference](/appendix/kernel/index), [framework reference](/appendix/framework/index)
and the [index of subjects](/appendix/subjects/index).

## Next

[Part I — The build](/book/part-1/index) — start with what a build produces.
