"""Compatibility shim for :mod:`kg_build_system.workflow.internal.ir`."""
from __future__ import annotations

from .internal.ir import (
    ArtifactTypeIR,
    ConnectionIR,
    ContributionIR,
    GivenIR,
    InputIR,
    ModuleReferenceIR,
    OutputIR,
    PublicationIR,
    RuntimeFieldIR,
    StepIR,
    WorkflowContractIR,
    WorkflowDefinitionIR,
    WorkflowIR,
    decode_workflow_contract,
    encode_workflow_contract,
    workflow_contract_from_json,
    workflow_contract_json,
    workflow_contract_to_json,
)

__all__ = [
    "ArtifactTypeIR",
    "ConnectionIR",
    "ContributionIR",
    "GivenIR",
    "InputIR",
    "ModuleReferenceIR",
    "OutputIR",
    "PublicationIR",
    "RuntimeFieldIR",
    "StepIR",
    "WorkflowContractIR",
    "WorkflowDefinitionIR",
    "WorkflowIR",
    "decode_workflow_contract",
    "encode_workflow_contract",
    "workflow_contract_from_json",
    "workflow_contract_json",
    "workflow_contract_to_json",
]
