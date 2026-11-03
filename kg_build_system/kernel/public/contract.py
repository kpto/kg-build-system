"""The module contract: contributions, steps, executions and artifacts.

These values are the shared vocabulary between the kernel and every module.
They are frozen and carry no service object. Execution services are passed to
an executor separately, through the ``services`` field of an execution context.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fnmatch import fnmatchcase
from typing import Any, Generic, Literal, TypeVar

ConfigT = TypeVar("ConfigT", covariant=True)


@dataclass(frozen=True, slots=True)
class ArtifactType:
    """The declared type of an artifact, as a namespace and a name.

    Both fields are patterns when used in an ``Input``; matching uses
    ``fnmatchcase``. An actual artifact type must match both patterns.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType

    value_type = ArtifactType("echo", "text")
    assert value_type.name == "text"
    ```
    """

    namespace: str
    name: str


def type_matches(declared: ArtifactType, actual: ArtifactType) -> bool:
    """Return whether ``actual`` satisfies the patterns in ``declared``.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, type_matches

    declared = ArtifactType("echo", "*")
    assert type_matches(declared, ArtifactType("echo", "text"))
    ```
    """
    return (
        fnmatchcase(actual.namespace, declared.namespace)
        and fnmatchcase(actual.name, declared.name)
    )


@dataclass(frozen=True, slots=True)
class Input:
    """A typed input a step consumes from another step's output.

    ``name`` selects a named output; ``None`` accepts the first output whose
    type matches.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, Input

    source = Input(ArtifactType("echo", "text"), "value")
    ```
    """

    type: ArtifactType
    name: str | None = None


@dataclass(frozen=True, slots=True)
class Output:
    """An artifact a step produces for downstream steps.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, Output

    result = Output(ArtifactType("echo", "text"), "value")
    ```
    """

    type: ArtifactType
    name: str | None = None


@dataclass(frozen=True, slots=True)
class Publication:
    """An output that is also a final build artifact.

    A publication is addressable downstream like an output and appears in the
    build report after execution.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, Publication

    report = Publication(ArtifactType("echo", "text"), "value")
    ```
    """

    type: ArtifactType
    name: str | None = None


Given = Output | Publication


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """One step a module contributes to the workflow contract.

    ``assembly_preference`` is ``"eager"`` when the assembler may share or
    reorganise the step, and ``"deferred"`` when it must keep the step intact.

    Example:
    ```python
    from kg_build_system.kernel import (
        ArtifactType, Input, Output, WorkflowStep,
    )

    step = WorkflowStep(
        inputs=(Input(ArtifactType("echo", "text")),),
        outputs=(Output(ArtifactType("echo", "text"), "value"),),
        name="echo",
    )
    ```
    """

    inputs: tuple[Input, ...] = ()
    outputs: tuple[Given, ...] = ()
    name: str | None = None
    assembly_preference: Literal["eager", "deferred"] = "eager"


@dataclass(frozen=True, slots=True)
class ModuleReference:
    """How to load a module implementation and the configuration to give it.

    The reference is enough to import the module class and instantiate its
    configuration; it stores no live class or object.

    Example:
    ```python
    from kg_build_system.kernel import ModuleReference

    reference = ModuleReference(
        "echo", "my_package.echo", "EchoModule", "1",
    )
    ```
    """

    module_id: str
    import_module: str
    class_qualname: str
    implementation_version: str
    configuration: Any = None


@dataclass(frozen=True, slots=True)
class RuntimeFieldDefinition:
    """One runtime value an operator must supply for a module.

    Example:
    ```python
    from kg_build_system.kernel import RuntimeFieldDefinition

    field = RuntimeFieldDefinition(
        "api_token", "Token for the source API", secret=True,
    )
    ```
    """

    key: str
    description: str
    required: bool = True
    value_type: Literal["string", "integer", "number", "boolean", "json"] = "string"
    secret: bool = False


@dataclass(frozen=True, slots=True)
class ModuleDefinition:
    """A module reference plus the runtime fields its execution needs.

    Example:
    ```python
    from kg_build_system.kernel import (
        ModuleDefinition, ModuleReference, RuntimeFieldDefinition,
    )

    module = ModuleDefinition(
        ModuleReference("echo", "my_package.echo", "EchoModule", "1"),
        (RuntimeFieldDefinition("prefix", "Text to prepend"),),
    )
    ```
    """

    reference: ModuleReference
    runtime_fields: tuple[RuntimeFieldDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkflowContribution:
    """The steps and variables one module contributes to a workflow.

    Example:
    ```python
    from kg_build_system.kernel import (
        ModuleDefinition, ModuleReference, WorkflowContribution, WorkflowStep,
    )

    contribution = WorkflowContribution(
        ModuleDefinition(ModuleReference(
            "echo", "my_package.echo", "EchoModule", "1",
        )),
        (WorkflowStep(name="echo"),),
    )
    ```
    """

    module: ModuleDefinition
    steps: tuple[WorkflowStep, ...] = ()
    variables: Any = None


@dataclass(frozen=True, slots=True)
class TakenInput:
    """An input already bound to a concrete upstream output.

    ``input_name`` is the consuming step's input name; ``type`` and ``name``
    identify the upstream artifact.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, TakenInput

    taken = TakenInput(ArtifactType("echo", "text"), "value", "source")
    ```
    """

    type: ArtifactType
    name: str
    input_name: str


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
    """Why a step failed, with the module and step that produced it.

    Example:
    ```python
    from kg_build_system.kernel import Failure

    failure = Failure("missing source", "echo", "echo", "FileNotFoundError")
    ```
    """

    message: str
    module_id: str
    step_id: str
    exception_type: str | None = None


@dataclass(frozen=True, slots=True)
class Artifact:
    """A value produced by a step under one output name and type.

    Example:
    ```python
    from kg_build_system.kernel import Artifact, ArtifactType

    artifact = Artifact("value", ArtifactType("echo", "text"), "hello")
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
    from kg_build_system.kernel import Artifact, ArtifactType, StepOutcome, StepStatus

    outcome = StepOutcome(
        "echo", "echo", StepStatus.SUCCEEDED,
        (Artifact("value", ArtifactType("echo", "text"), "hello"),),
    )
    ```
    """

    step_id: str
    module_id: str
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

    ready = ContinuableInput("echo.value", StepStatus.SUCCEEDED, None)
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

    broken = DisruptingInput("echo.value", StepStatus.FAILED, None, None)
    ```
    """

    output_id: str
    status: Literal[StepStatus.FAILED, StepStatus.SKIPPED]
    artifact: Artifact | None
    failure: Failure | None


