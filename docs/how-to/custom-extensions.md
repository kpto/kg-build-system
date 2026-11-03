# Write an extension

An extension adds a language, a linker, a planner, an executor, or a combination
of them to the toolchain. It does not implement one monolithic interface: a
planner emits steps, an executor owns one exact instruction kind, and a linker
assembles a new model.

This guide writes one planner and one executor in a single file. The planner
consumes every core graph record and the executor writes a small manifest file.

## Before you begin

Read [Planners and executors](../concepts/planners-and-executors.md) for the role of a planner
and an executor, and [Compile, execute and outputs](../concepts/build-and-outputs.md)
for the plan and report lifecycle.

The kernel protocols are importable from `kg_build_system.kernel`:

| Name | Responsibility |
| --- | --- |
| `Language` | collect, transcribe, validate and render one layer |
| `Linker` | link ordered layers into one opaque model |
| `Planner` | compile the model into `Step`s for one component |
| `StepExecutor` | execute one exact instruction kind |
| `Toolchain` | compose languages, linker, planners, executors and runtime |
| `Extension` | bundle languages, planners and executors |

A planner needs a `component_id`, a `version`, a `runtime_fields` tuple and a
`plan(model, context)` method. An executor needs a `kinds` tuple and an
`execute(context, instruction)` method.

## Steps

### Step 1: Decide which extension point you need

| Job | Extension point |
| --- | --- |
| read a new declaration syntax into its own layer | a `Language` and a `Linker` for the new model |
| change what records survive or what values they carry | a rewriting `Planner` |
| publish the graph in a new format | a `Planner` and a `StepExecutor` |
| validate a rule that spans components | a `Planner` and a `StepExecutor` |
| run one instruction in a new engine | a `StepExecutor` and, when needed, a `ResourceProvider` |

If the job belongs to one binding, it is not an extension. Keep it in the
declaration where the grain is known: an expression, a projection, or a binding.

### Step 2: Write the planner and executor

Create `people_graph/extensions/manifest.py`:

```python
"""A one-file extension: a manifest planner and its executor."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from kg_build_system.distribution.executors.runtime import (
    execution_services,
    instruction_payload,
    skipped,
    succeeded,
)
from kg_build_system.kernel import (
    ArtifactType,
    DisruptedExecutionContext,
    ExecutionContext,
    Input,
    Instruction,
    PlanContext,
    Publication,
    Step,
)

MANIFEST = ArtifactType("manifest", "manifest")
RECORDS = ArtifactType("core", "graph.*")


class ManifestPlanner:
    """Plan one deferred step that lists the record types it receives."""

    component_id = "manifest"
    version = "1"
    runtime_fields = ()

    def plan(self, model: Any, context: PlanContext) -> tuple[Step, ...]:
        return (
            Step(
                component=self.component_id,
                name="write",
                inputs=(Input(RECORDS, None, "records"),),
                outputs=(Publication(MANIFEST, "result"),),
                instruction=Instruction(
                    ("manifest", "default"),
                    {"relative_path": "manifest.txt"},
                ),
                assembly_preference="deferred",
            ),
        )


class ManifestExecutor:
    """Execute one ("manifest", "default") instruction."""

    kinds = (("manifest", "default"),)

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ):
        if isinstance(context, DisruptedExecutionContext):
            return skipped(context)

        services = execution_services(context)
        payload = instruction_payload(instruction)
        relative_path = payload["relative_path"]
        if not isinstance(relative_path, str):
            raise TypeError("manifest instruction requires a relative path")

        names = sorted({
            f"{contribution.artifact.type.namespace}/"
            f"{contribution.artifact.type.name}"
            for group in context.inputs.values()
            for contribution in group
            if contribution.artifact is not None
        })
        location = services.output_storage.child(PurePosixPath(relative_path))
        location.parent.mkdir(parents=True, exist_ok=True)
        location.write_text("\n".join(names) + "\n", encoding="utf-8")
        return succeeded(context, {"location": relative_path, "types": len(names)})
```

`RECORDS` is an input pattern: `fnmatchcase` matches it against every concrete
`core/graph.*` output, so one input accepts all node and edge record streams.
The planner declares a `Publication`, so the executor's result appears in the
report. The instruction carries a JSON payload; the executor reads only that
payload and its own step's inputs.

### Step 3: Add the planner and executor to the toolchain

Edit `people_graph/build.py`:

