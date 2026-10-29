"""The data a workflow is declared with, and the results of running one.

Every type here is amnesic data: it holds its own facts and nothing else. A step does not know
which module contributed it, a port does not know which step owns it, and no identity is stored
that the workflow can work out. The rules that need the wider picture are functions in
:mod:`.identity`, :mod:`.assembler` and :mod:`.executor`.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, ClassVar, Literal, TypeAlias

from .._frozen_json import FrozenJson, freeze_json


@dataclass(frozen=True, slots=True)
class ModuleReference:
    """Where a module's implementation lives, and how it is configured."""

    module_id: str
    import_module: str
    class_qualname: str
    implementation_version: str
    configuration: FrozenJson | None = None

    def __post_init__(self) -> None:
        if self.configuration is not None:
            object.__setattr__(self, "configuration", freeze_json(self.configuration))


@dataclass(frozen=True, slots=True)
class RuntimeFieldDefinition:
    """One setting a module asks for when the build runs rather than when it compiles."""

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
class ArtifactType:
    """What an artifact is: a namespace, and a name inside it.

    The two halves are matched by :func:`type_matches`, which reads ``*`` as any run of
    characters, so a name may be a pattern. A pattern asks a question and so belongs to an
    :class:`Input`; an :class:`Output` and a :class:`Publication` name one thing.
    """

    namespace: str
    name: str


def type_matches(declared: ArtifactType, actual: ArtifactType) -> bool:
    """Whether an artifact type is the one a declaration asked for, pattern included."""
    return (
        fnmatchcase(actual.namespace, declared.namespace)
        and fnmatchcase(actual.name, declared.name)
    )


@dataclass(frozen=True, slots=True)
class Input:
    """One opening where a step takes output.

    The type may be a pattern, which makes this an open input: the assembler answers it with
    one port per matching type, and the step then takes one output of each. Which output
    feeds any one of them is never the author's to say.
    """

    type: ArtifactType
    name: str | None = None


@dataclass(frozen=True, slots=True)
class Output:
    """One opening where a step gives out a value, which something must read."""

    type: ArtifactType
    name: str | None = None


@dataclass(frozen=True, slots=True)
class Publication:
    """One opening where a step hands a value to the build itself.

    A publication is given out by the step and read by nothing inside the workflow, which is
    why it is declared as this rather than as an :class:`Output`.
    """

    type: ArtifactType
    name: str | None = None


Given: TypeAlias = Output | Publication
"""What a step gives out: a value for the workflow to read, or one for the build."""


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """A declared unit of work, contributed by the module that wrote it.

    A name is optional and unique among the steps of its module; :mod:`.identity` forms the
    identity the workflow uses. ``assembly_preference`` is the step's own statement of when it
    runs relative to the others, and is one of the two things that place it in the rank order
    the assembler reads.
    """

    inputs: tuple[Input, ...] = ()
    outputs: tuple[Given, ...] = ()
    name: str | None = None
    assembly_preference: Literal["eager", "deferred"] = "eager"


@dataclass(frozen=True, slots=True)
class TakenInput:
    """An input of an assembled step: one opening answered with one type.

    ``name`` identifies this opening within its step and is what a connection names. An open
    input grows into one of these per matching type, and ``input_name`` records the declared
    input they all came from, which is how a running step receives them together.
    """

    type: ArtifactType
    name: str
    input_name: str


