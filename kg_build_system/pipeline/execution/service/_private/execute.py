"""The execution implementation: persist the contract, execute it, persist the report."""
from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

from ...model.public import BuildRuntime, WorkflowReport
from kg_build_system.pipeline.contract.model.public import WorkflowContractDTO
from .contract import read_contract
from .contract_codec import contract_to_document
from .runtime.executor import execute_contract, resolve_monitor
from .runtime.monitor import WorkflowExecutionMonitor


def _contract_text(contract: WorkflowContractDTO) -> str:
    if isinstance(contract, WorkflowContractDTO):
        return json.dumps(
            contract_to_document(contract),
            indent=2,
            sort_keys=True,
            default=str,
        )
    dump = getattr(contract, "model_dump_json", None)
    if callable(dump):
        return str(dump(indent=2))
    return json.dumps(contract, indent=2, sort_keys=True, default=str)


def _report_text(report: WorkflowReport) -> str:
    return json.dumps(
        asdict(report),
        indent=2,
        sort_keys=True,
        default=lambda item: (
            item.model_dump(mode="json")
            if hasattr(item, "model_dump") else str(item)
        ),
    )


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
    """
    base = runtime or BuildRuntime()
    resolved_output = Path(output_directory).resolve()
    requested_working = (
        Path(working_directory) if working_directory is not None
        else Path("_workdir")
    )
    resolved_working = (
        requested_working.resolve()
        if requested_working.is_absolute()
        else resolved_output / requested_working
    )
    resolved_temporary = (
        Path(temporary_directory)
        if temporary_directory is not None
        else base.temporary_directory
    )
    configured = replace(
        base,
        output_directory=resolved_output,
        working_directory=resolved_working,
        temporary_directory=resolved_temporary,
    )
    configured.output_directory.mkdir(parents=True, exist_ok=True)
    configured.working_directory.mkdir(parents=True, exist_ok=True)
    if configured.temporary_directory is not None:
        configured.temporary_directory.mkdir(parents=True, exist_ok=True)
    (configured.output_directory / "workflow_contract.json").write_text(
        _contract_text(contract), encoding="utf-8",
    )
    build_contract = read_contract(contract)
    execution_monitor = resolve_monitor(monitor)
    execution_monitor.start(build_contract.workflow)
    try:
        report = execute_contract(build_contract, configured, execution_monitor)
    except Exception as error:
        execution_monitor.workflow_halted(str(error))
        execution_monitor.log(
            "ERROR",
            f"Workflow execution stopped: {type(error).__name__}: {error}",
        )
        raise
    else:
        execution_monitor.workflow_finished(report)
    finally:
        execution_monitor.stop()
    (configured.output_directory / "build_report.json").write_text(
        _report_text(report), encoding="utf-8",
    )
    return report


__all__ = ["execute"]
