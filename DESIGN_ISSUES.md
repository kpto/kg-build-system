# Design limits

The model/service layout is implemented. These are the remaining limits, not
compatibility promises.

| Limit | Current choice |
| --- | --- |
| Capability modules are deferred. | `Capability` exists in `kernel`, but `Module` does not declare `requires`/`provides`; module composition does not enforce capability requirements. |
| DuckDB is the default emitter. | `DuckDbSqlEmitter` is the default SQL library. It is not a capability module; another engine supplies another emitter. |
| A Python binding source is a reference. | The blueprint stores `PythonRefDTO(module, qualname, signature)`, not the callable body. Source rendering reproduces the reference. |
| Some target executors still adapt instructions into `variables`. | The build target adapter copies the step's instruction payload into `variables["instructions"]` before calling executors that predate step-owned instructions. |
| Public `GraphBlueprint` fields reference internal layer DTOs. | `GraphBlueprint` is public, but `graph`, `data`, `bindings` and `sources` are typed by layer DTOs that are not exported public names. |
