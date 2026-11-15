---
title: "Part II — Authoring a graph"
summary: "Meaning, topology, extension and reaction frame the source rows, values, grain and binding that implement the design."
section: book
perspective: meta
part: II
order: 20
status: normative
verified: 2026-11-11
sources:
  - docs/content/index.md
  - docs/content/book/part-2/01-meaning-and-purpose.md
  - docs/content/book/part-2/02-topology.md
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

## The mentality

Part II is not a tour of the API. It is a way to decide what the graph is before
deciding how to produce it. The supplied operations are a baseline, not a domain
vocabulary; the work is to state the model, not to write a sequence of steps that
happens to produce data.

Four habits set the direction.

**Start from meaning.** A source describes bytes. A node, an edge and a claim
describe what those bytes are taken to mean. If the column list defines the
record, the source owns the model and every schema change becomes a change of
meaning. Start with the claim, then choose the record, then choose the rows.

**Design the record before the row.** A source supplies a shape; topology states
a design. A table names the source and its fields, a node names a record and its
properties, and a binding is the one place where a relation is offered to that
record. The binding is the fulfilment: it must not invent the grain, the identity
or the property set it is supposed to satisfy.

**Keep data operations semantic.** A domain calculation is not a step that does
something and disappears. It belongs in the expression language, and it becomes
graph meaning only when a named projection publishes the result with a grain and
a claim. If a claimed projection cannot be named and referenced outside the
pipeline, it is a data operation, not a semantics unit. A source adapter is thin:
it bridges a physical format to a relation and the SQL boundary, and it does not
carry joins, identity translation, aggregation or graph meaning.

**Treat the workflow as a chain of reactions.** A step does not own a semantic
goal. It reacts to artifact types and publishes an artifact; the assembler
derives the connection, and priority orders the assembly scan of eligible
reactions. Priority does not choose between two producers of one type.
Interception is deliberate: another producer or consumer should be insertable at
an artifact boundary without editing the steps around it. An exact input can
refuse interception, but that is a sealed boundary and must be named as one.
Start from the artifact the graph needs and ask which producers can make it; do
not start from a procedure and ask which steps to run.

The same domain sentence can be implemented at several levels. The level is
chosen by the kind of fact being added, not by convenience.

| Level | Question | A common wrong answer |
| --- | --- | --- |
| Meaning | What does the graph claim? | A step invents a purpose. |
| Topology | What is one record, property and direction? | A source column list becomes the record. |
| Data | What is one row, value and grain? | A field type hides absence or a row operation hides a fan-out. |
| Extension | What domain operation is missing? | A SQL string or lambda is buried in a reader. |
| Projection | Which named relation carries the result? | A pipeline-local relation is called a projection. |
| Binding | How does a row become the declared record? | The binding invents the model. |
| Workflow | Which reactions make the artifact available? | A dependency list or barrier orders the steps. |

The order of the chapters is a reading order, not a rule for how a project
evolves. A source reveals a property; a property suggests a claim; a claim
changes which records are worth declaring. The point of the separation is to make
each decision reviewable, not to pretend that authoring is one-way. The mechanics
of artifact matching and execution belong to Part III; the direction belongs here.

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
| [8. Relations and projections](/book/part-2/05-grain-and-projections) | What is one row after a filter, a join, a group or an expansion? |
| [9. Extending the semantics model](/book/part-2/06-extension) | Where do source adaptation, domain operations and named derived relations live? |
| [10. A workflow is a chain of reactions](/book/part-2/07-composition) | How do artifact types, priority and interception compose work without a dependency chain? |
| [11. Binding as fulfilment](/book/part-2/08-binding) | How does a row source populate the record the design already declared? |
| [12. Generating declarations](/book/part-2/09-generation) | How is a declaration package generated without taking over the model? |

The chapters divide into five movements. Chapters 4 and 5 state the design:
meaning, purpose, records, properties and direction. Chapters 6 to 8 settle the
row that will supply it: source, value and grain. Chapter 9 states how the
supplied vocabulary is extended when the domain needs an operation the framework
does not ship. Chapter 10 states how reactions compose by artifact type,
priority and interception. Chapters 11 and 12 turn the design into a mapping, and
then into a generated package that reproduces the declarations.

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
