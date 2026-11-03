"""Encode and decode a ``WorkflowPlan`` as a JSON-safe document.

The document belongs to the workflow plan. Tuple instruction kinds serialise as
JSON arrays and provenance is preserved verbatim. No executor or engine is
involved.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, cast

from ...model.public.workflow import (
    ArtifactType,
    Component,
    Connection,
    Input,
    Instruction,
    Output,
    Publication,
    RuntimeField,
    Step,
    WorkflowPlan,
)


def _type_to_document(artifact_type: ArtifactType) -> dict[str, Any]:
    return {"namespace": artifact_type.namespace, "name": artifact_type.name}


def _type_from_document(document: Mapping[str, Any]) -> ArtifactType:
    return ArtifactType(
        str(document["namespace"]),
        str(document["name"]),
    )


def _field_to_document(field: RuntimeField) -> dict[str, Any]:
    return {
        "key": field.key,
        "description": field.description,
        "required": field.required,
        "value_type": field.value_type,
        "secret": field.secret,
    }


def _field_from_document(document: Mapping[str, Any]) -> RuntimeField:
    value_type = cast(
        Literal["string", "integer", "number", "boolean", "json"],
        document.get("value_type", "string"),
    )
    return RuntimeField(
        key=str(document["key"]),
        description=str(document.get("description", "")),
        required=bool(document.get("required", True)),
        value_type=value_type,
        secret=bool(document.get("secret", False)),
    )


def _component_to_document(component: Component) -> dict[str, Any]:
    return {
        "id": component.id,
        "version": component.version,
        "runtime_fields": [
            _field_to_document(field) for field in component.runtime_fields
        ],
    }


def _component_from_document(document: Mapping[str, Any]) -> Component:
    return Component(
        id=str(document["id"]),
        version=str(document["version"]),
        runtime_fields=tuple(
            _field_from_document(field)
            for field in document.get("runtime_fields", ())
        ),
    )


def _input_to_document(taken: Input) -> dict[str, Any]:
    return {
        "type": _type_to_document(taken.type),
        "name": taken.name,
        "input_name": taken.input_name,
    }


def _input_from_document(document: Mapping[str, Any]) -> Input:
    name = document.get("name")
    return Input(
        type=_type_from_document(document["type"]),
        name=None if name is None else str(name),
        input_name=str(document.get("input_name", document.get("name") or "")),
    )


def _given_to_document(given: Output | Publication) -> dict[str, Any]:
    return {
        "kind": "publication" if isinstance(given, Publication) else "output",
        "type": _type_to_document(given.type),
        "name": given.name,
    }


def _given_from_document(document: Mapping[str, Any]) -> Output | Publication:
    name = document.get("name")
    artifact_type = _type_from_document(document["type"])
    resolved_name = None if name is None else str(name)
    if document.get("kind") == "publication":
        return Publication(type=artifact_type, name=resolved_name)
    return Output(type=artifact_type, name=resolved_name)


def _instruction_to_document(instruction: Instruction) -> dict[str, Any]:
    return {
        "kind": list(instruction.kind),
        "payload": instruction.payload,
    }


def _instruction_from_document(document: Mapping[str, Any]) -> Instruction:
    return Instruction(
        kind=tuple(str(item) for item in document.get("kind", ())),
        payload=document.get("payload"),
    )


def _step_to_document(step: Step) -> dict[str, Any]:
    return {
        "component": step.component,
        "name": step.name,
        "inputs": [_input_to_document(taken) for taken in step.inputs],
        "outputs": [_given_to_document(given) for given in step.outputs],
        "instruction": _instruction_to_document(step.instruction),
        "assembly_preference": step.assembly_preference,
    }


def _step_from_document(document: Mapping[str, Any]) -> Step:
    return Step(
        component=str(document["component"]),
        name=str(document["name"]),
        inputs=tuple(
            _input_from_document(taken)
            for taken in document.get("inputs", ())
        ),
        outputs=tuple(
            _given_from_document(given)
            for given in document.get("outputs", ())
        ),
        instruction=_instruction_from_document(document["instruction"]),
        assembly_preference=cast(
            Literal["eager", "deferred"],
            document.get("assembly_preference", "eager"),
        ),
    )


def workflow_plan_to_document(plan: WorkflowPlan) -> dict[str, Any]:
    """Render a workflow plan as a JSON-safe document.

    Example:
    ```python
    document = workflow_plan_to_document(plan)
    assert isinstance(document["steps"][0]["instruction"]["kind"], list)
    ```
    """
    return {
        "components": [
            _component_to_document(component) for component in plan.components
        ],
        "steps": [_step_to_document(step) for step in plan.steps],
        "connections": [
            {"input_id": connection.input_id, "output_id": connection.output_id}
            for connection in plan.connections
        ],
        "provenance": plan.provenance,
    }


def workflow_plan_from_document(document: Mapping[str, Any]) -> WorkflowPlan:
    """Read a workflow plan from its JSON-safe document.

    Example:
    ```python
    plan = workflow_plan_from_document(workflow_plan_to_document(plan))
    assert isinstance(plan.steps[0].instruction.kind, tuple)
    ```
    """
    return WorkflowPlan(
        components=tuple(
            _component_from_document(component)
            for component in document.get("components", ())
        ),
        steps=tuple(
            _step_from_document(step)
            for step in document.get("steps", ())
        ),
        connections=tuple(
            Connection(
                str(connection["input_id"]),
                str(connection["output_id"]),
            )
            for connection in document.get("connections", ())
        ),
        provenance=document.get("provenance"),
    )


__all__ = ["workflow_plan_from_document", "workflow_plan_to_document"]
