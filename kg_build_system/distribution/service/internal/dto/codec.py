"""Thin instruction-codec wrappers over the private codec."""
from __future__ import annotations

from typing import Any

from ....model.internal.dto.instruction_dto import (
    CoreInstructionDTO,
    DeclaredColumnDTO,
    InstructionDTO,
)
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO


def declared_column_type(column: DeclaredColumnDTO) -> LogicalTypeDTO:
    """The declared logical type a column DTO carries."""
    from ..._private.dto.instruction_codec import (
        declared_column_type as implementation,
    )

    return implementation(column)


def encode_declared_column(
    name: str, logical_type: LogicalTypeDTO,
) -> DeclaredColumnDTO:
    """One declared column, carrying the logical type in its JSON form."""
    from ..._private.dto.instruction_codec import (
        encode_declared_column as implementation,
    )

    return implementation(name, logical_type)


def encode_instruction(
    value: InstructionDTO | CoreInstructionDTO,
) -> InstructionDTO:
    """Return one instruction in its kind-and-payload form."""
    from ..._private.dto.instruction_codec import (
        encode_instruction as implementation,
    )

    return implementation(value)


def instruction_document(
    value: InstructionDTO | CoreInstructionDTO,
) -> dict[str, Any]:
    """Return the JSON-compatible document stored for one step."""
    from ..._private.dto.instruction_codec import (
        instruction_document as implementation,
    )

    return implementation(value)


def decode_instruction(value: object) -> InstructionDTO:
    """Read one kind-and-payload instruction from its stored form."""
    from ..._private.dto.instruction_codec import (
        decode_instruction as implementation,
    )

    return implementation(value)


def decode_core_instruction(
    value: InstructionDTO | CoreInstructionDTO | object,
) -> CoreInstructionDTO:
    """Read one typed core instruction from either its typed or stored form."""
    from ..._private.dto.instruction_codec import (
        decode_core_instruction as implementation,
    )

    return implementation(value)


__all__ = [
    "decode_core_instruction",
    "decode_instruction",
    "declared_column_type",
    "encode_declared_column",
    "encode_instruction",
    "instruction_document",
]
