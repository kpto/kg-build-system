"""Encode and decode a ``WorkflowPlan`` as a JSON-safe document.

The document belongs to the workflow plan. Every pipeline identity is written
as the ``Key`` array of its role type; the field name states the role, so no
role token is added. Provenance is preserved verbatim. No executor or engine is
involved.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, cast

from ...model.public.key import Key
from ...model.public.workflow import (
    ArtifactPattern,
    ArtifactType,
    Component,
    Connection,
    Input,
    Instruction,
    InstructionKind,
    OpeningDirection,
    OpeningId,
    Output,
    Publication,
    RuntimeField,
    Step,
    StepId,
    WorkflowPlan,
    step_id,
)


def _type_to_document(artifact_type: ArtifactType) -> list[str]:
    return artifact_type.key.to_document()


def _type_from_document(value: Any) -> ArtifactType:
    return ArtifactType(Key.from_document(value))


def _pattern_to_document(pattern: ArtifactPattern) -> list[str]:
    return pattern.key.to_document()


def _pattern_from_document(value: Any) -> ArtifactPattern:
    return ArtifactPattern(Key.from_document(value))


def _name_to_document(name: Key | None) -> list[str] | None:
    return None if name is None else name.to_document()


def _name_from_document(value: Any) -> Key | None:
    return None if value is None else Key.from_document(value)


def _step_id_from_document(value: Any) -> StepId:
    segments = Key.from_document(value).segments
    if len(segments) != 2:
        raise ValueError("a step id document must have exactly two segments")
    return StepId(segments[0], segments[1])


def _opening_from_document(value: Any) -> OpeningId:
    segments = Key.from_document(value).segments
    if len(segments) < 4:
        raise ValueError(
            "an opening document needs a component, a step, a direction and a name"
        )
    try:
        direction = OpeningDirection(segments[2])
    except ValueError:
        raise ValueError(
            f"an opening direction must be 'input' or 'output', not "
            f"{segments[2]!r}"
        ) from None
    return OpeningId(
        StepId(segments[0], segments[1]), direction, Key(segments[3:]),
    )


def _kind_from_document(value: Any) -> InstructionKind:
    segments = Key.from_document(value).segments
    if len(segments) != 2:
        raise ValueError(
            "an instruction kind document must have exactly two segments"
        )
    return InstructionKind(segments[0], segments[1])


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
        "type": _pattern_to_document(taken.type),
        "opening_name": _name_to_document(taken.opening_name),
        "declared_name": taken.declared_name,
    }


def _input_from_document(document: Mapping[str, Any]) -> Input:
    return Input(
        type=_pattern_from_document(document["type"]),
        opening_name=_name_from_document(document.get("opening_name")),
        declared_name=str(document.get("declared_name", "")),
    )


def _given_to_document(given: Output | Publication) -> dict[str, Any]:
    return {
        "kind": "publication" if isinstance(given, Publication) else "output",
        "type": _type_to_document(given.type),
        "opening_name": _name_to_document(given.opening_name),
    }


def _given_from_document(document: Mapping[str, Any]) -> Output | Publication:
    artifact_type = _type_from_document(document["type"])
    opening_name = _name_from_document(document.get("opening_name"))
    if document.get("kind") == "publication":
        return Publication(type=artifact_type, opening_name=opening_name)
    return Output(type=artifact_type, opening_name=opening_name)


def _instruction_to_document(instruction: Instruction) -> dict[str, Any]:
    return {
        "kind": instruction.kind.key.to_document(),
        "payload": instruction.payload,
    }


def _instruction_from_document(document: Mapping[str, Any]) -> Instruction:
    return Instruction(
        kind=_kind_from_document(document.get("kind")),
        payload=document.get("payload"),
    )


def _step_to_document(step: Step) -> dict[str, Any]:
    return {
        "id": step_id(step).key.to_document(),
        "inputs": [_input_to_document(taken) for taken in step.inputs],
        "outputs": [_given_to_document(given) for given in step.outputs],
        "instruction": _instruction_to_document(step.instruction),
        "assembly_preference": step.assembly_preference,
    }


def _step_from_document(document: Mapping[str, Any]) -> Step:
    identity = _step_id_from_document(document["id"])
    return Step(
        component=identity.component,
        name=identity.name,
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
    assert document["steps"][0]["id"] == ["echo", "echo"]
    ```
    """
    return {
        "components": [
            _component_to_document(component) for component in plan.components
        ],
        "steps": [_step_to_document(step) for step in plan.steps],
        "connections": [
            {
                "input": connection.input.key.to_document(),
                "output": connection.output.key.to_document(),
            }
            for connection in plan.connections
        ],
        "provenance": plan.provenance,
    }


def workflow_plan_from_document(document: Mapping[str, Any]) -> WorkflowPlan:
    """Read a workflow plan from its JSON-safe document.

    Example:
    ```python
    plan = workflow_plan_from_document(workflow_plan_to_document(plan))
    assert plan.steps[0].instruction.kind.operation == "echo"
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
                _opening_from_document(connection["input"]),
                _opening_from_document(connection["output"]),
            )
            for connection in document.get("connections", ())
        ),
        provenance=document.get("provenance"),
    )


__all__ = ["workflow_plan_from_document", "workflow_plan_to_document"]
