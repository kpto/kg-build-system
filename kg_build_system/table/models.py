"""Data-contract descriptors and source models."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar, Generic, Self, TypeAlias, TypeVar, get_args, get_type_hints, overload
from ..annotations import Annotation, annotation_tuple
from ..expressions import Expression, FieldPath, item_type
from .._support.naming import declaration_name, member_name

T = TypeVar("T")

@dataclass(frozen=True)
class Field(Generic[T]):
    name: str | None = None
    description: str | None = None
    type_hint: Any = None
    attr: str = ""
    annotations: tuple[Annotation, ...] = ()
    def __set_name__(self, owner: type, attr: str) -> None:
        object.__setattr__(self, "attr", attr)
        if self.name is None: object.__setattr__(self, "name", member_name(attr))
    @overload
    def __get__(self, instance: None, owner: type | None = None) -> FieldPath[T]: ...
    @overload
    def __get__(self, instance: object, owner: type | None = None) -> Self: ...
    def __get__(self, instance: object | None, owner: type | None = None) -> FieldPath[T] | Self:
        if instance is not None: return self
        path = (self.name or self.attr,); collections = (path,) if item_type(self.type_hint) is not None else ()
        return FieldPath[T](owner or object, path, self.type_hint, "collection" if collections else "scalar", collections, self.annotations)


def fields_for(cls: type) -> dict[str, "Field[Any]"]:
    """Resolve the declared data shape for final declarations and plain mixins alike."""
    fields: dict[str, Field[Any]] = {}
    for base in reversed(cls.__mro__):
        fields.update({name: value for name, value in vars(base).items() if isinstance(value, Field)})
    hints = get_type_hints(cls)
    for attribute, descriptor in fields.items():
        arguments = get_args(hints.get(attribute, Any))
        object.__setattr__(descriptor, "type_hint", arguments[0] if arguments else Any)
    return fields

@dataclass(frozen=True)
class ProjectedField(Generic[T]):
    expression: Expression[T] | FieldPath[T]
    name: str | None = None
    attr: str = ""
    annotations: tuple[Annotation, ...] = ()
    def __set_name__(self, owner: type, attr: str) -> None:
        object.__setattr__(self, "attr", attr)
        if self.name is None: object.__setattr__(self, "name", member_name(attr))
    def __get__(self, instance: object | None, owner: type | None = None) -> Expression[T] | FieldPath[T]:
        return self.expression if instance is not None else FieldPath[T](owner or object, (self.name or self.attr,), self.expression.type_hint, self.expression.cardinality, (), self.annotations)

class InputFormat(StrEnum): CSV = "csv"; JSON = "json"; PARQUET = "parquet"
@dataclass(frozen=True)
class DataSourceConfig: location: str; format: InputFormat = InputFormat.CSV; layout: str | None = None; credentials: str | None = None; version: str | None = None
@dataclass(frozen=True)
class BoundTable:
    table: type
    config: DataSourceConfig
    annotations: tuple[Annotation, ...] = ()


@dataclass(frozen=True)
class BoundTableGroup:
    group: type
    config: DataSourceConfig
    annotations: tuple[Annotation, ...] = ()


BoundSource: TypeAlias = BoundTable | BoundTableGroup


@dataclass(frozen=True)
class TableOptions:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None: object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True)
class TableTemplateOptions(TableOptions):
    pass


@dataclass(frozen=True)
class StructOptions:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None: object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True)
class ProjectionOptions:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None: object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True)
class TableGroupOptions:
    members: tuple[type, ...]
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None: object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True)
class SourceBindingOptions:
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None: object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


def _description(cls: type, configured: str | None) -> str | None:
    return configured if configured is not None else (vars(cls).get("__doc__") or None)


def _prepare_final(cls: type, kind: str, options: TableOptions | StructOptions | ProjectionOptions) -> None:
    if kind == "table" and any(vars(base).get("_data_declaration_kind") == "table" for base in cls.__mro__[1:]):
        raise TypeError("a final Table may not inherit from another final Table")
    suffixes = {"table": ("Table",), "table_template": ("TableTemplate", "Template"), "struct": ("Struct",), "projection": ("Projection",)}[kind]
    fields = fields_for(cls) if kind != "projection" else {}
    if kind == "projection":
        for value in vars(cls).values():
            if isinstance(value, ProjectedField):
                _validate_projection_value(value.expression)
        setattr(cls, "_projection_fields", {name: value for name, value in vars(cls).items() if isinstance(value, ProjectedField)})
        setattr(cls, "_projection_name", options.name or declaration_name(cls.__name__, suffixes=suffixes))
    else:
        setattr(cls, "_fields", fields)
        setattr(cls, "_data_name", options.name or declaration_name(cls.__name__, suffixes=suffixes))
        if kind == "table":
            setattr(cls, "_table_name", cls._data_name)
    setattr(cls, "_data_declaration_kind", kind)
    annotations = tuple(annotation for base in reversed(cls.__mro__[1:]) for annotation in vars(base).get("_data_annotations", ())) + tuple(options.annotations)
    description = _description(cls, options.description)
    setattr(cls, "_data_annotations", annotations)
    setattr(cls, "_data_metadata", {"description": description} if description is not None else {})


def _is_concrete_table(cls: type) -> bool:
    return vars(cls).get("_data_declaration_kind") == "table"


def _validate_projection_value(value: Expression[Any] | FieldPath[Any]) -> None:
    if isinstance(value, FieldPath):
        if not _is_concrete_table(value.table):
            raise TypeError("projections may reference only final Table inputs")
    elif isinstance(value, Expression):
        for argument in value.args:
            if isinstance(argument, (Expression, FieldPath)):
                _validate_projection_value(argument)


class Table:
    """Final, source-bindable logical table declaration."""
    options: ClassVar[TableOptions] = TableOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options", TableOptions())
        if not isinstance(options, TableOptions):
            raise TypeError("Table.options must be a TableOptions value")
        _prepare_final(cls, "table", options)


class TableTemplate:
    """Optional reusable table shape with annotations and a stable name."""
    options: ClassVar[TableTemplateOptions] = TableTemplateOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # A reusable template may precede Table in a natural multiple-
        # inheritance declaration.  In that MRO this hook wins, so finalise
        # the class as a table rather than as another template.
        if Table in cls.__mro__[1:]:
            options = vars(cls).get("options", TableOptions())
            if not isinstance(options, TableOptions):
                raise TypeError("Table.options must be a TableOptions value")
            _prepare_final(cls, "table", options)
            return
        options = vars(cls).get("options", TableTemplateOptions())
        if not isinstance(options, TableTemplateOptions):
            raise TypeError("TableTemplate.options must be a TableTemplateOptions value")
        _prepare_final(cls, "table_template", options)


class Struct:
    """Final reusable nested record declaration."""
    options: ClassVar[StructOptions] = StructOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options", StructOptions())
        if not isinstance(options, StructOptions):
            raise TypeError("Struct.options must be a StructOptions value")
        _prepare_final(cls, "struct", options)


class Projection:
    """Final logical projection declaration."""
    options: ClassVar[ProjectionOptions] = ProjectionOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options", ProjectionOptions())
        if not isinstance(options, ProjectionOptions):
            raise TypeError("Projection.options must be a ProjectionOptions value")
        _prepare_final(cls, "projection", options)


class TableGroup:
    """Final named group of source-bindable tables and nested groups."""
    options: ClassVar[TableGroupOptions]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options")
        if not isinstance(options, TableGroupOptions):
            raise TypeError("TableGroup.options must be a TableGroupOptions value")
        if not options.members:
            raise TypeError("TableGroup.options.members must not be empty")
        if any(not _is_concrete_table(item) and not vars(item).get("_is_table_group", False) for item in options.members):
            raise TypeError("table groups may include only final Table declarations or TableGroup declarations")
        cls._is_table_group = True
        cls._table_group_name = options.name or declaration_name(cls.__name__, suffixes=("TableGroup",))
        cls._table_group_entries = options.members
        annotations = tuple(annotation for base in reversed(cls.__mro__[1:]) for annotation in vars(base).get("_data_annotations", ())) + tuple(options.annotations)
        description = _description(cls, options.description)
        cls._data_annotations = annotations
        cls._data_metadata = {"description": description} if description is not None else {}
        # Validate recursive membership and duplicate inclusion as soon as the
        # declaration is completed, not only when a source is bound later.
        from .declarations import _group_tables
        _group_tables(cls)
