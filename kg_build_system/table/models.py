"""Data-contract descriptors and source models."""
from __future__ import annotations
from dataclasses import dataclass, field as dataclass_field, replace
from enum import StrEnum
from typing import Any, ClassVar, Generic, Protocol, Self, TypeAlias, TypeVar, cast, get_args, get_type_hints, overload
from ..annotations import Annotation, annotation_tuple
from ..data_types import Scalar, validate_value_type
from ..expressions import Expression, ValueRef, item_type
from .._support.annotations import type_shape
from .._support.naming import declaration_name, member_name

T = TypeVar("T")
V = TypeVar("V")
type FieldValue = Scalar | None
type TableValue = FieldValue | list[FieldValue]
D = TypeVar("D", bound=FieldValue)
P = TypeVar("P", bound=TableValue)
S = TypeVar("S", bound="Struct")


class _StructValue(Protocol):
    """The structural marker used to admit declared records in collections."""

    _is_struct_declaration: ClassVar[bool]


type CollectionItem = FieldValue | _StructValue
C = TypeVar("C", bound=CollectionItem)


@dataclass(frozen=True)
class TablePathValueRefMetadata:
    """Table-specific state carried by a value reference."""

    table: type = object
    path: tuple[str, ...] = ()
    collection_paths: tuple[tuple[str, ...], ...] = ()
    annotations: tuple[Annotation, ...] = ()
    name: str | None = None
    description: str | None = None
    attr: str = ""


@dataclass(frozen=True)
class TablePathValueRef(ValueRef[V]):
    """A typed value reference produced by table or projection navigation."""

    _metadata: TablePathValueRefMetadata = dataclass_field(default_factory=TablePathValueRefMetadata)

    def __getattr__(self, part: str) -> "TablePathValueRef[Any]":
        if part.startswith("_"):
            raise AttributeError(part)
        item = item_type(self.type_hint)
        if part == "element":
            if item is None:
                raise AttributeError("element is only available on a collection field reference")
            return TablePathValueRef[Any](item, "collection", self._metadata)
        shape = item or type_shape(self.type_hint).annotation
        fields = fields_for(shape) if isinstance(shape, type) else {}
        if part not in fields:
            raise AttributeError(f"{self.type_hint!r} has no declared field {part!r}")
        field = fields[part]
        path = self._metadata.path + (field._metadata.name or field._metadata.attr,)
        field_type = field.type_hint | None if type_shape(self.type_hint).nullable and field.type_hint is not Any else field.type_hint
        collection_paths = self._metadata.collection_paths + ((path,) if item_type(field_type) is not None else ())
        return TablePathValueRef[Any](field_type, "collection" if collection_paths else "scalar", TablePathValueRefMetadata(
            table=self._metadata.table,
            path=path,
            collection_paths=collection_paths,
            annotations=self._metadata.annotations + field._metadata.annotations,
        ))


def _bound_metadata(
    reference: TablePathValueRef[Any], instance: object | None, owner: type | None, *, collection: bool,
) -> TablePathValueRefMetadata:
    metadata = reference._metadata
    if isinstance(instance, Struct):
        parent = instance._metadata
        path = parent.path + (metadata.name or metadata.attr,)
        annotations = parent.annotations + metadata.annotations
        table = parent.table
        collection_paths = parent.collection_paths
    else:
        path = (metadata.name or metadata.attr,)
        annotations = metadata.annotations
        table = owner or object
        collection_paths = ()
    if collection:
        collection_paths += (path,)
    return replace(metadata, table=table, path=path, collection_paths=collection_paths, annotations=annotations)


@dataclass(frozen=True)
class Field(TablePathValueRef[D], Generic[D]):
    """A scalar table descriptor and root table value reference."""

    def __set_name__(self, owner: type, attr: str) -> None:
        metadata = self._metadata
        object.__setattr__(self, "_metadata", replace(metadata, attr=attr, name=metadata.name or member_name(attr)))

    @overload
    def __get__(self, instance: None, owner: type | None = None) -> Self: ...

    @overload
    def __get__(self, instance: object, owner: type | None = None) -> Self: ...

    def __get__(self, instance: object | None, owner: type | None = None) -> Self:
        if instance is not None and not isinstance(instance, Struct):
            return self
        metadata = _bound_metadata(self, instance, owner, collection=False)
        return replace(
            self,
            cardinality="collection" if metadata.collection_paths else "scalar",
            _metadata=metadata,
        )


