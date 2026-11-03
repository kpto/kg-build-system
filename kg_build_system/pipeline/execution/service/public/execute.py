"""The author-facing workflow execution entry point."""
from __future__ import annotations

from pathlib import Path

from ...model.public import BuildRuntime, WorkflowReport
from kg_build_system.pipeline.contract.model.public import WorkflowContractDTO
from ..internal.monitor import WorkflowExecutionMonitor


def execute(
    contract: WorkflowContractDTO,
    *,
    output_directory: str | Path,
    working_directory: str | Path | None = None,
    temporary_directory: str | Path | None = None,
    runtime: BuildRuntime | None = None,
    monitor: WorkflowExecutionMonitor | bool | None = None,
) -> WorkflowReport:
    """Run a frozen workflow contract and persist its contract and report.

    The contract supplies structure; each step supplies its own instruction.
    Instruction execution dispatches on ``instruction.kind`` and a kind this
    build does not implement is refused.

    ``workflow_contract.json`` is written before execution starts and
    ``build_report.json`` after it finishes. A step failure becomes a report
    entry; a failure before execution raises.

    Example:
    ```python
    from kg_build_system.pipeline.execution import execute

    report = execute(contract, output_directory="out", monitor=False)
    if not report.succeeded:
        for failure in report.unresolved_failures:
            print(failure.module_id, failure.step_id, failure.message)
    ```
    """
    from .._private.execute import execute as implementation

    return implementation(
        contract,
        output_directory=output_directory,
        working_directory=working_directory,
        temporary_directory=temporary_directory,
        runtime=runtime,
        monitor=monitor,
    )


__all__ = ["execute"]
