"""Compilation-only IR for a frozen workflow definition.

These types are not re-exported by :mod:`kg_build_system.workflow`; workflow authoring and
runtime APIs use their own models and interfaces.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Final, Literal

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
    configuration: JsonValue | None = None


class RuntimeFieldIR(WorkflowIR):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    required: bool = True
    value_type: Literal["string", "integer", "number", "boolean", "json"] = "string"
    secret: bool = False


class ArtifactTypeIR(WorkflowIR):
    namespace: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)


class InputIR(WorkflowIR):
    """One answered opening of an assembled step.

    ``name`` identifies the opening, which an open input shares nothing of with its siblings, and
    ``input_name`` is the declared input it came from, which they all share.
    """

    type: ArtifactTypeIR
    name: str = Field(min_length=1)
    input_name: str = Field(min_length=1)


class OutputIR(WorkflowIR):
    kind: Literal["output"] = "output"
    type: ArtifactTypeIR
    name: str = Field(min_length=1)


class PublicationIR(WorkflowIR):
    kind: Literal["publication"] = "publication"
    type: ArtifactTypeIR
    name: str = Field(min_length=1)


GivenIR = Annotated[OutputIR | PublicationIR, Field(discriminator="kind")]


class StepIR(WorkflowIR):
    name: str = Field(min_length=1)
    inputs: tuple[InputIR, ...] = ()
    outputs: tuple[GivenIR, ...] = ()


class ContributionIR(WorkflowIR):
    reference: ModuleReferenceIR
    runtime_fields: tuple[RuntimeFieldIR, ...] = ()
    variables: JsonValue | None = None
    steps: tuple[StepIR, ...] = Field(min_length=1)


class ConnectionIR(WorkflowIR):
    input_id: str = Field(min_length=1)
    output_id: str = Field(min_length=1)


class WorkflowDefinitionIR(WorkflowIR):
    contributions: tuple[ContributionIR, ...] = Field(min_length=1)
    connections: tuple[ConnectionIR, ...] = ()


class WorkflowContractIR(WorkflowIR):
    workflow: WorkflowDefinitionIR
    workflow_fingerprint: str = Field(min_length=1)
    provenance: JsonValue | None = None


__all__ = [
    "ArtifactTypeIR",
    "BlueprintModuleIR",
    "ContributionIR",
    "ConnectionIR",
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
]
