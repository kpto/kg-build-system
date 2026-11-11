---
title: "Part II — Authoring a graph"
summary: "Meaning and topology come first; source rows, values, grain and binding implement that design."
section: book
perspective: meta
part: II
order: 20
status: normative
verified: 2026-11-11
sources:
  - docs/index.md
  - docs/book/part-2/01-meaning-and-purpose.md
  - docs/book/part-2/02-topology.md
---

## In this part

Part I established the shape of a build: declarations become a blueprint, the
blueprint becomes a workflow plan, and the plan produces records. Part II is the
authoring surface those stages consume.

It starts at the opposite end from most data guides. **Meaning comes first**, then
**topology**: what the graph claims, under which purpose, and which record kinds and
properties the design asserts. Source rows, values, grain and bindings implement
that design afterwards. A binding is not the place where the model is invented; it
is the place where a declared record is populated from a row.

That order is a reading order, not a rule. A real project evolves both ends
together: a source reveals a property, a property suggests a claim, and a claim
changes which records are worth declaring. The chapters separate the decisions so
each one can be reviewed; they do not pretend that authoring is one-way.

The running example is a monitored estate. One export carries sites, equipment,
surveys and logger readings; a handful of tables read it. The graph says that a
site is an asset, a unit is installed at a site, and a survey reports a condition.
The rows then supply the names, identifiers and measurements those records carry.

Part II does not try to be a reference. Each chapter makes one argument and repeats
an earlier idea when the argument needs it. Exact signatures, refusal messages
and the full type table belong to the appendices; a chapter states the model and
the decision, and shows the public names you write.

<figure class="kb-plate">
  <img src="/_assets/authoring.svg" alt="Asset feeds Table, Field and Selection; row sources feed projections; topology and bindings meet at the graph; semantics attaches to every declaration.">
  <figcaption>The authoring dependencies. The book reads meaning and topology first; the arrows show what supplies what, not the order to learn it.</figcaption>
</figure>

## Chapters

| Chapter | Question |
| --- | --- |
| [4. Meaning and purpose](/book/part-2/01-meaning-and-purpose) | What does the graph claim, and under which purpose is the claim read? |
| [5. Topology](/book/part-2/02-topology) | Which record kinds, properties, directions and categories does the design assert? |
| [6. Source and rows](/book/part-2/03-source-and-rows) | Which source do the rows represent, and what shape does one row have? |
| [7. Values and nullability](/book/part-2/04-values-and-nullability) | What does a field read return, and who decides that a value may be absent? |
| [8. Grain and projections](/book/part-2/05-grain-and-projections) | What is one row after a filter, a join, a group or an expansion? |
| [9. Binding as implementation detail](/book/part-2/06-binding) | How does a row source populate the record the design already declared? |
| [10. Generating declarations](/book/part-2/07-generation) | How is a declaration package generated without taking over the model? |

The chapters divide into three movements. Chapters 4 and 5 state the design:
meaning, purpose, records, properties and direction. Chapters 6 to 8 settle the
row that will supply it: source, value and grain. Chapters 9 and 10 turn the
design into a mapping, and then into a generated package that reproduces the
declarations.

## How to read

Read the chapters in order the first time. The order is a way to separate
decisions, not a claim that a project writes them in that sequence. When a source
forces a design change, return to chapter 4 or 5; when a design needs a new
property, return to chapter 6 or 7.

Every code fragment is valid against the current public API. Fragments are
deliberately local; they show the declaration under discussion rather than a
complete package.

## Next

[4. Meaning and purpose](/book/part-2/01-meaning-and-purpose) — begin with what the graph says, before choosing the rows that supply it.
