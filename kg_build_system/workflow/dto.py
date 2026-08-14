"""Compilation-only transfer objects for a frozen workflow definition.

These types are not re-exported by :mod:`kg_build_system.workflow`; workflow
authoring and runtime APIs use their own models and interfaces.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from .._frozen_json import FrozenJson
from pydantic import BaseModel, ConfigDict, Field, JsonValue


@dataclass(frozen=True, slots=True)
class BlueprintModuleDTO:
    module_id: str
    module_import: str
    module_qualname: str
    configuration: FrozenJson | None = None


class WorkflowDTO(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ModuleReferenceDTO(WorkflowDTO):
    module_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    import_module: str = Field(min_length=1)
    class_qualname: str = Field(min_length=1)
    implementation_version: str = Field(min_length=1)
    priority: int = Field(ge=0)
    configuration: JsonValue | None = None


class RuntimeFieldDTO(WorkflowDTO):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    required: bool = True
    value_type: Literal["string", "integer", "number", "boolean", "json"] = "string"
    secret: bool = False


class ModuleDTO(WorkflowDTO):
    reference: ModuleReferenceDTO
    runtime_fields: tuple[RuntimeFieldDTO, ...] = ()


class ArtifactRoleDTO(WorkflowDTO):
    namespace: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)


class OutputSlotDTO(WorkflowDTO):
    slot_id: str = Field(min_length=1)
    artifact_role: ArtifactRoleDTO


class SingleInputSlotDTO(WorkflowDTO):
    kind: Literal["single"] = "single"
    slot_id: str = Field(min_length=1)


class CollectionInputSlotDTO(WorkflowDTO):
    kind: Literal["collection"] = "collection"
    slot_id: str = Field(min_length=1)


InputSlotDTO = Annotated[
    SingleInputSlotDTO | CollectionInputSlotDTO,
    Field(discriminator="kind"),
]


class WorkflowStepDTO(WorkflowDTO):
    step_id: str = Field(min_length=1)
    module_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    assembly_preference: Literal["eager", "deferred"] = "eager"
    inputs: tuple[InputSlotDTO, ...] = ()
    outputs: tuple[OutputSlotDTO, ...] = ()
    payload: JsonValue | None = None


class ConnectionDTO(WorkflowDTO):
    input_slot_id: str = Field(min_length=1)
    output_slot_id: str = Field(min_length=1)


class WorkflowDefinitionDTO(WorkflowDTO):
    modules: tuple[ModuleDTO, ...] = Field(min_length=1)
    steps: tuple[WorkflowStepDTO, ...] = Field(min_length=1)
    connections: tuple[ConnectionDTO, ...] = ()


__all__ = [
    "ArtifactRoleDTO", "BlueprintModuleDTO", "CollectionInputSlotDTO",
    "ConnectionDTO", "InputSlotDTO", "ModuleDTO", "ModuleReferenceDTO",
    "OutputSlotDTO", "RuntimeFieldDTO", "SingleInputSlotDTO",
    "WorkflowDefinitionDTO", "WorkflowStepDTO",
]
