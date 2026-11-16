---
title: "Part I — The build"
summary: "What a build is, and how to run one end to end."
section: book
perspective: meta
part: I
order: 10
status: normative
verified: 2026-11-15
sources:
  - docs/content/index.md
  - docs/content/book/part-3/index.md
  - reference_project/manifest.py
---

## In this part

Read [Preface: how to describe a graph](/book/intent) first. It states the
mentality this part assumes: intention before mechanism, and the claim that a
graph is an argument, not a pipeline.

A project states that argument in five places. `asset/` holds the logical
sources. `graph/` holds the record axis: the graph declaration, nodes, edges and
properties. `relation/source/` and `relation/derived/` hold the domain axis:
`SourceRelation` files and `DerivedRelation` packages with private stages.
`binding/` holds the fulfilment: the statement that a published relation supplies
a record at a stated grain, identity and coverage. `build.py` is the composition
root; it declares nothing.

A build is easy to mistake for a file-writing script. Source data goes in, records come out, and the script is the only explanation of either. Part I starts from the opposite end: a build is a chain of decisions about what records exist, what they mean and how they are produced. The files are the last link in that chain, not the whole of it.

The running example is a monitored estate: sites, installed equipment, survey visits, defects and logger readings. It is small enough to hold in one head and rich enough to show every handoff. An estate record has an identity, a type, properties, a relationship to another record and a source it came from. Those facts must survive the build; a JSON line that carries only the values has already lost most of them.

The three chapters move from the shape of a build, to a real run, to the boundary of a project. Chapter 1 names the three artifacts and the three moments that produce them. Chapter 2 runs the reference build and reads what it writes, including a first refusal. Chapter 3 explains where declarations live and what discovery can see.

<figure class="kb-plate">
  <img src="/_assets/system.svg" alt="A build moves from declarations through link, blueprint, plan and execute to published records, with an edit-time generation lane above.">
  <figcaption>One build, end to end. The book follows the lower lane from left to right; generation is the edit-time lane above it.</figcaption>
</figure>

## Chapters

| Chapter | Question |
| --- | --- |
| [1. The build](/book/part-1/01-the-build) | What does a build produce, and why are there three artifacts? |
| [2. A first build](/book/part-1/02-a-first-build) | What happens when the reference estate build runs? |
| [3. A project](/book/part-1/03-a-project) | Where do declarations live, and what can a build see? |

## Next

[1. The build](/book/part-1/01-the-build) — start with the shape of the whole.
