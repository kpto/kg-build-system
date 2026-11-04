"""The toolchain: languages, linker, planners, executors and runtime.

A toolchain is the kernel's composition surface. It links language declarations
into one opaque model, compiles that model into a workflow plan and executes the
plan through exact instruction-kind executors. The runtime owns resources; the
kernel never inspects a resource or an instruction payload.
"""
from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar

from ...model.public.language import Language, Namespace, ReferenceResolver
from ...model.public.runtime import (
    DisruptedExecutionContext,
    ExecutionContext,
    RuntimeConfiguration,
    StepOutcome,
    WorkflowReport,
)
from ...model.public.workflow import (
    Instruction,
    InstructionKind,
    RuntimeField,
    Step,
    WorkflowPlan,
)

ModelT = TypeVar("ModelT")
LinkerModelT = TypeVar("LinkerModelT", covariant=True)
PlannerModelT = TypeVar("PlannerModelT", contravariant=True)


class Linker(Protocol[LinkerModelT]):
    """Link ordered language declarations into one opaque model.

    The linker owns dependency order. It discovers each language's
    declarations, transcribes them into symbols and assembles the model. The
    kernel never inspects the model it receives.

    Example:
    ```python
    class EchoLinker:
        def link(self, languages, namespace):
            return {"languages": tuple(language.name for language in languages)}
    ```
    """

    def link(
        self, languages: Sequence[Language], namespace: Namespace,
    ) -> LinkerModelT:
        """Link the language declarations into one model.

        Example:
            ```python
            model = EchoLinker().link(languages, namespace)
            ```
        """
        ...


@dataclass(frozen=True, slots=True)
class PlanContext:
    """The frozen context every planner receives for one compile.

    ``runtime_configuration`` carries per-component runtime values known at plan
    time, keyed by component id. ``shared`` is a mutable per-compile scratch
    space so several planners that share one component can publish and read the
    same plan state.

    Example:
    ```python
    from kg_build_system.kernel import PlanContext

    context = PlanContext({"echo": {"prefix": "hello"}})
    context.shared["plan"] = "core"
    assert context.runtime_configuration["echo"]["prefix"] == "hello"
    ```
    """

    runtime_configuration: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict,
    )
    shared: MutableMapping[str, Any] = field(default_factory=dict)


class Planner(Protocol[PlannerModelT]):
    """Compile one opaque model into workflow steps for one component.

    ``component_id`` names the component the steps belong to; the toolchain
    assigns it to every step the planner returns. Several planners may share one
    ``component_id`` when their ``version`` and ``runtime_fields`` agree.
    ``version`` and ``runtime_fields`` are published in the workflow plan.

    Example:
    ```python
    class EchoPlanner:
        component_id = "echo"
        version = "1"
        runtime_fields = ()

        def plan(self, model, context):
            return ()
    ```
    """

    component_id: str
    version: str
    runtime_fields: tuple[RuntimeField, ...]

    def plan(
        self, model: PlannerModelT, context: PlanContext,
    ) -> Sequence[Step]:
        """Return the steps this component contributes to the plan.

        Example:
            ```python
            steps = EchoPlanner().plan(model, PlanContext())
            ```
        """
        ...


class Executor(Protocol):
    """Execute one exact instruction kind.

    A normal step receives an ``ExecutionContext``; a step whose upstream input
    failed or was skipped receives a ``DisruptedExecutionContext``. The executor
    returns a ``StepOutcome`` and owns any engine bookkeeping.

    Example:
    ```python
    class EchoExecutor:
        kinds = (InstructionKind("echo", "default"),)

        def execute(self, context, instruction):
            return StepOutcome(context.step_id, StepStatus.SUCCEEDED)
    ```
    """

    kinds: tuple[InstructionKind, ...]

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        """Execute one instruction and return its outcome.

        Example:
            ```python
            outcome = EchoExecutor().execute(context, instruction)
            ```
        """
        ...


class StepExecutor(Executor, Protocol):
    """An executor that names the runtime resources it needs.

    ``resources`` lists the resource types the executor reads from its
    ``ResourceView``. The runtime builds a view containing exactly these types;
    asking for any other type raises ``KeyError``.

    Example:
    ```python
    class EchoExecutor:
        kinds = (InstructionKind("echo", "default"),)
        resources = (int,)

        def execute(self, context, instruction):
            assert context.resources.get(int) > 0
            return StepOutcome(context.step_id, StepStatus.SUCCEEDED)
    ```
    """

    resources: tuple[type, ...] = ()


class Resource(Protocol):
    """A live capability with a lifecycle.

    A resource is opened by a provider and released when the provider closes.
    The kernel never inspects what the capability does.

    Example:
    ```python
    class Connection:
        def close(self):
            pass

    resource: Resource = Connection()
    resource.close()
    ```
    """

    def close(self) -> None:
        """Release the capability.

        Example:
            ```python
            resource.close()
            ```
        """
        ...


