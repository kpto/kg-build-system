"""Logical data declarations and physical source-binding models."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar, TypeAlias

from .._support.naming import declaration_name
from ..annotations import Annotation, annotation_tuple
from ..types import Struct as StructDeclaration


class InputFormat(StrEnum):
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"


@dataclass(frozen=True)
class DataSourceConfig:
    location: str
    format: InputFormat = InputFormat.CSV
    layout: str | None = None
    credentials: str | None = None
    version: str | None = None

    def __post_init__(self) -> None:
        if not self.location:
            raise ValueError("data sources require a non-empty location")


@dataclass(frozen=True)
class BoundTable:
    table: type[Table]
    config: DataSourceConfig
    annotations: tuple[Annotation, ...] = ()


@dataclass(frozen=True)
class BoundTableGroup:
    group: type[TableGroup]
    config: DataSourceConfig
    annotations: tuple[Annotation, ...] = ()


BoundSource: TypeAlias = BoundTable | BoundTableGroup


@dataclass(frozen=True)
class TableOptions:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("table names must be non-empty")
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True)
class TableTemplateOptions(TableOptions):
    pass


@dataclass(frozen=True)
class StructOptions:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("struct names must be non-empty")
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True)
class ProjectionOptions:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("projection names must be non-empty")
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True)
class TableGroupOptions:
    members: tuple[type, ...] = ()
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("table-group names must be non-empty")
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True)
class SourceBindingOptions:
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


def _description(cls: type[Any], configured: str | None) -> str | None:
    return configured if configured is not None else (vars(cls).get("__doc__") or None)


def _inherited_annotations(cls: type[Any]) -> tuple[Annotation, ...]:
    return tuple(
        annotation
        for base in cls.__bases__
        for annotation in vars(base).get("_data_annotations", ())
    )


def _prepare_fields(
    cls: type[Any],
    *,
    kind: str,
    name: str,
    description: str | None,
    annotations: tuple[Annotation, ...],
) -> None:
    from .fields import declared_fields

    cls._fields = declared_fields(cls)
    cls._data_declaration_kind = kind
    cls._data_name = name
    cls._data_annotations = annotations
    cls._data_metadata = {"description": description} if description is not None else {}


class Table:
    """A final, source-bindable logical table declaration."""

    options: ClassVar[TableOptions] = TableOptions()
    _data_declaration_kind: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if any(vars(base).get("_data_declaration_kind") == "table" for base in cls.__mro__[1:]):
            raise TypeError("a final Table may not inherit from another final Table")
        options = vars(cls).get("options", TableOptions())
        if not isinstance(options, TableOptions):
            raise TypeError("Table.options must be a TableOptions value")
        name = options.name or declaration_name(cls.__name__, suffixes=("Table",))
        cls._table_name = name
        _prepare_fields(
            cls,
            kind="table",
            name=name,
            description=_description(cls, options.description),
            annotations=(*_inherited_annotations(cls), *options.annotations),
        )


class TableTemplate:
    """An optional reusable table shape carrying framework metadata."""

    options: ClassVar[TableTemplateOptions] = TableTemplateOptions()
    _data_declaration_kind: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # ``class Concrete(Shape, Table)`` is finalised by Table's hook while
        # walking this cooperative MRO.
        if vars(cls).get("_data_declaration_kind") == "table":
            return
        options = vars(cls).get("options", TableTemplateOptions())
        if not isinstance(options, TableTemplateOptions):
            raise TypeError("TableTemplate.options must be a TableTemplateOptions value")
        name = options.name or declaration_name(
            cls.__name__, suffixes=("TableTemplate", "Template")
        )
        _prepare_fields(
            cls,
            kind="table_template",
            name=name,
            description=_description(cls, options.description),
            annotations=(*_inherited_annotations(cls), *options.annotations),
        )


class Struct(StructDeclaration):
    """A reusable nested-record declaration composed from unified fields."""

    options: ClassVar[StructOptions] = StructOptions()
    _data_declaration_kind: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options", StructOptions())
        if not isinstance(options, StructOptions):
            raise TypeError("Struct.options must be a StructOptions value")
        name = options.name or declaration_name(cls.__name__, suffixes=("Struct",))
        _prepare_fields(
            cls,
            kind="struct",
            name=name,
            description=_description(cls, options.description),
            annotations=(*_inherited_annotations(cls), *options.annotations),
        )


class Projection:
    """A final named logical product composed from typed expressions."""

    options: ClassVar[ProjectionOptions] = ProjectionOptions()
    _data_declaration_kind: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if any(vars(base).get("_data_declaration_kind") == "projection" for base in cls.__mro__[1:]):
            raise TypeError("a final Projection may not inherit from another final Projection")
        options = vars(cls).get("options", ProjectionOptions())
        if not isinstance(options, ProjectionOptions):
            raise TypeError("Projection.options must be a ProjectionOptions value")

        from .projections import declared_projection_fields

        fields = declared_projection_fields(cls)
        if not fields:
            raise TypeError("projections must declare at least one projection_field")
        cls._projection_name = options.name or declaration_name(
            cls.__name__, suffixes=("Projection",)
        )
        cls._projection_fields = fields
        cls._data_declaration_kind = "projection"
        cls._data_annotations = (*_inherited_annotations(cls), *options.annotations)
        description = _description(cls, options.description)
        cls._data_metadata = {"description": description} if description is not None else {}


def is_concrete_table(cls: type[Any]) -> bool:
    return vars(cls).get("_data_declaration_kind") == "table"


def is_table_group(cls: type[Any]) -> bool:
    return bool(vars(cls).get("_is_table_group", False))


class TableGroup:
    """A final named hierarchy of concrete tables and nested table groups."""

    options: ClassVar[TableGroupOptions] = TableGroupOptions()
    _is_table_group: ClassVar[bool] = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if any(vars(base).get("_is_table_group", False) for base in cls.__mro__[1:]):
            raise TypeError("a final TableGroup may not inherit from another final TableGroup")
        options = vars(cls).get("options", TableGroupOptions())
        if not isinstance(options, TableGroupOptions):
            raise TypeError("TableGroup.options must be a TableGroupOptions value")

        declared: dict[str, type[Any]] = {}
        for base in reversed(cls.__mro__):
            for attribute, value in vars(base).items():
                if isinstance(value, type) and (is_concrete_table(value) or is_table_group(value)):
                    declared[attribute] = value
                elif attribute in declared:
                    del declared[attribute]

        invalid = tuple(
            member
            for member in options.members
            if not is_concrete_table(member) and not is_table_group(member)
        )
        if invalid:
            raise TypeError("table groups may contain only final Table or TableGroup declarations")
        entries = tuple(dict.fromkeys((*options.members, *declared.values())))
        if not entries:
            raise TypeError("table groups must declare at least one member")

        cls._is_table_group = True
        cls._table_group_name = options.name or declaration_name(
            cls.__name__, suffixes=("TableGroup",)
        )
        cls._table_group_entries = entries
        cls._data_annotations = (*_inherited_annotations(cls), *options.annotations)
        description = _description(cls, options.description)
        cls._data_metadata = {"description": description} if description is not None else {}

        from .declarations import group_tables

        group_tables(cls)


__all__ = [
    "BoundSource",
    "BoundTable",
    "BoundTableGroup",
    "DataSourceConfig",
    "InputFormat",
    "Projection",
    "ProjectionOptions",
    "SourceBindingOptions",
    "Struct",
    "StructOptions",
    "Table",
    "TableGroup",
    "TableGroupOptions",
    "TableOptions",
    "TableTemplate",
    "TableTemplateOptions",
    "is_concrete_table",
    "is_table_group",
]
