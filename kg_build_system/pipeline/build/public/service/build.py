"""The author-facing build entry point."""
from __future__ import annotations

from pathlib import Path

from ..model.runtime import BuildRuntime, WorkflowReport
from ....contract.public import WorkflowContractDTO
from ..._private.runtime.monitor import WorkflowExecutionMonitor


def build(
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
    from kg_build_system.pipeline.build import build

    report = build(contract, output_directory="out", monitor=False)
    if not report.succeeded:
        for failure in report.unresolved_failures:
            print(failure.module_id, failure.step_id, failure.message)
    ```
    """
    from ..._private.build import build as implementation

    return implementation(
        contract,
        output_directory=output_directory,
        working_directory=working_directory,
        temporary_directory=temporary_directory,
        runtime=runtime,
        monitor=monitor,
    )


__all__ = ["build"]
