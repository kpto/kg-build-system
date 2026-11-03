"""The shared workflow contract artifact.

Compilation produces a :class:`WorkflowContractDTO`; a build consumes it. The
contract owns contributions, steps, connections and provenance, while each step
owns its opaque instruction.
"""
from __future__ import annotations

from .public import (
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
]
