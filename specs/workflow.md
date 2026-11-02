# Workflow

## Responsibility

The `workflow` package owns workflow declaration values, step assembly, the frozen execution contract, workflow execution, runtime services and execution monitoring.

## Public API

- Author-facing surface (`kg_build_system.workflow`): `build`, `BuildRuntime`, `WorkflowReport`.
- `build(contract: WorkflowContractIR, runtime: BuildRuntime | None = None, *, output_directory="build", working_directory="_workdir", temporary_directory=None, monitor=None) -> WorkflowReport`.
- `BuildRuntime(credentials={}, module_configuration={}, output_directory=Path.cwd()/"build", working_directory=Path("_workdir"), temporary_directory=None, duckdb_storage="memory", duckdb_threads=None, duckdb_memory_limit=None, duckdb_compression=True)`.
  - A relative `working_directory` is resolved beneath `output_directory`.
- `WorkflowReport(published_artifacts, recovered_failures, unresolved_failures, provenance)`.
  - `succeeded` is true when `unresolved_failures` is empty.

## Internal interface

`workflow.interfaces` exposes:

- Declaration and assembled models: `ArtifactType`, `Input`, `Output`, `Publication`, `Given`, `WorkflowStep`, `WorkflowContribution`, `ModuleReference`, `RuntimeFieldDefinition`, `ModuleDefinition`, `TakenInput`, `DefinedStep`, `DefinedContribution`, `Connection`, `WorkflowDefinition`.
- Kernel contract values re-exported for module authors: `Artifact`, `ArtifactType`, `CompilationContext`, `ContinuableInput`, `DisruptedExecutionContext`, `DisruptingInput`, `ExecutionContext`, `ExecutorFactoryContext`, `Failure`, `PublishedArtifact`, `StepOutcome`, `StepStatus`, `type_matches`.
- Assembly and contract: `assemble_workflow`, `AssemblyError`, `create_workflow_contract`.
- Mapping: `workflow_to_ir`, `workflow_from_ir`, `type_to_ir`, `type_from_ir`.
- Identity: `step_name`, `input_name`, `output_name`, `step_identity`, `opening_identity`, `expanded_input_name`, `type_text` and the default-name constants.
- Execution protocols: `ModuleExecutor` (ABC with `handle(context)` and `handle_disrupted(context)`), `ExecutableModule` (`ID`, `VERSION`, `create_executor(context)`).
- Services: `RelationRef`, `RelationQueryResult`, `RelationService`, `ExecutionServices`, `WorkflowLogger`, `WorkingStorage`, `CredentialResolver`, with in-process implementations `LocalWorkingStorage`, `LocalTemporaryStorage`, `MappingCredentialResolver`.
- Monitoring: `WorkflowExecutionMonitor`, `NullWorkflowMonitor`, `RichWorkflowMonitor`.
- Contract IR and codecs: `WorkflowContractIR`, `encode_workflow_contract`, `decode_workflow_contract`, `workflow_contract_json`, `workflow_contract_from_json`, `workflow_contract_to_json`.

Invariants:

- `WorkflowDefinition(contributions, connections=())` stores only the assembled contributions and the generated identities of connected openings. `modules`, `steps_by_module` and `variables_by_module` are derived.
- An assembled step holds its name, taken inputs, outputs and publications. No value holds an owner reference, a closure, a live service or a derived identity.
- `ExecutionContext` and `DisruptedExecutionContext` carry the module definition, step, module and step IDs, variables, runtime configuration, inputs and `services`. The `services` field is the compatibility bridge to the runtime; see `../DESIGN_ISSUES.md` item 1.
- `ModuleExecutor.handle` handles a step whose producers succeeded or warned. `handle_disrupted` defaults to `SKIPPED`.
- `BuildRuntime.module_configuration` is keyed by module ID and then runtime field key; values are not stored in the contract.

## IR

