---
title: Compile and execute reference
summary: Exact signatures for create_blueprint, compile, execute, BuildRuntime and WorkflowReport.
section: reference
perspective: reference
order: 150
status: normative
verified: 2026-11-10
sources:
  - kg_build_system/api.py
  - kg_build_system/kernel/model/public/workflow.py
  - kg_build_system/kernel/service/_private/pipeline.py
  - kg_build_system/kernel/service/_private/assembly.py
  - tests/kernel/test_toolchain_flow.py
---

`create_blueprint` collects declarations into a `GraphBlueprint`. `compile` compiles a blueprint with a planner composition into a `WorkflowPlan`. `execute` runs the plan and writes its outputs.

The calls separate inspection from execution. A blueprint describes the graph model; a workflow plan describes the resolved reaction graph of one planner composition. Neither reads data.

The plan is assembled by artifact matching, not by declared step dependencies. Consumers name artifact types or patterns; the assembler derives connections. See [A workflow is a chain of reactions](/book/part-2/07-composition) for the contract and [Plan](/book/part-3/02-planning) for the mechanics.

## Surface

| Call | Inputs | Returns | Reads data | Writes files |
| --- | --- | --- | --- | --- |
| `create_blueprint` | One declaration mode and optional languages | `GraphBlueprint` | No | No |
| `compile` | One declaration mode or a blueprint, plus planners or a toolchain | `WorkflowPlan` | No | No |
| `execute` | A plan, an output directory and an optional runtime or toolchain | `WorkflowReport` | Yes | Yes |

```python
from pathlib import Path

from kg_build_system import compile, create_blueprint, execute
from kg_build_system.distribution import FileConfiguration, FilePlanner

planners = (FilePlanner(FileConfiguration("graph.jsonl")),)

blueprint = create_blueprint(namespace_path=Path("graph_pipeline"))
plan = compile(blueprint=blueprint, planners=planners)

# The shortcut creates the blueprint and compiles it:
plan = compile(namespace_path=Path("graph_pipeline"), planners=planners)

report = execute(plan, output_directory=Path("build"))
```

## Details

**`create_blueprint`.**

```python
create_blueprint(
    *,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] = (),
    languages: Sequence[Language] | None = None,
) -> GraphBlueprint
```

`create_blueprint` takes no planners. It collects declarations through the selected languages, links the language declarations into symbols and one model, and validates the result.

| Argument | Meaning |
| --- | --- |
| `namespace_path` | An importable package name or directory to discover |
| `bindings` | Explicit bindings |
| `languages` | Language composition; defaults to expressions, asset, data, topology, binding and graph |

There are three declaration modes:

| Mode | Arguments | Discovery |
| --- | --- | --- |
| Calling file | none | Imports the calling file's directory recursively and collects module-level binding values |
| Explicit namespace | `namespace_path=...` | Imports that package or directory |
| Explicit declarations | `bindings=(...)` | Uses exactly the supplied bindings |

`namespace_path` cannot be combined with `bindings`. The exact refusal is `ValueError: namespace_path cannot be combined with bindings`.

```python
blueprint = create_blueprint(
    namespace_path=Path("graph_pipeline"),
)
```

Only reached declarations enter the blueprint: the source relations and derived relations a binding reads, the components it targets and their ancestors and endpoints, the structs those types use, and the assets those source relations name.

`GraphBlueprint` has four fields:

| Field | Content |
| --- | --- |
| `graph` | `GraphPartDTO`: nodes and edges with graph names, labels, endpoints, properties, annotations, `abstract` and `parent` |
| `data` | `DataPartDTO`: structs, source relations and derived relations |
| `assets` | `AssetPartDTO`: the logical source-data units source relations name |
| `bindings` | `NodeBindingDTO` and `EdgeBindingDTO` values |

The language DTOs are internal to the language packages. `GraphBlueprint` is the public handle; `graph`, `data`, `assets` and `bindings` reference internal language DTOs. `BindingDTO` is the shared binding DTO used by the blueprint and the core planners; it is not exported from the interpreter facade. Cross-symbol fields carry role-typed references such as `NodeRef`, `FieldRef`, `AssetRef` and `OperationRef`.

**`compile`.**

```python
compile(
    *,
    blueprint: GraphBlueprint | None = None,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Binding] | None = None,
    planners: Sequence[Planner] = (),
    toolchain: Toolchain[GraphBlueprint] | None = None,
    engine: SqlEmitter | None = None,
) -> WorkflowPlan
```

`SqlEmitter` is the engine-neutral protocol in `distribution/service/internal/emission.py`. `DuckDbSqlEmitter` implements it; the core planners import only the neutral relation plan and protocol, never the DuckDB module.

`compile` reads the blueprint exactly as given, or creates one from the declaration mode. It never reads data. A blueprint cannot be combined with `namespace_path` or `bindings`: `ValueError: blueprint cannot be combined with namespace_path or bindings`.

When `toolchain` is omitted, `compile` uses `default_toolchain`, adding the generic DuckDB source planner unless a supplied planner reports `component_id == "duckdb"`, and adding the four core planners unless a supplied planner reports `component_id == "core"`, then appending the planners passed. When `toolchain` is supplied, it appends the `planners` argument to that toolchain's planners. The `engine` argument selects the SQL emitter for the default toolchain path.

```python
plan = compile(blueprint=blueprint, planners=planners)
```

`plan.provenance["blueprint"]` is the source blueprint document. It is attached by the composition root (`compile()`), not by the kernel planner stage. A plan serialised with `workflow_plan_to_document` therefore carries the blueprint that produced it and can be read without a second artifact.

Compilation checks everything that does not need data:

