# workflow

## Responsibility

The `kg_build_system.workflow` package owns the workflow declaration model, step assembly, the frozen execution contract, workflow execution, runtime services, and execution monitoring.

## Public interface

- Declaration models exported by `kg_build_system.workflow`:
  - `ArtifactType(namespace, name)`; `type_matches(declared, actual) -> bool` uses `*` as a wildcard.
  - `Input(type, name=None)`; `Output(type, name=None)`; `Publication(type, name=None)`; `Given = Output | Publication`.
  - `WorkflowStep(inputs=(), outputs=(), name=None, assembly_preference="eager")`.
  - `WorkflowContribution(module: ModuleDefinition, steps=(), variables=None)`.
  - `ModuleReference(module_id, import_module, class_qualname, implementation_version, configuration=None)`.
  - `RuntimeFieldDefinition(key, description, required=True, value_type="string", secret=False)`.
  - `ModuleDefinition(reference, runtime_fields=())`.
- Assembled models:
  - `TakenInput(type, name, input_name)`.
  - `DefinedStep(name, inputs=(), outputs=())`.
  - `DefinedContribution(module, steps=(), variables=None)`.
  - `Connection(input_id, output_id)`.
  - `WorkflowDefinition(contributions, connections=())` with `modules`, `steps_by_module`, and `variables_by_module` properties.
- Assembly and contract interface:
  - `assemble_workflow(contributions: Sequence[WorkflowContribution]) -> WorkflowDefinition`.
  - `AssemblyError(ValueError)` for a workflow that cannot be completely wired.
  - `create_workflow_contract(workflow: WorkflowDefinition, *, provenance: JsonValue | None = None) -> WorkflowContractIR` in `workflow.contracts`.
  - `workflow_to_ir(WorkflowDefinition) -> WorkflowDefinitionIR` and `workflow_from_ir(WorkflowDefinitionIR) -> WorkflowDefinition` in `workflow.mapping`.
- Contract IR in `workflow.ir`:
  - `WorkflowContractIR(schema_version: Literal[2] = 2, workflow, workflow_fingerprint, provenance=None)`.
  - `WorkflowDefinitionIR(contributions: tuple[ContributionIR, ...], connections=())` with at least one contribution.
  - `ContributionIR(reference, runtime_fields=(), variables=None, steps)` with at least one step.
  - `ConnectionIR(input_id, output_id)`.
  - `WORKFLOW_CONTRACT_SCHEMA_VERSION = 2`.
  - IR models are frozen pydantic with `extra="forbid"` and `strict=True`; module IDs, artifact namespaces, and runtime field keys are pattern-constrained.
- Execution interface:
  - `build(contract: WorkflowContractIR, runtime: BuildRuntime | None = None, *, output_directory=Path("build"), working_directory=Path("_workdir"), temporary_directory=None, monitor=None) -> WorkflowReport`.
  - `BuildRuntime(credentials={}, module_configuration={}, output_directory=Path.cwd()/"build", working_directory=Path("_workdir"), temporary_directory=None, duckdb_storage="memory", duckdb_threads=None, duckdb_memory_limit=None, duckdb_compression=True)`.
  - `StepStatus`: `SUCCEEDED`, `WARNING`, `FAILED`, `SKIPPED`.
  - `Failure(message, module_id, step_id, exception_type=None)`.
  - `Artifact(output_name, type, value)`; `StepOutcome(step_id, module_id, status, artifacts=(), failure=None)`.
  - `ContinuableInput(output_id, status, artifact)` and `DisruptingInput(output_id, status, artifact, failure)`.
  - `ExecutionContext(module, step, module_id, step_id, variables, runtime_configuration, inputs, services)` where `inputs` is a mapping from declared input name to `ContinuableInput` values.
  - `DisruptedExecutionContext(module, step, module_id, step_id, variables, runtime_configuration, inputs, disruptions, services)` where `inputs` also holds `DisruptingInput` values and `disruptions` is the tuple of them.
  - `ExecutorFactoryContext(module, variables, runtime_configuration, services)`.
  - `PublishedArtifact(type, value)`; `WorkflowReport(published_artifacts, recovered_failures, unresolved_failures, provenance)` with `succeeded` true when there are no unresolved failures.
