# The kg-build-system authoring guide

kg-build-system turns Python declarations into a reproducible knowledge graph.
You describe three things separately:

1. **What the data looks like** — the tables, structs and fields you read.
2. **What the graph means** — the node and edge types, their properties and
   their place in a hierarchy.
3. **How rows become graph records** — bindings that connect one to the other.

The framework compiles those declarations into a frozen build plan and then
executes it. You do not write SQL, a mapping document, or a graph-loader script.
You write typed Python; the framework checks the shape of every value on the way
through.

## The mental model

```
source files ──> tables and structs ──> expressions ──> bindings ──> graph
                    (data shape)        (row values)     (meaning)    (records)
```

- **Tables** describe physical rows. A table is also a *shape*: a class whose
  fields are typed.
- **Expressions** read, transform and filter values row by row. They know their
  logical type, including nullability.
- **Topology** declares graph meaning independently of any file: `SiteNode`,
  `HAS_UNIT`, the properties a site carries.
- **Bindings** say which rows produce which nodes and edges, and what each
  property receives.
- **Modules** add reusable build stages (deduplication, merging, validation,
  file/meta-graph/Neo4j output). A build composes the modules it needs.

## What you get

One `compile()` call produces an immutable contract: the complete, portable
description of the graph build. One `build()` call executes that contract against
the configured runtime and writes the outputs selected by the modules. The same
contract can be built repeatedly, inspected, or stored.

## How to read this guide

Start with [Install](start/install.md) and [Your first graph](start/first-graph.md)
if you want to see the whole shape first. Otherwise read the concepts in order:

- [Data contracts](concepts/data-contracts.md) → [Types and
  nullability](concepts/types.md) → [Sources](concepts/sources.md)
- [Expressions](concepts/expressions.md) → [Projections](concepts/projections.md)
- [Topology](concepts/topology.md) → [Bindings](concepts/bindings.md)
- [Annotations and descriptions](concepts/annotations.md)
- [Modules](concepts/modules.md) → [Compile and build](concepts/build.md) →
  [Outputs](concepts/outputs.md)

The [modelling patterns](guides/patterns.md) page collects the decisions that
come up repeatedly in real graphs; [debugging](guides/debugging.md) explains the
errors you are most likely to meet. The [public API](reference/api.md) is a
lookup, not a substitute for the concepts.

The walkthrough builds a small people graph. The deeper concept pages borrow
their examples from the framework's monitored-estate reference project, so you
will meet sites, units, defects and survey readings as well as people. Where an
example imports a reference table, substitute your own; the API is unchanged.
