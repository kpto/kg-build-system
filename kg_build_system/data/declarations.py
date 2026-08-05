"""Table, struct, and projection decorators."""
from __future__ import annotations
from dataclasses import replace
from typing import Any, Callable, Protocol, TypeVar, cast, overload
from ..expressions import Expression, FieldPath
from .._support.naming import declaration_name
from .models import BoundSource, BoundTable, BoundTableGroup, DataSourceConfig, Field, ProjectedField, fields_for

T = TypeVar("T")
C = TypeVar("C")

class TableDecorator(Protocol):
    def __call__(self, cls: type[C]) -> type[C]: ...


class TableGroupDecorator(Protocol):
    def __call__(self, cls: type[C]) -> type[C]: ...


class ProjectionDecorator(Protocol):
    def __call__(self, cls: type[C]) -> type[C]: ...


class Included:
    def __init__(self, target: type) -> None:
        self.target = target

def field[T](*, name: str | None = None, description: str | None = None) -> Field[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    return Field(name=name, description=description)

def _declaration_kind(cls: type) -> str | None:
    return vars(cls).get("_data_declaration_kind")


def is_concrete_table(cls: type) -> bool:
    return _declaration_kind(cls) == "table"


def _is_table_group(cls: type) -> bool:
    return bool(vars(cls).get("_is_table_group", False))


def _prepare(cls: type[C], kind: str, *, name: str | None = None, metadata: dict[str, Any] | None = None) -> type[C]:
    if kind == "table" and any(_declaration_kind(base) == "table" for base in cls.__mro__[1:]):
        raise TypeError("a final @table may not inherit from another final @table")
    inherited_metadata: dict[str, Any] = {}
    for base in reversed(cls.__mro__[1:]):
        inherited_metadata.update(vars(base).get("_data_metadata", {}))
    inherited_metadata.update(metadata or {})
    setattr(cls, "_fields", fields_for(cls))
    setattr(cls, "_data_declaration_kind", kind)
    setattr(cls, "_data_metadata", inherited_metadata)
    suffixes = {
        "table": ("Table",),
        "table_template": ("TableTemplate", "Template"),
        "struct": ("Struct",),
    }.get(kind, ())
    resolved_name = name or declaration_name(cls.__name__, suffixes=suffixes)
    setattr(cls, "_data_name", resolved_name)
    if kind == "table":
        setattr(cls, "_table_name", resolved_name)
    return cls

def table(*, name: str | None = None) -> TableDecorator:
    def decorate(cls: type[C]) -> type[C]: return _prepare(cls, "table", name=name)
    return cast(TableDecorator, decorate)

def table_template(*, name: str | None = None, description: str | None = None, **metadata: Any) -> TableDecorator:
    if description is not None:
        metadata["description"] = description
    def decorate(cls: type[C]) -> type[C]: return _prepare(cls, "table_template", name=name, metadata=metadata)
    return cast(TableDecorator, decorate)


def include(target: type) -> Included:
    if not is_concrete_table(target) and not _is_table_group(target):
        raise TypeError("table groups may include only final @table declarations or @table_group declarations")
    return Included(target)


def table_group(*, name: str | None = None) -> TableGroupDecorator:
    def decorate(cls: type[C]) -> type[C]:
        entries = tuple(value.target for value in vars(cls).values() if isinstance(value, Included))
        if not entries:
            raise TypeError("a @table_group must include at least one table or nested group")
        setattr(cls, "_is_table_group", True)
        setattr(cls, "_table_group_name", name or declaration_name(cls.__name__, suffixes=("TableGroup",)))
        setattr(cls, "_table_group_entries", entries)
        _group_tables(cls)  # validate nesting and duplicate table inclusion eagerly
        return cls
    return cast(TableGroupDecorator, decorate)


def _group_tables(group: type, prefix: tuple[str, ...] = (), visited: tuple[type, ...] = ()) -> tuple[tuple[type, tuple[str, ...]], ...]:
    if group in visited:
        raise TypeError("table groups may not contain a cycle")
    path = prefix + (group._table_group_name,)
    result: list[tuple[type, tuple[str, ...]]] = []
    for target in group._table_group_entries:
        if is_concrete_table(target):
            result.append((target, path + (target._table_name,)))
        else:
            result.extend(_group_tables(target, path, visited + (group,)))
    tables = [table for table, _ in result]
    paths = [catalog_path for _, catalog_path in result]
    if len(set(tables)) != len(tables):
        raise TypeError("a table group may include a final table only once")
    if len(set(paths)) != len(paths):
        raise TypeError("a table group has duplicate catalog paths")
    return tuple(result)


@overload
def struct(cls: type[C]) -> type[C]: ...
@overload
def struct(*, name: str | None = None, description: str | None = None, **metadata: Any) -> Callable[[type[C]], type[C]]: ...
def struct(cls: type[C] | None = None, *, name: str | None = None, description: str | None = None, **metadata: Any) -> type[C] | Callable[[type[C]], type[C]]:
    if description is not None:
        metadata["description"] = description
    def decorate(shape: type[C]) -> type[C]: return _prepare(shape, "struct", name=name, metadata=metadata)
    return decorate if cls is None else decorate(cls)

def projected_field[T](value: Expression[T] | FieldPath[T]) -> ProjectedField[T]: return ProjectedField(value)

def _validate_projection_value(value: Expression[Any] | FieldPath[Any]) -> None:
    if isinstance(value, FieldPath):
        if not is_concrete_table(value.table):
            raise TypeError("projections may reference only final @table inputs")
        return
    for argument in value.args:
        if isinstance(argument, (Expression, FieldPath)):
            _validate_projection_value(argument)


@overload
def projection(cls: type[C]) -> type[C]: ...
@overload
def projection(*, name: str | None = None) -> ProjectionDecorator: ...
def projection(cls: type[C] | None = None, *, name: str | None = None) -> type[C] | ProjectionDecorator:
    def decorate(shape: type[C]) -> type[C]:
        for value in vars(shape).values():
            if isinstance(value, ProjectedField):
                _validate_projection_value(value.expression)
        setattr(shape, "_projection_fields", {attribute: value for attribute, value in vars(shape).items() if isinstance(value, ProjectedField)})
        setattr(shape, "_projection_name", name or declaration_name(shape.__name__, suffixes=("Projection",)))
        return shape
    return decorate if cls is None else decorate(cls)

def _location_for(config: DataSourceConfig, group_path: tuple[str, ...], table_name: str) -> str:
    if config.layout is None:
        raise ValueError("group sources require DataSourceConfig.layout to resolve each final resource address")
    try:
        relative_location = config.layout.format(group_path="/".join(group_path), table_name=table_name)
    except (IndexError, KeyError) as error:
        raise ValueError("group source layouts may use only {group_path} and {table_name}") from error
    return f"{config.location.rstrip('/\\')}/{relative_location.lstrip('/\\')}"


def resolve_bound_source(source: BoundSource) -> tuple[BoundTable, ...]:
    """Resolve a group source to its executable concrete table resources."""
    if isinstance(source, BoundTable):
        return (source,)
    return tuple(
        BoundTable(table, replace(source.config, location=_location_for(source.config, catalog_path[:-1], catalog_path[-1]), layout=None))
        for table, catalog_path in _group_tables(source.group)
    )


def bind_source(*, target: type, config: DataSourceConfig) -> BoundSource:
    if is_concrete_table(target):
        return BoundTable(target, config)
    if _is_table_group(target):
        return BoundTableGroup(target, config)
    raise TypeError("sources require a final @table or @table_group")
