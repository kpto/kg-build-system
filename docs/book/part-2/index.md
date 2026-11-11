---
title: "Part II — Authoring a graph"
summary: "How a source becomes a typed row, a value with a null policy, and a named grain a binding can read."
section: book
perspective: meta
part: II
order: 20
status: normative
verified: 2026-11-11
sources:
  - docs/index.md
  - docs/book/part-2/01-source-and-rows.md
---

## In this part

Part I established the shape of a build: declarations become a blueprint, the
blueprint becomes a workflow plan, and the plan produces records. Part II is the
authoring surface those stages consume. It starts at the source and moves upward,
one decision at a time: where the rows come from, what one value means, what one
row means, what the rows become in the graph, what the graph says about them, and
how a declaration package is generated rather than written by hand.

The running example is a monitored estate. One export carries sites, equipment,
surveys and logger readings; a handful of tables read it. The example stays small
on purpose. The questions it raises are the questions every graph raises: whether a
missing value is an error, whether two relations accidentally multiply rows, and
whether a derived grain deserves a name.

Part II does not try to be a reference. Each chapter makes one argument and repeats
an earlier idea when the argument needs it. Exact signatures, refusal messages
and the full type table belong to the appendices; a chapter states the model and
the decision, and shows the public names you write.

<figure class="kb-plate">
  <img src="/_assets/authoring.svg" alt="Asset feeds Table, Field and Selection; row sources feed projections; topology and bindings meet at the graph; semantics attaches to every declaration.">
  <figcaption>The authoring chain. An arrow means “is read by” or “is named by”, not an import.</figcaption>
</figure>

## Chapters

| Chapter | Question |
| --- | --- |
| [4. Source and rows](/book/part-2/01-source-and-rows) | Which source do the rows represent, and what shape does one row have? |
| [5. Values and nullability](/book/part-2/02-values-and-nullability) | What does a field read return, and who decides that a value may be absent? |
| [6. Grain and projections](/book/part-2/03-grain-and-projections) | What is one row after a filter, a join, a group or an expansion? |
| [7. Topology and bindings](/book/part-2/04-topology-and-bindings) | How does one row become a node or edge record, and where does the mapping live? |
| [8. Meaning and purpose](/book/part-2/05-meaning-and-purpose) | What does the graph claim, and under which purpose is the claim read? |
| [9. Generating declarations](/book/part-2/06-generation) | How is a declaration package generated without taking over the model? |

The chapters divide into two movements. Chapters 4 to 6 settle the row: its source,
its values, and its grain. Chapters 7 to 9 settle the graph that the rows become:
the records and their bindings, the meaning attached to the design, and the
generated package that reproduces the declarations. Every later chapter assumes
the row decisions, because a binding inherits a grain rather than inventing one.

## How to read

The six chapters are read in order. Each chapter takes one question to a decision and
returns to the estate example where the decision needs a concrete shape. A later
page assumes the earlier ones, but it does not send you elsewhere to learn them: a
rule that matters is restated where it is used.

Every code fragment is valid against the current public API. Fragments are
deliberately local; they show the declaration under discussion rather than a
complete package.

## Next

[4. Source and rows](/book/part-2/01-source-and-rows) — begin where the rows begin.
