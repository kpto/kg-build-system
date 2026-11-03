"""The toolchain: languages, linker, planners, executors, resources and runtime.

A toolchain is the kernel's composition surface. It orders and transcribes
languages, links their layers into one opaque model, compiles that model into a
workflow plan and executes the plan through exact instruction-kind executors.
The kernel never inspects a service or an instruction payload.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar

from ...model.public.language import Language, Namespace
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
    """Link ordered language layers into one opaque model.

    ``requires`` names the layers the linker needs; the toolchain refuses a
    missing layer before calling ``link``. The kernel never inspects the model
    it receives.

    Example:
    ```python
    class EchoLinker:
        requires = ("echo",)

        def link(self, layers):
            return {"echo": layers["echo"].value}
    ```
    """

    requires: tuple[str, ...]

    def link(self, layers: Mapping[str, Any]) -> LinkerModelT:
        """Link the transcribed layers into one model.

        Example:
            ```python
            model = EchoLinker().link({"echo": layer})
            ```
        """
        ...


@dataclass(frozen=True, slots=True)
class PlanContext:
    """The frozen context every planner receives for one compile.

    ``runtime_configuration`` carries per-component runtime values known at plan
    time, keyed by component id.

    Example:
    ```python
    from kg_build_system.kernel import PlanContext

    context = PlanContext({"echo": {"prefix": "hello"}})
    assert context.runtime_configuration["echo"]["prefix"] == "hello"
    ```
    """

    runtime_configuration: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict,
    )


class Planner(Protocol[PlannerModelT]):
    """Compile one opaque model into workflow steps for one component.

    ``component_id`` names the component the steps belong to; the toolchain
    assigns it to every step the planner returns. ``version`` and
    ``runtime_fields`` are published in the workflow plan.

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


class StepExecutor(Protocol):
    """Execute one exact instruction kind.

    A normal step receives an ``ExecutionContext``; a step whose upstream input
    failed or was skipped receives a ``DisruptedExecutionContext``. The executor
    returns a ``StepOutcome`` and owns any engine bookkeeping.

    Example:
    ```python
    class EchoExecutor:
        kinds = (("echo", "default"),)

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


class ResourceProvider(Protocol):
    """Create and close the live services one execution needs.

    Services are opaque to the kernel. ``close`` is called exactly once for a
    successfully created service object, even when execution raises.

    Example:
    ```python
    class EchoResources:
        def services(self, plan, configuration):
            return {"connected": True}

        def close(self, services):
            services.clear()
    ```
    """

    def services(
        self, plan: WorkflowPlan, configuration: RuntimeConfiguration,
    ) -> Any:
        """Create the services for one plan execution.

        Example:
            ```python
            services = EchoResources().services(plan, configuration)
            ```
        """
        ...

    def close(self, services: Any) -> None:
        """Release the services created for one execution.

        Example:
            ```python
            EchoResources().close(services)
            ```
        """
        ...


class Runtime(Protocol):
    """Schedule a workflow plan and dispatch each step to its executor.

    ``executors`` is an exact-kind map built by the toolchain; every instruction
    kind in the plan is guaranteed to have an executor. ``services`` and
    ``monitor`` are opaque to the kernel.

    Example:
    ```python
    report = runtime.execute(
        plan, executors, services=services, configuration=configuration,
    )
    ```
    """

    def execute(
        self,
        plan: WorkflowPlan,
        executors: Mapping[InstructionKind, StepExecutor],
        *,
        services: Any,
        configuration: RuntimeConfiguration,
        monitor: Any = None,
    ) -> WorkflowReport:
        """Run one plan and return its report.

        Example:
            ```python
            report = runtime.execute(
                plan,
                executors,
                services=services,
                configuration=configuration,
            )
            ```
        """
        ...


@dataclass(frozen=True, slots=True)
class Extension:
    """A named bundle of languages, planners and executors.

    Example:
    ```python
    from kg_build_system.kernel import Extension

    extension = Extension("echo", languages=(EchoLanguage(),))
    assert extension.name == "echo"
    ```
    """

    name: str
    languages: tuple[Language, ...] = ()
    planners: tuple[Any, ...] = ()
    executors: tuple[StepExecutor, ...] = ()


@dataclass(frozen=True, slots=True)
class Toolchain(Generic[ModelT]):
    """The full kernel composition: build, compile and execute.

    Languages are ordered by ``requires``, transcribed and validated before the
    linker sees them. Planners compile the same linked model in order. Execution
    maps each executor's exact instruction kinds to the plan's instructions.

    Example:
    ```python
    from kg_build_system.kernel import Toolchain

    toolchain = Toolchain(
        languages=(EchoLanguage(),),
        linker=EchoLinker(),
        resources=EchoResources(),
        runtime=WorkflowRuntime(),
    )
    model = toolchain.build(namespace)
    ```
    """

    languages: Sequence[Language]
    linker: Linker[ModelT]
    resources: ResourceProvider | None = None
    runtime: Runtime | None = None
    planners: Sequence[Planner[ModelT]] = ()
    executors: Sequence[StepExecutor] = ()

    def build(self, namespace: Namespace) -> ModelT:
        """Order and transcribe languages, then link their layers.

        Duplicate language names, unknown dependencies, cycles and a layer whose
        ``language`` does not match its language name raise ``ValueError``.

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
        planner's ``component_id``. Duplicate component or step ids raise
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
        """Execute a plan through the registered executors and resources.

        A duplicate instruction kind or a plan instruction with no executor is
        refused before any step runs. Services are always closed.

        Example:
        ```python
        report = toolchain.execute(
            plan, output_directory=Path("build"),
        )
        assert report.succeeded
        ```
        """
        from ..internal.pipeline import execute_plan

        if self.resources is None or self.runtime is None:
            raise RuntimeError(
                "this toolchain has no resources or runtime; it cannot execute"
            )
        return execute_plan(
            self.executors,
            self.resources,
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
    "Extension", "Linker", "PlanContext", "Planner", "ResourceProvider",
    "Runtime", "StepExecutor", "Toolchain",
]
