"""The runtime model: configuration, execution contexts, outcomes and reports.

These values are frozen and anaemic. Live services are passed to an executor
through ``services``; they are not stored in the model, and the kernel never
inspects them.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from .workflow import ArtifactType, Step


@dataclass(frozen=True, slots=True)
class RuntimeConfiguration:
    """How one workflow run is configured.

    ``component_configuration`` holds per-component runtime values keyed by the
    component id. ``credentials`` maps a credential reference to its value.

    Example:
    ```python
    from pathlib import Path

    from kg_build_system.kernel import RuntimeConfiguration

    configuration = RuntimeConfiguration(
        output_directory=Path("build"),
        working_directory=Path("build/_workdir"),
        component_configuration={"echo": {"prefix": "hello"}},
    )
    ```
    """

    output_directory: Path
    working_directory: Path
    temporary_directory: Path | None = None
    credentials: Mapping[str, str] = field(default_factory=dict)
    component_configuration: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict,
    )


class StepStatus(StrEnum):
    """The outcome of executing one step.

    ``SUCCEEDED`` and ``WARNING`` may feed downstream steps. ``FAILED`` and
    ``SKIPPED`` disrupt them, and the executor receives a disrupted context.

    Example:
    ```python
    from kg_build_system.kernel import StepStatus

    assert StepStatus.SUCCEEDED == "succeeded"
    ```
    """

    SUCCEEDED = "succeeded"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class Failure:
    """Why one step failed.

    Example:
    ```python
    from kg_build_system.kernel import Failure

    failure = Failure("missing source", "echo.echo", "FileNotFoundError")
    assert failure.step_id == "echo.echo"
    ```
    """

    message: str
    step_id: str
    exception_type: str | None = None


@dataclass(frozen=True, slots=True)
class Artifact:
    """A value produced by a step under one output name and type.

    Example:
    ```python
    from kg_build_system.kernel import Artifact, ArtifactType

    artifact = Artifact("value", ArtifactType("echo", "text"), "hello")
    assert artifact.value == "hello"
    ```
    """

    output_name: str
    type: ArtifactType
    value: Any


@dataclass(frozen=True, slots=True)
class StepOutcome:
    """What one step execution produced: artifacts, status and failure.

    Example:
    ```python
    from kg_build_system.kernel import (
        Artifact, ArtifactType, StepOutcome, StepStatus,
    )

    outcome = StepOutcome(
        "echo.echo",
        StepStatus.SUCCEEDED,
        (Artifact("value", ArtifactType("echo", "text"), "hello"),),
    )
    assert outcome.status is StepStatus.SUCCEEDED
    ```
    """

    step_id: str
    status: StepStatus
    artifacts: tuple[Artifact, ...] = ()
    failure: Failure | None = None


@dataclass(frozen=True, slots=True)
class ContinuableInput:
    """An upstream result that a downstream step may still consume.

    The status is restricted to ``SUCCEEDED`` and ``WARNING``.

    Example:
    ```python
    from kg_build_system.kernel import ContinuableInput, StepStatus

    ready = ContinuableInput("echo.echo.value", StepStatus.SUCCEEDED, None)
    assert ready.artifact is None
    ```
    """

    output_id: str
    status: Literal[StepStatus.SUCCEEDED, StepStatus.WARNING]
    artifact: Artifact | None


@dataclass(frozen=True, slots=True)
class DisruptingInput:
    """An upstream result that prevents a downstream step from running normally.

    The status is restricted to ``FAILED`` and ``SKIPPED``.

    Example:
    ```python
    from kg_build_system.kernel import DisruptingInput, StepStatus

    broken = DisruptingInput("echo.echo.value", StepStatus.FAILED, None, None)
    assert broken.failure is None
    ```
    """

    output_id: str
    status: Literal[StepStatus.FAILED, StepStatus.SKIPPED]
    artifact: Artifact | None
    failure: Failure | None


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Everything an executor needs to run one normal step.

    ``inputs`` is keyed by the consuming step's declared input name; each value
    is the tuple of continuable upstream results for that input.

    Example:
    ```python
    from kg_build_system.kernel import ExecutionContext, Step

    context = ExecutionContext(
        step=step,
        step_id="echo.echo",
        component="echo",
        runtime_configuration={},
        inputs={},
        services=None,
    )
    ```
    """

    step: Step
    step_id: str
    component: str
    runtime_configuration: Mapping[str, Any]
    inputs: Mapping[str, tuple[ContinuableInput, ...]]
    services: Any


@dataclass(frozen=True, slots=True)
class DisruptedExecutionContext:
    """Everything an executor needs when an upstream input failed or was skipped.

    ``disruptions`` names the upstream results that blocked the step. The
    executor normally records a skipped outcome instead of running the step.

    Example:
    ```python
    from kg_build_system.kernel import DisruptedExecutionContext

    context = DisruptedExecutionContext(
        step=step,
        step_id="echo.echo",
        component="echo",
        runtime_configuration={},
        inputs={},
        disruptions=(),
        services=None,
    )
    ```
    """

    step: Step
    step_id: str
    component: str
    runtime_configuration: Mapping[str, Any]
    inputs: Mapping[str, tuple[ContinuableInput | DisruptingInput, ...]]
    disruptions: tuple[DisruptingInput, ...]
    services: Any


@dataclass(frozen=True, slots=True)
class PublishedArtifact:
    """A final artifact of a successful workflow.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, PublishedArtifact

    published = PublishedArtifact(ArtifactType("echo", "text"), "hello")
    assert published.value == "hello"
    ```
    """

    type: ArtifactType
    value: Any


@dataclass(frozen=True, slots=True)
class WorkflowReport:
    """The user-facing result of a completed workflow.

    Example:
    ```python
    from kg_build_system.kernel import WorkflowReport

    report = WorkflowReport((), (), (), {})
    assert report.succeeded
    ```
    """

    published_artifacts: tuple[PublishedArtifact, ...]
    recovered_failures: tuple[Failure, ...]
    unresolved_failures: tuple[Failure, ...]
    provenance: dict[str, Any]

    @property
    def succeeded(self) -> bool:
        """Whether no failure blocked a publication.

        Example:
        ```python
        report = WorkflowReport((), (), (), {})
        assert report.succeeded == (not report.unresolved_failures)
        ```
        """
        return not self.unresolved_failures


__all__ = [
    "Artifact", "ContinuableInput", "DisruptedExecutionContext",
    "DisruptingInput", "ExecutionContext", "Failure", "PublishedArtifact",
    "RuntimeConfiguration", "StepOutcome", "StepStatus", "WorkflowReport",
]
