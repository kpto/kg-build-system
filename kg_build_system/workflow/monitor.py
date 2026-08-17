"""Terminal-neutral workflow monitoring with an optional Rich presentation."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Protocol

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskID, TaskProgressColumn, TextColumn
from rich.spinner import Spinner
from rich.text import Text

from .models import StepOutcome, StepStatus, WorkflowDefinition, WorkflowStep


class WorkflowExecutionMonitor(Protocol):
    """Observer used by the executor without coupling execution to a UI."""

    def start(self, workflow: WorkflowDefinition) -> None: ...

    def step_started(self, step: WorkflowStep, detail: str) -> None: ...

    def step_finished(self, outcome: StepOutcome, detail: str) -> None: ...

    def log(
        self, level: str, message: str, *, step_id: str | None = None,
    ) -> None: ...

    def stop(self) -> None: ...


class NullWorkflowMonitor:
    """No-op observer for non-interactive and embedded execution."""

    def start(self, workflow: WorkflowDefinition) -> None:
        pass

    def step_started(self, step: WorkflowStep, detail: str) -> None:
        pass

    def step_finished(self, outcome: StepOutcome, detail: str) -> None:
        pass

    def log(
        self, level: str, message: str, *, step_id: str | None = None,
    ) -> None:
        pass

    def stop(self) -> None:
        pass


@dataclass
class _StepDisplay:
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
    """Live three-section monitor for workflow execution."""

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
        self._live: Live | None = None
        self._lock = RLock()

    def start(self, workflow: WorkflowDefinition) -> None:
        with self._lock:
            if self._live is not None:
                raise RuntimeError("workflow monitor is already running")
            self._step_order = tuple(step.step_id for step in workflow.steps)
            self._steps = {
                step.step_id: _StepDisplay(step.module_id)
                for step in workflow.steps
            }
            self._finish_order = []
            self._completed = 0
            self._progress = Progress(
                TextColumn("[bold]Overall[/bold] {task.completed:.0f}/{task.total:.0f} steps"),
                BarColumn(bar_width=None),
                TaskProgressColumn(),
                console=self.console,
                expand=True,
            )
            self._progress_task = self._progress.add_task(
                "workflow", total=len(workflow.steps), completed=0,
            )
            self._live = Live(
                self._render(),
                console=self.console,
                refresh_per_second=self._refresh_per_second,
                transient=False,
            )
            self._live.start(refresh=True)

    def step_started(self, step: WorkflowStep, detail: str) -> None:
        with self._lock:
            display = self._steps[step.step_id]
            display.state = "processing"
            display.detail = detail
            self._refresh()

    def step_finished(self, outcome: StepOutcome, detail: str) -> None:
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
            self._refresh()

    def log(
        self, level: str, message: str, *, step_id: str | None = None,
    ) -> None:
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
        with self._lock:
            if self._live is None:
                return
            self._refresh()
            live, self._live = self._live, None
            live.stop()

    def _render_steps(self) -> RenderableType:
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
        progress: RenderableType = self._progress or Text("Preparing workflow")
        logs: RenderableType
        if self._log_messages:
            logs = Group(*self._log_messages)
        else:
            logs = Text("Waiting for step messages…", style="dim")
        return Group(
            Panel(progress, title="Workflow", border_style="blue"),
            Panel(
                self._render_steps(), title="Steps", border_style="cyan",
                height=self._step_lines + 2,
            ),
            Panel(logs, title="Logs", border_style="dim"),
        )

    def _refresh(self) -> None:
        if self._live is not None:
            self._live.update(self._render(), refresh=True)


__all__ = [
    "NullWorkflowMonitor", "RichWorkflowMonitor", "WorkflowExecutionMonitor",
]
