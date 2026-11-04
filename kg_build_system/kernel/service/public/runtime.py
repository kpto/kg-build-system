"""The kernel runtime: a public wrapper over the scheduler implementation.

The class is a thin delegation; resource allocation, scheduling, input
classification and the step lifecycle live in ``kernel.service._private.runtime``.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ...model.public.events import Listener
from ...model.public.runtime import RuntimeConfiguration, WorkflowReport
from ...model.public.workflow import InstructionKind, WorkflowPlan
from .pipeline import ResourceProvider, StepExecutor


class WorkflowRuntime:
    """Schedule a workflow plan, allocate resources and dispatch its steps.

    The runtime is the kernel's default ``Runtime`` implementation. It is
    transport-agnostic: resources and instruction payloads are opaque. Each
    execution creates a fresh event bus and resource registry, subscribes its
    providers and frontend listeners, emits the pipeline lifecycle and builds
    one resource view per executor.

    Example:
    ```python
    from kg_build_system.kernel import WorkflowRuntime

    runtime = WorkflowRuntime()
    ```
    """

    def __init__(self, providers: Sequence[ResourceProvider] = ()) -> None:
        self._providers = tuple(providers)

    def execute(
        self,
        plan: WorkflowPlan,
        executors: Mapping[InstructionKind, StepExecutor],
        *,
        configuration: RuntimeConfiguration,
        listeners: Sequence[Listener] = (),
    ) -> WorkflowReport:
        """Run one plan and return its report.

        Example:
        ```python
        report = runtime.execute(
            plan, executors, configuration=configuration,
        )
        ```
        """
        from .._private.runtime import WorkflowRuntime as implementation

        return implementation(self._providers).execute(
            plan,
            executors,
            configuration=configuration,
            listeners=listeners,
        )


__all__ = ["WorkflowRuntime"]
