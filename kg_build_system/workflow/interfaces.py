"""Framework-internal interface of the workflow domain.

Other subpackages assemble a contract, execute it and implement module executors
here. A graph author reads ``build``, ``BuildRuntime`` and ``WorkflowReport``
from :mod:`kg_build_system.workflow`; the contract IR is
:mod:`kg_build_system.workflow.ir`.

The module contract itself is owned by :mod:`kg_build_system.kernel.contract`;
this interface re-exports it together with the assembled workflow values so a
module author has one import path.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Protocol

from .assembler import AssemblyError, assemble_workflow
from .contracts import create_workflow_contract
from .identity import (
    DEFAULT_INPUT_NAME,
    DEFAULT_OUTPUT_NAME,
    DEFAULT_STEP_NAME,
    expanded_input_name,
    input_name,
    opening_identity,
    output_name,
    step_identity,
    step_name,
    type_text,
)
from .ir import (
    WorkflowContractIR,
    decode_workflow_contract,
    encode_workflow_contract,
    workflow_contract_from_json,
    workflow_contract_json,
    workflow_contract_to_json,
)
from .mapping import type_from_ir, type_to_ir, workflow_from_ir, workflow_to_ir
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
    type_matches,
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
