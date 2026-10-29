# modules

## Responsibility

The `kg_build_system.modules` package owns the public module extension contract, module registration, the built-in workflow modules, and the composition vocabulary those modules share.

## Public interface

- `ModuleRegistrationConfiguration` is a frozen, slotted dataclass base for serialisable registration configuration. `to_json()` returns `dataclasses.asdict(self)`; a subclass may override it.
- `Module(ABC)`:
  - `ID: ClassVar[str]`
  - `VERSION: ClassVar[str]`
  - `CONFIGURATION_TYPE: ClassVar[type[Any]]`
  - `async create_compiler(context: CompilationContext[Any]) -> ModuleCompiler`
  - `create_executor(context: ExecutorFactoryContext) -> ModuleExecutor`
- `ModuleRegistration[ConfigT](module_class: type[Module], configuration: ConfigT)`.
  - Rejects a configuration that is not an instance of `module_class.CONFIGURATION_TYPE` with `TypeError`.
- `register_module(module_class: type[Module], configuration: ModuleRegistrationConfiguration | None = None) -> ModuleRegistration[Any]`.
  - With no configuration, constructs `module_class.CONFIGURATION_TYPE()`; a configuration type whose required field has no default therefore raises `TypeError`.
- Compile protocol in `compile.interfaces`:
  - `CompilationContext[ConfigT](blueprint, module_id, configuration)`.
  - `ModuleCompiler.compile(context: CompilationContext[Any]) -> WorkflowContribution` (async).
  - `CompilableModule` with `ID`, `VERSION`, `CONFIGURATION_TYPE`, and async `create_compiler`.
  - `CompileModuleRegistration[ConfigT]` with `module_class` and `configuration`.
- Runtime protocol in `workflow.interfaces`:
  - `ModuleExecutor.handle(context: ExecutionContext) -> StepOutcome`.
  - `ModuleExecutor.handle_disrupted(context: DisruptedExecutionContext) -> StepOutcome`; the base implementation skips the step.
  - `ExecutableModule` with `ID`, `VERSION`, and `create_executor`.
- Built-in exports from `kg_build_system.modules`:
  - `CollapseExactDuplicatesModule`
  - `MergeCompatibleFactsModule`, `MergeCompatibleFactsModuleConfiguration`
  - `RejectConflictingNonNullValuesConfiguration`, `RejectConflictingNonNullValuesModule`
  - `FileModule`, `FileModuleConfiguration`
  - `MetaGraphModule`, `MetaGraphModuleConfiguration`
  - `Neo4jModule`, `Neo4jModuleConfiguration`
  - `Module`, `ModuleRegistration`, `ModuleRegistrationConfiguration`, `register_module`
- Core workflow vocabulary is in `modules.core`: `CoreModule`, `CoreArtifactTypes`, and `graph_record_components`. These names are not re-exported from `kg_build_system.modules`; the composition root imports `CoreModule` from `modules.core`.
- `CoreArtifactTypes` names:
  - `core/graph.<kind>.<component>` for graph records;
  - `core/binding.<symbol_id>` for a lowered binding;
  - `core/data.table.<name>` for a source table;
  - `core/data.projection.<name>` for a projection;
  - `core/data.row_source.<key>` for a derived row source.

## Boundaries

- Allowed dependencies: `types`, `annotations`, `expressions`, `table`, `topology`, `binding`, `relational`, `engines`, `compile`, `workflow`, and the private `_frozen_json` kernel.
- The current built-ins use `engines.duckdb`, `compile.interfaces`, `workflow.models`, `workflow.identity`, `workflow.interfaces`, `workflow.services`, and `topology.ir`.
- Must not import `api` or `cli`.
- A module compiler may inspect the compiled blueprint and its own registration configuration. It may not receive authoring classes, a runtime connection, or executor state.
- A module executor receives only the compiled module definition, step, variables, resolved runtime configuration, inputs, and `ExecutionServices`.
- `compile` and `workflow` must not import a concrete module; the composition root and the `modules` package own that downward dependency.

## Current decisions