class ResourceProvider(Protocol):
    """Create and close the live resources one execution needs.

    Resources are opaque to the kernel and keyed by their exact type. The
    runtime opens every provider before the first step and closes every provider
    in reverse order afterwards, even when execution raises.

    Example:
    ```python
    class EchoResources:
        def resources(self, configuration):
            return {str: "connected"}

        def close(self):
            pass
    ```
    """

    def resources(
        self, configuration: RuntimeConfiguration,
    ) -> Mapping[type, Any]:
        """Create the resources for one execution.

        Example:
            ```python
            resources = EchoResources().resources(configuration)
            ```
        """
        ...

    def close(self) -> None:
        """Release every resource this provider owns.

        Example:
            ```python
            EchoResources().close()
            ```
        """
        ...


class Runtime(Protocol):
    """Open resources, schedule a workflow plan and dispatch its steps.

    ``executors`` is an exact-kind map built by the toolchain; every instruction
    kind in the plan is guaranteed to have an executor. ``monitor`` is opaque to
    the kernel.

    Example:
    ```python
    report = runtime.execute(plan, executors, configuration=configuration)
    ```
    """

    def execute(
        self,
        plan: WorkflowPlan,
        executors: Mapping[InstructionKind, StepExecutor],
        *,
        configuration: RuntimeConfiguration,
        monitor: Any = None,
    ) -> WorkflowReport:
        """Run one plan and return its report.

        Example:
            ```python
            report = runtime.execute(
                plan, executors, configuration=configuration,
            )
            ```
        """
        ...


@dataclass(frozen=True, slots=True)
class Toolchain(Generic[ModelT]):
    """The full kernel composition: build, compile and execute.

    The linker owns language order and transcription. Planners compile the same
    linked model in order; several planners may share a component. Execution
    maps each executor's exact instruction kinds to the plan's instructions.

    Example:
    ```python
    from kg_build_system.kernel import Toolchain

    toolchain = Toolchain(
        languages=(EchoLanguage(),),
        linker=EchoLinker(),
        runtime=WorkflowRuntime(providers=(EchoResources(),)),
    )
    model = toolchain.build(namespace)
    ```
    """

    languages: Sequence[Language]
    linker: Linker[ModelT]
    runtime: Runtime | None = None
    planners: Sequence[Planner[ModelT]] = ()
    executors: Sequence[StepExecutor] = ()

    def build(self, namespace: Namespace) -> ModelT:
        """Link the language declarations into one model.

        Duplicate language names, cycles and a symbol reference to a missing
        symbol are the linker's responsibility; ``ValueError`` states them.

        Example:
        ```python
        model = toolchain.build(namespace)
        ```
        """
        from ..internal.pipeline import build_model

        return build_model(self.languages, self.linker, namespace)

    def compile(self, model: ModelT) -> WorkflowPlan:
        """Compile a linked model into one assembled workflow plan.

        Every planner receives the same model and its steps are assigned the
        planner's ``component_id``. Planners that share a component must agree
        on ``version`` and ``runtime_fields``. Duplicate step ids raise
        ``ValueError``.

        Example:
        ```python
        plan = toolchain.compile(model)
        assert plan.components
        ```
        """
        from ..internal.pipeline import compile_model

        return compile_model(self.planners, model, PlanContext())

    def execute(
        self,
        plan: WorkflowPlan,
        *,
        output_directory: Path,
        configuration: RuntimeConfiguration | None = None,
        monitor: Any = None,
    ) -> WorkflowReport:
        """Execute a plan through the registered executors and runtime.

        A duplicate instruction kind or a plan instruction with no executor is
        refused before any step runs. The runtime opens and closes resources.

        Example:
        ```python
        report = toolchain.execute(
            plan, output_directory=Path("build"),
        )
        assert report.succeeded
        ```
        """
        from ..internal.pipeline import execute_plan

        if self.runtime is None:
            raise RuntimeError("this toolchain has no runtime; it cannot execute")
        return execute_plan(
            self.executors,
            self.runtime,
            plan,
            output_directory=output_directory,
            configuration=configuration,
            monitor=monitor,
        )

    def with_planners(
        self, planners: Sequence[Planner[ModelT]],
    ) -> Toolchain[ModelT]:
        """Return a toolchain with its planners replaced.

        Example:
        ```python
        extended = toolchain.with_planners((EchoPlanner(),))
        ```
        """
        return replace(self, planners=tuple(planners))

    def with_executors(
        self, executors: Sequence[StepExecutor],
    ) -> Toolchain[ModelT]:
        """Return a toolchain with its executors replaced.

        Example:
        ```python
        extended = toolchain.with_executors((EchoExecutor(),))
        ```
        """
        return replace(self, executors=tuple(executors))


__all__ = [
    "Executor", "Linker", "PlanContext", "Planner",
    "ReferenceResolver", "Resource", "ResourceProvider", "Runtime",
    "StepExecutor", "Toolchain",
]
