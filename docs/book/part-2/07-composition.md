---
title: "10. A workflow is a chain of reactions"
summary: "Steps declare artifact ports and assembly priority, not producer identities; composition is matching, interception and derived order."
section: book
perspective: book
part: II
chapter: 10
order: 27
status: normative
verified: 2026-11-11
sources:
  - docs/book/part-3/02-planning.md
  - docs/appendix/spec/plan.md
  - docs/appendix/reference/planners-and-executors.md
  - docs/appendix/developer/system-design.md
  - kg_build_system/kernel/service/_private/assembly.py
---

A graph build is often described as a sequence of phases: ingest, normalize, build records, validate, write. The description sounds like a plan, and the plan looks like a sequence of steps. That reading is wrong in a way that survives compilation.

A step is not a task with a purpose. It is a reaction. It declares what artifact types it needs and what artifact types it makes available. When the types line up, it can react; when they do not, it waits. The same graph can be built by a different set of reactions without changing the declarations that describe the graph.

This chapter states the composition contract. The mechanics are in Part III; the direction is here because the contract decides what a step is allowed to mean.

## A step is a reaction, not a task

The procedural reading says:

```text
ingest → normalize → build records → write
```

Each arrow means “run this next.” The reaction reading says:

```text
artifact available → compatible reactions run → more artifacts available
```

The arrow is not a command. It is an availability relation. A reaction is eligible when every input type it consumes has a producer; it becomes available when those inputs exist.

A `Step` therefore has ports, not a task body:

| Field | Meaning |
| --- | --- |
| `inputs` | Artifact types or patterns this reaction consumes |
| `outputs` | Concrete types this reaction makes available |
| `publication` | An output that is also a final artifact |
| `instruction` | What one executor does when this reaction runs |
| `assembly_preference` | `eager` or `deferred` for assembly order |
| `component` / `name` | The reaction's identity inside a planner group |

There is no `depends_on`, no `before`, no `after` and no producer step id in a step. If a design needs one, it is trying to encode execution order in the model. That order is derived.

## Declared and derived

The composition contract is easiest to hold as two columns.

| Declared | Derived |
| --- | --- |
| A producer's output artifact type | Which consumer inputs it can feed |
| A consumer's input type or pattern | Which producer outputs match |
| A planner's component and position | Assembly priority and rank |
| `assembly_preference` | Eager before deferred within a component |
| A step and its instruction | A connection between openings |
| A publication | A report artifact and a downstream port |
| Artifact availability | Execution waves and run order |

The left column is authored. The right column is assembled. A reader who confuses the two will add a producer list, a barrier or a dependency edge to the left column and wonder why the design stops being compostable.

## Priority is assembly order, not data dependency

Two reactions that are both eligible still need an order for assembly. That order is priority:

1. planners are grouped in the order they appear in the toolchain;
2. within a component, `eager` contributions rank before `deferred` ones;
3. within one preference, declaration order decides.

The assembler derives a rank from those facts and uses it for scan order and for choosing the freshest compatible output in an endofunctor case. It is an assembly detail, not a runtime schedule. It is not a tie-break between two producers of the same artifact type: those are refused as ambiguous because the declaration does not distinguish them.

> **Priority orders the assembly scan. It does not make an input exist, and it does not choose between two producers of one type.**

Execution schedules dependency waves after assembly. A step is ready when every producer of every taken input has completed. All ready steps form a wave; steps in one wave run one at a time in plan order. Priority does not let a step run before its input artifact is available, and it does not override a missing producer.

The current checkout has no public per-step `priority` field. Assembly priority is expressed by planner order and `assembly_preference`. A contributor that needs earlier assembly precedence places its planner earlier or marks the step `eager`. That is a limit of the current surface, not a licence to encode order in an input type.

The same limit applies to same-type interception. If two producers publish one artifact type and the consumer does not distinguish them, assembly refuses the ambiguity. Priority does not break the tie. To intercept a producer, replace it in the composition or give the normalized result a distinct type. If both producers must coexist, the model needs a real distinction—a different type, a narrower consumer declaration, or a future public priority policy. The current checkout does not provide the last one.

## Interception is the design goal

The reaction model exists so another contributor can insert a reaction without editing the reactions around it.

Suppose a source producer publishes `ingest/site_row`. A graph consumer declares `ArtifactPattern.of("ingest", "site_row")`. A normalization producer can replace the source producer in the composition, publishing the same type, and the consumer declaration does not change. Its pattern matches the replacement. The plan's connection changes; the consumer source does not.

That is interception by replacement. It is the reason a consumer names an artifact, not a producer, and the reason priority is separate from type. If the new producer is added alongside the old one and both publish `ingest/site_row`, assembly refuses the pair as ambiguous; the type does not tell it which one the consumer means.

An **exact input** is the deliberate exception, with a limit worth stating precisely. An exact input names an artifact type, not a producer. It accepts every producer that publishes that type. It seals interception only when the type has one producer, or when the type is reserved to one producer by the model. If another producer publishes the same type, the exact input still matches it; the boundary is not sealed.

A sealed boundary is therefore a type-level decision: *this consumer requires the audited release type, and only the audited producer may publish it*. The seal is legitimate only when it is named as a decision. Exactness alone is not a producer identity.

An exact input used only to force a step to run earlier is an anti-pattern. It narrows the eligible producers and hides the real ordering decision in the type. The author has used data eligibility as a scheduling device.

