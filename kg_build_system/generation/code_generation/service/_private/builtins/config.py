"""Configuration values accepted by the built-in data-contract provider."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from ....model.internal.providers import ProviderGenerationConfig


class ColumnOverride(BaseModel):
    """The author's declared view of one relation's whole top-level column."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    #: The canonical unit type the column means to hold, whatever the reader
    #: reports; the scan then applies the checked cast to it.
    type: str | None = None
    #: ``True`` declines a source-declared non-nullability, ``False`` asserts
    #: one the build guard will test; absence keeps the source's own claim.
    nullable: bool | None = None

    @model_validator(mode="after")
    def _declares_something(self) -> "ColumnOverride":
        if self.type is None and self.nullable is None:
            raise ValueError("an override declares at least one of type and nullable")
        return self


class DataContractInferenceConfig(ProviderGenerationConfig):
    #: The observed input. When omitted, the provider uses the decorated
    #: asset's ``AssetLayout.locator``; a request with neither is refused.
    source: str | None = None
    relation: str | None = None
    mode: Literal["table", "table_group"] = "table"
    layout: Literal["files", "parquet_parts", "hive_partitioned_parquet"] = "files"
    anonymous: bool = False
    #: Author declarations that replace what the reader reports for a column,
    #: keyed by the column's full ``<relation path>.<column>`` path.
    override: dict[str, dict[str, Any]] = {}


__all__ = ["ColumnOverride", "DataContractInferenceConfig"]
