# Workflow module specification

The `kg_build_system/workflow/` package: how a workflow is described, wired, frozen into a
contract, and run. Describes the code as it stands at `22fedcd`.

| File | Role |
|---|---|
| `models.py` | The shared data: modules, steps, slots, connections, outcomes, report |
| `assembly.py` | Chooses the connections between contributed steps |
| `validation.py` | Checks a finished definition |
| `contracts.py` | Freezes a definition and fingerprints it |
| `ir.py`, `mapping.py` | Serialisable form of the same data, and the round trip |
| `interfaces.py` | What an executable module must provide |
| `services.py` | Runtime capabilities handed to a module |
| `executor.py` | Runs a contract and writes the report |
| `monitor.py` | Progress reporting hooks |

Compilation of modules into contributions lives in `kg_build_system/compile/`; this package
supplies the models, the assembler, and the runtime.

## 1. Data model

```
ModuleReference   module_id, import_module, class_qualname, implementation_version, configuration
ModuleDefinition  reference + runtime_fields: tuple[RuntimeFieldDefinition, ...]
ArtifactRole      namespace, name                 — what a produced value is
OutputSlot        slot_id, artifact_role          — where a step writes one role
SingleInputSlot   slot_id                         — takes one output
CollectionInputSlot slot_id                       — takes many outputs
WorkflowStep      step_id, module_id, inputs, outputs, payload
Connection        input_slot_id, output_slot_id
WorkflowDefinition modules, steps, connections
```

Everything is frozen data. `slot_id` is authored by the module and is the only handle a slot has:
it must be unique across the whole workflow, and it is what connections, artifacts and
`ExecutionContext.inputs` are keyed by. Steps carry a `payload`, opaque JSON the same module's
executor reads later.

Declaration comes in two layers:

```
WorkflowStepDraft       definition, assembly_preference ("eager" | "deferred"),
                        candidates: slot_id -> CandidatePredicate
WorkflowContribution    module: ModuleDefinition, steps: tuple[WorkflowStepDraft, ...]
```

A `CandidatePredicate` is `(InputSlot, OutputSlot) -> bool` and says which outputs an input slot
will accept. `role_is(role)` is the usual one. Predicates exist only during assembly: the contract
records the connections they produced, never the predicates.

`WorkflowArtifactRoles.published(module_id, name)` builds the role
`workflow/publication.<module_id>.<name>`, the convention for a value the build should hand back.

## 2. Assembly

`assemble_workflow(contributions)` flattens the drafts, requires unique module ids, and resolves
each step's inputs in **claim order**: eager steps first in module order, then deferred steps in
reverse module order, each group in declaration order.

For every input slot the candidate outputs are those whose predicate accepts the pair, excluding
the reader's own outputs and anything that would close a cycle. Selection then depends on the slot
kind:

- **Single**: take the highest-ranked candidate, preferring ones no input has used yet. Ranking is
  `(module order, output declaration order, slot_id)`, higher wins.
- **Collection**: group candidates by artifact role. For each role take every unused candidate, or
  the single highest-ranked one when all are already used, and record the connections in
  ranked order.

Each choice records a `Connection`, counts a use against the output, and adds a step dependency. An
input with no candidate at all raises `input '<slot_id>' has no compatible output`. Nothing
requires an output to be read.

`validate_workflow` runs at the end, and is also safe to call on any definition on its own.

## 3. Validation

| Check | Message |
|---|---|
| module ids unique | `workflow module IDs must be unique` |
| step ids unique | `workflow step IDs must be unique` |
| every step names a declared module | `workflow step references an unknown module` |
| input and output slot ids unique | `workflow input/output slot IDs must be unique` |
| connections name real slots | `workflow connection references an unknown input/output slot` |
| no repeated connection | `workflow connections must be unique` |
| every input wired | `input '<id>' requires at least one connection` |
| single input wired once | `single input '<id>' requires exactly one connection` |
| acyclic | `workflow dependency graph contains a cycle` |

## 4. Contract

