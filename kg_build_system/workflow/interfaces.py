"""Framework-internal interface of the workflow domain.

Other subpackages assemble a contract, execute it and implement module executors
here. A graph author reads ``build``, ``BuildRuntime`` and ``WorkflowReport``
from :mod:`kg_build_system.workflow`; the contract IR is
:mod:`kg_build_system.workflow.ir`.

The module contract itself is owned by :mod:`kg_build_system.kernel.contract`;
this interface re-exports it together with the assembled workflow values so a
module author has one import path. The functions below are thin wrappers over
the workflow implementation modules: their signatures are the interface, and
the implementation stays private.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar, Protocol

from pydantic import JsonValue

from .assembler import AssemblyError, assemble_workflow as _assemble_workflow
from .contracts import create_workflow_contract as _create_workflow_contract
from .identity import (
    DEFAULT_INPUT_NAME,
    DEFAULT_OUTPUT_NAME,
    DEFAULT_STEP_NAME,
    expanded_input_name as _expanded_input_name,
    input_name as _input_name,
    opening_identity as _opening_identity,
    output_name as _output_name,
    step_identity as _step_identity,
    step_name as _step_name,
    type_text as _type_text,
)
from .ir import (
    ArtifactTypeIR,
    WorkflowContractIR,
    WorkflowDefinitionIR,
    decode_workflow_contract as _decode_workflow_contract,
    encode_workflow_contract as _encode_workflow_contract,
    workflow_contract_from_json as _workflow_contract_from_json,
    workflow_contract_json as _workflow_contract_json,
    workflow_contract_to_json as _workflow_contract_to_json,
)
from .mapping import (
    type_from_ir as _type_from_ir,
    type_to_ir as _type_to_ir,
    workflow_from_ir as _workflow_from_ir,
    workflow_to_ir as _workflow_to_ir,
)
from .models import (
    Artifact,
    ArtifactType,
    BuildRuntime,
    CompilationContext,
    Connection,
    ContinuableInput,
    DefinedContribution,
    DefinedStep,
    DisruptedExecutionContext,
    DisruptingInput,
    ExecutionContext,
    ExecutorFactoryContext,
    Failure,
    Given,
    Input,
    ModuleDefinition,
    ModuleReference,
    Output,
    Publication,
    PublishedArtifact,
    RuntimeFieldDefinition,
    StepOutcome,
    StepStatus,
    TakenInput,
    WorkflowContribution,
    WorkflowDefinition,
    WorkflowReport,
    WorkflowStep,
    type_matches as _type_matches,
)
from .monitor import (
    NullWorkflowMonitor,
    RichWorkflowMonitor,
    WorkflowExecutionMonitor,
)
from .services import (
    CredentialResolver,
    ExecutionServices,
    LocalTemporaryStorage,
    LocalWorkingStorage,
    MappingCredentialResolver,
    RelationQueryResult,
    RelationRef,
    RelationService,
    WorkflowLogger,
    WorkingStorage,
)


class ModuleExecutor(ABC):
    """Handles a step according to the state of its connected inputs.

    The services are on ``context.services``; the handler receives one context
    and returns one outcome in both the normal and disrupted cases.
    """

    @abstractmethod
    def handle(self, context: ExecutionContext) -> StepOutcome:
        """Handle a step whose every input producer succeeded or warned."""

    def handle_disrupted(self, context: DisruptedExecutionContext) -> StepOutcome:
        """Default response to failed or skipped inputs: skip this step."""
        return StepOutcome(
            step_id=context.step_id,
            module_id=context.module_id,
            status=StepStatus.SKIPPED,
        )


class ExecutableModule(Protocol):
    """Runtime capabilities of a module the executor can import."""

    ID: ClassVar[str]
    VERSION: ClassVar[str]

    @classmethod
    def create_executor(
        cls, context: ExecutorFactoryContext,
    ) -> ModuleExecutor: ...


def assemble_workflow(
    contributions: Sequence[WorkflowContribution],
) -> WorkflowDefinition:
    """Resolve the connections the contributed steps imply.

    Each contribution declares its steps' inputs and outputs; the assembler
    finds the wiring that feeds every input and reads every output. It raises
    :class:`AssemblyError` when no such wiring exists.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import assemble_workflow

    workflow = assemble_workflow(contributions)
    ```
    """
    return _assemble_workflow(contributions)


def create_workflow_contract(
    workflow: WorkflowDefinition,
    provenance: JsonValue | None = None,
) -> WorkflowContractIR:
    """Freeze an assembled workflow into an executable, fingerprinted contract.

    The fingerprint is the SHA-256 of the serialised workflow IR, so any change
    to order, steps, openings, types, module data or connections changes it.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import create_workflow_contract

    contract = create_workflow_contract(workflow, provenance={"compile": {}})
    ```
    """
    return _create_workflow_contract(workflow, provenance)


def workflow_to_ir(value: WorkflowDefinition) -> WorkflowDefinitionIR:
    """Map an assembled workflow to its serialisable IR.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import workflow_to_ir

    workflow_ir = workflow_to_ir(workflow)
    ```
    """
    return _workflow_to_ir(value)


def workflow_from_ir(value: WorkflowDefinitionIR) -> WorkflowDefinition:
    """Map workflow IR back to the domain model used during execution.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import workflow_from_ir

    workflow = workflow_from_ir(contract.workflow)
    ```
    """
    return _workflow_from_ir(value)


def type_to_ir(value: ArtifactType) -> ArtifactTypeIR:
    """Map an artifact type to its serialisable IR.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import ArtifactType, type_to_ir

    artifact_type_ir = type_to_ir(ArtifactType("kg", "row"))
    ```
    """
    return _type_to_ir(value)


def type_from_ir(value: ArtifactTypeIR) -> ArtifactType:
    """Map artifact-type IR back to the domain type.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import type_from_ir

    artifact_type = type_from_ir(contract.workflow.contributions[0].steps[0].outputs[0].type)
    ```
    """
    return _type_from_ir(value)


def encode_workflow_contract(value: WorkflowContractIR) -> dict[str, Any]:
    """Encode a contract into its canonical JSON-compatible representation.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import encode_workflow_contract

    document = encode_workflow_contract(contract)
    ```
    """
    return _encode_workflow_contract(value)


def decode_workflow_contract(value: Mapping[str, Any]) -> WorkflowContractIR:
    """Decode a contract from its canonical JSON-compatible representation.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import decode_workflow_contract

    contract = decode_workflow_contract(document)
    ```
    """
    return _decode_workflow_contract(value)


def workflow_contract_json(
    value: WorkflowContractIR, *, indent: int | None = None,
) -> str:
    """Render a contract as JSON text, the form written beside a build.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import workflow_contract_json

    text = workflow_contract_json(contract, indent=2)
    ```
    """
    return _workflow_contract_json(value, indent=indent)


def workflow_contract_to_json(
    value: WorkflowContractIR, *, indent: int | None = None,
) -> str:
    """Alias of :func:`workflow_contract_json`.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import workflow_contract_to_json

    text = workflow_contract_to_json(contract)
    ```
    """
    return _workflow_contract_to_json(value, indent=indent)


def workflow_contract_from_json(value: str | bytes) -> WorkflowContractIR:
    """Read a contract from the JSON text written by an earlier build.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import workflow_contract_from_json

    contract = workflow_contract_from_json(text)
    ```
    """
    return _workflow_contract_from_json(value)


def step_name(step: WorkflowStep, position: int) -> str:
    """The name a step goes by within its module: its own, or its position.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import WorkflowStep, step_name

    assert step_name(WorkflowStep(), 0) == "step1"
    ```
    """
    return _step_name(step, position)


def input_name(declared: Input) -> str:
    """The name a declared input goes by within its step.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import ArtifactType, Input, input_name

    assert input_name(Input(ArtifactType("kg", "row"))) == "input"
    ```
    """
    return _input_name(declared)


def output_name(given: Output | Publication) -> str:
    """The name a declared output or publication goes by within its step.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import ArtifactType, Output, output_name

    assert output_name(Output(ArtifactType("kg", "row"))) == "output"
    ```
    """
    return _output_name(given)


def type_text(artifact_type: ArtifactType) -> str:
    """One artifact type written as a single name, as it appears in an identity.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import ArtifactType, type_text

    assert type_text(ArtifactType("kg", "row")) == "kg.row"
    ```
    """
    return _type_text(artifact_type)


def expanded_input_name(declared_name: str, taken_type: ArtifactType) -> str:
    """The name of one port an open input grew into.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import ArtifactType, expanded_input_name

    assert expanded_input_name("row", ArtifactType("kg", "row")) == "row:kg.row"
    ```
    """
    return _expanded_input_name(declared_name, taken_type)


def step_identity(module_id: str, name: str) -> str:
    """The identity of one step across the whole workflow.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import step_identity

    assert step_identity("file", "write") == "file::write"
    ```
    """
    return _step_identity(module_id, name)


def opening_identity(identity: str, name: str) -> str:
    """The identity of one input or output of a step known by its identity.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import opening_identity

    assert opening_identity("file::write", "output") == "file::write.output"
    ```
    """
    return _opening_identity(identity, name)


def type_matches(declared: ArtifactType, actual: ArtifactType) -> bool:
    """Whether an actual artifact type satisfies a declared, possibly open type.

    Example:
    ```python
    from kg_build_system.workflow.interfaces import ArtifactType, type_matches

    assert type_matches(ArtifactType("kg", "row"), ArtifactType("kg", "row"))
    ```
    """
    return _type_matches(declared, actual)


__all__ = [
    "Artifact",
    "ArtifactType",
    "AssemblyError",
    "BuildRuntime",
    "CompilationContext",
    "Connection",
    "ContinuableInput",
    "CredentialResolver",
    "DefinedContribution",
    "DefinedStep",
    "DisruptedExecutionContext",
    "DisruptingInput",
    "ExecutableModule",
    "ExecutionContext",
    "ExecutionServices",
    "ExecutorFactoryContext",
    "Failure",
    "Given",
    "Input",
    "LocalTemporaryStorage",
    "LocalWorkingStorage",
    "MappingCredentialResolver",
    "ModuleDefinition",
    "ModuleExecutor",
    "ModuleReference",
    "NullWorkflowMonitor",
    "Output",
    "Publication",
    "PublishedArtifact",
    "RelationQueryResult",
    "RelationRef",
    "RelationService",
    "RichWorkflowMonitor",
    "RuntimeFieldDefinition",
    "StepOutcome",
    "StepStatus",
    "TakenInput",
    "WorkflowContribution",
    "WorkflowContractIR",
    "WorkflowDefinition",
    "WorkflowExecutionMonitor",
    "WorkflowLogger",
    "WorkflowReport",
    "WorkflowStep",
    "WorkingStorage",
    "assemble_workflow",
    "create_workflow_contract",
    "decode_workflow_contract",
    "encode_workflow_contract",
    "expanded_input_name",
    "input_name",
    "opening_identity",
    "output_name",
    "step_identity",
    "step_name",
    "type_from_ir",
    "type_matches",
    "type_text",
    "type_to_ir",
    "workflow_contract_from_json",
    "workflow_contract_json",
    "workflow_contract_to_json",
    "workflow_from_ir",
    "workflow_to_ir",
]
