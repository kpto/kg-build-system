# Why this framework

A graph build usually starts with files and ends with records. The meaning of
those records — which node types exist, what an edge asserts, which direction it
points, what identifies a record, what an absent value means, and where the data
cannot tell you — often lives in code, comments or the memory of the person who
wrote the loader. A consumer of the graph then has to reverse-engineer it.

kg-build-system exists to make that meaning part of the delivered build. The
author declares it in typed Python, the framework checks it before reading data,
and the build publishes it alongside the graph. A downstream reader can then
reason about node and edge types, identity, absence and limits without reading
the pipeline that produced them.

## What it is for

The author writes three separate things:

- what a source row looks like, as a typed contract;
- what the graph means, as node and edge declarations;
- how rows become records, as bindings over explicit row plans.

The framework compiles those declarations into an inspectable workflow contract,
executes it, and publishes reports and artifacts. The contract carries the
declared meaning, and the meta-graph module can publish the effective topology
for consumers. The product is not the Python and not the loader; it is a graph
whose meaning survives the build.

## The values

### Semantics as contract

A node or edge type is a statement: what it means, which direction it points,
what identifies it, when a value may be absent, and what the model cannot
express. That statement is declared and published, not left in a comment or an
implementation detail. A consumer can rely on it.

When a meaning cannot be stated faithfully, the framework records a limit rather
than inventing precision. A nullable property stays nullable; an unresolved
reference fails; a target that cannot store a type refuses it.

### Explicit assumptions

Nullability, row grain, keys, joins, unions, groupings and expansions are written
where the author makes the decision. Source fields read as nullable and are
narrowed deliberately. A join states its keys and mode. A group states its keys.
An expansion is visible at the point where it changes the row count.

Nothing important is inferred from a sample of the data. A value that happens to
be present in the first thousand rows does not become a promise about the rest.

### Typed authoring

Declarations are ordinary Python classes with typed fields and properties. A
static type checker catches many mistakes while the author writes; compilation
catches the rest before a row is read. There is no string SQL, no separate
mapping document and no untyped dictionary at the centre of the model.

A type error names the declaration and both sides of the mismatch, so the author
can see whether the problem is a nullable key, an array where a scalar is
required, or a property that needs a different type.

### Reproducible, inspectable builds

`compile()` turns the declarations and module composition into an immutable
contract with a workflow fingerprint. `build()` executes that contract and
returns a report; the contract and report are written next to the outputs.

The fingerprint identifies the plan, not the input bytes. The same declarations
and module configuration produce the same plan; a source file can change without
changing the plan. Use the fingerprint to say what was built and your own data
versioning to say what it was built from.

The contract is durable data, not a compatibility promise. It can be stored and
rebuilt while the same module implementations and versions are available. The
framework has no schema compatibility or migration path, so a changed module or
framework means compiling again.

### Separation of meaning, acquisition, planning and execution

The graph model is independent of where rows come from and of the engine that
runs the build. Topology declares nodes, edges and properties without importing a
table or a target. Tables describe logical rows; a source binding supplies the
physical location. Bindings are the only layer that imports both sides. Output
modules decide whether the result becomes JSON Lines, a meta-graph, a Neo4j
bundle or something else.

That separation is what lets a feed move without changing the graph, a node type
be reused across feeds, or an output target change without rewriting the
mapping. The same compiled plan can feed several targets.

### Honest limits

The framework does not pretend to do more than it does:

- a source field is nullable on access even when the source calls it required;
- generated nullability is a recorded source claim, not a non-null field type in
  the contract;
- a `ComputedStruct` used as a field supplies member types as witnesses; it does
  not evaluate those expressions;
- grouping collects members but has no count, sum or `having` aggregate;
- generated join and group shapes are typed at runtime but not statically
  exposed by the type checker;
- custom scalars have no value operations, and a target may refuse them;
- Neo4j refuses `uuid` and custom scalar properties;
- meta-graph counts are exact for the records that reached the module, while
  example values are approximate.

These are stated so an author can design around them and a consumer does not
mistake a limit for a guarantee.

### The user perspective

The framework is not a coding exercise. It exists so that an author can express a
graph whose meaning survives the build, and so that a consumer can ask what a
node type means, what identifies it and what is missing without reading the
pipeline. Every authoring choice should serve that outcome.

## What you can rely on

| Stage | What is guaranteed |
| --- | --- |
| Declaration | Types are explicit; source access is nullable; a field type is a value record, not a relation |
| Compile | Components and bindings exist; properties are mapped; keys are present scalars; sources are bound; expressions name known fields |
| Build | The contract is frozen; failures are reported; outputs are published by the modules that ran |
| Publication | Labels, descriptions and annotations travel with the graph; when the meta-graph module is composed, it states the effective topology and exact counts |

## What it does not promise

- A stable API. The framework is experimental and breaking changes are expected.
- Schema compatibility or migration between framework or module versions.
- That the input data is unchanged; fingerprints cover the plan, not the bytes.
- Exact example values in the meta-graph; they are approximate by design.
- That every graph question is expressible; a stated limit is a decision, not a
  missing feature to work around silently.

## Where to go next

- [The authoring guide](index.md) shows the three layers and how they fit.
- [Your first graph](start/first-graph.md) builds a complete small example.
- [Data contracts](concepts/data-contracts.md) and
  [Topology](concepts/topology.md) define the two halves of meaning.
- [Compile and build](concepts/build.md) and [Outputs](concepts/outputs.md)
  describe the contract and what it publishes.
- [Debugging](guides/debugging.md) explains the errors an author is most likely
  to meet.
