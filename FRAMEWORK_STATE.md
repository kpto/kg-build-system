# Framework state

This is the reviewer briefing for the clean reimplementation. The legacy tree is
at `legacy/kg_build_system` (ignored, untracked) and its tests are archived at
`/tmp/opencode/legacy-tests`.

## At a glance

- The kernel is domain-agnostic: `Language`, `Module`, `BuildIR`, `Registry`,
  contract values. Importing `kg_build_system.kernel` loads no language, workflow
  or engine package.
- `table`, `topology` and `binding` are languages. `core` is a module. `engines`
  owns code generation. `workflow` owns contract assembly and execution.
- Every subpackage has `public/`, `internal/` and `_private/`; `__init__.py` is a
  facade over `public`.
- Every public function or method is a thin wrapper over a private
  implementation, with a user docstring and an `Example:` block.
- Every operation has one spec file in `expressions/internal/operations/` and one
  lowering file in `engines/_private/duckdb/operators/`.
- A custom operation is one `OperationSpec` plus one engine lowerer. A custom
  language and module compile and execute without the default distribution.
- Verification: **27 tests**, pyright **0 errors**, Open Targets KG **6 tests**,
  and the reference project compiles and builds with file, meta-graph and Neo4j
  outputs.

## Architecture

```text
kernel
  language.py     Language, LanguageContext, Namespace
  module.py       Module, ModuleCompiler, ModuleExecutor
  build.py        BuildIR, Build
  registry.py     Registry, language ordering
  contract.py     steps, contributions, executions, outcomes

types -> expressions -> relational -> engines
                    \-> table / topology -> binding
compile -> languages + modules + workflow
workflow -> kernel.contract, engines.interfaces, _relations
modules -> languages, compile, workflow, engines
code_generation -> types, engines (observer only)
```

Each domain package exposes `__init__.py`, `public/`, `internal/` (with `ir.py`)
and `_private/`. Protocol implementations live in `internal/adapters/`.
`relational` and `engines` have an empty `public/`; `cli` is a leaf entry point.

## Compatibility

The effective Open Targets KG API works unchanged: old projection spelling,
`where_present`/`pick`/`drop_null_items`/`expand`, `rows=TableClass`,
`value_expression`, `BuildBlueprint` at `compile.models`, `workflow.models`
module contract and the custom semantics module.

The reference project used the newer spelling and was regenerated so source
nullability is declared: `Field[T | None]` for defaulted sources, `Field[T]` for
required/declared sources.

## Design issues

See `DESIGN_ISSUES.md`. The material ones:

- `ExecutionContext.services` remains for module compatibility.
- The contract still stores rendered SQL; a neutral plan is the cleaner model.
- `compile` is both a public function and a package; the package is callable.
- Source access follows the declaration, not a global nullable rule.
- Strict pyright covers the framework and the public authoring fixture, not the
  generated reference project.

## Verification commands

```console
uv run pytest -q
uv run pyright
uv run mkdocs build --strict
cd ~/Repos/opentargets-kg && uv run pytest -q
```