- `workflow.ir` uses frozen pydantic models with `extra="forbid"` and `strict=True`.
- `WorkflowContractIR(workflow, workflow_fingerprint, provenance=None)`.
- `WorkflowDefinitionIR(contributions, connections=())`; at least one contribution.
- `ContributionIR(reference, runtime_fields=(), variables=None, steps)`; at least one step.
- `ModuleReferenceIR(module_id, import_module, class_qualname, implementation_version, configuration=None)`.
- `RuntimeFieldIR`, `ArtifactTypeIR`, `InputIR`, `OutputIR`, `PublicationIR`, `StepIR`, `ConnectionIR`.
- `encode_workflow_contract`/`decode_workflow_contract` convert between the model and JSON-compatible mappings; `workflow_contract_json`/`workflow_contract_from_json` handle JSON text. `workflow_contract_to_json` aliases `workflow_contract_json`.
- Module IDs, artifact namespaces and runtime field keys are pattern-constrained lowercase identifiers. There is no schema version.

## Boundaries

- Surfaces: `workflow.ir` is the contract IR; `workflow.interfaces` is the internal interface; `kg_build_system.workflow` is the author-facing surface.
- Allowed dependencies: `kernel`, `engines.interfaces`, `_relations` and `_frozen_json`.
- Must not import `compile`, `modules`, `binding`, `table`, `topology`, `expressions`, `relational`, `code_generation`, `api` or `cli`.
- Workflow domain models never retain IR objects. `workflow.ir` is the serialisable form used only at the contract boundary; executors receive workflow models.
- The executor imports module classes only through the compiled `ModuleReference` import coordinates. The contract stores no Python class.
- Execution context holds data; the runtime passes `ExecutionServices` on the context for compatibility.

## Current decisions

