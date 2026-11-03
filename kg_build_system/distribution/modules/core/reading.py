"""Read one physical source and expose its widened relation."""
from __future__ import annotations

from typing import Any

from .credentials import configure_source_credentials
from .guards import (
    report_declared_null_statistics,
    require_declared_columns,
    widened_column,
)
from ...internal.dto.instruction_dto import SourceRelationInstructionDTO

_SCAN_FUNCTIONS = {
    "csv": "read_csv_auto",
    "json": "read_json_auto",
    "parquet": "read_parquet",
}


def source_scan(instruction: SourceRelationInstructionDTO) -> str:
    """The engine scan expression for one declared source."""
    scan_function = _SCAN_FUNCTIONS[instruction.format]
    location = instruction.location.replace("'", "''")
    return f"{scan_function}('{location}')"


def open_source(
    instruction: SourceRelationInstructionDTO,
    services: Any,
) -> tuple[Any, bool]:
    """Create the source view and return it with whether statistics warned.

    ``DESCRIBE`` reads file metadata only, so the contract's shape is checked
    before a view exists and before any consumer can reach this relation. The
    widening happens in the per-source view, so every reader downstream sees one
    type for one declared column even when partitions disagree.
    """
    if instruction.credential_reference is not None:
        configure_source_credentials(
            services,
            location=instruction.location,
            credential_reference=instruction.credential_reference,
        )

    scan = source_scan(instruction)
    require_declared_columns(instruction, scan, services)
    select = ", ".join(
        widened_column(column) for column in instruction.declared_columns
    ) or "*"
    sql = f"SELECT {select} FROM {scan}"
    try:
        relation = services.relations.view(instruction.relation, sql)
    except Exception as error:
        raise RuntimeError(
            f"the source at '{instruction.location}' for "
            f"'{instruction.declaration}' cannot be read as the declared "
            f"'{instruction.format}' format: {error}"
        ) from error
    found = report_declared_null_statistics(instruction, services)
    return relation, found


__all__ = ["open_source", "source_scan"]
