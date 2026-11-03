"""Framework-internal interface of the compilation package.

It exposes the module compilation pipeline, the engine-neutral relation plans,
the instruction emitters and the shared contract vocabulary. Callers outside the
framework use :func:`compile_blueprint`.
"""
from __future__ import annotations

from ...contract.public import (
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
from .compiler import (
    GraphBlueprint,
    assemble_contract,
    compile_blueprint,
    decompose,
)
from .instruction import (
    DuckDbSqlEmitter,
    InstructionEmitter,
    PythonInstructionEmitter,
    PythonReference,
    SqlEmissionContext,
)
from .relational import (
    Expand,
    Filter,
    RelationPlan,
    Scan,
    expansion_scope,
    plan_product,
)

__all__ = [
    "ArtifactTypeDTO",
    "ConnectionDTO",
    "ContributionDTO",
    "DuckDbSqlEmitter",
    "Expand",
    "Filter",
    "GivenDTO",
    "GraphBlueprint",
    "InputDTO",
    "InstructionDTO",
    "InstructionEmitter",
    "ModuleDefinitionDTO",
    "ModuleReferenceDTO",
    "OutputDTO",
    "PublicationDTO",
    "PythonInstructionEmitter",
    "PythonReference",
    "RelationPlan",
    "RuntimeFieldDTO",
    "Scan",
    "SqlEmissionContext",
    "StepDTO",
    "WorkflowContractDTO",
    "assemble_contract",
    "compile_blueprint",
    "decompose",
    "expansion_scope",
    "plan_product",
]