- **The model is frozen and anaemic.** A step holds its inputs, outputs, name and assembly preference. An opening holds a type and an optional name. Nothing holds an owner reference, a derived identity or a closure. Per-step instruction data belongs to the contributing module's `variables`.
- **Identity is generated from names.** A step is `module_id::step_name`; an input or output is `<step_identity>.<opening_name>`. The assembled definition stores these identities in connections. No declared model stores one.
- **Open inputs.** `Input` is open when either half of its `ArtifactType` contains `*`. The assembler expands it into one `TakenInput` per matching type actually written by some output, each named `<declared_name>:<namespace>.<name>`. A non-pattern input is always answered with the one type it names, even when nothing writes it, so the missing writer is reported. Outputs and publications cannot be patterns. At execution an open input's several artifacts arrive together under the declared `input_name`.
- **Default names.** An unnamed step is `step{N}` within its module; an unnamed input is `input`; an unnamed output or publication is `output`. A name must be unique among its siblings. A duplicate step name, duplicate opening name, duplicate module ID or pattern on an output/publication raises `AssemblyError`.
- **Rank.** Rank orders steps by module contribution order, then eager before deferred, then step position within the module; the earlier of two steps has the greater rank. The public API appends core after the supplied modules, so core has the lowest rank. Rank chooses which writer an input takes; it never gates a step, refuses a connection or determines execution order.
- **Two assembly passes.** The assembler first repeatedly makes every connection that holds for any valid wiring: an unfed input with exactly one admissible writer, or an unread `Output` with exactly one admissible unfed reader. It then scans inputs in rank order and makes the first connection its rules justify, restarting after each connection. A candidate that would close a cycle is never admissible. A writer that may yet turn out to take the type it writes defers a conclusion. Otherwise the latest step that both takes and writes the type before the input wins; a single producer is accepted; multiple indistinguishable producers are indeterminate.
- **Completeness.** A workflow assembles only when every input is fed and every `Output` is read. A `Publication` is exempt because it has no reader inside the workflow. Otherwise `assemble_workflow` raises `AssemblyError` explaining every unsettled input in assembly order and every unread output; it does not return a partial definition.
- **Cardinality.** An input takes exactly one feeder. An output may have any number of readers and at least one unless it is a publication. No connection joins a step to itself and no connection closes a cycle.
- **Contract.** The assembled `WorkflowDefinition` is mapped to IR and frozen into `WorkflowContractIR`. `workflow_fingerprint` is the SHA-256 of the serialised workflow IR, so any change to contribution order, step name, opening name, type, module data or connection changes the fingerprint. Provenance is opaque JSON attached by the compiler; the contract carries only workflow semantics and provenance.
- **Execution is a wavefront.** Each round runs every pending step whose connected producers have all completed. If no pending step is ready, execution raises `RuntimeError("workflow has a dependency cycle")`. A ready step's inputs are grouped by `TakenInput.input_name`; each connected artifact is classified by its producer's final status.
- **Disruption.** If any connected producer failed or was skipped, the step receives `DisruptedExecutionContext` and `handle_disrupted(context)`; otherwise it receives `ExecutionContext` and `handle(context)`. The base disrupted policy skips the step. A module may recover by returning `SUCCEEDED` or `WARNING`, may emit artifacts or may fail. An exception from either handler becomes a `FAILED` outcome carrying a `Failure`.
- **Outcome checks.** An outcome must name the step and module it was asked for. A `FAILED` outcome must carry a failure. Artifacts may appear only on declared outputs or publications, and each artifact type must equal the declared type. Missing artifacts are valid; consumers must accept a connected producer that emitted nothing.
- **Failure propagation.** A `FAILED` step's active failures are its own plus those inherited from its inputs; a `SKIPPED` step inherits without adding; a succeeded or warned step clears them. Failures still active at a step that publishes a publication are `unresolved_failures`; all other failures are `recovered_failures`. `WorkflowReport.succeeded` means no unresolved failures.
- **Publication and reporting.** Only publication artifacts that exist at the end become `published_artifacts`. `build` writes `workflow_contract.json` before execution and `build_report.json` after, and returns the `WorkflowReport`. Report provenance is the contract provenance plus `workflow_fingerprint` and the effective DuckDB `TimeZone` (`UTC`).
- **Runtime configuration.** The executor imports each module class from its compiled reference and checks the class ID and `VERSION` against the contract. `BuildRuntime.module_configuration` is keyed by module ID. Before any step runs, the executor rejects unknown keys, missing required keys and values whose type does not match the module's `RuntimeFieldDefinition`s. Runtime values are not stored in the contract.
- **Runtime services.** Modules receive a synchronous `RelationService`, storage roots, a credential resolver and a step-scoped logger through `ExecutionServices`. The relation service owns identifier quoting and execution; modules never receive the raw connection or compression policy. `view` is lazy, `materialize` creates a private backing table behind a public view, `query` accepts only read statements (`DESCRIBE`, `EXPLAIN`, `SELECT`, `SHOW`, `SUMMARIZE`, `VALUES`, `WITH`), and `export_parquet` writes a query result. The service checkpoints after a dirty step when compression or disk storage is enabled.
- **Relation reuse is explicit.** Core defines table, projection, row-source, binding and aggregation relations as lazy views. The deduplication and merging built-ins call `materialize` for their own outputs. There is no automatic fan-out rule, consumer count, row threshold or global runtime flag that materialises a relation. A module that wants reuse calls `materialize` itself.
- **Monitoring.** `monitor=None` selects `RichWorkflowMonitor` on an interactive terminal and `NullWorkflowMonitor` otherwise. `monitor=True` forces the Rich monitor, `monitor=False` disables monitoring, and any other value is used as the `WorkflowExecutionMonitor`.
- **Compatibility model path.** `workflow.models` re-exports the kernel contract names unchanged for existing modules. The workflow package adds only `WorkflowDefinition`, `BuildRuntime` and `WorkflowReport`; see `../DESIGN_ISSUES.md` items 1, 2, 8 and 19.
