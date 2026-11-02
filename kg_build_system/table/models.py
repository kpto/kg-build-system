"""Logical data declarations and physical source-binding models.

A declaration class is authoring syntax. While the class is created, its fields
and options are lowered into a frozen ``DeclarationSpec`` stored on the class.
The language reads that spec, never a private authoring attribute, so the IR is
independent of the class that produced it.

Two compatibility forms are supported deliberately:

* ``Projection(source.row_source())`` pins a row source, the preferred model;
  a bare ``class P(Projection)`` with ``projection_field(...)`` outputs is the
  older form and derives its scan from its output expressions.
* ``field()`` is the one source-backed descriptor and ``computed_field()`` the
  one expression-backed descriptor; they replace the old separate field classes.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Self, TypeAlias, TypeVar

from .._support.interfaces import declaration_name
from ..annotations.interfaces import Annotation, annotation_tuple
from ..types.interfaces import Shape, Struct as StructDeclaration
from .fields import FieldSpec, resolve_field_specs
from .row_sources.values import RowSource

if TYPE_CHECKING:
    from ..expressions.interfaces import BoolExpression
    from .row_sources import DerivedRowSource, RelationRowSource


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
class TableOptions:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("table names must be non-empty")
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True, slots=True)
class StructOptionsTemplate:
    """Annotations-only options for the data-domain template tier."""

    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True, slots=True)
class StructOptions:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("struct names must be non-empty")
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True, slots=True)
class ProjectionOptions:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("projection names must be non-empty")
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True, slots=True)
class TableGroupOptions:
    members: tuple[type, ...] = ()
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("table-group names must be non-empty")
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True, slots=True)
class SourceBindingOptions:
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True, slots=True)
class DeclarationSpec:
    """The frozen authoring facts of one declaration class."""

    kind: str
    name: str | None
    description: str | None
    annotations: tuple[Annotation, ...]
    fields: tuple[FieldSpec, ...] = ()
    final: bool = True
    row_source: Any = None
    members: tuple[type[Any], ...] = ()


def _description(cls: type[Any], configured: str | None) -> str | None:
    return configured if configured is not None else (vars(cls).get("__doc__") or None)


def _final_kind(cls: type[Any]) -> str | None:
    spec = vars(cls).get("_kg_declaration_spec")
    return spec.kind if isinstance(spec, DeclarationSpec) and spec.final else None


def _template_annotations(cls: type[Any]) -> tuple[Annotation, ...]:
    """Collect each template's own contribution in C3 order, base first."""
    return tuple(
        annotation
        for base in reversed(cls.__mro__[1:])
        for annotation in vars(base).get("_kg_template_annotations", ())
    )


def _record_template_annotations(cls: type[Any], options: Any) -> None:
    if options is None:
        cls._kg_template_annotations = ()
        return
    if isinstance(options, StructOptionsTemplate):
        cls._kg_template_annotations = tuple(options.annotations)
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
    if isinstance(options, StructOptionsTemplate):
        raise TypeError(
            f"{cls.__name__} is a {kind} declaration: declare {expected.__name__}, "
            "not template options"
        )
    if not isinstance(options, expected):
        raise TypeError(f"{kind}.options must be a {expected.__name__} value")


def _prepare_declaration(
    cls: type[Any],
    *,
    kind: str,
    name: str | None,
    description: str | None,
    annotations: tuple[Annotation, ...],
    final: bool = True,
    row_source: Any = None,
    members: tuple[type[Any], ...] = (),
) -> DeclarationSpec:
    field_kind = "source" if kind in {"table", "struct"} else "computed"
    fields = resolve_field_specs(cls, field_kind)
    spec = DeclarationSpec(
        kind=kind,
        name=name,
        description=description,
        annotations=annotations,
        fields=fields,
        final=final,
        row_source=row_source,
        members=members,
    )
    cls._kg_declaration_spec = spec
    cls._fields = {item.attribute: item.descriptor for item in fields}
    cls._data_name = name
    cls._data_annotations = annotations
    cls._data_metadata = {"description": description} if description is not None else {}
    cls._data_declaration_kind = kind if final else None
    return spec


S = TypeVar("S", bound=Shape)


