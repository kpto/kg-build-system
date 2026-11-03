"""The kernel runtime: a public wrapper over the scheduler implementation.

The class is a thin delegation; scheduling, input classification and the step
lifecycle live in ``kernel.service._private.runtime``.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...model.public.runtime import RuntimeConfiguration, WorkflowReport
from ...model.public.workflow import InstructionKind, WorkflowPlan
from .pipeline import StepExecutor


class WorkflowRuntime:
    """Schedule a workflow plan and dispatch each step to its executor.

    The runtime is the kernel's default ``Runtime`` implementation. It is
    transport-agnostic: services and instruction payloads are opaque.

    Example:
    ```python
    from kg_build_system.kernel import WorkflowRuntime

    runtime = WorkflowRuntime()
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
            plan, executors, services=services, configuration=configuration,
        )
        ```
        """
        from .._private.runtime import WorkflowRuntime as implementation

        return implementation().execute(
            plan,
            executors,
            services=services,
            configuration=configuration,
            monitor=monitor,
        )


__all__ = ["WorkflowRuntime"]
