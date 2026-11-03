"""Framework-internal interface of the shared workflow contract.

The DTOs are the artifact vocabulary; the wrappers are the contract's assembly
and document services. The mechanisms live in ``_private``.
"""
from __future__ import annotations

from ..public import (
    ArtifactTypeDTO,
    ConnectionDTO,
    ContributionDTO,
    GivenDTO,
    InputDTO,
    InstructionDTO,
    ModuleDefinitionDTO,
    ModuleReferenceDTO,
    OutputDTO,
    PublicationDTO,
    RuntimeFieldDTO,
    StepDTO,
    WorkflowContractDTO,
)
from .service import (
    assemble_contract,
    contract_from_document,
    contract_to_document,
)

__all__ = [
    "ArtifactTypeDTO",
    "ConnectionDTO",
    "ContributionDTO",
    "GivenDTO",
    "InputDTO",
    "InstructionDTO",
    "ModuleDefinitionDTO",
    "ModuleReferenceDTO",
    "OutputDTO",
    "PublicationDTO",
    "RuntimeFieldDTO",
    "StepDTO",
    "WorkflowContractDTO",
    "assemble_contract",
    "contract_from_document",
    "contract_to_document",
]
