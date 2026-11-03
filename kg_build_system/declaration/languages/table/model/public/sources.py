"""Author-facing physical source bindings for tables and table groups.

``bind_source`` binds a final ``Table`` or ``TableGroup`` to a
``DataSourceConfig``. A group binding resolves each member through the config's
``layout``.

Example:
    ```python
    from kg_build_system import DataSourceConfig, InputFormat, bind_source

    source = bind_source(
        target=SiteTable,
        config=DataSourceConfig(
            location="data/sites.json", format=InputFormat.JSON,
        ),
    )
    ```
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, TypeAlias

from kg_build_system.declaration.foundations.annotations.service.internal import annotation_tuple
from kg_build_system.declaration.foundations.annotations.model.public import (
    Annotation,
)

if TYPE_CHECKING:
    from .declarations import Table, TableGroup


class InputFormat(StrEnum):
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"


@dataclass(frozen=True, slots=True)
class DataSourceConfig:
    location: str
    format: InputFormat = InputFormat.CSV
    layout: str | None = None
    credentials: str | None = None
    version: str | None = None

    def __post_init__(self) -> None:
        if not self.location:
            raise ValueError("data sources require a non-empty location")


@dataclass(frozen=True, slots=True)
class BoundTable:
    table: type["Table"]
    config: DataSourceConfig
    annotations: tuple[Annotation, ...] = ()


@dataclass(frozen=True, slots=True)
class BoundTableGroup:
    group: type["TableGroup"]
    config: DataSourceConfig
    annotations: tuple[Annotation, ...] = ()


BoundSource: TypeAlias = BoundTable | BoundTableGroup


@dataclass(frozen=True, slots=True)
class SourceBindingOptions:
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


__all__ = [
    "BoundSource", "BoundTable", "BoundTableGroup", "DataSourceConfig",
    "InputFormat", "SourceBindingOptions",
]
