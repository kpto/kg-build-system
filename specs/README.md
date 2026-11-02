# Internal interface specs

These specs are for the framework reviewer. Author-facing documentation is in
`../docs/`; it is not duplicated here.

A spec states one responsibility, the author-visible names, the names another
package may import, the frozen IR, the allowed package edges and the decisions an
implementer must honour. It describes the current code, not a target design.
Implementation walkthroughs, private helpers and line numbers are out of scope.

Every framework subpackage uses the four-part layout:

```text
pkg/
  __init__.py          # facade; re-exports only pkg.public
  public/              # definition site for author-facing names
  internal/            # cross-package interface; ir.py (or ir/) and adapters/<protocol>.py
  _private/            # mechanisms; imported only inside the package
```

| Surface | Reader | Rule |
| --- | --- | --- |
| `__init__.py` | graph author | exposes only `pkg.public` |
| `public/` | graph author | definition site for authoring classes, values and wrapper functions/methods with user docstrings and `Example:` blocks |
| `internal/` | another subpackage | cross-package interface; holds the IR in `ir.py` or `ir/` |
| `_private/` | the package itself | mechanisms; never imported from another package |

- `pkg/public` functions and methods are thin wrappers over `pkg._private` or
  `pkg.internal`; the mechanism never lives in `public`.
- Another subpackage imports `pkg`, `pkg.internal` and `pkg.internal.ir`. It does
  not import `pkg._private`; `_private` may import `pkg.internal`,
  `pkg.internal.ir` and its own public data classes.
- `pkg/internal/adapters/<protocol>.py` is the explicit file that implements a
  foreign protocol:
  - `table/internal/adapters/kernel_language.py`,
    `topology/internal/adapters/kernel_language.py` and
    `binding/internal/adapters/kernel_language.py` implement the kernel
    `Language` protocol;
  - `modules/internal/adapters/core_module.py` implements the kernel `Module`
    protocol;
  - `engines/internal/adapters/engine.py` implements the neutral engine
    protocol;
  - `code_generation/internal/adapters/provider.py` implements provider loading.
- Public docstrings are user-facing and carry runnable `Example:` blocks.
  Internal and private docstrings are developer-only and need no example.
- `kernel` is the domain-agnostic package. `relational` and `engines` have an
  empty `public/` stating that they have no authoring surface. `cli` exposes `main` through `public/` and keeps argument
  parsing in `_private/`.
- Root `interfaces.py`, `ir.py` and `models.py` files are compatibility shims
  for the Open Targets project only. They are not the interface.

`kernel` is the only domain-agnostic package. `table`, `topology` and `binding`
are languages. The core module is one module, not a domain package. `engines`
own SQL and code generation. Implementation modules are private; another package
imports only `pkg`, `pkg.internal`, `pkg.internal.ir` or the shared kernel.

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
