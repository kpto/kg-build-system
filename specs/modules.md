# Modules

## Responsibility

The `modules` package owns the public module extension contract, module registration, the mandatory core module, the supplied operator and target modules, and the composition vocabulary those modules share.

## Public API

Names are defined in `modules.public`; `kg_build_system.modules` exposes only that package.

- `Module` is the extension base (`modules.internal`); `modules` exports registration and the supplied modules.
- `ModuleRegistrationConfiguration` is a frozen, slotted dataclass base for serialisable registration configuration. `to_json()` returns `dataclasses.asdict(self)`; a subclass may override it.
- `Module(ABC)`:
  - `ID: ClassVar[str]`
  - `VERSION: ClassVar[str]`
  - `CONFIGURATION_TYPE: ClassVar[type[Any]]`
  - `async create_compiler(context: CompilationContext[Any]) -> ModuleCompiler`
  - `create_executor(context: ExecutorFactoryContext) -> ModuleExecutor`
- `ModuleRegistration[ConfigT](module_class, configuration)` rejects a configuration that is not an instance of `module_class.CONFIGURATION_TYPE`.
- `register_module(module_class, configuration=None) -> ModuleRegistration`; with no configuration it constructs `module_class.CONFIGURATION_TYPE()`.
- `module_configuration_json(configuration) -> Any` returns the configuration's JSON-compatible form.
- Built-in exports from `kg_build_system.modules`:
  - `CollapseExactDuplicatesModule`
  - `MergeCompatibleFactsModule`, `MergeCompatibleFactsModuleConfiguration`
  - `RejectConflictingNonNullValuesConfiguration`, `RejectConflictingNonNullValuesModule`
  - `FileModule`, `FileModuleConfiguration`
  - `MetaGraphModule`, `MetaGraphModuleConfiguration`
  - `Neo4jModule`, `Neo4jModuleConfiguration`
  - `ModuleRegistration`, `ModuleRegistrationConfiguration`, `register_module`
- Target classes are loaded lazily on first attribute access, so importing `kg_build_system.modules` does not import DuckDB or a target.
- Core module: `CoreModule` and `CoreConfiguration` are in `modules.internal.adapters.core_module`; `CoreArtifactTypes`, `graph_record_components`, `CoreCompiler` and `CoreExecutor` are private in `modules._private.core`. The composition root imports `CoreModule` from the adapter.

## Internal interface

`modules.internal` exposes:

- `Module`, `ModuleRegistration`, `ModuleRegistrationConfiguration`, `register_module`, `module_configuration_json`.
- `ModuleCompiler` through the `compile.internal` protocol.
- `CompilationContext`, `ExecutorFactoryContext`, `ModuleExecutor` through the kernel contract.
- The kernel `Module` protocol is implemented by `modules.internal.adapters.core_module`; the core compiler, executor and plan stay private in `modules._private.core`.

`modules.internal.ir` aggregates module-produced instruction IR:

- Core instructions: `CoreInstructionIR`, `CoreStepInstructionIR`, `SourceRelationInstructionIR`, `RelationInstructionIR`, `AggregateInstructionIR`, `DeclaredColumnIR`, `DeclaredPathIR`; `encode_core_instruction`, `decode_core_instruction`, `encode_declared_column`, `declared_column_type`.
- Target instructions are re-exported lazily: Neo4j and meta-graph IR values and codecs.
- A module instruction is frozen data with an `action` discriminator and payload; it carries no behaviour or owner.

Invariants:

- A module class declares non-empty `ID`, `VERSION` and `CONFIGURATION_TYPE`; `create_compiler` is async; `create_executor` is synchronous.
- A registration holds a module class and a serialisable, non-secret configuration. It never holds a Python instance of the module.
- A contribution's steps use the kernel contract; its own instruction data lives in `variables`.
- Core instruction decoding refuses an unknown action and unknown fields.
- Module IDs are lower-case identifiers in the workflow contract.

## IR

`modules.internal.ir` owns the aggregate module-instruction surface.