- **One module ID, one configured instance.** A module ID is the semantic namespace for its steps, openings, artifact types, runtime configuration, and owned annotations. Module IDs, runtime field keys, and artifact namespaces are lower-case with underscores where the workflow contract validates them. A workflow contains at most one configured instance of an ID.
- **Registration is compile-time.** A registration holds a module class and a serialisable, non-secret configuration. The blueprint records import coordinates and the configuration, never a Python object. Compilation reconstructs the registration, verifies the class ID, and rejects a class that cannot be imported as a top-level class.
- **Reference is execution-time configuration.** `ModuleReference` carries the module ID, import module, class qualname, implementation version, and the configuration the module's compiler chose for execution. It must not be assumed to equal the registration configuration; the module owns that mapping. `implementation_version` is checked at execution against the class's `VERSION`.
- **Runtime configuration is separate.** A module may declare `RuntimeFieldDefinition`s for settings supplied at build time. A field has `key`, `description`, `required`, `value_type` (`"string"`, `"integer"`, `"number"`, `"boolean"`, or `"json"`), and `secret`. `BuildRuntime.module_configuration` holds values keyed by module ID and field key. The contract records the definitions, not the values. Unknown, missing required, or wrongly typed values stop the build before any step runs. A `secret` field is never written to module variables, artifacts, manifests, or fingerprints.
- **Compiler protocol.** `CompilationContext` exposes the blueprint, the module ID, and the reconstructed registration configuration. `create_compiler` returns a `ModuleCompiler`; `compile` returns one `WorkflowContribution` containing the module definition, its steps, and its opaque variables. The contribution's module ID must match the blueprint entry. Contribution order is preserved and becomes the module order used by assembly.
- **Executor protocol.** `create_executor` is called once per module with `ExecutorFactoryContext`; the resulting `ModuleExecutor` handles every step of that module. It receives `variables` once. `handle` runs only when every connected producer succeeded or warned. `handle_disrupted` runs when any connected producer failed or was skipped; its base implementation returns `SKIPPED`, and a module opts into that policy by calling `super().handle_disrupted(context)`.
- **Steps and openings.** `WorkflowStep` carries `inputs`, `outputs`, optional `name`, and `assembly_preference` (`"eager"` or `"deferred"`). An `Input` takes one artifact of its type. An `Output` gives one artifact that something must read. A `Publication` gives one artifact to the build and is exempt from the read requirement. An opening's name is optional and defaults to `input` or `output`; a step name defaults to `step{N}` within its module. Names are unique among siblings.
- **Open inputs.** An `Input` whose type has `*` in either half is open. It expands into one taken input per type actually written by an output in the build, each fed by one output; it may match none. The step receives every matched artifact together under the declared input name. Outputs and publications must name one concrete type.
- **Assembly guarantees.** A module may rely on every input being fed and every non-publication output being read before a contract exists. An input has exactly one feeder; an output may have many readers; no step reads what it writes and no connection closes a cycle. A module states a type, not a producer. Two indistinguishable producers leave the workflow unassembled, and an unconsumed output fails compilation with the unread opening named.
- **Module order is priority.** Registration order is the author's priority order, and the public API appends core after the supplied modules. Rank is derived from that order, then eagerness, then step position; higher rank means earlier. Rank only chooses which writer an input takes; it does not schedule execution. A module that needs a specific producer states a type only that producer writes.
- **Disruption and outcome.** A failed or skipped producer reaches a reader as a `DisruptingInput`; a succeeded or warned producer reaches it as a `ContinuableInput`. A module may recover, warn, publish, or fail deliberately. An exception becomes a `FAILED` outcome. Outcomes must answer the requested step and module, artifacts may appear only on declared outputs or publications, and each artifact's type must equal its declared type. A step may omit a declared artifact.
- **Relation service.** Executors use the synchronous `RelationService` for `reference`, lazy `view`, opt-in `materialize`, read-only `query`, `export_parquet`, and `register_filesystem`. The service returns `RelationRef` values that name public views; a materialised relation hides its private backing table behind that view. The service owns identifier handling and checkpoint policy; modules never receive the raw connection or the storage/compression configuration.
- **Annotations.** Topology annotations are canonical graph metadata carried in `ComponentIR.annotations`; they are not target configuration. Core preserves them and includes them in the blueprint. A module may interpret the annotations it supports. There is no central annotation policy. `NodeLabel` and `EdgeLabel` are the matching-kind semantic labels; at most one matching-kind label may be effective on a component. `modules._labels.semantic_label(component)` returns that label or the component's logical name and validates the serialised annotation shape.
- **Core module.** `CoreModule` is mandatory in the public API and is composed last. It declares source, row-source, projection, binding, and aggregation steps. Source steps expose widened source relations and report declared-null statistics; row-source and projection steps define lazy relations; binding steps evaluate binding expressions into binding relations; aggregation steps combine all bindings of one bound component into `core/graph.<kind>.<component>`. Abstract categories are not record producers and therefore get no aggregation step.
- **Built-in modules.** The supplied modules are ordinary modules with no privileged scheduling role:

| Module | ID / version | Configuration | Behaviour |
| --- | --- | --- | --- |
| `CoreModule` | `core` / `3` | none | Materialises the core pipeline and graph records. |
| `CollapseExactDuplicatesModule` | `collapse_exact_duplicates` / `1` | none | Drops exact duplicate rows per bound record component; outputs the same graph-record types. |
| `MergeCompatibleFactsModule` | `merge_compatible_facts` / `1` | `components: tuple[concrete Node \| Edge, ...] \| None = None` | Groups records by `build_key`, keeping the minimum value of each copied column; `None` covers every bound component. Outputs the same graph-record types. |
| `RejectConflictingNonNullValuesModule` | `reject_conflicting_non_null_values` / `1` | `fail_on_error: bool = True` | Finds more than one distinct non-null value per key and property; publishes `reject_conflicting_non_null_values/report`; forwards records under `.validated` when it continues. |
| `FileModule` | `file` / `1` | `relative_path: str` (required) | Writes sorted JSON Lines for `core/graph.*`; runtime field `relative_path` may override the path; publishes `file/write_result`. |
| `MetaGraphModule` | `meta_graph` / `2` | `relative_path="meta_graph.json"`, `example_limit=3`, `include_html=True`, `html_relative_path="meta_graph.html"` | Consumes `core/graph.*`; writes the effective-topology JSON and optional self-contained HTML; publishes `meta_graph/meta_graph_document`. |
| `Neo4jModule` | `neo4j` / `2` | `relative_directory="neo4j-import"`, `script_name="import_neo4j.py"`, `default_database="neo4j"` | Exports one Parquet file per bound node and edge, writes an import script, and publishes `neo4j/import_bundle`; runtime field `relative_directory` may override the directory. |

- **Target capabilities are module decisions.** `Neo4jModule` accepts `bool`, `int`, `float`, `str`, `date`, `time`, and `timestamp` properties and arrays of `bool`, `int`, `float`, and `str`; it refuses `uuid`, temporal arrays, nested shapes, reserved import-field names, and edges whose declared endpoints are not bound concrete nodes. `FileModule` and `MetaGraphModule` use canonical value text for temporal and UUID values. These checks belong to the module, not to the core graph model.
