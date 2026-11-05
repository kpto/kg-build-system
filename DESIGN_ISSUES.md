# Design limits

The toolchain kernel and the distribution are implemented. These are the
remaining limits, not compatibility promises.

| Limit | Current choice |
| --- | --- |
| A toolchain is the only composition unit. | A caller composes a `Toolchain`, uses `default_toolchain`, or passes planners and executors to `compile` and `execute`. There is no registry. |
| DuckDB is the default emitter. | `DuckDbSqlEmitter` implements the neutral `SqlEmitter` protocol from `distribution/service/internal`. The core planners consume that protocol and import no DuckDB module; another engine supplies another emitter and executor. |
| A Python instruction is a reference. | `("python", "cpython")` carries `{module, qualname}`, not a live callable. |
| Public `GraphBlueprint` fields reference internal language DTOs. | `GraphBlueprint` is public, but `graph`, `data`, `assets` and `bindings` are typed by language DTOs that are not exported public names. `BindingDTO` is shared by the blueprint and the core planners but is not exported from the interpreter facade. |
| A repeated struct graph name needs a qualified key. | A struct whose graph name repeats takes its qualified Python name as an extra key segment; the blueprint still names the struct by its graph role. |
| An unregistered instruction kind is refused. | `execute` builds the exact-kind map before the first step and raises `ValueError` for a kind no executor claims. |
| An asset layout is descriptive, not an access contract. | `AssetLayout` tells a compatible planner how to resolve a location; it opens no file and proves no relation exists. |
| There is no adapter registry. | A module contributes an ordinary relation-producing planner. `DuckDbSourcePlanner` handles `parquet`, `json` and `csv`; another format is another planner. |