```python
from pathlib import Path

from kg_build_system import compile, execute
from kg_build_system.distribution import (
    FileConfiguration,
    FilePlanner,
    default_toolchain,
)

from people_graph.extensions.manifest import ManifestExecutor, ManifestPlanner


def main() -> None:
    toolchain = default_toolchain(
        planners=(
            ManifestPlanner(),
            FilePlanner(FileConfiguration("graph.jsonl")),
        ),
    )
    toolchain = toolchain.with_executors(
        (*toolchain.executors, ManifestExecutor()),
    )
    plan = compile(toolchain=toolchain)
    report = execute(
        plan,
        output_directory=Path(__file__).parent / "build",
        toolchain=toolchain,
    )
    for artifact in report.published_artifacts:
        print(artifact.type.namespace, artifact.value)


if __name__ == "__main__":
    main()
```

`default_toolchain` adds the core planner because no supplied planner has
`component_id == "core"`. `with_executors` replaces the executor sequence, so the
call appends the manifest executor to the default executors. `compile` and
`execute` use the same toolchain, which is why the manifest instruction has an
executor.

### Step 4: Run and inspect the result

Run the entry point from the project root:

```bash
python -m people_graph.build
```

The build writes `graph.jsonl`, `manifest.txt`, `workflow_plan.json` and
`build_report.json` under `people_graph/build/`. `manifest.txt` lists the record
artifact types the step received. The report contains one
`manifest/manifest` publication.

Inspect the plan before execution when the wiring is not what you expected:

```python
for component in plan.components:
    print(component.id, component.version)

for step in plan.steps:
    print(step.component, step.name, step.instruction.kind)

for connection in plan.connections:
    print(connection.input_id, "<-", connection.output_id)
```

### Step 5: Extend a language or linker

A new declaration syntax is a `Language` plus a `Linker` for its model. A
language returns one `Layer` whose `language` is its own `name`; a linker
declares the layer names it needs in `requires`. Compose them directly:

```python
from kg_build_system.kernel import Toolchain

toolchain = Toolchain(
    languages=(MyLanguage(),),
    linker=MyLinker(),
    planners=(MyPlanner(),),
    executors=(MyExecutor(),),
)
model = toolchain.build(namespace)
plan = toolchain.compile(model)
```

A linker that reads several languages names all of them in `requires`; the
toolchain orders the languages and refuses a missing dependency or a cycle
before `link` runs.

A `Language` must also implement `render`. The blueprint must regenerate
equivalent authoring source, so a language whose declarations cannot be rendered
is not complete.

## Semantics and edge cases

- **Instruction kinds are exact.** `("manifest", "default")` matches only that
  tuple. Two executors may not claim the same kind; an unclaimed kind in the plan
  is refused before any step runs.
- **A deferred step stays intact.** Use `assembly_preference="deferred"` when an
  executor expects to see its own step as planned.
- **An input pattern is a question.** Only an `Input` may use a pattern. An
  output or publication names one concrete type.
- **A disrupted downstream step still reaches its executor.** Return
  `StepOutcome(step_id, StepStatus.SKIPPED)` for the default policy, or inspect
  `context.disruptions` and recover deliberately.
- **Publish a summary when a step writes a side effect.** A publication is how
  the result appears in `WorkflowReport.published_artifacts`.
- **Runtime fields are execution settings.** Declare one with `RuntimeField` and
  read it from `context.runtime_configuration`; it is not compile-time planner
  configuration.
- **An executor does not schedule.** The runtime owns scheduling, input
  classification and the step lifecycle.

## Troubleshoot

| Message or symptom | What to change |
| --- | --- |
| `no executor for instruction kind(s)` | Add an executor whose `kinds` contains the exact tuple the planner emitted. |
| `duplicate executor for instruction kind` | Remove one executor that claims the same tuple. |
| `duplicate component id` | Give the planner a unique `component_id`. |
| `duplicate step id` | Give each step in one component a unique `name`; identity is `component.name`. |
| A step has no reader | Make the output a `Publication`, or add a step that consumes it. |
| `no candidate producer` or `workflow cannot be assembled` | The input pattern matches no output. Check the namespace and name, for example `core/graph.*`. |
| `step executors require execution services` | The executor was called without a resource provider. Execute through a toolchain, not by calling the executor directly. |
| A custom language is refused | Its `Layer.language` must equal its `name`, and its `requires` must name existing layers. |

## Next steps

- [Planners and executors](../concepts/planners-and-executors.md) explains composition and
  ordering.
- [Compile, execute and outputs](../concepts/build-and-outputs.md) follows the plan
  and the report.
- [Debug a build](debug.md) reads failures and inspects the plan.
- The [planners and executors reference](../reference/planners-and-executors.md) lists the
  supplied extension points.
- The [compile reference](../reference/compile.md) lists the public calls and
  plan fields.
- The [system design](../developer/system-design.md) states the kernel protocols
  for framework developers.
