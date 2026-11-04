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
| `Language` | discover declarations, derive keys, transcribe symbols and render source |
| `Linker` | select roots, resolve the symbol closure and assemble one opaque model |
| `Planner` | compile the model into `Step`s for one component |
| `StepExecutor` | execute one exact instruction kind and declare its resources |
| `ResourceProvider` | subscribe to pipeline events and own the resources one execution needs |
| `Toolchain` | compose languages, linker, planners, executors and runtime |

A planner needs a `component_id`, a `version`, a `runtime_fields` tuple and a
`plan(model, context)` method. An executor needs a `kinds` tuple, a `resources`
tuple and an `execute(context, instruction)` method. Several planners may share
one `component_id` when their version and runtime fields agree.

## Steps

### Step 1: Decide which extension point you need

| Job | Extension point |
| --- | --- |
| read a new declaration syntax into its own model | a `Language` and a `Linker` for the new model |
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

from kg_build_system.distribution.modules.runtime import (
    OutputStorage,
    instruction_payload,
    skipped,
    succeeded,
)
from kg_build_system.kernel import (
    ArtifactPattern,
    ArtifactType,
    DisruptedExecutionContext,
    ExecutionContext,
    Input,
    Instruction,
    InstructionKind,
    Key,
    PlanContext,
    Publication,
    Step,
)

MANIFEST = ArtifactType.of("manifest", "manifest")
RECORDS = ArtifactPattern.of("core", "graph", "**")


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
                outputs=(Publication(MANIFEST, Key(("result",))),),
                instruction=Instruction(
                    InstructionKind("manifest", "default"),
                    {"relative_path": "manifest.txt"},
                ),
                assembly_preference="deferred",
            ),
        )


class ManifestExecutor:
    """Execute one ("manifest", "default") instruction."""

    kinds = (InstructionKind("manifest", "default"),)
    resources = (OutputStorage,)

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ):
        if isinstance(context, DisruptedExecutionContext):
            return skipped(context)

        output_storage = context.resources.get(OutputStorage)
        payload = instruction_payload(instruction)
        relative_path = payload["relative_path"]
        if not isinstance(relative_path, str):
            raise TypeError("manifest instruction requires a relative path")

        names = sorted({
            str(contribution.artifact.type)
            for group in context.inputs.values()
            for contribution in group
            if contribution.artifact is not None
        })
        location = output_storage.child(PurePosixPath(relative_path))
        location.parent.mkdir(parents=True, exist_ok=True)
        location.write_text("\n".join(names) + "\n", encoding="utf-8")
        return succeeded(context, {"location": relative_path, "types": len(names)})
```

`RECORDS` is an `ArtifactPattern`: `Key.matches` matches it against every
concrete `core/graph/...` output, so one input accepts all node and edge record
streams. `*` matches one segment; a final `**` matches the rest.
The planner declares a `Publication`, so the executor's result appears in the
report. The instruction carries a JSON payload; the executor reads only that
payload and its own step's inputs. The executor declares `OutputStorage`, so the
runtime gives it a resource view containing exactly that resource.

### Step 3: Add the planner and executor to the toolchain

Edit `people_graph/build.py`:

```python
from pathlib import Path

from kg_build_system import compile, default_toolchain, execute
from kg_build_system.distribution import FileConfiguration, FilePlanner

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

`default_toolchain` adds the five core planners because no supplied planner has
`component_id == "core"`. `with_executors` replaces the executor sequence, so the
call appends the manifest executor to the default executors. `compile` and
`execute` use the same toolchain, which is why the manifest instruction has an
executor and its resource is available.

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
language discovers declarations, derives each key with `compute_key`,
transcribes a batch into symbols and renders a symbol value back to source. It
does not own keys itself: a `Declaration` holds only the authoring value that
the language recognised.

