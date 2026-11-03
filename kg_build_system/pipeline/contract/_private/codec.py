"""Conversion between contract DTOs and their JSON-compatible document.

The codec composes the document from the DTOs and reads it back. An instruction
is copied as a kind and an opaque payload; the codec never branches on the
kind, so a ``python`` instruction and a ``sql`` instruction round-trip through
the same code.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, cast

from pydantic import JsonValue

from ..public.dto.contract import (
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

_RuntimeValueType = Literal["string", "integer", "number", "boolean", "json"]
_AssemblyPreference = Literal["eager", "deferred"]


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    """Read one document value that must be an object."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} must be an object")
    return cast(Mapping[str, Any], value)


def _sequence(value: object, field: str) -> Sequence[object]:
    """Read one document value that must be an array."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{field} must be an array")
    return cast(Sequence[object], value)


def _text(value: object, field: str) -> str:
    """Read one document value that must be a string."""
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    return value


def _optional_text(value: object, field: str) -> str | None:
    """Read one document value that may be absent or a string."""
    return None if value is None else _text(value, field)


def _boolean(value: object, field: str) -> bool:
    """Read one document value that must be a boolean."""
    if not isinstance(value, bool):
        raise TypeError(f"{field} must be a boolean")
    return value


def _artifact_type_to_document(value: ArtifactTypeDTO) -> dict[str, Any]:
    """Write one artifact type."""
    return {"namespace": value.namespace, "name": value.name}


def _artifact_type_from_document(value: Mapping[str, Any]) -> ArtifactTypeDTO:
    """Read one artifact type."""
    return ArtifactTypeDTO(
        namespace=_text(value.get("namespace"), "artifact type namespace"),
        name=_text(value.get("name"), "artifact type name"),
    )


def _input_to_document(value: InputDTO) -> dict[str, Any]:
    """Write one input opening."""
    return {
        "type": _artifact_type_to_document(value.type),
        "name": value.name,
        "input_name": value.input_name,
    }


def _input_from_document(value: Mapping[str, Any]) -> InputDTO:
    """Read one input opening."""
    return InputDTO(
        type=_artifact_type_from_document(
            _mapping(value.get("type"), "input type"),
        ),
        name=_optional_text(value.get("name"), "input name"),
        input_name=_text(value.get("input_name"), "input input_name"),
    )


def _output_to_document(value: GivenDTO) -> dict[str, Any]:
    """Write one output or publication."""
    return {
        "kind": value.kind,
        "type": _artifact_type_to_document(value.type),
        "name": value.name,
    }


def _output_from_document(value: Mapping[str, Any]) -> GivenDTO:
    """Read one output or publication."""
    kind = _text(value.get("kind"), "output kind")
    artifact_type = _artifact_type_from_document(
        _mapping(value.get("type"), "output type"),
    )
    name = _optional_text(value.get("name"), "output name")
    if kind == "publication":
        return PublicationDTO(type=artifact_type, name=name)
    if kind == "output":
        return OutputDTO(type=artifact_type, name=name)
    raise ValueError(f"unknown output kind {kind!r}")


def _instruction_to_document(value: InstructionDTO) -> dict[str, Any]:
    """Write one instruction without reading its kind or payload."""
    return {"kind": value.kind, "payload": value.payload}


def _instruction_from_document(value: Mapping[str, Any]) -> InstructionDTO:
    """Read one instruction without reading its kind or payload."""
    return InstructionDTO(
        kind=_text(value.get("kind"), "instruction kind"),
        payload=cast(JsonValue, value.get("payload")),
    )


def _step_to_document(value: StepDTO) -> dict[str, Any]:
    """Write one step."""
    return {
        "name": value.name,
        "inputs": [_input_to_document(item) for item in value.inputs],
        "outputs": [_output_to_document(item) for item in value.outputs],
        "instruction": _instruction_to_document(value.instruction),
        "assembly_preference": value.assembly_preference,
    }


def _step_from_document(value: Mapping[str, Any]) -> StepDTO:
    """Read one step."""
    return StepDTO(
        name=_text(value.get("name"), "step name"),
        inputs=tuple(
            _input_from_document(_mapping(item, "step input"))
            for item in _sequence(value.get("inputs"), "step inputs")
        ),
        outputs=tuple(
            _output_from_document(_mapping(item, "step output"))
            for item in _sequence(value.get("outputs"), "step outputs")
        ),
        instruction=_instruction_from_document(
            _mapping(value.get("instruction"), "step instruction"),
        ),
        assembly_preference=cast(
            _AssemblyPreference,
            _text(value.get("assembly_preference"), "step assembly_preference"),
        ),
    )


def _runtime_field_to_document(value: RuntimeFieldDTO) -> dict[str, Any]:
    """Write one runtime field."""
    return {
        "key": value.key,
        "description": value.description,
        "required": value.required,
        "value_type": value.value_type,
        "secret": value.secret,
    }


def _runtime_field_from_document(value: Mapping[str, Any]) -> RuntimeFieldDTO:
    """Read one runtime field."""
    return RuntimeFieldDTO(
        key=_text(value.get("key"), "runtime field key"),
        description=_text(value.get("description"), "runtime field description"),
        required=_boolean(value.get("required"), "runtime field required"),
        value_type=cast(
            _RuntimeValueType,
            _text(value.get("value_type"), "runtime field value_type"),
        ),
        secret=_boolean(value.get("secret"), "runtime field secret"),
    )


def _module_reference_to_document(value: ModuleReferenceDTO) -> dict[str, Any]:
    """Write one module reference."""
    return {
        "module_id": value.module_id,
        "import_module": value.import_module,
        "class_qualname": value.class_qualname,
        "implementation_version": value.implementation_version,
        "configuration": value.configuration,
    }


def _module_reference_from_document(
    value: Mapping[str, Any],
) -> ModuleReferenceDTO:
    """Read one module reference."""
    return ModuleReferenceDTO(
        module_id=_text(value.get("module_id"), "module reference module_id"),
        import_module=_text(
            value.get("import_module"), "module reference import_module",
        ),
        class_qualname=_text(
            value.get("class_qualname"), "module reference class_qualname",
        ),
        implementation_version=_text(
            value.get("implementation_version"),
            "module reference implementation_version",
        ),
        configuration=cast(JsonValue | None, value.get("configuration")),
    )


def _module_definition_to_document(value: ModuleDefinitionDTO) -> dict[str, Any]:
    """Write one module definition."""
    return {
        "reference": _module_reference_to_document(value.reference),
        "runtime_fields": [
            _runtime_field_to_document(item) for item in value.runtime_fields
        ],
    }


def _module_definition_from_document(
    value: Mapping[str, Any],
) -> ModuleDefinitionDTO:
    """Read one module definition."""
    return ModuleDefinitionDTO(
        reference=_module_reference_from_document(
            _mapping(value.get("reference"), "module reference"),
        ),
        runtime_fields=tuple(
            _runtime_field_from_document(_mapping(item, "runtime field"))
            for item in _sequence(
                value.get("runtime_fields"), "module runtime_fields",
            )
        ),
    )


def _contribution_to_document(value: ContributionDTO) -> dict[str, Any]:
    """Write one contribution."""
    return {
        "module": _module_definition_to_document(value.module),
        "steps": [_step_to_document(item) for item in value.steps],
    }


def _contribution_from_document(value: Mapping[str, Any]) -> ContributionDTO:
    """Read one contribution."""
    return ContributionDTO(
        module=_module_definition_from_document(
            _mapping(value.get("module"), "contribution module"),
        ),
        steps=tuple(
            _step_from_document(_mapping(item, "contribution step"))
            for item in _sequence(value.get("steps"), "contribution steps")
        ),
    )


def _connection_to_document(value: ConnectionDTO) -> dict[str, Any]:
    """Write one connection."""
    return {"input_id": value.input_id, "output_id": value.output_id}


def _connection_from_document(value: Mapping[str, Any]) -> ConnectionDTO:
    """Read one connection."""
    return ConnectionDTO(
        input_id=_text(value.get("input_id"), "connection input_id"),
        output_id=_text(value.get("output_id"), "connection output_id"),
    )


def contract_to_document(contract: WorkflowContractDTO) -> dict[str, Any]:
    """Write a contract as its canonical JSON-compatible document.

    The instruction kind and payload are copied unchanged.
    """
    return {
        "contributions": [
            _contribution_to_document(item) for item in contract.contributions
        ],
        "connections": [
            _connection_to_document(item) for item in contract.connections
        ],
        "provenance": contract.provenance,
    }


def contract_from_document(document: Mapping[str, Any]) -> WorkflowContractDTO:
    """Read a contract from the document written by :func:`contract_to_document`.

    The instruction kind and payload are passed through unchanged.
    """
    return WorkflowContractDTO(
        contributions=tuple(
            _contribution_from_document(_mapping(item, "contribution"))
            for item in _sequence(document.get("contributions"), "contributions")
        ),
        connections=tuple(
            _connection_from_document(_mapping(item, "connection"))
            for item in _sequence(document.get("connections"), "connections")
        ),
        provenance=cast(JsonValue | None, document.get("provenance")),
    )


__all__ = ["contract_from_document", "contract_to_document"]
