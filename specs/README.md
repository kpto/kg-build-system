# Internal interface specs

These specs are for the framework reviewer. Author-facing documentation is in
`../docs/`; it is not duplicated here.

A spec states the internal interface: responsibility, names and signatures,
invariants, allowed dependencies and the decisions an implementer must honour. It
does not describe implementation.

Read in this order:

| Spec | Responsibility |
| --- | --- |
| [overview](overview.md) | purpose, pipeline and package map |
| [types](types.md) | logical types, nullability and DuckDB acceptance |
| [declarations](declarations.md) | Table, Struct, ComputedStruct, Projection, TableGroup, fields and templates |
| [expressions](expressions.md) | selections, value operations, `alter_rows` and row semantics |
| [row-sources](row-sources.md) | relation values and the row-source algebra |
| [projections](projections.md) | pinned projections and computed outputs |
| [topology](topology.md) | node/edge hierarchy, properties and endpoints |
| [bindings](bindings.md) | node/edge binding authoring |
| [compile](compile.md) | blueprint, IR boundary and compilation |
| [workflow](workflow.md) | workflow model, assembly and execution |
| [modules](modules.md) | module extension interface and built-ins |
| [ingest](ingest.md) | sources, trust, nullability and guards |
| [generation](generation.md) | edit-time generated declaration packages |

`../FRAMEWORK_STATE.md` is the reviewer briefing: the current state, the known
interface conflicts and the decisions that need attention.
