"""Terminal-neutral build monitoring with an optional Rich presentation."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import TYPE_CHECKING

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    Task,
    TaskID,
    TaskProgressColumn,
)
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from ......kernel import StepStatus
from ...internal.monitor import WorkflowExecutionMonitor
from .identity import step_identity

if TYPE_CHECKING:
    from ......kernel import StepOutcome
    from ....model.public import WorkflowReport
    from ....model.internal.contract import ContractWorkflow


class _WorkflowStatusColumn(ProgressColumn):
    """Render the workflow status and completed step count."""

    def render(self, task: Task) -> Text:
        """Render the workflow status and completed step count."""
        status = str(task.fields.get("workflow_status", "Running"))
        style = str(task.fields.get("workflow_status_style", "bold green"))
        total = task.total or 0
        return Text(
            f"{status} {task.completed:.0f}/{total:.0f} steps", style=style,
        )


class NullWorkflowMonitor:
    """No-op observer for non-interactive and embedded execution."""

    def start(self, workflow: ContractWorkflow) -> None:
        """Begin observing one workflow."""
        pass

    def step_started(self, step_id: str, detail: str) -> None:
        """Record that one step started."""
        pass

    def step_finished(self, outcome: StepOutcome, detail: str) -> None:
        """Record that one step finished."""
        pass

    def workflow_finished(self, report: WorkflowReport) -> None:
        """Record the completed report."""
        pass

    def workflow_halted(self, message: str) -> None:
        """Record that execution halted."""
        pass

    def log(
        self, level: str, message: str, *, step_id: str | None = None,
    ) -> None:
        """Record one log message."""
        pass

    def stop(self) -> None:
        """Stop observing and release presentation resources."""
        pass


@dataclass
class _StepDisplay:
    """The state of one step in the live presentation."""

    module_id: str
    state: str = "pending"
    detail: str = "Waiting"


_STATUS_ICON = {
    StepStatus.SUCCEEDED: ("✓", "green"),
    StepStatus.WARNING: ("!", "yellow"),
    StepStatus.FAILED: ("✗", "red"),
    StepStatus.SKIPPED: ("−", "dim"),
}


class RichWorkflowMonitor:
    """Live three-section monitor for build execution."""

    def __init__(
        self, *, console: Console | None = None, log_lines: int = 10,
        step_lines: int = 8,
        refresh_per_second: float = 10,
    ) -> None:
        if log_lines < 1:
            raise ValueError("log_lines must be at least one")
        if step_lines < 2:
            raise ValueError("step_lines must be at least two")
        self.console = console or Console()
        self._log_messages: deque[Text] = deque(maxlen=log_lines)
        self._step_lines = step_lines
        self._refresh_per_second = refresh_per_second
        self._steps: dict[str, _StepDisplay] = {}
        self._step_order: tuple[str, ...] = ()
        self._finish_order: list[str] = []
        self._completed = 0
        self._progress: Progress | None = None
        self._progress_task: TaskID | None = None
        self._bar_column: BarColumn | None = None
        self._duckdb_settings: Text | None = None
        self._live: Live | None = None
        self._lock = RLock()

    def set_duckdb_settings(
        self, *, storage: str, compression: bool,
        memory_limit: str | None, threads: int | None,
    ) -> None:
        """Set the safe runtime summary rendered beside overall progress."""
        with self._lock:
            summary = Text()
            summary.append("DuckDB ", style="bold")
            summary.append(storage, style="cyan")
            summary.append(" · compression ", style="dim")
            summary.append("on" if compression else "off")
            summary.append(" · memory ", style="dim")
            summary.append(memory_limit or "default")
            summary.append(" · threads ", style="dim")
            summary.append(str(threads) if threads is not None else "default")
            self._duckdb_settings = summary
            self._refresh()

    def start(self, workflow: ContractWorkflow) -> None:
        """Begin the live presentation for one workflow."""
        with self._lock:
            if self._live is not None:
                raise RuntimeError("workflow monitor is already running")
            steps = tuple(
                (step_identity(module_id, step.name), module_id)
                for module_id, step in workflow.steps_by_module
            )
            self._step_order = tuple(identity for identity, _module in steps)
            self._steps = {
                identity: _StepDisplay(module_id) for identity, module_id in steps
            }
            self._finish_order = []
            self._completed = 0
            self._bar_column = BarColumn(
                bar_width=None,
                style="green dim",
                complete_style="green",
                finished_style="green",
                pulse_style="green",
            )
            self._progress = Progress(
                _WorkflowStatusColumn(),
                self._bar_column,
                TaskProgressColumn(),
                console=self.console,
                expand=True,
            )
            self._progress_task = self._progress.add_task(
                "workflow", total=len(self._step_order), completed=0,
                workflow_status="Running",
                workflow_status_style="bold green",
            )
            self._live = Live(
                self._render(),
                console=self.console,
                refresh_per_second=self._refresh_per_second,
                transient=False,
            )
            self._live.start(refresh=True)

    def step_started(self, step_id: str, detail: str) -> None:
        """Mark one step as processing."""
        with self._lock:
            display = self._steps[step_id]
            display.state = "processing"
            display.detail = detail
            self._refresh()

    def step_finished(self, outcome: StepOutcome, detail: str) -> None:
        """Mark one step with its final status and detail."""
        with self._lock:
            display = self._steps[outcome.step_id]
            display.state = outcome.status.value
            display.detail = detail
            self._finish_order.append(outcome.step_id)
            self._completed += 1
            if self._progress is not None and self._progress_task is not None:
                self._progress.update(
                    self._progress_task, completed=self._completed,
                )
            if outcome.status == StepStatus.FAILED:
                self._set_workflow_status(
                    "Continuing with errors", "yellow",
                )
            self._refresh()

    def workflow_finished(self, report: WorkflowReport) -> None:
        """Mark the workflow with the outcome of its report."""
        with self._lock:
            if report.unresolved_failures:
                self._set_workflow_status("Halted", "red")
            elif report.recovered_failures:
                self._set_workflow_status("Completed with errors", "yellow")
            else:
                self._set_workflow_status("Succeeded", "green")
            self._refresh()

    def workflow_halted(self, message: str) -> None:
        """Mark the workflow as halted."""
        with self._lock:
            self._set_workflow_status("Halted", "red")
            self._refresh()

    def log(
        self, level: str, message: str, *, step_id: str | None = None,
    ) -> None:
        """Append one formatted log line to the live panel."""
        with self._lock:
            timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
            level_name = level.upper()
            level_style = {
                "DEBUG": "dim",
                "INFO": "cyan",
                "WARNING": "yellow",
                "ERROR": "red",
            }.get(level_name, "white")
            line = Text()
            line.append(timestamp, style="dim")
            line.append(f" {level_name:<7}", style=level_style)
            if step_id is not None:
                line.append(f" {step_id}", style="bold")
            line.append(f" {message}")
            self._log_messages.append(line)
            self._refresh()

    def stop(self) -> None:
        """Stop the live presentation."""
        with self._lock:
            if self._live is None:
                return
            self._refresh()
            live, self._live = self._live, None
            live.stop()

    def _render_steps(self) -> RenderableType:
        """Render the visible step lines in processing, finished, rest order."""
        processing = [
            step_id for step_id in self._step_order
            if self._steps[step_id].state == "processing"
        ]
        finished = list(reversed(self._finish_order))
        rest = [
            step_id for step_id in self._step_order
            if step_id not in processing and step_id not in self._finish_order
        ]
        ordered = (*processing, *finished, *rest)
        visible_count = (
            self._step_lines - 1
            if len(ordered) > self._step_lines
            else self._step_lines
        )
        overflow = max(0, len(ordered) - visible_count)
        lines: list[RenderableType] = []
        for step_id in ordered[:visible_count]:
            display = self._steps[step_id]
            label = Text()
            label.append(step_id, style="bold")
            label.append(f" [{display.module_id}]", style="dim")
            label.append(f" — {display.detail}")
            if display.state == "processing":
                lines.append(Spinner("dots", text=label, style="cyan"))
            elif display.state == "pending":
                lines.append(Text.assemble(("○ ", "dim"), label))
            else:
                status = StepStatus(display.state)
                icon, style = _STATUS_ICON[status]
                lines.append(Text.assemble((f"{icon} ", style), label))
        if overflow:
            lines.append(Text(
                f"… {overflow} more step(s)", style="dim italic",
            ))
        return Group(*lines) if lines else Text("No workflow steps", style="dim")

    def _render(self) -> RenderableType:
        """Render the live view."""
        progress: RenderableType = self._progress or Text("Preparing workflow")
        workflow_header: RenderableType = progress
        if self._duckdb_settings is not None:
            header_grid = Table.grid(expand=True, padding=(0, 2))
            header_grid.add_column(ratio=3)
            header_grid.add_column(justify="right")
            header_grid.add_row(progress, self._duckdb_settings)
            workflow_header = header_grid
        logs: RenderableType
        if self._log_messages:
            logs = Group(*self._log_messages)
        else:
            logs = Text("Waiting for step messages…", style="dim")
        return Group(
            Panel(workflow_header, title="Workflow", border_style="blue"),
            Panel(
                self._render_steps(), title="Steps", border_style="cyan",
                height=self._step_lines + 2,
            ),
            Panel(logs, title="Logs", border_style="dim"),
        )

    def _refresh(self) -> None:
        """Refresh the live view when one is active."""
        if self._live is not None:
            self._live.update(self._render(), refresh=True)

    def _set_workflow_status(self, status: str, color: str) -> None:
        """Update the workflow status and progress bar colour."""
        if self._progress is not None and self._progress_task is not None:
            self._progress.update(
                self._progress_task,
                workflow_status=status,
                workflow_status_style=f"bold {color}",
            )
        if self._bar_column is not None:
            self._bar_column.style = f"{color} dim"
            self._bar_column.complete_style = color
            self._bar_column.finished_style = color
            self._bar_column.pulse_style = color


__all__ = [
    "NullWorkflowMonitor",
    "RichWorkflowMonitor",
    "WorkflowExecutionMonitor",
]