def _derive(
    declaration: type[Any],
    predicate: Callable[[Any], "BoolExpression"],
) -> "DerivedRowSource[Any]":
    from ..expressions.interfaces import BoolExpression
    from .row_sources import derive_row_source, shape_context, shape_view

    if not callable(predicate):
        raise TypeError("where requires a callable predicate")
    shape = shape_view(declaration)
    result = predicate(shape_context(shape))
    if not isinstance(result, BoolExpression):
        raise TypeError("where predicates must return a BoolExpression")
    return derive_row_source(declaration.row_source(), result, shape=shape)


def shape_view(source: Any) -> type[Shape]:
    """A shape class with the source's fields, usable as a projection base."""
    from .row_sources import shape_view as _shape_view

    return _shape_view(source)


def pinned_base(row_source: Any) -> type["Projection"]:
    """A dynamic base carrying only a row source pin."""
    attrs: dict[str, Any] = {
        "_kg_row_source": row_source,
        "_projection_base": True,
    }
    return type("PinnedProjectionBase", (Projection,), attrs)


def projection_base(row_source: Any) -> type["Projection"]:
    """A dynamic base carrying a row source plan and its inherited fields.

    The base is not a final projection; finish it with a named subclass.

    Example:
        ```python
        from kg_build_system import computed_field

        class SiteLabels(SiteTable.projection_base()):
            label = computed_field(SiteTable.name)
        ```
    """
    from .row_sources import as_row_source, projection_attrs

    source = as_row_source(row_source)
    attrs = projection_attrs(source.shape)
    attrs["_kg_row_source"] = source
    attrs["_projection_base"] = True
    base_name = getattr(getattr(source, "source", None), "__name__", "RowSource")
    name = f"{base_name}ProjectionBase"
    return type(name, (Projection,), attrs)


def _derive_projection_plan(declaration: type[Any]) -> Any | None:
    """Derive the scan of an unpinned projection from its output expressions.

    The compatibility form has no pin, so its plan is the one logical source its
    outputs read. A projection reading no source or several unrelated sources has
    no single driving relation and stays unplanned; compilation rejects it.
    """
    from ..expressions.interfaces import expression_to_ir
    from ..expressions.ir import FieldReferenceExpressionIR
    from .ir import RowScanIR

    try:
        from ..expressions.interfaces import walk_expression_ir
    except ImportError:  # pragma: no cover - depends on the expressions surface
        from ..expressions.ir import walk_expression_ir

    spec = vars(declaration).get("_kg_declaration_spec")
    if spec is None:
        return getattr(declaration, "_projection_row_source", None)
    sources: set[str] = set()
    for item in spec.fields:
        expression = item.descriptor.expression
        if expression is None:
            continue
        for node in walk_expression_ir(expression_to_ir(expression.model)):
            if isinstance(node, FieldReferenceExpressionIR):
                sources.add(node.source)
    if len(sources) == 1:
        return RowScanIR(next(iter(sources)))
    return None


def projection_row_source(declaration: type["Projection"]) -> Any | None:
    """The pinned plan, or the plan derived from an old-style projection."""
    spec = vars(declaration).get("_kg_declaration_spec")
    pinned = spec.row_source if spec is not None else getattr(
        declaration, "_projection_row_source", None,
    )
    if pinned is not None:
        return pinned
    return _derive_projection_plan(declaration)


