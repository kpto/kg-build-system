# Design limits

The toolchain kernel and the distribution are implemented. These are the
remaining limits, not compatibility promises.

| Limit | Current choice |
| --- | --- |
| A toolchain is the only composition unit. | A caller composes a `Toolchain`, uses `default_toolchain`, or passes planners and executors to `compile` and `execute`. There is no registry. |
| DuckDB is the default emitter. | `DuckDbSqlEmitter` is the core planner's SQL library. Another engine supplies another emitter and executor. |
| A Python instruction is a reference. | `("python", "cpython")` carries `{module, qualname}`, not a live callable. |
| Public `GraphBlueprint` fields reference internal layer DTOs. | `GraphBlueprint` is public, but `graph`, `data`, `bindings` and `sources` are typed by layer DTOs that are not exported public names. |
| A language may publish only its layer value. | Publishing one `Definition` per declaration is allowed; publishing only the layer value is recorded as a limit. |
| An unregistered instruction kind is refused. | `execute` builds the exact-kind map before the first step and raises `ValueError` for a kind no executor claims. |
