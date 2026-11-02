# Design issues

The clean model and the effective API do not fully agree. Each item states the
conflict and the choice made for compatibility.

| # | Conflict | Choice |
| --- | --- | --- |
| 1 | `ExecutionContext` carries `services`, which makes a frozen data model hold live connections and loggers. | Keep `services` for compatibility with existing modules. The clean model passes services as a separate executor argument. |
| 2 | The kernel wants one `BuildIR`; existing modules read `CompilationContext.blueprint`. | Keep both: `build` for new modules, `blueprint` for existing ones. The blueprint is assembled from the language parts. |
| 3 | `Projection` without a pin plus `projection_field` is the effective API; a pinned projection is the cleaner model. | Support both. An unpinned projection derives its row plan from its output expressions; a pinned projection states it. |
| 4 | `rows=TableClass` is accepted by existing bindings; a row source value is the cleaner input. | Accept a declaration class and convert it to `row_source()`. |
| 5 | `where_present()`, `pick()`, `drop_null_items()`, `expand()` are effective; `alter_rows()`/`extract()` are cleaner. | Keep the old methods and implement both on the same operation specs. |
| 6 | `debug_name` participates in binding identity in the effective API, although it is display data. | Keep it in identity for compatibility; the blueprint fingerprint removes it as before. |
| 7 | The contract currently stores rendered SQL; an engine-neutral plan is the cleaner contract. | Keep rendered SQL for compatibility with core/target modules; isolate the renderer behind the engine interface so it can become neutral later. |
| 8 | `Module` is an ABC with `create_compiler`/`create_executor`; the kernel wants a simple protocol. | Keep the classmethod shape and align the protocol with it. |
| 9 | `Nullable` is an internal marker but is imported by effective code. | Export it from `types` and document it as an authoring marker. |
| 10 | `Table`/`Struct` are declaration classes but also logical-type markers. | Keep `Struct`/`Shape` in `types`; `Table` is a shape, not a value record. |
| 11 | `Semantics` annotations rely on `asdict()` payloads and `AnnotationIR.arguments` as frozen JSON. | Keep dataclass annotation payloads and `AnnotationIR`. |
| 12 | `TableGroup` source layout is a string template with `{table_name}`. | Keep the effective layout language. |
| 13 | `generation(...)` is executed at import and must validate a provider/config pair without observing. | Keep the inert request model; provider implementations may refuse at generation time, not at import. |
| 14 | The code-generation provider imports engine metadata helpers; that couples edit-time generation to DuckDB. | Keep `engines.interfaces` as the observer boundary; do not import the runtime executor. |
| 15 | The old topology stores metadata in untyped class dictionaries. | Keep a compatibility metadata view, but lower to typed `ComponentIR` at the language boundary. |
| 16 | `Projection` fields are class attributes evaluated at class creation; the clean model lowers fields to specs. | Keep class creation as the lowering point and store a frozen spec alongside the class. |
| 17 | `Table` and `Projection` are row sources at class level (`Table.row_source()`, `Projection.row_source()`), while the row-source algebra is a value model. | Keep the class methods as entry points; the algebra operates on values. |
| 18 | The old workflow assembler is a stateful mutable algorithm; the clean model is a fold of rules. | Preserve the algorithm's behavior while extracting values and rule functions. |
| 19 | The old module executor builds `StepOutcome` by hand in every module. | Keep the shape; allow a shared result helper without changing the contract. |
| 20 | Schema versions were removed from the effective model, but old artifacts may exist. | There is no migration path; compile again. |

## Findings from the clean reimplementation

| # | Finding | Decision |
| --- | --- | --- |
| 21 | The Open Targets declarations read `Field[str]` as non-null, while generated JSON contracts mark every member nullable in a header only. A single access rule cannot satisfy both by declaration alone. | Source access follows the declared type. Generated JSON contracts now render `Field[T | None]` for the `DEFAULTED` tier; the reference project was regenerated. |
| 22 | The author-facing `compile` function and the `kg_build_system.compile` package collide in Python's import machinery. | The package is callable (`__call__` delegates to `api.compile`) so both `from kg_build_system import compile` and `from kg_build_system.compile.models import ...` work. |
| 23 | `from kg_build_system import compile` may resolve to the package when the submodule was imported first. | `api._calling_namespace_path` skips frames inside the framework package, so the callable package still finds the author's file. |
| 24 | `PropertySlot` must be a runtime declaration object for class creation but an authoring-input union for typing. | It is a type alias `ValueInput[T] | NullableAuthoringInput[T]`; `property()` casts its declaration object to that alias. |
| 25 | `RowEffects.drop_null()` is meaningful only on nullable selections, but the effective API calls it on declared non-null fields. | Base `RowEffects` has no-op `drop_null()`/`expand()` spellings; concrete handles override them. |
| 26 | A custom operation needs an engine lowerer at compile time, but the engine is not a serialized contract fact. | `api.compile(..., engine=...)` passes the engine bundle through `CompilationContext`; the compiled SQL is the artifact. |
| 27 | `create_build`/`compile_build` prove the kernel, and a custom module executes through the workflow runtime; the default graph pipeline still routes through the graph-specific blueprint. | The kernel owns protocols and IR; workflow owns contract assembly and execution. This is the minimal split, not a second pipeline. |
| 28 | The target package and `modules.targets._relations` duplicate relation/storage adapters. | Kept local to targets; it is a compatibility boundary, not a shared model. |
| 29 | `code_generation` intentionally duplicates the DuckDB digest/metadata reads instead of importing `engines`. | Edit-time generation is a separate lane; the duplication keeps the generation path independent of the runtime engine. |
| 30 | Strict pyright over the generated/handwritten reference project reports unknown lambda types in `extract` calls. | The public typecheck fixture is strict; the reference project is an example tested by compile/build, not the typing gate. |
