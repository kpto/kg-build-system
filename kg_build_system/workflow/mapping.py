"""Mappings between workflow domain models and compilation IRs."""
from __future__ import annotations

from dataclasses import asdict

from . import ir
from . import models


def role_to_ir(value: models.ArtifactRole) -> ir.ArtifactRoleIR:
    return ir.ArtifactRoleIR(namespace=value.namespace, name=value.name)


def role_from_ir(value: ir.ArtifactRoleIR) -> models.ArtifactRole:
    return models.ArtifactRole(namespace=value.namespace, name=value.name)


def workflow_to_ir(value: models.WorkflowDefinition) -> ir.WorkflowDefinitionIR:
    return ir.WorkflowDefinitionIR(
        modules=tuple(
            ir.ModuleIR(
                reference=ir.ModuleReferenceIR(
                    module_id=module.reference.module_id,
                    import_module=module.reference.import_module,
                    class_qualname=module.reference.class_qualname,
                    implementation_version=module.reference.implementation_version,
                    configuration=module.reference.configuration,
                ),
                runtime_fields=tuple(ir.RuntimeFieldIR(**asdict(field)) for field in module.runtime_fields),
            )
            for module in value.modules
        ),
        steps=tuple(
            ir.WorkflowStepIR(
                step_id=step.step_id,
                module_id=step.module_id,
                inputs=tuple(
                    ir.SingleInputSlotIR(slot_id=slot.slot_id)
                    if isinstance(slot, models.SingleInputSlot)
                    else ir.CollectionInputSlotIR(slot_id=slot.slot_id)
                    for slot in step.inputs
                ),
                outputs=tuple(
                    ir.OutputSlotIR(slot_id=slot.slot_id, artifact_role=role_to_ir(slot.artifact_role))
                    for slot in step.outputs
                ),
                payload=step.payload,
            )
            for step in value.steps
        ),
        connections=tuple(ir.ConnectionIR(**asdict(connection)) for connection in value.connections),
    )


def workflow_from_ir(value: ir.WorkflowDefinitionIR) -> models.WorkflowDefinition:
    return models.WorkflowDefinition(
        modules=tuple(
            models.ModuleDefinition(
                reference=models.ModuleReference(
                    module_id=module.reference.module_id,
                    import_module=module.reference.import_module,
                    class_qualname=module.reference.class_qualname,
                    implementation_version=module.reference.implementation_version,
                    priority=0,
                    configuration=module.reference.configuration,
                ),
                runtime_fields=tuple(models.RuntimeFieldDefinition(**field.model_dump()) for field in module.runtime_fields),
            )
            for module in value.modules
        ),
        steps=tuple(
            models.WorkflowStep(
                step_id=step.step_id,
                module_id=step.module_id,
                inputs=tuple(
                    models.SingleInputSlot(slot_id=slot.slot_id)
                    if isinstance(slot, ir.SingleInputSlotIR)
                    else models.CollectionInputSlot(slot_id=slot.slot_id)
                    for slot in step.inputs
                ),
                outputs=tuple(
                    models.OutputSlot(slot_id=slot.slot_id, artifact_role=role_from_ir(slot.artifact_role))
                    for slot in step.outputs
                ),
                payload=step.payload,
            )
            for step in value.steps
        ),
        connections=tuple(models.Connection(**connection.model_dump()) for connection in value.connections),
    )


__all__ = ["role_from_ir", "role_to_ir", "workflow_from_ir", "workflow_to_ir"]
