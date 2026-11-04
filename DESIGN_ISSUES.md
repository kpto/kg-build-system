# Design limits

The toolchain kernel and the distribution are implemented. These are the
remaining limits, not compatibility promises.

| Limit | Current choice |
| --- | --- |
| A toolchain is the only composition unit. | A caller composes a `Toolchain`, uses `default_toolchain`, or passes planners and executors to `compile` and `execute`. There is no registry. |
| DuckDB is the default emitter. | `DuckDbSqlEmitter` is the core module's SQL library. Another engine supplies another emitter and executor. |
| A Python instruction is a reference. | `("python", "cpython")` carries `{module, qualname}`, not a live callable. |
| Public `GraphBlueprint` fields reference internal language DTOs. | `GraphBlueprint` is public, but `graph`, `data`, `bindings` and `sources` are typed by language DTOs that are not exported public names. |
| A repeated struct graph name needs a qualified key. | A struct whose graph name repeats takes its qualified Python name as an extra key segment; the blueprint still names the struct by its graph role. |
| An unregistered instruction kind is refused. | `execute` builds the exact-kind map before the first step and raises `ValueError` for a kind no executor claims. |
