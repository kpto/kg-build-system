"""Compilation-only IR for a frozen workflow definition.

These types are not re-exported by :mod:`kg_build_system.workflow`; workflow
authoring and runtime APIs use their own models and interfaces.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from .._frozen_json import FrozenJson
from pydantic import BaseModel, ConfigDict, Field, JsonValue


@dataclass(frozen=True, slots=True)
class BlueprintModuleIR:
    module_id: str
    module_import: str
    module_qualname: str
    configuration: FrozenJson | None = None


class WorkflowIR(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ModuleReferenceIR(WorkflowIR):
    module_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    import_module: str = Field(min_length=1)
    class_qualname: str = Field(min_length=1)
    implementation_version: str = Field(min_length=1)
    priority: int = Field(ge=0)
    configuration: JsonValue | None = None


class RuntimeFieldIR(WorkflowIR):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    required: bool = True
    value_type: Literal["string", "integer", "number", "boolean", "json"] = "string"
    secret: bool = False


class ModuleIR(WorkflowIR):
    reference: ModuleReferenceIR
    runtime_fields: tuple[RuntimeFieldIR, ...] = ()


class ArtifactRoleIR(WorkflowIR):
    namespace: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)


class OutputSlotIR(WorkflowIR):
    slot_id: str = Field(min_length=1)
    artifact_role: ArtifactRoleIR


class SingleInputSlotIR(WorkflowIR):
    kind: Literal["single"] = "single"
    slot_id: str = Field(min_length=1)


class CollectionInputSlotIR(WorkflowIR):
    kind: Literal["collection"] = "collection"
    slot_id: str = Field(min_length=1)


InputSlotIR = Annotated[
    SingleInputSlotIR | CollectionInputSlotIR,
    Field(discriminator="kind"),
]


class WorkflowStepIR(WorkflowIR):
    step_id: str = Field(min_length=1)
    module_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    assembly_preference: Literal["eager", "deferred"] = "eager"
    inputs: tuple[InputSlotIR, ...] = ()
    outputs: tuple[OutputSlotIR, ...] = ()
    payload: JsonValue | None = None


class ConnectionIR(WorkflowIR):
    input_slot_id: str = Field(min_length=1)
    output_slot_id: str = Field(min_length=1)


class WorkflowDefinitionIR(WorkflowIR):
    modules: tuple[ModuleIR, ...] = Field(min_length=1)
    steps: tuple[WorkflowStepIR, ...] = Field(min_length=1)
    connections: tuple[ConnectionIR, ...] = ()


__all__ = [
    "ArtifactRoleIR", "BlueprintModuleIR", "CollectionInputSlotIR",
    "ConnectionIR", "InputSlotIR", "ModuleIR", "ModuleReferenceIR",
    "OutputSlotIR", "RuntimeFieldIR", "SingleInputSlotIR",
    "WorkflowDefinitionIR", "WorkflowStepIR",
]