@dataclass(frozen=True, slots=True)
class DefinedStep:
    """A workflow step after inputs and outputs have been resolved.

    ``instruction`` is the step's opaque instruction value, kept intact from the
    contract. An executor reads its ``kind`` and ``payload``; the kernel does not
    interpret either.

    Example:
    ```python
    from kg_build_system.kernel import DefinedStep

    step = DefinedStep("echo")
    ```
    """

    name: str
    inputs: tuple[TakenInput, ...] = ()
    outputs: tuple[Given, ...] = ()
    instruction: Any = None


@dataclass(frozen=True, slots=True)
class DefinedContribution:
    """A contribution after its steps have been resolved into defined steps.

    Example:
    ```python
    from kg_build_system.kernel import (
        DefinedContribution, ModuleDefinition, ModuleReference,
    )

    defined = DefinedContribution(
        ModuleDefinition(ModuleReference(
            "echo", "my_package.echo", "EchoModule", "1",
        )),
    )
    ```
    """

    module: ModuleDefinition
    steps: tuple[DefinedStep, ...] = ()
    variables: Any = None


@dataclass(frozen=True, slots=True)
class Connection:
    """A resolved edge from one output to one input in the workflow.

    Example:
    ```python
    from kg_build_system.kernel import Connection

    edge = Connection("echo.source", "echo.value")
    ```
    """

    input_id: str
    output_id: str


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Everything an executor needs to run one normal step.

    ``services`` carries live execution services; the contract value itself
    stays frozen and holds no engine or connection of its own.

    Example:
    ```python
    from kg_build_system.kernel import (
        DefinedStep, ExecutionContext, ModuleDefinition, ModuleReference,
    )

    context = ExecutionContext(
        ModuleDefinition(ModuleReference(
            "echo", "my_package.echo", "EchoModule", "1",
        )),
        DefinedStep("echo"),
        "echo",
        "echo",
        variables=None,
        runtime_configuration=None,
        inputs={},
        services=None,
    )
    ```
    """

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
    """Everything an executor needs when an upstream input failed or was skipped.

    ``disruptions`` names the upstream results that blocked the step. The
    executor normally records a skipped outcome instead of running the step.

    Example:
    ```python
    from kg_build_system.kernel import (
        DefinedStep, DisruptedExecutionContext, ModuleDefinition, ModuleReference,
    )

    context = DisruptedExecutionContext(
        ModuleDefinition(ModuleReference(
            "echo", "my_package.echo", "EchoModule", "1",
        )),
        DefinedStep("echo"),
        "echo",
        "echo",
        variables=None,
        runtime_configuration=None,
        inputs={},
        disruptions=(),
        services=None,
    )
    ```
    """

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
    """The frozen facts a module receives when it creates an executor.

    Example:
    ```python
    from kg_build_system.kernel import (
        ExecutorFactoryContext, ModuleDefinition, ModuleReference,
    )

    context = ExecutorFactoryContext(
        ModuleDefinition(ModuleReference(
            "echo", "my_package.echo", "EchoModule", "1",
        )),
        variables=None,
        runtime_configuration=None,
    )
    ```
    """

    module: ModuleDefinition
    variables: Any
    runtime_configuration: Any


@dataclass(frozen=True, slots=True)
class PublishedArtifact:
    """A final artifact of a successful build.

    Example:
    ```python
    from kg_build_system.kernel import ArtifactType, PublishedArtifact

    published = PublishedArtifact(ArtifactType("echo", "text"), "hello")
    ```
    """

    type: ArtifactType
    value: Any


@dataclass(frozen=True, slots=True)
class CompilationContext(Generic[ConfigT]):
    """The frozen context a module compiler receives.

    ``build`` is the transcribed build, ``configuration`` is an instance of the
    module's ``CONFIGURATION_TYPE``, and ``blueprint``/``engine`` are optional
    compatibility views supplied by the composition layer.

    Example:
    ```python
    from kg_build_system.kernel import Build, CompilationContext

    context = CompilationContext(
        build=Build({"echo": ("hello",)}),
        module_id="echo",
        configuration=None,
    )
    assert context.build.part("echo") == ("hello",)
    ```
    """

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
