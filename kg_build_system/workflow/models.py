"""Runtime-only workflow models shared by the executor and workflow modules."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, TypeAlias

from .services import ExecutionServices


@dataclass(frozen=True, slots=True)
class ModuleReference:
    module_id: str
    import_module: str
    class_qualname: str
    implementation_version: str
    priority: int
    configuration: Any = None


@dataclass(frozen=True, slots=True)
class RuntimeFieldDefinition:
    key: str
    description: str
    required: bool = True
    value_type: Literal["string", "integer", "number", "boolean", "json"] = "string"
    secret: bool = False


@dataclass(frozen=True, slots=True)
class ModuleDefinition:
    reference: ModuleReference
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class ArtifactRole:
    namespace: str
    name: str


@dataclass(frozen=True, slots=True)
class OutputSlot:
    slot_id: str
    artifact_role: ArtifactRole


@dataclass(frozen=True, slots=True)
class SingleInputSlot:
    slot_id: str
    kind: Literal["single"] = "single"


@dataclass(frozen=True, slots=True)
class CollectionInputSlot:
    slot_id: str
    kind: Literal["collection"] = "collection"


InputSlot: TypeAlias = SingleInputSlot | CollectionInputSlot


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    step_id: str
    module_id: str
    assembly_preference: Literal["eager", "deferred"] = "eager"
    inputs: tuple[InputSlot, ...] = ()
    outputs: tuple[OutputSlot, ...] = ()
    payload: Any = None


@dataclass(frozen=True, slots=True)
class Connection:
    input_slot_id: str
    output_slot_id: str


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    modules: tuple[ModuleDefinition, ...]
    steps: tuple[WorkflowStep, ...]
    connections: tuple[Connection, ...] = ()


class StepStatus(StrEnum):
    SUCCEEDED = "succeeded"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


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


class WorkflowArtifactRoles:
    """Workflow-owned artifact-role conventions for module implementers."""

    NAMESPACE = "workflow"

    @classmethod
    def published(cls, module_id: str, name: str) -> ArtifactRole:
        return ArtifactRole(namespace=cls.NAMESPACE, name=f"publication.{module_id}.{name}")

    @classmethod
    def is_published(cls, role: ArtifactRole) -> bool:
        return role.namespace == cls.NAMESPACE and role.name.startswith("publication.")


@dataclass(frozen=True)
class StepOutcome:
    """The complete runtime result for one declared workflow step."""

    step_id: str
    module_id: str
    status: StepStatus
    # A step may omit a declared output when it has no meaningful runtime
    # artifact to publish. Consumers then receive no artifact for that slot.
    artifacts: tuple[Artifact, ...] = ()
    failure: Failure | None = None


@dataclass(frozen=True)
class ContinuableInput:
    """A connected output whose producer completed successfully or warned."""

    output_slot_id: str
    status: Literal[StepStatus.SUCCEEDED, StepStatus.WARNING]
    artifact: Artifact | None


@dataclass(frozen=True)
class DisruptingInput:
    """A connected output whose producer failed or was skipped."""

    output_slot_id: str
    status: Literal[StepStatus.FAILED, StepStatus.SKIPPED]
    artifact: Artifact | None
    failure: Failure | None


@dataclass(frozen=True)
class BuildRuntime:
    credentials: dict[str, str] = field(default_factory=dict)
    module_configuration: dict[str, dict[str, Any]] = field(default_factory=dict)
    output_directory: Path = field(default_factory=lambda: Path.cwd())
    working_directory: Path | None = None
    temporary_directory: Path | None = None


@dataclass(frozen=True)
class ExecutionContext:
    module: ModuleDefinition
    step: WorkflowStep
    runtime_configuration: Mapping[str, Any]
    inputs: Mapping[str, tuple[ContinuableInput, ...]]
    services: ExecutionServices


@dataclass(frozen=True)
class DisruptedExecutionContext:
    """Context for a step with at least one failed or skipped input."""

    module: ModuleDefinition
    step: WorkflowStep
    runtime_configuration: Mapping[str, Any]
    inputs: Mapping[str, tuple[ContinuableInput | DisruptingInput, ...]]
    disruptions: tuple[DisruptingInput, ...]
    services: ExecutionServices


@dataclass(frozen=True)
class ExecutorFactoryContext:
    """Generic context used once while constructing a module executor."""

    module: ModuleDefinition
    runtime_configuration: Mapping[str, Any]
    services: ExecutionServices


@dataclass(frozen=True)
class PublishedArtifact:
    """A semantic workflow result, without producer-specific slot metadata."""

    role: ArtifactRole
    value: Any


@dataclass(frozen=True)
class WorkflowReport:
    """The user-facing result of a completed workflow."""

    published_artifacts: tuple[PublishedArtifact, ...]
    recovered_failures: tuple[Failure, ...]
    unresolved_failures: tuple[Failure, ...]
    provenance: dict[str, Any]

    @property
    def succeeded(self) -> bool:
        return not self.unresolved_failures