@dataclass(frozen=True, slots=True)
class DefinedStep:
    """A step of an assembled workflow, with every input answered and every name settled."""

    name: str
    inputs: tuple[TakenInput, ...] = ()
    outputs: tuple[Given, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkflowContribution:
    """One module's compilation result: its identity, its steps, and its private data.

    ``variables`` is opaque to every rule. A module that needs data per step keys it by step
    name inside its own variables, and the module's executor is handed the whole of it once.
    """

    module: ModuleDefinition
    steps: tuple[WorkflowStep, ...] = ()
    variables: FrozenJson | None = None

    def __post_init__(self) -> None:
        if self.variables is not None:
            object.__setattr__(self, "variables", freeze_json(self.variables))


@dataclass(frozen=True, slots=True)
class DefinedContribution:
    """One module's part in an assembled workflow: its definition, steps and variables."""

    module: ModuleDefinition
    steps: tuple[DefinedStep, ...] = ()
    variables: FrozenJson | None = None

    def __post_init__(self) -> None:
        if self.variables is not None:
            object.__setattr__(self, "variables", freeze_json(self.variables))


@dataclass(frozen=True, slots=True)
class Connection:
    """One output feeding one input, both named by :mod:`.identity`."""

    input_id: str
    output_id: str


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """An assembled workflow: the contributions it was made from, and the connections."""

    contributions: tuple[DefinedContribution, ...]
    connections: tuple[Connection, ...] = ()

    @property
    def modules(self) -> tuple[ModuleDefinition, ...]:
        return tuple(contribution.module for contribution in self.contributions)

    @property
    def steps_by_module(self) -> tuple[tuple[str, DefinedStep], ...]:
        """Every step with the id of the module that contributed it, in contribution order."""
        return tuple(
            (contribution.module.reference.module_id, step)
            for contribution in self.contributions
            for step in contribution.steps
        )

    @property
    def variables_by_module(self) -> Mapping[str, FrozenJson | None]:
        """Each module's own data, which no rule of the workflow reads."""
        return {
            contribution.module.reference.module_id: contribution.variables
            for contribution in self.contributions
        }


class StepStatus(StrEnum):
    SUCCEEDED = "succeeded"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class Failure:
    """A runtime step failure, carrying the step it happened at."""

    message: str
    module_id: str
    step_id: str
    exception_type: str | None = None


@dataclass(frozen=True)
class Artifact:
    """A produced value, attached to the output of one step that declares it."""

    output_name: str
    type: ArtifactType
    value: Any


@dataclass(frozen=True)
class StepOutcome:
    """The complete runtime result for one declared workflow step.

    A step may omit a declared output when it has no meaningful value for it; consumers then
    receive no artifact for that output.
    """

    step_id: str
    module_id: str
    status: StepStatus
    artifacts: tuple[Artifact, ...] = ()
    failure: Failure | None = None


@dataclass(frozen=True)
class ContinuableInput:
    """A connected output whose producer succeeded or warned."""

    output_id: str
    status: Literal[StepStatus.SUCCEEDED, StepStatus.WARNING]
    artifact: Artifact | None


@dataclass(frozen=True)
class DisruptingInput:
    """A connected output whose producer failed or was skipped."""

    output_id: str
    status: Literal[StepStatus.FAILED, StepStatus.SKIPPED]
    artifact: Artifact | None
    failure: Failure | None


@dataclass(frozen=True)
class BuildRuntime:
    """How a build runs: where it writes, and the settings it is given."""

    credentials: dict[str, str] = field(default_factory=dict)
    module_configuration: dict[str, dict[str, Any]] = field(default_factory=dict)
    output_directory: Path = field(default_factory=lambda: Path.cwd() / "build")
    working_directory: Path = field(default_factory=lambda: Path("_workdir"))
    temporary_directory: Path | None = None
    duckdb_storage: Literal["memory", "disk"] = "memory"
    duckdb_threads: int | None = None
    duckdb_memory_limit: str | None = None
    duckdb_compression: bool = True

    def __post_init__(self) -> None:
        if not self.working_directory.is_absolute():
            object.__setattr__(
                self,
                "working_directory",
                self.output_directory / self.working_directory,
            )


@dataclass(frozen=True)
class ExecutionContext:
    """Everything a step's handler may use.

    ``inputs`` is keyed by the step's own input names, so an open input's several artifacts
    arrive together under the one name the author gave it. ``variables`` is the contributing
    module's own data, and ``step_id`` and ``module_id`` are the identities this step is known
    by outside itself.
    """

    module: ModuleDefinition
    step: DefinedStep
    module_id: str
    step_id: str
    variables: Mapping[str, Any]
    runtime_configuration: Mapping[str, Any]
    inputs: Mapping[str, tuple[ContinuableInput, ...]]


@dataclass(frozen=True)
class DisruptedExecutionContext:
    """Context for a step with at least one failed or skipped input."""

    module: ModuleDefinition
    step: DefinedStep
    module_id: str
    step_id: str
    variables: Mapping[str, Any]
    runtime_configuration: Mapping[str, Any]
    inputs: Mapping[str, tuple[ContinuableInput | DisruptingInput, ...]]
    disruptions: tuple[DisruptingInput, ...]


@dataclass(frozen=True)
class ExecutorFactoryContext:
    """Generic context used once while constructing a module executor."""

    module: ModuleDefinition
    variables: Mapping[str, Any]
    runtime_configuration: Mapping[str, Any]


@dataclass(frozen=True)
class PublishedArtifact:
    """A semantic workflow result, without the producing step's detail."""

    type: ArtifactType
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


__all__ = [
    "Artifact",
    "ArtifactType",
    "BuildRuntime",
    "Connection",
    "ContinuableInput",
    "DefinedContribution",
    "DefinedStep",
    "DisruptedExecutionContext",
    "DisruptingInput",
    "ExecutionContext",
    "ExecutorFactoryContext",
    "Failure",
    "Given",
    "Input",
    "ModuleDefinition",
    "ModuleReference",
    "Output",
    "Publication",
    "PublishedArtifact",
    "RuntimeFieldDefinition",
    "StepOutcome",
    "StepStatus",
    "TakenInput",
    "WorkflowContribution",
    "WorkflowDefinition",
    "WorkflowReport",
    "type_matches",
]