class Table(StructDeclaration, RowSource["Table"]):
    """A final, source-bindable logical table declaration."""

    options: ClassVar[TableOptions] = TableOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if any(_final_kind(base) == "table" for base in cls.__mro__[1:]):
            raise TypeError("a final Table may not inherit from another final Table")
        options = vars(cls).get("options", TableOptions())
        _require_host_options(cls, "Table", options, TableOptions)
        name = options.name or declaration_name(cls.__name__, suffixes=("Table",))
        cls._table_name = name
        _prepare_declaration(
            cls,
            kind="table",
            name=name,
            description=_description(cls, options.description),
            annotations=(*_template_annotations(cls), *options.annotations),
        )
        cls.shape = cls

    @classmethod
    def where(
        cls, predicate: Callable[[Self], "BoolExpression"],
    ) -> "DerivedRowSource[Self]":
        """Keep the rows of this table that satisfy ``predicate``.

        The predicate receives a symbolic instance of the table and must return
        a ``BoolExpression``.

        Example:
            ```python
            active = SiteTable.where(
                lambda site: site.name.alter_rows().drop_null().expression.equals("Depot")
            )
            ```
        """
        return _derive(cls, predicate)

    @classmethod
    def projection_base(cls) -> type:
        """Return a projection base pinned to this table's relation.

        Example:
            ```python
            from kg_build_system import computed_field

            class SiteLabels(SiteTable.projection_base()):
                label = computed_field(SiteTable.name)
            ```
        """
        return projection_base(cls.row_source())

    @classmethod
    def row_source(cls) -> "RelationRowSource[Self]":
        """Return the relation row source for this table.

        Example:
            ```python
            sites = SiteTable.row_source()
            ```
        """
        from .row_sources import RelationRowSource

        return RelationRowSource(cls, cls)


class StructTemplate:
    """The template tier for ``Table``, ``Struct`` and ``ComputedStruct`` hosts.

    A template shares field slots and annotation flow with its hosts and never
    enters the IR. It carries annotations only, no name or description.
    """

    options: ClassVar[Any] = StructOptionsTemplate()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if issubclass(cls, (Projection, TableGroup)):
            raise TypeError(
                f"{cls.__name__} mixes StructTemplate into a non-record declaration: "
                "the template tier serves only Table, Struct and ComputedStruct hosts"
            )
        super().__init_subclass__(**kwargs)
        if issubclass(cls, (Table, Struct, ComputedStruct)):
            return
        _record_template_annotations(cls, vars(cls).get("options"))


class Struct(StructDeclaration):
    """A nested-record declaration composed from source-backed fields."""

    options: ClassVar[StructOptions] = StructOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options", StructOptions())
        _require_host_options(cls, "Struct", options, StructOptions)
        name = options.name or declaration_name(cls.__name__, suffixes=("Struct",))
        _prepare_declaration(
            cls,
            kind="struct",
            name=name,
            description=_description(cls, options.description),
            annotations=(*_template_annotations(cls), *options.annotations),
        )


class ComputedStruct(StructDeclaration):
    """A value record whose members are expression-backed type witnesses."""

    options: ClassVar[StructOptions] = StructOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        options = vars(cls).get("options", StructOptions())
        _require_host_options(cls, "ComputedStruct", options, StructOptions)
        name = options.name or declaration_name(cls.__name__, suffixes=("ComputedStruct",))
        _prepare_declaration(
            cls,
            kind="computed_struct",
            name=name,
            description=_description(cls, options.description),
            annotations=(*_template_annotations(cls), *options.annotations),
        )


class ProjectionMeta(type):
    """Make ``Projection(source)`` return a base pinned to a row source."""

    def __call__(cls, source: Any | None = None) -> type["Projection"]:
        if source is None:
            raise TypeError(
                "Projection(source) requires a row source; "
                "declare outputs on a named subclass"
            )
        from .row_sources import as_row_source

        return pinned_base(as_row_source(source))


