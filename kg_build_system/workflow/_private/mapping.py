"""Mappings between workflow domain models and their compilation IR."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..._frozen_json import freeze_json, thaw_json
from ...kernel import (
    ArtifactType,
    Connection,
    DefinedContribution,
    DefinedStep,
    ModuleDefinition,
    ModuleReference,
    Output,
    Publication,
    RuntimeFieldDefinition,
    TakenInput,
)
from .identity import output_name

if TYPE_CHECKING:
    from ..internal import ir
    from ..internal.models import WorkflowDefinition


def type_to_ir(value: ArtifactType) -> ir.ArtifactTypeIR:
    """Lower one artifact type to its IR value."""
    from ..internal import ir

    return ir.ArtifactTypeIR(namespace=value.namespace, name=value.name)


def type_from_ir(value: ir.ArtifactTypeIR) -> ArtifactType:
    """Read one artifact type back from its IR value."""
    return ArtifactType(namespace=value.namespace, name=value.name)


def _reference_to_ir(value: ModuleReference) -> ir.ModuleReferenceIR:
    """Lower one module reference to its IR value."""
    from ..internal import ir

    return ir.ModuleReferenceIR(
        module_id=value.module_id,
        import_module=value.import_module,
        class_qualname=value.class_qualname,
        implementation_version=value.implementation_version,
        configuration=(
            thaw_json(value.configuration)
            if value.configuration is not None else None
        ),
    )


def _reference_from_ir(value: ir.ModuleReferenceIR) -> ModuleReference:
    """Read one module reference back from its IR value."""
    return ModuleReference(
        module_id=value.module_id,
        import_module=value.import_module,
        class_qualname=value.class_qualname,
        implementation_version=value.implementation_version,
        configuration=(
            freeze_json(value.configuration)
            if value.configuration is not None else None
        ),
    )


def _contribution_to_ir(value: DefinedContribution) -> ir.ContributionIR:
    """Lower one assembled contribution to its IR value."""
    from ..internal import ir

    return ir.ContributionIR(
        reference=_reference_to_ir(value.module.reference),
        runtime_fields=tuple(
            ir.RuntimeFieldIR(
                key=field.key,
                description=field.description,
                required=field.required,
                value_type=field.value_type,
                secret=field.secret,
            )
            for field in value.module.runtime_fields
        ),
        variables=thaw_json(value.variables) if value.variables is not None else None,
        steps=tuple(
            ir.StepIR(
                name=step.name,
                inputs=tuple(
                    ir.InputIR(
                        type=type_to_ir(taken.type),
                        name=taken.name,
                        input_name=taken.input_name,
                    )
                    for taken in step.inputs
                ),
                outputs=tuple(
                    ir.PublicationIR(type=type_to_ir(given.type), name=output_name(given))
                    if isinstance(given, Publication)
                    else ir.OutputIR(type=type_to_ir(given.type), name=output_name(given))
                    for given in step.outputs
                ),
            )
            for step in value.steps
        ),
    )


def _contribution_from_ir(value: ir.ContributionIR) -> DefinedContribution:
    """Read one assembled contribution back from its IR value."""
    from ..internal import ir

    return DefinedContribution(
        module=ModuleDefinition(
            reference=_reference_from_ir(value.reference),
            runtime_fields=tuple(
                RuntimeFieldDefinition(
                    key=field.key,
                    description=field.description,
                    required=field.required,
                    value_type=field.value_type,
                    secret=field.secret,
                )
                for field in value.runtime_fields
            ),
        ),
        steps=tuple(
            DefinedStep(
                name=step.name,
                inputs=tuple(
                    TakenInput(
                        type=type_from_ir(taken.type),
                        name=taken.name,
                        input_name=taken.input_name,
                    )
                    for taken in step.inputs
                ),
                outputs=tuple(
                    Publication(type=type_from_ir(given.type), name=given.name)
                    if isinstance(given, ir.PublicationIR)
                    else Output(type=type_from_ir(given.type), name=given.name)
                    for given in step.outputs
                ),
            )
            for step in value.steps
        ),
        variables=freeze_json(value.variables) if value.variables is not None else None,
    )


def workflow_to_ir(value: WorkflowDefinition) -> ir.WorkflowDefinitionIR:
    """Lower an assembled workflow to its serialisable IR."""
    from ..internal import ir

    return ir.WorkflowDefinitionIR(
        contributions=tuple(_contribution_to_ir(item) for item in value.contributions),
        connections=tuple(
            ir.ConnectionIR(
                input_id=connection.input_id,
                output_id=connection.output_id,
            )
            for connection in value.connections
        ),
    )


def workflow_from_ir(value: ir.WorkflowDefinitionIR) -> WorkflowDefinition:
    """Read an assembled workflow back from its IR."""
    from ..internal.models import WorkflowDefinition

    return WorkflowDefinition(
        contributions=tuple(_contribution_from_ir(item) for item in value.contributions),
        connections=tuple(
            Connection(input_id=item.input_id, output_id=item.output_id)
            for item in value.connections
        ),
    )


__all__ = ["type_from_ir", "type_to_ir", "workflow_from_ir", "workflow_to_ir"]
