"""Mappings between workflow domain models and compilation DTOs."""
from __future__ import annotations

from dataclasses import asdict

from . import dto
from . import models


def role_to_dto(value: models.ArtifactRole) -> dto.ArtifactRoleDTO:
    return dto.ArtifactRoleDTO(namespace=value.namespace, name=value.name)


def role_from_dto(value: dto.ArtifactRoleDTO) -> models.ArtifactRole:
    return models.ArtifactRole(namespace=value.namespace, name=value.name)


def workflow_to_dto(value: models.WorkflowDefinition) -> dto.WorkflowDefinitionDTO:
    return dto.WorkflowDefinitionDTO(
        modules=tuple(
            dto.ModuleDTO(
                reference=dto.ModuleReferenceDTO(**asdict(module.reference)),
                runtime_fields=tuple(dto.RuntimeFieldDTO(**asdict(field)) for field in module.runtime_fields),
            )
            for module in value.modules
        ),
        steps=tuple(
            dto.WorkflowStepDTO(
                step_id=step.step_id,
                module_id=step.module_id,
                assembly_preference=step.assembly_preference,
                inputs=tuple(
                    dto.SingleInputSlotDTO(slot_id=slot.slot_id)
                    if isinstance(slot, models.SingleInputSlot)
                    else dto.CollectionInputSlotDTO(slot_id=slot.slot_id)
                    for slot in step.inputs
                ),
                outputs=tuple(
                    dto.OutputSlotDTO(slot_id=slot.slot_id, artifact_role=role_to_dto(slot.artifact_role))
                    for slot in step.outputs
                ),
                payload=step.payload,
            )
            for step in value.steps
        ),
        connections=tuple(dto.ConnectionDTO(**asdict(connection)) for connection in value.connections),
    )


def workflow_from_dto(value: dto.WorkflowDefinitionDTO) -> models.WorkflowDefinition:
    return models.WorkflowDefinition(
        modules=tuple(
            models.ModuleDefinition(
                reference=models.ModuleReference(**module.reference.model_dump()),
                runtime_fields=tuple(models.RuntimeFieldDefinition(**field.model_dump()) for field in module.runtime_fields),
            )
            for module in value.modules
        ),
        steps=tuple(
            models.WorkflowStep(
                step_id=step.step_id,
                module_id=step.module_id,
                assembly_preference=step.assembly_preference,
                inputs=tuple(
                    models.SingleInputSlot(slot_id=slot.slot_id)
                    if isinstance(slot, dto.SingleInputSlotDTO)
                    else models.CollectionInputSlot(slot_id=slot.slot_id)
                    for slot in step.inputs
                ),
                outputs=tuple(
                    models.OutputSlot(slot_id=slot.slot_id, artifact_role=role_from_dto(slot.artifact_role))
                    for slot in step.outputs
                ),
                payload=step.payload,
            )
            for step in value.steps
        ),
        connections=tuple(models.Connection(**connection.model_dump()) for connection in value.connections),
    )


__all__ = ["role_from_dto", "role_to_dto", "workflow_from_dto", "workflow_to_dto"]