`create_workflow_contract(workflow, provenance=…)` maps the definition to `WorkflowDefinitionIR`
and sets `workflow_fingerprint` to the SHA-256 of its `model_dump_json()`. The IR is a set of
frozen pydantic models (`extra="forbid"`, `strict=True`) that repeat the data with pattern
constraints on ids, namespaces and keys, and a `kind` discriminator on the two input slot kinds.

`workflow_to_ir` and `workflow_from_ir` round-trip exactly. Because the fingerprint covers the
serialised workflow, any change to a slot id, role, payload or connection order changes the
contract of every build.

## 5. Execution

`build(contract, runtime=None, *, output_directory, working_directory, temporary_directory, monitor)`
runs a frozen workflow. It writes `workflow_contract.json` before executing and `build_report.json`
after, and returns a `WorkflowReport`.

Setup opens DuckDB (`memory` or `disk`, threads, memory limit, compression), builds
`ExecutionServices`, and validates each module's runtime configuration against its declared
`RuntimeFieldDefinition` list, rejecting values of the wrong type.

The run is a wavefront: each round, every pending step whose producers have all completed is
handled. Inputs are grouped by the consumer's slot id, and each contribution is classified by its
producer's status:

- `ContinuableInput` — producer succeeded or warned; carries the artifact if there was one.
- `DisruptingInput` — producer failed or was skipped; carries the failure.

A step with any disruption gets `handle_disrupted(context)`; otherwise `handle(context)`.
The base executor's `handle_disrupted` skips the step. An exception raised by a module becomes a
`FAILED` outcome with a `Failure`. Outcomes are checked: they must name the same step and module,
artifacts may only appear on declared output slots, and each artifact's role must match its slot.

Failure propagation is per step. A `FAILED` step's active failures are its own plus those it
inherited; a `SKIPPED` step inherits without adding; a succeeded or warned step clears them.
Failures still active at a **sink step** — one that writes nothing any other step reads — become
`unresolved_failures`; the rest are `recovered_failures`. Artifacts whose role starts with
`workflow/publication.` are collected into `published_artifacts`, and
`WorkflowReport.succeeded` means there were no unresolved failures.

## 6. Module interface

```python
class ExecutableModule(Protocol):
    ID: ClassVar[str]
    VERSION: ClassVar[str]
    @classmethod
    def create_executor(cls, context: ExecutorFactoryContext) -> ModuleExecutor: ...

class ModuleExecutor(ABC):
    def handle(self, context: ExecutionContext) -> StepOutcome: ...
    def handle_disrupted(self, context: DisruptedExecutionContext) -> StepOutcome: ...  # skips
```

Executors are created once per module from `ExecutorFactoryContext` (module definition, runtime
configuration, services) and then reused for every step of that module.

## 7. Services

`ExecutionContext.services` gives a module:

- `logger` — routed through the monitor, tagged with module and step
- `relations` — `reference`, `view`, `materialize`, `query`, `export_parquet`,
  `register_filesystem`; a step's materializations are checkpointed by `finish_step`
- `output_storage`, `working_storage` — `child(relative_path)` under the build's output and
  working directories
- `temporary_storage` — per-step scratch space
- `credentials` — `resolve(reference)`

## 8. Monitoring

`WorkflowExecutionMonitor` receives `start`, `step_started`, `step_finished`, `log`,
`workflow_finished`, `workflow_halted`, `stop`. `NullWorkflowMonitor` is silent and
`RichWorkflowMonitor` draws a terminal UI, chosen automatically on an interactive terminal, or by
passing `monitor=True`, `False`, or your own implementation to `build`.

## 9. Properties worth knowing

- A slot carries no type on the input side: what an input accepts is a predicate known only at
  assembly time, so the contract cannot say why a connection was made.
- Variable arity is expressed by one collection slot holding many connections, so a step's input
  count is smaller than its wire count.
- Reading is optional for a producer and mandatory for a consumer: an unread output is valid.
- Slot ids are free-form strings owned by the module; the collision check happens after assembly.
- Publication is recognised by name prefix on the role, and sink-ness by the connection graph;
  neither is declared.
