"""Runtime-only workflow results shared by module executors and the build runner."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from ..compile.models import ArtifactRole, BuildContract, ModuleDefinition


class StepStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RECOVERED = "recovered"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Diagnostic:
    """A structured finding emitted by a completed workflow step."""

    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    module_id: str
    step_id: str
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Failure:
    """A runtime step failure; propagation is introduced in the next slice."""

    message: str
    module_id: str
    step_id: str
    exception_type: str | None = None


@dataclass(frozen=True)
class Artifact:
    """A produced runtime value attached to one declared output slot."""

    slot_id: str
    role: ArtifactRole
    value: Any


@dataclass(frozen=True)
class StepOutcome:
    """The complete runtime result for one declared workflow step."""

    step_id: str
    module_id: str
    status: StepStatus
    artifacts: tuple[Artifact, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    failure: Failure | None = None
    metrics: Mapping[str, int] = field(default_factory=dict)
    result: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModuleExecutionContext:
    contract: BuildContract
    module: ModuleDefinition
    runtime_configuration: Mapping[str, Any]
    inputs: Mapping[str, tuple[Artifact, ...]]
    services: Mapping[str, Any]
