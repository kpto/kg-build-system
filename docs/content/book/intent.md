---
title: "Preface: how to describe a graph"
summary: "The mentality before the mechanism: intention, purpose, claim, limitation, relation, record, and the binding that fulfils one with the other."
section: book
perspective: book
part: 0
chapter: 0
order: 5
status: normative
verified: 2026-11-15
sources:
  - docs/content/book/intent.md
  - docs/content/book/part-2/01-meaning-and-purpose.md
  - docs/content/appendix/philosophy/semantic-hierarchy.md
---

## A graph is an argument, not a pipeline

A pipeline answers one question: which rows came out? A graph answers three:
what exists, what is asserted about it, and what is that assertion for? The
pipeline is one way to produce the records. It is not the model, and it is
replaceable behind the model.

The common failure is to start with the source. A schema arrives, the columns
are mapped, joins are written to make the shapes fit, and a graph appears as a
by-product. The result can be correct and still unexplainable: a reader can see
which table produced a value but not why the record exists, what a consumer may
use it for, or what that use excludes.

This book starts from the other end. State the intention first, then design the
relations and records that serve it, then let the build execute them.

## Start with intention

Before a table, a join or a node, answer:

- Why does this graph exist?
- What is it for, and for whom?
- What is it explicitly not for?

The answer is not a description of the data. It is the author's reason for
building the graph. A graph that cannot state that reason has no test for
whether a query is inside its scope.

The root intention is singular. A graph may have many local purposes under it,
but they all narrow one expected use. If two purposes cannot be read under the
same root, they are two graphs or one graph with a stated limitation.

## Three questions, three units

Every statement answers one of three questions, and the question decides its
unit:

| Question | Unit |
| --- | --- |
| What is the subject for? | `Purpose` |
| What is asserted about it regardless of use? | `Claim` |
| What must a reader not infer while using it? | `Limitation` |

- A definition, identity, grain or cardinality is a claim, not a purpose.
- A prohibition, absence, exclusion or inference ceiling is a limitation, not a
  claim.
- A measurement is evidence for a boundary, not the boundary. The figure is a
  claim beside the purpose; the limitation states only the excluded reading.
- A declaration with no positive use carries claims only. Do not invent a
  purpose to fill a shape.
- A unit states one thing. A category prefix is a label, not a field.

This is a discipline about language before it is a discipline about code. If a
sentence is in the wrong unit, a consumer will read a caveat as a fact, or a
local use as a universal one.

## Two axes, one fulfilment

A graph design has two axes, and they are not a hierarchy:

```text
records                                 relations
what the graph asserts                  what the domain contains
purpose, claims, limitations            purpose, grain, limitations
        ▲                                       │
        └──────────── binding ──────────────────┘
                    fulfilment
```

The relation axis supplies a relation. The record axis demands a record. A
binding states whether and how the relation fulfils that demand: its grain, its
identity, its coverage and its meaning. The binding owns neither side's meaning;
it owns the adequacy between them.

That is why a binding is not plumbing. It is the place where a design is tested
against the data. If the relation's grain is wrong, or it cannot carry the
record's identity, or its coverage contradicts the record's purpose, the binding
does not fix it. The design changes.

## A projection is a relation

A projection is a named relation that exists in the domain. Its row plan is how
the relation is computed, not what it is. It has a grain, a purpose and its own
limitations, and those can be stated without naming this graph, a node, a
binding or a pipeline step.

The test is:

> State the relation in one sentence with no graph nouns and no operator verbs.

“One condition severity per defect” is a relation. “Join defects to conditions
and drop nulls” is an operator. The second is a derived row source. Keep it
private. If it cannot be stated as a relation, it has no name to publish and no
purpose to fulfil.

A relation may have several consumers. The graph is one of them. Its purpose is
not defined by the graph's use of it, and the binding is what makes it relevant
to the graph.

## Meaning is the artifact

The declarations are the product. A table, a projection, a node, an edge, a
property and a binding each carry the meaning that belongs to them. The
blueprint publishes those meanings; a consumer can read what exists, what it is
for, what is asserted and what is excluded without reading the pipeline.

The build, the planner, the executor and the database are mechanisms. They can
be replaced as long as the declarations still state the same model. A graph that
exists only in its pipeline has no contract to preserve.

## How to read the rest

This preface names no framework type on purpose. It is the mentality the rest of
the book assumes, not an API.

The book then shows one way to make that mentality executable: typed
declarations, a checked blueprint, a plan and published records. Read the
mechanism as an implementation of the argument, not as the argument itself.

## Next

[Part I — The build](/book/part-1/index) — start with what a build produces.