- `SourceRelationInstructionIR(relation, location, format, credential_reference=None, declaration="", declared_columns=(), declared_paths=())`.
- `RelationInstructionIR(relation, sql)`.
- `AggregateInstructionIR(relation)`.
- `DeclaredColumnIR(name, logical_type)` stores the logical type in JSON form; `DeclaredPathIR(schema_path, logical_path)`.
- `encode_core_instruction` returns a frozen JSON value; `decode_core_instruction` returns the typed instruction.
- Target instruction IR is owned by its target implementation in `modules._private.targets` and re-exported through `modules.internal.ir`.
- Module IR carries no schema version; unknown fields are refused.

## Boundaries

- Surfaces: `kg_build_system.modules` exposes only `modules.public`; `modules.public` is the author-facing registration and supplied-module surface; `modules.internal` is the module protocol and configuration interface; `modules.internal.ir` aggregates module-produced IR; mechanisms are in `modules._private`. `modules.interfaces` is a compatibility shim.
- Allowed dependencies: `kernel`, and the `internal` and `internal.ir` surfaces of `types`, `annotations`, `expressions`, `table`, `topology`, `binding`, `relational`, `engines`, `compile` and `workflow`, plus `_frozen_json`.
- Must not import `api` or `cli`.
- A module compiler may inspect the build/blueprint and its own registration configuration. It may not receive authoring classes, a runtime connection or executor state.
- A module executor receives the compiled module definition, step, variables, resolved runtime configuration, inputs and `ExecutionServices` through the context.
- `compile` and `workflow` never import a concrete module; the composition root and `kg_build_system.modules` own that dependency.

## Current decisions

- **One module ID, one configured instance.** A module ID is the semantic namespace for its steps, openings, artifact types, runtime configuration and owned annotations. A workflow contains at most one configured instance of an ID.
- **Registration is compile-time.** A registration holds a module class and a serialisable, non-secret configuration. The blueprint records import coordinates and the configuration, never a Python object. Compilation reconstructs the registration and imports the class; the executor checks the class's `ID` and `VERSION`.
- **Reference is execution-time configuration.** `ModuleReference` carries the module ID, import module, class qualname, implementation version and the configuration the module's compiler chose for execution. It must not be assumed to equal the registration configuration; the module owns that mapping. `implementation_version` is checked against the class's `VERSION` at execution.
- **Runtime configuration is separate.** A module may declare `RuntimeFieldDefinition`s for settings supplied at build time. A field has `key`, `description`, `required`, `value_type` (`"string"`, `"integer"`, `"number"`, `"boolean"` or `"json"`) and `secret`. `BuildRuntime.module_configuration` holds values keyed by module ID and field key. The contract records the definitions, not the values. Unknown, missing required or wrongly typed values stop the build before any step runs.
- **Compiler protocol.** `CompilationContext` exposes the build, the blueprint compatibility view, the module ID, the reconstructed registration configuration and the engine. `create_compiler` returns a `ModuleCompiler`; `compile` returns one `WorkflowContribution` containing the module definition, its steps and its opaque variables.
- **Executor protocol.** `create_executor` is called once per module with `ExecutorFactoryContext`; the result handles every step of that module. It receives `variables` once. `handle` runs only when every connected producer succeeded or warned. `handle_disrupted` runs when any connected producer failed or was skipped; the base implementation returns `SKIPPED`. Services are on the execution context for compatibility.
- **Steps and openings.** `WorkflowStep` carries `inputs`, `outputs`, optional `name` and `assembly_preference` (`"eager"` or `"deferred"`). An `Input` takes one artifact of its type. An `Output` gives one artifact that something must read. A `Publication` gives one artifact to the build and is exempt from the read requirement. An opening's name defaults to `input` or `output`; a step name defaults to `step{N}` within its module. Names are unique among siblings.
- **Open inputs.** An `Input` whose type has `*` in either half is open. It expands into one taken input per type actually written by an output in the build, each fed by one output; it may match none. The step receives every matched artifact together under the declared input name. Outputs and publications must name one concrete type.
- **Assembly guarantees.** A module may rely on every input being fed and every non-publication output being read before a contract exists. An input has exactly one feeder; an output may have many readers; no step reads what it writes and no connection closes a cycle. A module states a type, not a producer. Two indistinguishable producers leave the workflow unassembled, and an unconsumed output fails compilation with the unread opening named.
- **Module order is priority.** Registration order is the author's priority order, and the public API appends core after the supplied modules. Rank is derived from that order, then eagerness, then step position; higher rank means earlier. Rank only chooses which writer an input takes; it does not schedule execution. A module that needs a specific producer states a type only that producer writes.
- **Disruption and outcome.** A failed or skipped producer reaches a reader as a `DisruptingInput`; a succeeded or warned producer reaches it as a `ContinuableInput`. A module may recover, warn, publish or fail deliberately. An exception becomes a `FAILED` outcome. Outcomes must answer the requested step and module, artifacts may appear only on declared outputs or publications, and each artifact's type must equal its declared type. A step may omit a declared artifact.
- **Relation service.** Executors use the synchronous `RelationService` for `reference`, lazy `view`, opt-in `materialize`, read-only `query`, `export_parquet` and `register_filesystem`. The service returns `RelationRef` values that name public views; a materialised relation hides its private backing table behind that view. The service owns identifier handling and checkpoint policy; modules never receive the raw connection or the storage/compression configuration.
- **Annotations.** Topology annotations are canonical graph metadata carried in `ComponentIR.annotations`; they are not target configuration. Core preserves them. `NodeLabel` and `EdgeLabel` are the matching-kind semantic labels; at most one matching-kind label may be effective on a component. `modules._labels.semantic_label(component)` returns that label or the component's logical name and validates the serialised annotation shape.
- **Core module.** `CoreModule` (`ID="core"`, `VERSION="3"`) is mandatory in the public API and is composed last. It declares source, row-source, projection, binding and aggregation steps:
  - source steps expose widened source relations and report declared-null statistics;
  - row-source steps define derived relations from their canonical plans;
  - projection steps define lazy projection relations;
  - binding steps evaluate binding expressions into guarded binding relations;
  - aggregation steps combine all bindings of one bound component into `core/graph.<kind>.<component>`.
  Abstract categories are not record producers and get no aggregation step.