- Executor protocol in `workflow.interfaces`:
  - `ModuleExecutor.handle(context: ExecutionContext) -> StepOutcome` (abstract).
  - `ModuleExecutor.handle_disrupted(context: DisruptedExecutionContext) -> StepOutcome`; the base implementation returns `SKIPPED`.
  - `ExecutableModule` with `ID`, `VERSION`, and `create_executor(context) -> ModuleExecutor`.
- Runtime services in `workflow.services`:
  - `RelationRef(name)`, non-empty.
  - `RelationService.reference(value: object) -> str`; `view(name, query) -> RelationRef`; `materialize(name, query, parameters=()) -> RelationRef`; `query(query, parameters=()) -> RelationQueryResult`; `export_parquet(query, destination, *, compression="zstd") -> None`; `register_filesystem(filesystem) -> None`.
  - `RelationQueryResult.description`, `fetchone()`, `fetchall()`, `fetchmany(size)`.
  - `ExecutionServices(relations, output_storage, working_storage, temporary_storage, credentials, logger)`.
  - `WorkflowLogger` with `debug`, `info`, `warning`, `error`.
  - `WorkingStorage.child(relative_path: PurePosixPath) -> Path`; `CredentialResolver.resolve(reference) -> str`.
- Monitoring in `workflow.monitor`: `WorkflowExecutionMonitor`, `NullWorkflowMonitor`, `RichWorkflowMonitor`. The protocol has `start`, `step_started`, `step_finished`, `workflow_finished`, `workflow_halted`, `log`, and `stop`.
- Identity helpers in `workflow.identity`: `step_name`, `input_name`, `output_name`, `step_identity`, `opening_identity`, `expanded_input_name`, `type_text`. Defaults are `step{N}` (one-based position within the module), `input`, and `output`.

## Boundaries

- Allowed package dependency: `engines`, specifically `engines.duckdb` for the relation service and connection setup; plus the private `_frozen_json` kernel.
- Must not import `compile`, `modules`, `binding`, `table`, `topology`, `expressions`, `relational`, `code_generation`, `api`, or `cli`.
- Workflow domain models never retain IR objects. `workflow.ir` is the serialisable form used only at the contract boundary; executors never receive IR.
- The executor imports module classes only through the compiled `ModuleReference` import coordinates. It stores no Python class in the contract.

## Current decisions