```python
from kg_build_system.kernel import (
    Declaration, Key, Language, Namespace, SourceFragment, Symbol,
    SymbolContext, SymbolRef,
)


class MyLanguage(Language):
    name = "my_language"

    def discover_declarations(self, namespace: Namespace):
        return (Declaration(value) for value in namespace.values())

    def compute_key(self, declaration: Declaration) -> Key:
        return Key((declaration.value.name,))

    def get_kind(self, declaration: Declaration) -> str:
        return "my_kind"

    def owns(self, value) -> bool:
        return isinstance(value, MyDeclaration)

    def get_identity(self, value) -> SymbolRef | None:
        if isinstance(value, MyDeclaration):
            return SymbolRef(self.name, Key((value.name,)))
        return None

    def get_references(self, value, resolver) -> tuple[SymbolRef, ...]:
        return ()

    def transcribe_many(
        self,
        declarations,
        context: SymbolContext,
    ) -> dict[SymbolRef, Symbol]:
        symbols = {}
        for declaration in declarations:
            reference = SymbolRef(self.name, self.compute_key(declaration))
            symbols[reference] = Symbol(
                reference.key, self.get_kind(declaration), declaration.value,
            )
        return symbols

    def render(self, symbol, context):
        return SourceFragment("declaration", f"value = {symbol.value!r}")
```

A `Linker` receives the language sequence and the namespace. It decides which
declarations are roots, orders the languages, transcribes them, resolves the
reference closure and assembles the model. There is no `requires` field:
language order is the linker's decision.

Compose them directly:

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

A language that reads several other languages receives their symbols through
`SymbolContext`; the linker transcribes those languages first. A `Language` must
also implement `render`. The blueprint must regenerate equivalent authoring
source, so a language whose declarations cannot be rendered is not complete.

## Semantics and edge cases

- **Instruction kinds are exact.** `InstructionKind("manifest", "default")`
  matches only that operation and engine. Two executors may not claim the same
  kind; an unclaimed kind in the plan is refused before any step runs.
- **A deferred step stays intact.** Use `assembly_preference="deferred"` when an
  executor expects to see its own step as planned.
- **An input pattern is a question.** Only an `Input` may use a pattern. An
  output or publication names one concrete type.
- **A disrupted downstream step still reaches its executor.** Return
  `StepOutcome(context.step_id, StepStatus.SKIPPED)` for the default policy, or
  inspect `context.disruptions` and recover deliberately.
- **Publish a summary when a step writes a side effect.** A publication is how
  the result appears in `WorkflowReport.published_artifacts`.
- **Runtime fields are execution settings.** Declare one with `RuntimeField` and
  read it from `context.runtime_configuration`; it is not compile-time planner
  configuration.
- **Resources are declared, not fetched.** List the exact resource types in the
  executor's `resources` tuple and read them from `context.resources.get(...)`.
  A provider publishes them on `PipelineStarted` and disposes them on
  `PipelineFinished` or `PipelineHalted`; the runtime owns the providers.
- **An executor does not schedule.** The runtime owns scheduling, input
  classification and the step lifecycle.

## Troubleshoot

| Message or symptom | What to change |
| --- | --- |
| `no executor for instruction kind(s)` | Add an executor whose `kinds` contains the exact `InstructionKind` the planner emitted. |
| `duplicate executor for instruction kind` | Remove one executor that claims the same kind. |
| `planners for component ... disagree on version` | Give every planner that shares a `component_id` the same `version` and `runtime_fields`. |
| `duplicate step id` | Give each step in one component a unique `name`; the identity is `StepId(component, name)`. |
| A step has no reader | Make the output a `Publication`, or add a step that consumes it. |
| `no candidate producer` or `workflow cannot be assembled` | The input pattern matches no output. Check its key, for example `ArtifactPattern.of("core", "graph", "**")`. |
| `executor ... requires missing resource(s)` | Add a provider that supplies every type the executor lists in `resources`. |
| `duplicate resource type` | Remove one provider that supplies the same exact resource type. |
| A custom language is refused | Language names must be unique, and a language may produce `SymbolRef`s only in its own `name`. Check `get_references` for unknown references and cycles. |

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