- every binding targets a concrete component;
- every declared property is mapped exactly once;
- every selection names a known source-relation or derived-relation field;
- keys are non-null scalars;
- edge endpoints exist, are concrete and descend from the declared categories;
- every source relation names an asset present in the blueprint;
- every derived relation carries a `Contract` whose `Meaning` states a purpose;
- every declared contract has both a `Definition` and a `Meaning`;
- every binding carries a `Meaning` with a purpose and reads a published relation;
- each planner's compile-time configuration is valid;
- the step wiring can feed every input and read every ordinary output.

`WorkflowPlan` owns the workflow structure:

| Field | Content |
| --- | --- |
| `components` | One component per distinct component id, with its id, version and runtime fields |
| `steps` | The scheduled instructions with typed inputs and outputs |
| `connections` | Resolved connections between step openings |
| `provenance` | The source blueprint document under `blueprint`, plus any planner provenance; the plan is self-contained |

A `Step` owns its inputs, outputs, `assembly_preference` and one `Instruction(kind, payload)`. `Step.component` and `Step.name` are the facts; `Step.id` derives a `StepId`. An `OpeningId` is a `StepId`, a direction and an opening name (`Key`); the direction is part of the key, so an input and an output with the same name stay distinct. An input declares an `ArtifactPattern`; an output and a publication name a concrete `ArtifactType`. A `Connection` holds one input `OpeningId` and one output `OpeningId`. `assembly_preference` is `"eager"` or `"deferred"`.

`InstructionKind(operation, engine)` is the exact executor key. `Instruction.kind` is that value; SQL is one instruction kind, not a plan field. `workflow_plan.json` writes every identity as its `Key` array; `build_report.json` uses the same form for `step_id` and a publication `opening`.

**`execute`.**

```python
execute(
    plan: WorkflowPlan,
    *,
    output_directory: str | Path,
    runtime: BuildRuntime | None = None,
    toolchain: Toolchain[GraphBlueprint] | None = None,
    monitor: Monitor | bool | None = None,
) -> WorkflowReport
```

| Argument | Meaning |
| --- | --- |
| `plan` | The `WorkflowPlan` returned by `compile` |
| `output_directory` | Where publications, `workflow_plan.json` and `build_report.json` land |
| `runtime` | Credentials, component runtime overrides and engine settings |
| `toolchain` | The executors, resources and runtime; defaults to `DEFAULT_TOOLCHAIN` |
| `monitor` | `None`/`False` presents nothing; `True` selects `ConsoleMonitor`; a monitor is used as supplied |

A monitor is a frontend listener on the pipeline event stream: `PipelineStarted`, `StepStarted`, `StepFinished`, `StepLogged`, `PipelineFinished` and `PipelineHalted`. It cannot change scheduling, resources or the report.

`execute` writes the plan before execution starts and the report after it finishes. It dispatches each step by the exact `InstructionKind` in `step.instruction.kind`. A kind the toolchain does not implement is refused before any step runs with `no executor for instruction kind(s): <kinds>`.

```python
report = execute(
    plan,
    output_directory=Path("out"),
)

if not report.succeeded:
    for failure in report.unresolved_failures:
        print(failure.step_id, failure.message)
```

A failure before execution raises. A failure inside a step becomes a report entry. A raised run leaves `workflow_plan.json` but no `build_report.json`.

**`BuildRuntime`.**

```python
BuildRuntime(
    credentials: dict[str, str] = {},
    component_configuration: dict[str, dict[str, Any]] = {},
    provider_configuration: dict[str, dict[str, Any]] = {},
    output_directory: Path = Path.cwd() / "build",
    working_directory: Path = Path("_workdir"),
    temporary_directory: Path | None = None,
    duckdb_storage: Literal["memory", "disk"] = "memory",
    duckdb_threads: int | None = None,
    duckdb_memory_limit: str | None = None,
    duckdb_compression: bool = True,
)
```

`BuildRuntime` supplies credentials, per-component runtime overrides and engine settings. Runtime values are not part of the plan. A relative working directory resolves beneath the output directory. `to_configuration()` returns the kernel `RuntimeConfiguration` that execution reads.

The engine settings are published under the `duckdb` provider id in `RuntimeConfiguration.provider_configuration`. `component_configuration` holds only plan component ids; `duckdb` is not a plan component.

**`WorkflowReport`.**

| Attribute | Meaning |
| --- | --- |
| `published_artifacts` | One entry per publication, with its `OpeningId`, type and value |
| `recovered_failures` | Failures that a later step handled |
| `unresolved_failures` | Failures that blocked a publication |
| `provenance` | The plan provenance, including the source blueprint document |
| `succeeded` | True when `unresolved_failures` is empty |

Each failure exposes `message`, a typed `step_id` and `exception_type`.

**Required inputs.**

| Requirement | Enforced by |
| --- | --- |
| Exactly one declaration mode | `create_blueprint` / `compile` argument checks |
| An asset for every reached source relation | the blueprint validation inside `compile` |
| Valid compile-time configuration for every planner | each planner's `plan` |
| A wireable planner composition | kernel assembly |
| An output directory for execution | `execute` |
| An executor for every instruction kind | `Toolchain.execute` |
| Matching plans and executors at execution | `execute` |

Continue with [Compile a plan](/book/part-3/02-planning), [Execute a plan](/book/part-3/03-execution-and-outputs), [Publish outputs](/book/part-3/03-execution-and-outputs), [Extend the toolchain](/book/part-4/01-the-kernel-and-extension), [Plan specification](/appendix/spec/plan), [Execution specification](/appendix/spec/execution), [Plan subject](/appendix/subjects/plan), [Execution subject](/appendix/subjects/execution), [Planners and executors](/appendix/reference/planners-and-executors), [Documents](/appendix/reference/documents) and [Failures](/appendix/reference/failures).
