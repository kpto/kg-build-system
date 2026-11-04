"""Pipeline events and the resource registry a run publishes while it executes.

The pipeline emits events. A frontend presentation is a listener; a resource
provider is a listener that owns the resource lifecycle. The kernel defines the
event values, the bus and the registry and knows neither the presentation nor
the provider's resources.

A listener error propagates through ``EventBus.emit``. The runtime treats that
error as a pipeline failure and emits ``PipelineHalted`` before re-raising it.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .runtime import RuntimeConfiguration, StepOutcome, WorkflowReport
from .workflow import StepId, WorkflowPlan


class ResourceRegistry:
    """The live resources one run publishes, keyed by their exact type.

    Providers add resources while they handle ``PipelineStarted``; the runtime
    reads the registry to validate executor declarations and to build one
    ``ResourceView`` per executor. A duplicate exact type is refused.

    Example:
    ```python
    from kg_build_system.kernel import ResourceRegistry

    resources = ResourceRegistry()
    resources.add(int, 7)
    assert resources.get(int) == 7
    ```
    """

    def __init__(self) -> None:
        self._values: dict[type, Any] = {}

    def add(self, resource_type: type, value: Any) -> None:
        """Add one live resource under its exact type.

        A second provider that supplies the same type raises ``ValueError``.

        Example:
        ```python
        resources = ResourceRegistry()
        resources.add(int, 1)
        ```
        """
        if resource_type in self._values:
            name = f"{resource_type.__module__}.{resource_type.__qualname__}"
            raise ValueError(
                f"duplicate resource type {name} provided by more than one "
                "provider"
            )
        self._values[resource_type] = value

    def get(self, resource_type: type) -> Any:
        """Return the resource of one exact type.

        Example:
        ```python
        resources = ResourceRegistry()
        resources.add(str, "connected")
        assert resources.get(str) == "connected"
        ```
        """
        return self._values[resource_type]

    def snapshot(self) -> Mapping[type, Any]:
        """Return a copy of the resources available at this moment.

        Example:
        ```python
        resources = ResourceRegistry()
        resources.add(int, 1)
        assert resources.snapshot() == {int: 1}
        ```
        """
        return dict(self._values)


@dataclass(frozen=True, slots=True)
class PipelineStarted:
    """A run has started: its plan, configuration and empty resource registry.

    Example:
    ```python
    from kg_build_system.kernel import PipelineStarted, WorkflowPlan

    event = PipelineStarted(WorkflowPlan((), ()), configuration, resources)
    assert event.plan.steps == ()
    ```
    """

    plan: WorkflowPlan
    configuration: RuntimeConfiguration
    resources: ResourceRegistry


@dataclass(frozen=True, slots=True)
class StepStarted:
    """One step is about to execute.

    Example:
    ```python
    from kg_build_system.kernel import StepId, StepStarted

    event = StepStarted(StepId("core", "source"), "Reading 0 input(s)")
    assert event.step_id.name == "source"
    ```
    """

    step_id: StepId
    detail: str = ""


@dataclass(frozen=True, slots=True)
class StepFinished:
    """One step produced its outcome.

    Example:
    ```python
    from kg_build_system.kernel import StepFinished

    event = StepFinished(outcome, "succeeded; 1 artifact(s)")
    assert event.outcome.step_id == outcome.step_id
    ```
    """

    outcome: StepOutcome
    detail: str = ""


@dataclass(frozen=True, slots=True)
class StepLogged:
    """One step wrote a log message.

    Example:
    ```python
    from kg_build_system.kernel import StepId, StepLogged

    event = StepLogged(StepId("core", "source"), "info", "reading rows")
    assert event.level == "info"
    ```
    """

    step_id: StepId
    level: str
    message: str


@dataclass(frozen=True, slots=True)
class PipelineFinished:
    """A run completed and produced its report.

    Example:
    ```python
    from kg_build_system.kernel import PipelineFinished, WorkflowReport

    event = PipelineFinished(WorkflowReport((), (), (), {}))
    assert event.report.succeeded
    ```
    """

    report: WorkflowReport


@dataclass(frozen=True, slots=True)
class PipelineHalted:
    """A run stopped with an error before it could produce a report.

    Example:
    ```python
    from kg_build_system.kernel import PipelineHalted

    event = PipelineHalted(RuntimeError("missing resource"))
    assert str(event.error) == "missing resource"
    ```
    """

    error: BaseException


type PipelineEvent = (
    PipelineStarted | StepStarted | StepFinished | StepLogged
    | PipelineFinished | PipelineHalted
)
"""Every event one pipeline run emits."""

type Listener = Callable[[PipelineEvent], None]
"""A frontend or provider that observes every event of one run."""


class EventBus:
    """Deliver every event to every listener subscribed for one run.

    A listener is either a callable or an object exposing ``on_event``. A
    listener error propagates; the runtime classifies it as a pipeline failure.

    Example:
    ```python
    from kg_build_system.kernel import EventBus

    seen = []
    bus = EventBus()
    bus.subscribe(seen.append)
    ```
    """

    def __init__(self) -> None:
        self._listeners: list[Listener] = []
        self._failure: BaseException | None = None

    @property
    def failure(self) -> BaseException | None:
        """The last listener error, or ``None`` when no listener failed.

        Example:
        ```python
        bus = EventBus()
        assert bus.failure is None
        ```
        """
        return self._failure

    def subscribe(self, listener: Listener) -> None:
        """Subscribe one listener to this bus.

        Example:
        ```python
        bus.subscribe(lambda event: None)
        ```
        """
        self._listeners.append(listener)

    def emit(self, event: PipelineEvent) -> None:
        """Deliver one event to each listener in subscription order.

        A listener may also be an object with an ``on_event`` method. The first
        error stops delivery, is recorded on the bus and propagates.

        Example:
        ```python
        bus.emit(StepStarted(StepId("core", "source")))
        ```
        """
        for listener in tuple(self._listeners):
            handler = getattr(listener, "on_event", None)
            try:
                if callable(handler):
                    handler(event)
                else:
                    listener(event)
            except BaseException as error:
                self._failure = error
                raise


__all__ = [
    "EventBus",
    "Listener",
    "PipelineEvent",
    "PipelineFinished",
    "PipelineHalted",
    "PipelineStarted",
    "ResourceRegistry",
    "StepFinished",
    "StepLogged",
    "StepStarted",
]