class Projection(Shape, RowSource["Projection"], metaclass=ProjectionMeta):
    """A final named logical relation composed from typed expressions."""

    options: ClassVar[ProjectionOptions] = ProjectionOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        is_base = bool(vars(cls).get("_projection_base", False))
        if not is_base and any(
            _final_kind(base) == "projection" for base in cls.__mro__[1:]
        ):
            raise TypeError("a final Projection may not inherit from another final Projection")
        options = vars(cls).get("options", ProjectionOptions())
        _require_host_options(cls, "Projection", options, ProjectionOptions)

        row_source = next(
            (
                vars(base).get("_kg_row_source")
                for base in cls.__mro__
                if "_kg_row_source" in vars(base)
            ),
            None,
        )
        name = options.name or declaration_name(
            cls.__name__, suffixes=("Projection",)
        )
        spec = _prepare_declaration(
            cls,
            kind="projection",
            name=name,
            description=_description(cls, options.description),
            annotations=tuple(options.annotations),
            final=not is_base,
            row_source=row_source,
        )
        if not spec.fields and not is_base:
            raise TypeError("projections must declare at least one computed_field")
        cls._projection_name = name
        cls._projection_row_source = row_source
        setattr(cls, "shape", shape_view(cls))

    @classmethod
    def where(
        cls, predicate: Callable[[Self], "BoolExpression"],
    ) -> "DerivedRowSource[Self]":
        """Keep the rows of this projection that satisfy ``predicate``.

        The predicate receives a symbolic instance of the projection and must
        return a ``BoolExpression``.

        Example:
            ```python
            active = SiteProjection.where(
                lambda projection: projection.label.alter_rows().drop_null()
                .expression.equals("Depot")
            )
            ```
        """
        return _derive(cls, predicate)

    @classmethod
    def projection_base(cls) -> type:
        """Return a projection base pinned to this projection's relation.

        Example:
            ```python
            from kg_build_system import computed_field

            class SiteLabels(SiteProjection.projection_base()):
                display = computed_field(SiteProjection.label)
            ```
        """
        return projection_base(cls.row_source())

    @classmethod
    def row_source(cls) -> "RelationRowSource[Any]":
        """Return the relation row source for this projection.

        Example:
            ```python
            rows = SiteProjection.row_source()
            ```
        """
        from .row_sources import RelationRowSource

        return RelationRowSource(cls, cls.shape)


def is_concrete_table(cls: type[Any]) -> bool:
    spec = vars(cls).get("_kg_declaration_spec")
    return spec is not None and spec.kind == "table" and spec.final


def is_table_group(cls: type[Any]) -> bool:
    spec = vars(cls).get("_kg_declaration_spec")
    return spec is not None and spec.kind == "table_group" and spec.final


class TableGroup:
    """A final named catalog of concrete tables and nested table groups.

    A group is not a shape and not a row source. ``bind_source`` binds a group
    when its ``DataSourceConfig`` carries a layout for its members.

    Example:
        ```python
        from kg_build_system import (
            Field, Table, TableGroup, TableGroupOptions, field,
        )

        class Site(Table):
            site_id: Field[str] = field()

        class Reading(Table):
            reading_id: Field[str] = field()

        class Estate(TableGroup):
            options = TableGroupOptions(name="estate")
            sites = Site
            readings = Reading
        ```
    """

    options: ClassVar[TableGroupOptions] = TableGroupOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if any(
            _final_kind(base) == "table_group" for base in cls.__mro__[1:]
        ):
            raise TypeError("a final TableGroup may not inherit from another final TableGroup")
        options = vars(cls).get("options", TableGroupOptions())
        _require_host_options(cls, "TableGroup", options, TableGroupOptions)

        declared: dict[str, type[Any]] = {}
        for base in reversed(cls.__mro__):
            for attribute, value in vars(base).items():
                if isinstance(value, type) and (
                    is_concrete_table(value) or is_table_group(value)
                ):
                    declared[attribute] = value
                elif attribute in declared:
                    del declared[attribute]

        invalid = tuple(
            member
            for member in options.members
            if not is_concrete_table(member) and not is_table_group(member)
        )
        if invalid:
            raise TypeError(
                "table groups may contain only final Table or TableGroup declarations"
            )
        entries = tuple(dict.fromkeys((*options.members, *declared.values())))
        if not entries:
            raise TypeError("table groups must declare at least one member")

        name = options.name or declaration_name(cls.__name__, suffixes=("TableGroup",))
        cls._table_group_name = name
        cls._table_group_entries = entries
        _prepare_declaration(
            cls,
            kind="table_group",
            name=name,
            description=_description(cls, options.description),
            annotations=tuple(options.annotations),
            members=entries,
        )
        cls._is_table_group = True

        from .declarations import group_tables

        group_tables(cls)


__all__ = [
    "BoundSource", "BoundTable", "BoundTableGroup", "ComputedStruct",
    "DataSourceConfig", "DeclarationSpec", "InputFormat", "Projection",
    "ProjectionMeta", "ProjectionOptions", "SourceBindingOptions", "Struct",
    "StructOptions", "StructOptionsTemplate", "StructTemplate", "Table",
    "TableGroup", "TableGroupOptions", "TableOptions", "is_concrete_table",
    "is_table_group", "projection_base", "projection_row_source",
]