- **Supplied modules.**

| Module | ID / version | Configuration | Behaviour |
| --- | --- | --- | --- |
| `CoreModule` | `core` / `3` | none | Materialises the core pipeline and graph records. |
| `CollapseExactDuplicatesModule` | `collapse_exact_duplicates` / `1` | none | Drops exact duplicate rows per bound record component; outputs the same graph-record types. |
| `MergeCompatibleFactsModule` | `merge_compatible_facts` / `1` | `components: tuple[concrete Node \| Edge, ...] \| None = None` | Groups records by `build_key`, keeping the minimum value of each copied column; `None` covers every bound component. |
| `RejectConflictingNonNullValuesModule` | `reject_conflicting_non_null_values` / `1` | `fail_on_error: bool = True` | Finds more than one distinct non-null value per key and property; publishes a report and forwards records under `.validated` when it continues. |
| `FileModule` | `file` / `1` | `relative_path: str` (required) | Writes sorted JSON Lines for `core/graph.*`; runtime field `relative_path` may override the path; publishes `file/write_result`. |
| `MetaGraphModule` | `meta_graph` / `2` | `relative_path="meta_graph.json"`, `example_limit=3`, `include_html=True`, `html_relative_path="meta_graph.html"` | Consumes `core/graph.*`; writes the effective-topology JSON and optional self-contained HTML; publishes `meta_graph/meta_graph_document`. |
| `Neo4jModule` | `neo4j` / `2` | `relative_directory="neo4j-import"`, `script_name="import_neo4j.py"`, `default_database="neo4j"` | Exports one Parquet file per bound node and edge, writes an import script and publishes `neo4j/import_bundle`; runtime field `relative_directory` may override the directory. |

- **Target capabilities are module decisions.** `Neo4jModule` accepts `bool`, `int`, `float`, `str`, `date`, `time` and `timestamp` properties and arrays of `bool`, `int`, `float` and `str`; it refuses `uuid`, temporal arrays, nested shapes, reserved import-field names and edges whose declared endpoints are not bound concrete nodes. `FileModule` and `MetaGraphModule` use canonical value text for temporal and UUID values.
- **Custom distribution.** A custom language and module compile and execute through `compile.create_build`, `compile.compile_build` and `workflow.build` without the default modules. A graph build is one distribution, not the kernel.
