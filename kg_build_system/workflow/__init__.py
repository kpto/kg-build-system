"""Author-facing workflow execution.

A graph author calls :func:`build` and reads :class:`BuildRuntime` and
:class:`WorkflowReport` here. The framework-internal workflow model, extension
protocols and contract codec are :mod:`kg_build_system.workflow.interfaces`; the
contract IR is :mod:`kg_build_system.workflow.ir`.
"""
from __future__ import annotations

from pathlib import Path

from .executor import build as _build
from .ir import WorkflowContractIR
from .models import BuildRuntime, WorkflowReport
from .monitor import WorkflowExecutionMonitor


def build(
    contract: WorkflowContractIR,
    runtime: BuildRuntime | None = None,
    *,
    output_directory: str | Path = Path("build"),
    working_directory: str | Path = Path("_workdir"),
    temporary_directory: str | Path | None = None,
    monitor: WorkflowExecutionMonitor | bool | None = None,
) -> WorkflowReport:
    """Run a frozen workflow and persist its contract and report.

    Rich monitoring is enabled automatically on an interactive terminal. Pass
    ``monitor=True`` to force it, ``False`` to disable it, or provide a custom
    :class:`WorkflowExecutionMonitor` implementation.

    ``workflow_contract.json`` is written before execution starts, and
    ``build_report.json`` after it finishes. A step failure becomes a report
    entry; a failure before execution raises.

    Example:
    ```python
    from pathlib import Path

    from kg_build_system import build

    report = build(contract, output_directory=Path("out"), monitor=False)
    if not report.succeeded:
        for failure in report.unresolved_failures:
            print(failure.module_id, failure.step_id, failure.message)
    ```
    """
    return _build(
        contract,
        runtime,
        output_directory=output_directory,
        working_directory=working_directory,
        temporary_directory=temporary_directory,
        monitor=monitor,
    )


__all__ = ["BuildRuntime", "WorkflowReport", "build"]
