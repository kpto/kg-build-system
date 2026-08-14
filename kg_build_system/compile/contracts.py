"""Compilation inputs and immutable compiled build contract."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer, PlainValidator

from ..table.dto import SourceDTO
from ..workflow.dto import WorkflowDefinitionDTO
from ..workflow.mapping import workflow_to_dto
from ..workflow.models import WorkflowDefinition
from .blueprint import BuildBlueprint


class ContractModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class BuildSettings(ContractModel):
    duckdb_threads: int | None = Field(default=None, ge=1)


class SourceOverride(ContractModel):
    table: str = Field(min_length=1)
    original: SourceDTO | None = None
    override: SourceDTO


class BuildOverrides(ContractModel):
    sources: tuple[SourceOverride, ...] = ()


def _decode_blueprint(value: Any) -> BuildBlueprint:
    return BuildBlueprint.model_validate(value)


def _encode_blueprint(value: BuildBlueprint) -> dict[str, Any]:
    return value.model_dump(mode="json")


BlueprintField = Annotated[
    BuildBlueprint,
    PlainValidator(_decode_blueprint),
    PlainSerializer(_encode_blueprint, return_type=dict[str, Any]),
]


def _decode_workflow(value: Any) -> WorkflowDefinitionDTO:
    if isinstance(value, WorkflowDefinitionDTO):
        return value
    if isinstance(value, WorkflowDefinition):
        return workflow_to_dto(value)
    return WorkflowDefinitionDTO.model_validate(value, strict=False)


WorkflowField = Annotated[
    WorkflowDefinitionDTO,
    BeforeValidator(_decode_workflow),
]


class BuildContract(ContractModel):
    """A complete executable workflow with its resolved declaration graph."""

    blueprint: BlueprintField
    blueprint_fingerprint: str = Field(min_length=1)
    sources: tuple[SourceDTO, ...] = Field(min_length=1)
    settings: BuildSettings = Field(default_factory=BuildSettings)
    overrides: BuildOverrides = Field(default_factory=BuildOverrides)
    workflow_fingerprint: str = Field(min_length=1)
    workflow: WorkflowField


__all__ = [
    "BuildContract", "BuildOverrides", "BuildSettings", "SourceOverride",
]