- **The model is frozen and amnesic.** A step holds its inputs, outputs, name, and assembly preference. An opening holds a type and an optional name. Nothing holds an owner reference, a derived identity, or a closure. Per-step instruction data belongs to the contributing module's `variables`, not to the step.
- **Identity is generated from names.** A step is `module_id::step_name`; an input or output is `<step_identity>.<opening_name>`. The assembled definition stores these generated identities in connections. No declared model stores one.
- **Open inputs.** `Input` is open when either half of its `ArtifactType` contains `*`. The assembler expands it into one `TakenInput` per matching type actually written by some output, each named `<declared_name>:<namespace>.<name>`. A non-pattern input is always answered with the one type it names, even when nothing writes it, so the missing writer is reported. Outputs and publications cannot be patterns. At execution, an open input's several artifacts arrive together under the declared `input_name`.
- **Default names.** An unnamed step is `step{N}` within its module; an unnamed input is `input`; an unnamed output or publication is `output`. A name must be unique among its siblings. A duplicate step name, duplicate opening name, duplicate module ID, or pattern on an output/publication raises `AssemblyError`.
- **Rank.** Rank orders steps by module contribution order, then eager before deferred, then step position within the module; the earlier of two steps has the greater rank. The public API appends core after the supplied modules, so core has the lowest rank. Rank is used only to choose which writer an input takes. It never gates a step, refuses a connection, or determines the execution order.
- **Two assembly passes.** The assembler first repeatedly makes every connection that holds for any valid wiring: an unfed input with exactly one admissible writer, or an unread `Output` with exactly one admissible unfed reader. It then scans inputs in rank order and makes the first connection its rules justify, restarting after each connection. A candidate that would close a cycle is never admissible. A writer that may yet turn out to take the type it writes defers a conclusion. Otherwise the latest step that both takes and writes the type before the input wins; a single producer is accepted; multiple producers with nothing distinguishing them are indeterminate.
- **Completeness.** A workflow assembles only when every input is fed and every `Output` is read. A `Publication` is exempt because it has no reader inside the workflow. Otherwise `assemble_workflow` raises `AssemblyError` explaining every unsettled input in assembly order and every unread output; it does not return a partial definition.
- **Cardinality.** An input takes exactly one feeder. An output may have any number of readers and at least one unless it is a publication. No connection joins a step to itself and no connection closes a cycle.
- **Contract.** The assembled `WorkflowDefinition` is mapped to IR and frozen into a `WorkflowContractIR`. Its `workflow_fingerprint` is the SHA-256 of the serialised workflow IR, so any change to contribution order, step name, input/output name, type, module data, or connection changes the fingerprint. Provenance is opaque JSON attached by the compiler; the contract carries only workflow semantics and provenance.
- **Execution is a wavefront.** Each round runs every pending step whose connected producers have all completed. If no pending step is ready, execution raises `RuntimeError` for a dependency cycle. A ready step's inputs are grouped by `TakenInput.input_name`; each connected artifact is classified by its producer's final status.
- **Disruption.** If any connected producer failed or was skipped, the step receives `DisruptedExecutionContext` and `handle_disrupted`; otherwise it receives `ExecutionContext` and `handle`. The base disrupted policy skips the step. A module may recover by returning `SUCCEEDED` or `WARNING`, may emit artifacts, or may fail. An exception from either handler becomes a `FAILED` outcome carrying a `Failure`.
- **Outcome checks.** An outcome must name the step and module it was asked for. A `FAILED` outcome must carry a failure. Artifacts may appear only on declared outputs or publications, and each artifact type must equal the declared type. Missing artifacts are valid; consumers must accept a connected producer that emitted nothing.
- **Failure propagation.** A `FAILED` step's active failures are its own plus those inherited from its inputs; a `SKIPPED` step inherits without adding; a succeeded or warned step clears them. Failures still active at a step that publishes a publication are `unresolved_failures`; all other failures are `recovered_failures`. `WorkflowReport.succeeded` means no unresolved failures.
- **Publication and reporting.** Only publication artifacts that exist at the end become `published_artifacts`. `build` writes `workflow_contract.json` before execution and `build_report.json` after, and returns the `WorkflowReport`. Report provenance is the contract provenance plus `workflow_fingerprint` and the effective DuckDB `TimeZone` (`UTC`).
- **Runtime configuration.** The executor imports each module class from its compiled reference and checks the class ID and `VERSION` against the contract. `BuildRuntime.module_configuration` is keyed by module ID. Before any step runs, the executor rejects unknown keys, missing required keys, and values whose type does not match the module's `RuntimeFieldDefinition`s. Runtime values are not stored in the contract.
- **Runtime services.** Modules receive a synchronous `RelationService`, storage roots, a credential resolver, and a step-scoped logger through `ExecutionServices`. The relation service owns identifier quoting and execution; modules never receive the raw connection or compression policy. `view` is lazy, `materialize` creates a private backing table behind a public view, `query` accepts only read statements (`DESCRIBE`, `EXPLAIN`, `SELECT`, `SHOW`, `SUMMARIZE`, `VALUES`, `WITH`), and `export_parquet` writes a query result. The service checkpoints after a dirty step when compression or disk storage is enabled.
- **Relation reuse is explicit.** Core defines table, projection, row-source, binding, and aggregation relations as lazy views. The deduplication and merging built-ins call `materialize` for their own outputs. There is no automatic fan-out rule, consumer count, row threshold, or global runtime flag that materialises a relation. A module that wants reuse must call `materialize` itself.
- **Monitoring.** `monitor=None` selects `RichWorkflowMonitor` on an interactive terminal and `NullWorkflowMonitor` otherwise. `monitor=True` forces the Rich monitor, `monitor=False` disables monitoring, and any other value is used as the `WorkflowExecutionMonitor`.
