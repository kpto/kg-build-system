# Internal interface specs

These specs are for the framework reviewer. Author-facing documentation is in
`../docs/`; it is not duplicated here.

A spec states one responsibility, the author-visible names, the names another
package may import, the frozen IR, the allowed package edges and the decisions an
implementer must honour. It describes the current code, not a target design.
Implementation walkthroughs, private helpers and line numbers are out of scope.

Every domain subpackage exposes three surfaces:

| Surface | Reader |
| --- | --- |
| `__init__.py` | graph author: names written or read |
| `interfaces.py` | another subpackage: values, protocols, functions |
| `ir.py` | compiler: frozen DTOs and codecs |

`kernel` is the only domain-agnostic package. `table`, `topology` and `binding`
are languages. `modules.core` is a module. `engines` own SQL and code
generation. Implementation modules are private; another package imports only
`interfaces`, `ir`, a nested package `__init__`, or the shared kernel.

Read in this order:

| Spec | Responsibility |
| --- | --- |
| [overview](overview.md) | purpose, kernel, languages, build pipeline and package map |
| [types](types.md) | logical types, normalization, validation and type codecs |
| [declarations](declarations.md) | Table, Struct, ComputedStruct, Projection, TableGroup, fields and sources |
| [expressions](expressions.md) | selections, expression families, operations and row semantics |
| [row-sources](row-sources.md) | row-source values, generated shapes and plan IR |
| [projections](projections.md) | pinned and unpinned named projections and computed outputs |
| [topology](topology.md) | node and edge declarations, properties, endpoints and components |
| [bindings](bindings.md) | node and edge bindings, keys, properties and endpoints |
| [compile](compile.md) | blueprint aggregate, codecs, validation and the compile pipeline |
| [workflow](workflow.md) | assembly, contract, execution, services and reporting |
| [modules](modules.md) | module extension contract, core and supplied modules |
| [ingest](ingest.md) | physical sources, declared nullability, guards and DuckDB acceptance |
| [generation](generation.md) | edit-time generation requests, providers, rendering and ownership |

`../FRAMEWORK_STATE.md` is the reviewer briefing. `../DESIGN_ISSUES.md` records
where the clean model and the effective compatibility surface conflict.