## A phase is a group of producers

A project may still speak of an ingestion phase or a normalization phase. That word is useful for a feature family, not for a scheduler.

A phase is a set of producers and the artifact types they publish. It is not a barrier, not a sequence and not a step that names its members. One source can publish several relation types; each type is a separate availability fact. A phase consumer reads the types it needs; it does not list the producers.

A barrier step that names every producer is a workaround for missing artifact types. If the consumer needs all outputs together, it should declare a pattern over the phase's output namespace and let assembly expand it. If it needs one output, it should declare that type. It should not know the producer count.

## The anti-patterns

Each of these compiles. Each one moves composition back into procedure.

| Anti-pattern | Why it compiles | The reaction replacement |
| --- | --- | --- |
| A producer declaration with a dependency list | Python accepts a new field; assembly does not need to forbid it because it does not read it | Declare output types; let consumers match |
| A barrier naming every producer | A step can name an exact artifact from each producer | A pattern input over the phase's output types |
| An exact input used only to force order | Exact types are valid data requirements | Use an artifact type or pattern; use priority for assembly order |
| A consumer enumerating producers | The consumer can read several exact artifacts | Declare a pattern; assembly expands every match |
| Priority or rank used as data availability | Rank is an integer and can be written anywhere | Priority orders eligible reactions; availability comes from producers |
| A phase modelled as a chain | A chain of steps produces the expected plan | A phase is a set of producers and artifact types |
| A step that does a domain operation with no named output | The instruction can compute anything | Publish a named artifact; if it is graph meaning, publish a projection |

The last row is the semantic failure. A step that hides its result cannot be intercepted, referenced or reviewed. The model can execute it, but no other reaction can depend on what it produced.

## Adding a producer

The change surface is small, and that is the point:

1. add the producer planner to the composition;
2. declare its output artifact type;
3. declare any publication or final artifact;
4. choose its assembly position and preference;
5. do not edit downstream consumers.

For a new artifact type, the addition is additive. For the same type, the addition must replace the existing producer; two producers of one type are an ambiguity, not an interception. The check is the invariant:

> Adding a producer of a new type must not require editing a consumer. Replacing a producer of the same type must not either.

The check is about the consumer's declaration, not the plan. A new producer normally adds steps and connections. A new execution wave may appear. The consumer source must remain unchanged because it named a type, not a producer.

## Change scenarios

| Change | What changes | What must not change |
| --- | --- | --- |
| Add a producer of a new type | One planner, one or more output types, priority | Consumer declarations that match the type |
| Replace a producer of one type | The producer, its output type and position; the old producer is removed | Consumer declaration; two same-type producers are refused as ambiguous |
| Add a consumer | One planner and its input type or pattern | Existing producers |
| Add an optional producer | A fallback producer or a module over absence; the input must still be fed | Consumer declaration; the framework has no optional input port |
| Split a producer | Two producers and their output types; a pattern consumer may need no edit | Exact consumers that narrowed the type; a true seal needs one producer for it |
| Merge producers | One producer publishing the combined types, or a pattern join | Consumers of the original types, unless the types change |
| Change an artifact type | The producer and every exact consumer; pattern consumers may still match | The graph's semantic model |
| Remove a producer | The producer and its connections; an unfed exact or pattern input is refused | The consumer declarations, if a replacement producer remains |
| Add a phase | A group of producers and output types | Neighbouring reactions; no barrier is introduced |

Two rows are deliberately uncomfortable. An optional producer is not optional to assembly: every input must be fed. The framework has no optional input port, so absence needs a guaranteed fallback producer or a module that handles it. Removing a producer exposes an unfed input at compile time; that is a correct refusal, not a reason to add a barrier.

## The test that judges the design

The local-change invariant is executable:

1. compile a plan with a pattern consumer and one matching producer;
2. add a second producer of a different matching type;
3. leave the consumer declaration untouched;
4. assert the consumer now receives both producers.

A second test narrows the boundary: give the consumer an exact input and add a producer of a different type; the consumer still receives only the exact type. A true seal needs one producer for that type; if a second producer publishes the same type, the exact input matches it too, and the design has not sealed anything.

A third test asserts the ambiguity: two producers of one type, one consumer, no distinguishing declaration, and assembly refuses rather than letting priority choose. That is the current boundary of arbitrary same-type interception; a future public priority policy would need its own contract and test.

These tests belong beside the plan tests, not only in the framework's internal assembly suite. They are the documentation of the contract that a successful build cannot prove.

## The contract

> Steps declare artifact ports, not producer identities.
>
> Consumers declare artifact types or patterns, not step identities.
>
> Eligibility is artifact matching. Priority is assembly order, not data dependency.
>
> Adding a producer must not require editing a consumer.
>
> An exact input narrows eligibility; it seals a boundary only when one producer owns the type. A seal must be named as a deliberate refusal of interception.
>
> A phase is a group of producers and artifact types, not a dependency chain.
>
> A step that hides its result inside a procedure has not composed a semantic unit.

The rest of Part II uses these rules when it turns a row source into a record. The mechanics of planning, assembly and execution are in Part III; the reactions themselves are the model.

## Next

[11. Binding as implementation detail](/book/part-2/08-binding) — from a named relation and its reactions to the node and edge records they populate.
