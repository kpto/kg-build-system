"""The module contract: contributions, steps, executions and artifacts.

These values are the shared vocabulary between the kernel and every module.
They are frozen and carry no service object; the execution services are passed
to an executor separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fnmatch import fnmatchcase
from typing import Any, Generic, Literal, TypeVar

ConfigT = TypeVar("ConfigT", covariant=True)


@dataclass(frozen=True, slots=True)
class ArtifactType:
    namespace: str
    name: str


def type_matches(declared: ArtifactType, actual: ArtifactType) -> bool:
    return (
        fnmatchcase(actual.namespace, declared.namespace)
        and fnmatchcase(actual.name, declared.name)
    )


@dataclass(frozen=True, slots=True)
class Input:
    type: ArtifactType
    name: str | None = None


@dataclass(frozen=True, slots=True)
class Output:
    type: ArtifactType
    name: str | None = None


@dataclass(frozen=True, slots=True)
class Publication:
    type: ArtifactType
    name: str | None = None


Given = Output | Publication


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    inputs: tuple[Input, ...] = ()
    outputs: tuple[Given, ...] = ()
    name: str | None = None
    assembly_preference: Literal["eager", "deferred"] = "eager"


@dataclass(frozen=True, slots=True)
class ModuleReference:
    module_id: str
    import_module: str
    class_qualname: str
    implementation_version: str
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
class WorkflowContribution:
    module: ModuleDefinition
    steps: tuple[WorkflowStep, ...] = ()
    variables: Any = None


@dataclass(frozen=True, slots=True)
class TakenInput:
    type: ArtifactType
    name: str
    input_name: str


class StepStatus(StrEnum):
    SUCCEEDED = "succeeded"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class Failure:
    message: str
    module_id: str
    step_id: str
    exception_type: str | None = None


@dataclass(frozen=True, slots=True)
class Artifact:
    output_name: str
    type: ArtifactType
    value: Any


@dataclass(frozen=True, slots=True)
class StepOutcome:
    step_id: str
    module_id: str
    status: StepStatus
    artifacts: tuple[Artifact, ...] = ()
    failure: Failure | None = None


@dataclass(frozen=True, slots=True)
class ContinuableInput:
    output_id: str
    status: Literal[StepStatus.SUCCEEDED, StepStatus.WARNING]
    artifact: Artifact | None


@dataclass(frozen=True, slots=True)
class DisruptingInput:
    output_id: str
    status: Literal[StepStatus.FAILED, StepStatus.SKIPPED]
    artifact: Artifact | None
    failure: Failure | None


@dataclass(frozen=True, slots=True)
class DefinedStep:
    name: str
    inputs: tuple[TakenInput, ...] = ()
    outputs: tuple[Given, ...] = ()


@dataclass(frozen=True, slots=True)
class DefinedContribution:
    module: ModuleDefinition
    steps: tuple[DefinedStep, ...] = ()
    variables: Any = None


@dataclass(frozen=True, slots=True)
class Connection:
    input_id: str
    output_id: str


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    module: ModuleDefinition
    step: DefinedStep
    module_id: str
    step_id: str
    variables: Any
    runtime_configuration: Any
    inputs: Any
    services: Any


@dataclass(frozen=True, slots=True)
class DisruptedExecutionContext:
    module: ModuleDefinition
    step: DefinedStep
    module_id: str
    step_id: str
    variables: Any
    runtime_configuration: Any
    inputs: Any
    disruptions: tuple[DisruptingInput, ...]
    services: Any


@dataclass(frozen=True, slots=True)
class ExecutorFactoryContext:
    module: ModuleDefinition
    variables: Any
    runtime_configuration: Any


@dataclass(frozen=True, slots=True)
class PublishedArtifact:
    type: ArtifactType
    value: Any


@dataclass(frozen=True, slots=True)
class CompilationContext(Generic[ConfigT]):
    build: Any
    module_id: str
    configuration: ConfigT
    blueprint: Any = None
    engine: Any = None


__all__ = [
    "Artifact", "ArtifactType", "CompilationContext", "Connection",
    "ContinuableInput", "DefinedContribution", "DefinedStep",
    "DisruptedExecutionContext", "DisruptingInput", "ExecutionContext",
    "ExecutorFactoryContext", "Failure", "Given", "Input", "ModuleDefinition",
    "ModuleReference", "Output", "Publication",
    "PublishedArtifact", "RuntimeFieldDefinition", "StepOutcome", "StepStatus",
    "TakenInput", "WorkflowContribution", "WorkflowStep", "type_matches",
]
