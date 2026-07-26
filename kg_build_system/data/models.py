"""Source-independent data declaration models."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Generic, TypeVar

from ..expressions import Expression, FieldPath, item_type
from ..specification import Declaration

T = TypeVar("T")

@dataclass(frozen=True)
class Field(Declaration[T], Generic[T]):
    name: str
    type_hint: Any = None
    attr: str = ""
    def __set_name__(self, owner: type, attr: str) -> None: object.__setattr__(self, "attr", attr)
    def __get__(self, instance: Any, owner: type) -> FieldPath[T] | T | None:
        return FieldPath[T](owner, (self.name,), self.type_hint, "collection" if item_type(self.type_hint) is not None else "scalar") if instance is None else instance

@dataclass(frozen=True)
class ProjectedField(Declaration[T], Generic[T]):
    expression: Expression[T] | FieldPath[T]
    name: str | None = None
    attr: str = ""
    def __set_name__(self, owner: type, attr: str) -> None:
        object.__setattr__(self, "attr", attr)
        if self.name is None: object.__setattr__(self, "name", attr)
    def __get__(self, instance: Any, owner: type) -> Expression[T] | FieldPath[T]:
        return FieldPath[T](owner, (self.name or self.attr,), self.expression.type_hint, self.expression.cardinality) if instance is None else self.expression

class InputFormat(StrEnum):
    CSV = "csv"
    PARQUET = "parquet"

@dataclass(frozen=True)
class DataSourceConfig:
    location: str
    format: InputFormat = InputFormat.CSV
    credentials: str | None = None
    version: str | None = None

@dataclass(frozen=True)
class BoundTable:
    table: type
    config: DataSourceConfig