@dataclass(frozen=True)
class StructField(TablePathValueRef[S], Generic[S]):
    """A reference to a declared struct, navigated through ``member`` or ``m``."""

    def __set_name__(self, owner: type, attr: str) -> None:
        metadata = self._metadata
        object.__setattr__(self, "_metadata", replace(metadata, attr=attr, name=metadata.name or member_name(attr)))

    def __get__(self, instance: object | None, owner: type | None = None) -> Self:
        if instance is not None and not isinstance(instance, Struct):
            return self
        metadata = _bound_metadata(self, instance, owner, collection=False)
        return replace(self, cardinality="collection" if metadata.collection_paths else "scalar", _metadata=metadata)

    @property
    def member(self) -> S:
        shape = type_shape(self.type_hint).annotation
        if not isinstance(shape, type) or not issubclass(shape, Struct):
            raise TypeError("StructField requires a Struct type")
        return cast(S, shape(_metadata=self._metadata))

    @property
    def m(self) -> S:
        return self.member


@dataclass(frozen=True)
class CollectionField(TablePathValueRef[list[C]], Generic[C]):
    """A collection declaration, whose item may be a scalar or a ``Struct``."""

    def __set_name__(self, owner: type, attr: str) -> None:
        metadata = self._metadata
        object.__setattr__(self, "_metadata", replace(metadata, attr=attr, name=metadata.name or member_name(attr)))

    def __get__(self, instance: object | None, owner: type | None = None) -> Self:
        if instance is not None and not isinstance(instance, Struct):
            return self
        return replace(self, cardinality="collection", _metadata=_bound_metadata(self, instance, owner, collection=True))

    @property
    def element(self) -> C:
        shape = item_type(self.type_hint)
        if not isinstance(shape, type) or not issubclass(shape, Struct):
            raise TypeError("CollectionField.element requires a Struct item type")
        return cast(C, shape(_metadata=self._metadata))

    @property
    def e(self) -> C:
        return self.element


def fields_for(cls: type) -> dict[str, "TablePathValueRef[Any]"]:
    """Resolve the declared data shape for final declarations and plain mixins alike."""
    fields: dict[str, TablePathValueRef[Any]] = {}
    for base in reversed(cls.__mro__):
        fields.update({name: value for name, value in vars(base).items() if isinstance(value, (Field, StructField, CollectionField))})
    hints = get_type_hints(cls)
    for attribute, descriptor in fields.items():
        arguments = get_args(hints.get(attribute, Any))
        type_hint = arguments[0] if arguments else Any
        if isinstance(descriptor, Field):
            shape = type_shape(type_hint)
            structured_type = shape.item_annotation or shape.annotation
            if isinstance(structured_type, type) and Struct in getattr(structured_type, "__mro__", ()):
                required = "CollectionField" if shape.item_annotation is not None else "StructField"
                raise TypeError(f"{cls.__name__}.{attribute} uses a Struct type; declare it with {required}")
            validate_value_type(type_hint, context=f"{cls.__name__}.{attribute}", allow_collection=False)
        elif isinstance(descriptor, StructField):
            if not isinstance(type_hint, type) or Struct not in getattr(type_hint, "__mro__", ()):
                raise TypeError(f"{cls.__name__}.{attribute} must declare a StructField[Struct]")
        elif isinstance(descriptor, CollectionField):
            if not (isinstance(type_hint, type) and Struct in getattr(type_hint, "__mro__", ())):
                validate_value_type(type_hint, context=f"{cls.__name__}.{attribute} collection item", allow_collection=False)
            type_hint = list[type_hint]
        object.__setattr__(descriptor, "type_hint", type_hint)
    return fields

@dataclass(frozen=True)
class ProjectedField(Generic[P]):
    expression: Expression[P] | ValueRef[P]
    name: str | None = None
    attr: str = ""
    annotations: tuple[Annotation, ...] = ()
    def __set_name__(self, owner: type, attr: str) -> None:
        object.__setattr__(self, "attr", attr)
        if self.name is None: object.__setattr__(self, "name", member_name(attr))
    def __get__(self, instance: object | None, owner: type | None = None) -> Expression[P] | ValueRef[P]:
        return self.expression if instance is not None else TablePathValueRef[P](
            self.expression.type_hint,
            self.expression.cardinality,
            TablePathValueRefMetadata(
                table=owner or object,
                path=(self.name or self.attr,),
                annotations=self.annotations,
            ),
        )

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
        for attribute, value in vars(cls).items():
            if isinstance(value, ProjectedField):
                _validate_projection_value(value.expression)
                validate_value_type(value.expression.type_hint, context=f"{cls.__name__}.{attribute}", allow_collection=True)
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


def _validate_projection_value(value: Expression[Any] | ValueRef[Any]) -> None:
    if isinstance(value, TablePathValueRef):
        if not _is_concrete_table(value._metadata.table):
            raise TypeError("projections may reference only final Table inputs")
    elif isinstance(value, Expression):
        for argument in value.args:
            if isinstance(argument, (Expression, ValueRef)):
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
    _is_struct_declaration: ClassVar[bool] = True

    def __init__(self, *, _metadata: TablePathValueRefMetadata = TablePathValueRefMetadata()) -> None:
        self._metadata = _metadata

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
