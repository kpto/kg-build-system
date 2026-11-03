# kg-build-system documentation

Build a knowledge graph whose meaning survives the build.

kg-build-system turns typed Python declarations into an inspectable knowledge
graph. You describe the rows you read, declare what the graph means, and connect
the two with bindings. The framework compiles those declarations into a frozen
contract, executes it, and publishes the graph together with the meaning you
declared for it.

Read the [philosophy](philosophy.md) for the problem the framework addresses and
the values behind its design.

## Get started

- [Install](get-started/install.md) — set up the package and verify it.
- [Build your first graph](get-started/first-graph.md) — a complete walkthrough.
- [Project layout](get-started/project-layout.md) — where declarations,
  bindings and sources live.

## How a build works

```text
source files
    │
    ▼
data contracts ──► expressions ──► row sources ──► projections
    │                                                │
    └──────────────► topology ◄── bindings ◄─────────┘
                           │
                           ▼
                  compile ──► contract ──► build ──► graph and reports
```

A build has four layers. **Data contracts** describe the rows: their fields,
types and nested records. **Expressions and row sources** turn those rows into
the values and the grain a record needs. **Topology** declares the graph:
nodes, edges, properties and their meaning. **Bindings** map one row context
onto one node or edge record.

`compile()` checks the declarations and freezes one workflow contract.
`execute()` executes it and writes the outputs selected by the modules. The same
contract can be reviewed before data is read, executed repeatedly, or sent to
several targets.

## Learn the model

Read these in order for the complete story, or jump to the concept you need:

1. [Data contracts](concepts/data-contracts.md) — rows as typed Python classes.
2. [Types and nullability](concepts/types.md) — the vocabulary every value
   carries.
3. [Sources](concepts/sources.md) — where the rows physically live.
4. [Expressions](concepts/expressions.md) — reading, transforming and filtering
   values.
5. [Row sources and grain](concepts/row-sources.md) — what one row means.
6. [Projections](concepts/projections.md) — naming a reusable relation.
7. [Topology](concepts/topology.md) — the meaning of nodes and edges.
8. [Bindings](concepts/bindings.md) — turning rows into records.
9. [Semantics and annotations](concepts/semantics.md) — making the meaning part
   of the delivered graph.
10. [Modules](concepts/modules.md) — composing build stages.
11. [Compile, build and outputs](concepts/build-and-outputs.md) — from
    declarations to artifacts.

## Do a task

- [Join, group and union](how-to/relations.md) — choose and combine grains.
- [Write a custom module](how-to/custom-modules.md) — add a build stage.
- [Debug a build](how-to/debug.md) — read error messages and reports.
- [Modelling patterns](how-to/patterns.md) — recurring graph shapes.

## For framework developers

- [Developer guide](developer/index.md) — internal model, target architecture,
  data and expressions, and the contract tests that guard each interface.

## Reference

- [Authoring API reference](reference/index.md) — the surface you write.
- [Types reference](reference/types.md) — canonical types, nullability and
  limits.
- [Glossary](reference/glossary.md) — terms used across the guide.
