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
class StructOptionsTemplate:
    """Annotations-only options for the data-domain template tier.

    A template carries no identity syntax, so it has no name or description.
    """

    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


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


def _template_annotations(cls: type[Any]) -> tuple[Annotation, ...]:
    """Collect each template's own contribution in C3 order, base first.

    Only templates contribute: an IR-visible declaration's own options stay
    on its own IR entry. Because the walk reads each class's own dict over
    the MRO, a template entering through several branches contributes once.
    """
    return tuple(
        annotation
        for base in reversed(cls.__mro__[1:])
        for annotation in vars(base).get("_data_template_annotations", ())
    )


def _record_template_annotations(cls: type[Any], options: Any) -> None:
    """Record a template class's own annotation contribution."""
    if options is None:
        cls._data_template_annotations = ()
        return
    if isinstance(options, StructOptionsTemplate):
        cls._data_template_annotations = tuple(options.annotations)
        return
    if isinstance(options, (TableOptions, StructOptions)):
        raise TypeError(
            f"{cls.__name__} is a data template: its options must be "
            "StructOptionsTemplate, which carries no name or description — wrap it: "
            "`options = StructOptionsTemplate(annotations=(...))`"
        )
    raise TypeError(
        f"{cls.__name__} is a data template: wrap the value: "
        "`options = StructOptionsTemplate(annotations=(...))`"
    )


def _require_host_options(cls: type[Any], kind: str, options: Any, expected: type) -> None:
    """IR-visible declarations own real options; templates never flow as hosts."""
    if isinstance(options, StructOptionsTemplate):
        raise TypeError(
            f"{cls.__name__} is a {kind} declaration: declare {expected.__name__}, "
            "not template options"
        )
    if not isinstance(options, expected):
        raise TypeError(f"{kind}.options must be a {expected.__name__} value")


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


class Table(StructDeclaration):
    """A final, source-bindable logical table declaration."""

    options: ClassVar[TableOptions] = TableOptions()
    _data_declaration_kind: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if any(vars(base).get("_data_declaration_kind") == "table" for base in cls.__mro__[1:]):
            raise TypeError("a final Table may not inherit from another final Table")
        options = vars(cls).get("options", TableOptions())
        _require_host_options(cls, "Table", options, TableOptions)
        name = options.name or declaration_name(cls.__name__, suffixes=("Table",))
        cls._table_name = name
        _prepare_fields(
            cls,
            kind="table",
            name=name,
            description=_description(cls, options.description),
            annotations=(*_template_annotations(cls), *options.annotations),
        )


class StructTemplate:
    """The data-domain template tier for both ``Table`` and ``Struct`` hosts.

    A template shares field slots and annotation flow with its hosts and
    never enters the blueprint IR; it carries no name or description.
    Authoring order follows the topology convention with templates first:
    ``class Entity(EntityTemplate, Table)``. A template extending a base
    template simply names the base, which already carries this root —
    ``class AuditedShape(EntityTemplate)``.
    """

    options: ClassVar[Any] = StructOptionsTemplate()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if issubclass(cls, (Projection, TableGroup)):
            raise TypeError(
                f"{cls.__name__} mixes StructTemplate into a non-record declaration: "
                "the template tier serves only Table and Struct hosts"
            )
        if issubclass(cls, (Table, Struct)):
            return  # host declaration: the host's own hook finalizes it
        _record_template_annotations(cls, vars(cls).get("options"))


class Struct(StructDeclaration):
    """A nested-record declaration composed from unified fields.

    A struct is composable (referenced as ``Field[CityStruct]``), not a reuse
    mechanism: shared shape concerns belong to the ``StructTemplate`` tier.
    """

    options: ClassVar[StructOptions] = StructOptions()
    _data_declaration_kind: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options", StructOptions())
        _require_host_options(cls, "Struct", options, StructOptions)
        name = options.name or declaration_name(cls.__name__, suffixes=("Struct",))
        _prepare_fields(
            cls,
            kind="struct",
            name=name,
            description=_description(cls, options.description),
            annotations=(*_template_annotations(cls), *options.annotations),
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
        _require_host_options(cls, "Projection", options, ProjectionOptions)

        from .projections import declared_projection_fields

        fields = declared_projection_fields(cls)
        if not fields:
            raise TypeError("projections must declare at least one projection_field")
        cls._projection_name = options.name or declaration_name(
            cls.__name__, suffixes=("Projection",)
        )
        cls._projection_fields = fields
        cls._data_declaration_kind = "projection"
        cls._data_annotations = tuple(options.annotations)
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
        _require_host_options(cls, "TableGroup", options, TableGroupOptions)

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
        cls._data_annotations = tuple(options.annotations)
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
    "StructOptionsTemplate",
    "StructTemplate",
    "Table",
    "TableGroup",
    "TableGroupOptions",
    "TableOptions",
    "is_concrete_table",
    "is_table_group",
]
