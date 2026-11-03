"""Observer interface used by the build executor."""
from __future__ import annotations

from typing import Protocol

from .....kernel import StepOutcome
from ...model.internal.contract import ContractWorkflow
from ...model.public import WorkflowReport


class WorkflowExecutionMonitor(Protocol):
    """Observer used by the executor without coupling execution to a UI."""

    def start(self, workflow: ContractWorkflow) -> None:
        """Begin observing one workflow."""
        ...

    def step_started(self, step_id: str, detail: str) -> None:
        """Record that one step started."""
        ...

    def step_finished(self, outcome: StepOutcome, detail: str) -> None:
        """Record that one step finished."""
        ...

    def workflow_finished(self, report: WorkflowReport) -> None:
        """Record the completed report."""
        ...

    def workflow_halted(self, message: str) -> None:
        """Record that execution halted."""
        ...

    def log(
        self, level: str, message: str, *, step_id: str | None = None,
    ) -> None:
        """Record one log message."""
        ...

    def stop(self) -> None:
        """Stop observing and release presentation resources."""
        ...


__all__ = ["WorkflowExecutionMonitor"]
