"""Frontend monitors that observe pipeline events.

A monitor is a listener. It does not own execution, resources or scheduling;
``resolve_monitor`` turns the public ``monitor`` argument into a listener or
``None``. ``rich`` is optional and imported only when a console monitor writes.
"""
from __future__ import annotations

from typing import Any, Protocol

from kg_build_system.kernel import (
    PipelineEvent,
    PipelineFinished,
    PipelineHalted,
    PipelineStarted,
    StepFinished,
    StepLogged,
    StepStarted,
)


class Monitor(Protocol):
    """A frontend listener that presents one pipeline run.

    A monitor may be passed directly as a listener because it is callable, and
    the event bus also recognises an object exposing ``on_event``.

    Example:
    ```python
    from kg_build_system.frontend import NullMonitor

    monitor: Monitor = NullMonitor()
    ```
    """

    def on_event(self, event: PipelineEvent) -> None:
        """Handle one pipeline event.

        Example:
            ```python
            monitor.on_event(StepStarted(StepId("core", "source")))
            ```
        """
        ...

    def __call__(self, event: PipelineEvent) -> None:
        """Handle one event when the monitor is subscribed as a callable.

        Example:
            ```python
            monitor(StepStarted(StepId("core", "source")))
            ```
        """
        ...


class NullMonitor:
    """A monitor that presents nothing."""

    def on_event(self, event: PipelineEvent) -> None:
        """Ignore one pipeline event.

        Example:
            ```python
            NullMonitor().on_event(event)
            ```
        """
        pass

    def __call__(self, event: PipelineEvent) -> None:
        """Ignore one pipeline event.

        Example:
            ```python
            NullMonitor()(event)
            ```
        """
        self.on_event(event)


class ConsoleMonitor:
    """A simple text monitor for interactive builds.

    Messages are printed to a ``rich`` console when available; otherwise they
    are printed with the built-in ``print``. ``rich`` is imported lazily so the
    kernel and non-interactive runs do not load it.

    Example:
    ```python
    from kg_build_system.frontend import ConsoleMonitor

    monitor = ConsoleMonitor()
    ```
    """

    def __init__(self, console: Any = None) -> None:
        self._console = console

    def _write(self, text: str) -> None:
        console = self._console
        if console is None:
            try:
                from rich.console import Console
            except ImportError:
                print(text)
                return
            console = Console()
            self._console = console
        console.print(text)

    def on_event(self, event: PipelineEvent) -> None:
        """Render one pipeline event as one text line.

        Example:
            ```python
            ConsoleMonitor().on_event(StepStarted(StepId("core", "source")))
            ```
        """
        if isinstance(event, PipelineStarted):
            self._write(
                f"Pipeline started: {len(event.plan.steps)} step(s)",
            )
        elif isinstance(event, StepStarted):
            self._write(f"▶ {event.step_id} {event.detail}".rstrip())
        elif isinstance(event, StepLogged):
            self._write(
                f"[{event.step_id}] {event.level.upper()} {event.message}",
            )
        elif isinstance(event, StepFinished):
            self._write(
                f"■ {event.outcome.step_id} {event.detail}".rstrip(),
            )
        elif isinstance(event, PipelineFinished):
            self._write(
                "Pipeline finished: "
                f"{len(event.report.published_artifacts)} artifact(s)",
            )
        elif isinstance(event, PipelineHalted):
            self._write(f"Pipeline halted: {event.error}")

    def __call__(self, event: PipelineEvent) -> None:
        """Handle one event when the monitor is subscribed as a callable.

        Example:
            ```python
            ConsoleMonitor()(StepStarted(StepId("core", "source")))
            ```
        """
        self.on_event(event)


def resolve_monitor(value: Monitor | bool | None) -> Monitor | None:
    """Turn the public monitor argument into a listener or ``None``.

    ``False`` and ``None`` select no listener; ``True`` selects a
    ``ConsoleMonitor``; a monitor is returned unchanged.

    Example:
    ```python
    from kg_build_system.frontend import resolve_monitor

    assert resolve_monitor(False) is None
    assert isinstance(resolve_monitor(True), ConsoleMonitor)
    ```
    """
    if value is True:
        return ConsoleMonitor()
    if value is False or value is None:
        return None
    return value


__all__ = ["ConsoleMonitor", "Monitor", "NullMonitor", "resolve_monitor"]
