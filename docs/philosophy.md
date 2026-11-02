# Philosophy

This page states the problem kg-build-system addresses and the values behind
its design.

kg-build-system is a Python framework that turns typed declarations into an
inspectable knowledge graph whose meaning is part of the delivered build.

## The problem

A graph build usually starts with files and ends with records. The records can be correct while their meaning is not written down: which node types exist, what an edge asserts, which direction it points, what identifies a record, what an absent value means, and where the data cannot answer the question.

That knowledge often lives in a loader, a comment, or the memory of the person who wrote it.

A consumer then has to reconstruct the model before using the graph. When the feed changes, the reconstruction starts again. Documentation alone does not solve this, because it drifts from the code unless something checks it.

kg-build-system makes the meaning part of the declaration and part of the build. You state the model in typed Python, the framework checks it before reading data, and the build publishes it with the graph.

## What the framework promises

You write three kinds of declaration.

A **data contract** describes the rows you read: their fields, types, and nested records. A **topology declaration** states what a node or edge means, including its properties and, for an edge, its direction. A **binding** connects one row shape to one graph record and supplies the values.

The framework compiles those declarations into a frozen contract, checks what can be checked before a row is read, and executes the contract. A build writes the contract and a report; the output modules write the graph. The product is not the Python and not the loader; it is a graph whose meaning survives the build.

## Values

### Semantics as contract

A node or edge type states what it means, which properties it carries, which values may be absent, and, for an edge, which direction it points. The binding adds which rows produce records and which non-null value identifies each record. Together, those statements are declared and published, not left in a comment or an implementation detail.

The compiled contract records the declared meaning. When you compose the meta-graph module, the published meta-graph states the effective topology: labels, descriptions, properties, and counts. A consumer can read the model from the artifact instead of reconstructing it from the pipeline that produced it.

When a meaning cannot be stated faithfully, the framework records a limit instead of inventing precision. A nullable property stays nullable, an unresolved reference fails, and a target that cannot store a type refuses it.

See [semantics and annotations](concepts/semantics.md) for how descriptions, labels, and annotations become build data.

### Explicit assumptions

Nullability, row grain, keys, joins, unions, groupings, and expansions are written where you make the decision. A source field reads the presence its declaration names; a nullable field is narrowed deliberately. A join states its keys and mode. A group states its keys. An expansion is visible at the point where it changes the row count.

Nothing important is inferred from a sample of the data. A value that happens to be present in the first thousand rows does not become a promise about the rest.

### Typed authoring

Declarations are ordinary Python classes with typed fields and properties. A static type checker catches many mistakes while you write, and compilation catches the rest before a row is read. There is no string SQL and no separate mapping document at the centre of the model.

A type error names the declaration and both sides of the mismatch, so you can see whether the problem is a nullable key, an array where a scalar is required, or a property that needs a different type.

### Reproducible builds

`compile()` turns the declarations and module composition into an immutable contract with a workflow fingerprint. `build()` executes that contract and returns a report. The contract and report are written in the output directory beside the graph.

The fingerprint identifies the plan, not the input bytes. The same declarations and module configuration produce the same plan, and a source file can change without changing the plan. Use the fingerprint to say what was built and your own data versioning to say what it was built from.

The contract is durable data, not a compatibility promise. It can be stored and built again while the same module implementations and versions are available. The framework has no schema compatibility or migration path, so a changed module or framework means compiling again.

### Separation of meaning and execution

The graph model is independent of where rows come from and of the engine that runs the build. Topology declares nodes, edges, and properties without importing a table or a target. Tables describe logical rows. A source binding supplies the physical location. Bindings are the only layer that imports both sides. Output modules decide whether the result becomes JSON Lines, a meta-graph, a Neo4j bundle, or something else.

That separation lets a feed move without changing the graph, a node type be reused across feeds, or an output target change without rewriting the mapping. The same compiled plan can feed several targets.

### Honest limits

The framework states what it does not do, so you can design around it and a consumer does not mistake a limit for a guarantee:

- A source field reads the presence the declaration names. A generated
  `DEFAULTED` source renders a nullable field; an enforced or declared source
  renders a non-null field, and a null there is a data failure.
- Grouping collects members but has no count, sum, or `having` aggregate.
- Generated join and group shapes are typed at runtime but are not exposed to the static type checker.
- Custom scalars have no value operations, and a target may refuse them. Neo4j refuses `uuid` and custom scalar properties.
- Meta-graph counts are exact for the records that reached the module; example values are approximate.
- There is no schema version, compatibility negotiation, or migration path.

## Who it is for

kg-build-system is for authors who have tabular, JSON, or Parquet input and need a graph that other people can inspect. You should be comfortable writing Python and thinking about data models.

You will get the most from it when the graph is a product that changes over time, when a consumer needs to know what a record means, and when you want a change to a feed or an output to leave the rest of the model alone.

## What it is not

- It is not an orchestrator or a scheduler. It runs one compiled build; another system decides when to run it.
- It is not a graph database or a query service. It produces artifacts for a target.
- It is not a schema migration tool. There is no schema version or compatibility path; compile again when a declaration or module changes.
- It is not a substitute for source data quality. If a key is missing, your binding must drop the row or fail; the framework does not invent an identity.
- It is not a stable public API. The API is experimental, and breaking changes are expected. Treat this guide and the code as the current model, not as a compatibility contract.

## What to remember

- The product is a graph whose meaning survives the build.
- You declare rows, graph meaning, and mappings separately.
- `compile()` checks declarations before data is read; `build()` executes the plan and writes outputs.
- A stated limit is part of the model, not a hidden gap.

## Next steps

- [Install kg-build-system](get-started/install.md) and verify the environment.
- [Build your first graph](get-started/first-graph.md) for a complete, runnable example.
- [Project layout](get-started/project-layout.md) for where each declaration and output belongs.
- [Data contracts](concepts/data-contracts.md) and [topology](concepts/topology.md) for the two halves of the model.
- [Compile, build and outputs](concepts/build-and-outputs.md) for the contract and the published artifacts.
- [Semantics and annotations](concepts/semantics.md) for how descriptions, labels, and annotations travel with the build.
- [Authoring API reference](reference/index.md) for the full public surface.
