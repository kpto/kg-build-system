"""Portable schema models for physical binding inputs.

These models describe an input table independently of the class-based
authoring API in :mod:`kg_build_system.binding.declaration`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum


class BindingValidationError(ValueError):
    """Raised when a binding or input schema is structurally invalid."""


class InputFormat(StrEnum):
    """Physical input formats supported by the initial binding model."""

    CSV = "csv"
    PARQUET = "parquet"


@dataclass(frozen=True, slots=True)
class Column:
    """A typed column in a portable input-table schema."""

    name: str
    python_type: str
    nullable: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise BindingValidationError("Column names must be non-empty.")
        if not self.python_type:
            raise BindingValidationError("Column Python types must be non-empty.")

    def to_dict(self) -> dict[str, str | bool]:
        return {"name": self.name, "python_type": self.python_type, "nullable": self.nullable}


@dataclass(frozen=True, slots=True)
class Table:
    """A physical input table and its portable logical schema."""

    name: str
    location: str
    format: InputFormat
    columns: Sequence[Column]
    options: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise BindingValidationError("Table names must be non-empty.")
        if not self.location:
            raise BindingValidationError("Table locations must be non-empty.")
        column_names = [column.name for column in self.columns]
        if len(column_names) != len(set(column_names)):
            raise BindingValidationError("Table column names must be unique.")
        object.__setattr__(self, "columns", tuple(self.columns))
        object.__setattr__(self, "options", dict(self.options))

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "location": self.location,
            "format": self.format.value,
            "options": dict(self.options),
            "columns": [column.to_dict() for column in self.columns],
        }
