# Architecture

This is the implementation contract for the framework. The legacy tree is at
`legacy/kg_build_system`; it is reference only.

## Kernel

`kg_build_system.kernel` is the only domain-agnostic package. It imports no
other framework package.

| Name | Responsibility |
| --- | --- |
| `Language` | collect authoring declarations, lower them to one named IR part, validate, encode/decode |
| `Module` | compile against the frozen build, execute contract steps |
| `BuildIR` | immutable named parts, one per language |
| `Registry` | validate names and language dependencies, order languages, compose modules and engine |
| `Build` | run languages, freeze `BuildIR`, run module compilers, assemble the contract |
| `CompilationContext` | build, module id, configuration, blueprint view, engine |
| `contract` | artifact types, steps, contributions, execution contexts, outcomes |

The kernel owns no table, topology, expression, SQL or graph knowledge.

## Package layout

Every framework subpackage uses the same four-part layout:

```text
pkg/
  __init__.py      public facade; imports only from .public
  public/          public domain: names a graph author writes or reads
  internal/        framework-internal interface; ir.py and adapters/
  _private/        mechanisms; imported only inside the package
```

| Zone | Reader | May be imported by |
| --- | --- | --- |
| `pkg` | graph author | any package |
| `pkg.public` | graph author; type vocabulary | any package, for frozen data types |
| `pkg.internal` | framework code | any package |
| `pkg.internal.ir` | compiler code | any package |
| `pkg._private` | its own package | no other package |

- `public` is the definition site for author-facing names. Its functions and
  methods are thin wrappers over `_private` or `internal`; the mechanism is not
  in `public`.
- `internal` is the cross-package contract: frozen models, protocols, helpers
  and the compilation IR. It does not import another package's `_private`.
- `_private` is a mechanism. A cross-package import of `_private` is a boundary
  error.
- `relational` and `engines` have no authoring surface; their `public/` states
  that. `cli` is a leaf entry point and keeps the simple entry-point layout.
- A public function or class method carries a user-facing docstring with a
  runnable `Example:`. Internal and private functions carry only a developer
  docstring.

## Protocol adapters

Implementing another package's protocol is a separate, named file under
`internal/adapters/`:

| Adapter | Protocol |
| --- | --- |
| `table/internal/adapters/kernel_language.py` | `kernel.Language` |
| `topology/internal/adapters/kernel_language.py` | `kernel.Language` |
| `binding/internal/adapters/kernel_language.py` | `kernel.Language` |
| `modules/internal/adapters/core_module.py` | `kernel.Module` |
| `engines/internal/adapters/engine.py` | `engines.internal.Engine` |
| `code_generation/internal/adapters/provider.py` | `code_generation.internal.Provider` |

The adapter file names the protocol, imports the foreign protocol, and delegates
to `_private`. A protocol implementation buried in a model or factory file is a
boundary error.

## Packages

| Package | Public | Internal | Private |
| --- | --- | --- | --- |
| `kernel` | protocols, build pipeline, contract | no separate internal surface | ordering and composition |
| `types` | markers, unit constants, representative classes | logical type algebra, normalization, codecs | normalization, validation, codec, mapping |
| `expressions` | expression and selection API | model, operation specs, codecs, visitors, IR | coercion, literals, semantics, dispatch |
| `table` | `Table`, `Struct`, `Projection`, `Field`, sources | declaration access, row-source plans, data IR | descriptors, class creation, shape and plan algebra |
| `topology` | `Node`, `Edge`, categories, templates, properties | metadata, endpoint rules, component IR | class creation and property mechanics |
| `binding` | `node_binding`, `edge_binding`, values | binding model, validation, binding IR | factory mechanics |
| `relational` | none | engine-neutral plans, planner | planner implementation |
| `engines` | none | engine protocol, type IR | DuckDB lowering and service |
| `compile` | composition functions | blueprint aggregate, protocols, codecs | discovery, lowering, pipeline |
| `workflow` | `build`, runtime, report | contract assembly, executor, services, IR | identity, mapping, monitor |
| `modules` | registration, supplied modules | module protocol, registration, instruction IR | core, operators, targets |
| `code_generation` | request/run surface | provider contract, generated IR | engine, discovery, rendering, builtins |

## Languages

- `table` is the `data` language. It collects `Table`, `Struct`, `Projection`
  classes and `BoundSource` values.
- `topology` is the `topology` language. It collects `Node` and `Edge` classes.
- `binding` is the `binding` language. It requires `data` and `topology`.
- `expressions` contributes operation specs, not declarations.

`BuildBlueprint` is a compatibility aggregate assembled from the `data`,
`topology` and `binding` parts. Modules may read `context.blueprint` (legacy) or
`context.build.part(...)` (kernel).

## Operations

Each operation has one spec file under `expressions/internal/operations/` and
one lowering file under `engines/_private/duckdb/operators/`. A spec states name,
arity, parameters, result type and row effect. The expression IR stores only
name, arguments, parameters and logical type. The engine registry is keyed by
the same name. A custom operation is one spec plus one lowerer; no dispatcher
edits.

## Compatibility (Open Targets KG)

The effective API includes the older authoring forms:

- `Projection` without a pin and `projection_field(...)`.
- `pick(...)`, `where_present()`, `drop_null_items()`, `expand()`, `.append(...)`.
- `node_binding(rows=TableClass, ...)` as well as a row-source value.
- `value_expression`, `Nullable`, `NullableType`, `ArrayType`, `STR`, `FLOAT`.
- `BuildBlueprint` at `compile.models`.
- `workflow.models` and `modules.interfaces` module contract names.
- `code_generation.generation` and `code_generation.builtins`.

The package-root `interfaces.py`, `ir.py`, `models.py`, `language.py`,
`factories.py`, `compile/models.py`, `compile/interfaces.py`,
`workflow/{identity,interfaces,ir,models}.py`, `modules/{interfaces,_paths}.py`
and `modules/targets/...` files are compatibility shims for the Open Targets
project. They re-export the migrated zones; new framework code imports `pkg`,
`pkg.internal` or `pkg.internal.ir`.

These obligations are not the preferred model. Where they conflict with the
cleaner model, the conflict is recorded in `DESIGN_ISSUES.md`.
