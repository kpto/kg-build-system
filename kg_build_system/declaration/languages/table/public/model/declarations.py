"""Author-facing logical data declarations and their options.

A graph author subclasses ``Table``, ``Struct``, ``ComputedStruct``,
``Projection`` or ``TableGroup``. While the class is created, its fields and
options are transcribed into a frozen ``DeclarationSpec`` stored on the class; the
``data`` language reads that spec, never a private authoring attribute.

Example:
    ```python
    from kg_build_system import (
        Field, Projection, Table, TableGroup, TableGroupOptions, field,
        computed_field,
    )

    class Site(Table):
        site_id: Field[str] = field()
        name: Field[str] = field()

    class SiteLabels(Projection(Site.row_source())):
        label = computed_field(Site.name)

    class Estate(TableGroup):
        options = TableGroupOptions(name="estate")
        sites = Site
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, Self

from ..._private.naming import declaration_name
from kg_build_system.declaration.foundations.annotations.internal import Annotation, annotation_tuple
from kg_build_system.declaration.foundations.expressions.public import BoolExpression
from kg_build_system.kernel.internal.types import Shape, Struct as StructDeclaration
from ..._private.declarations import (
    _description,
    _final_kind,
    _prepare_declaration,
    _record_template_annotations,
    _require_host_options,
    _template_annotations,
    is_concrete_table,
    is_table_group,
    projection_base,
    projection_row_source,
    shape_view,
)
from .row_sources import DerivedRowSource, RelationRowSource, RowSource


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
        cls, predicate: Callable[[Self], BoolExpression],
    ) -> DerivedRowSource[Self]:
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
        from ..._private.declarations import _derive

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
    def row_source(cls) -> RelationRowSource[Self]:
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
    enters the blueprint DTO. It carries annotations only, no name or description.
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
        from ..._private.declarations import pinned_base
        from ..._private.plans import as_row_source

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
        cls, predicate: Callable[[Self], BoolExpression],
    ) -> DerivedRowSource[Self]:
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
        from ..._private.declarations import _derive

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
    def row_source(cls) -> RelationRowSource[Any]:
        """Return the relation row source for this projection.

        Example:
            ```python
            rows = SiteProjection.row_source()
            ```
        """
        from .row_sources import RelationRowSource

        return RelationRowSource(cls, cls.shape)


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

        from ..._private.sources import group_tables

        group_tables(cls)


__all__ = [
    "ComputedStruct", "Projection", "ProjectionMeta", "ProjectionOptions",
    "Struct", "StructOptions", "StructOptionsTemplate", "StructTemplate",
    "Table", "TableGroup", "TableGroupOptions", "TableOptions",
    "is_concrete_table", "is_table_group", "projection_base",
    "projection_row_source",
]
