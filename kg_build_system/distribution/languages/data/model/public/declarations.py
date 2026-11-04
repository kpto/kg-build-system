"""Author-facing logical data declarations and their options.

A graph author subclasses ``Table``, ``Struct``, ``ComputedStruct``,
``Projection`` or ``TableGroup``. While the class is created, its fields and
options are transcribed into a frozen ``DeclarationSpec`` stored on the class; the
``data`` language reads that spec, never a private authoring attribute.

Example:
    ```python
    from kg_build_system import (
        Asset, AssetOptions, Field, Projection, Table, TableGroup,
        TableGroupOptions, computed_field, field,
    )

    class Estate(Asset):
        options = AssetOptions(...)

    class Site(Table[Estate]):
        site_id: Field[str] = field()
        name: Field[str] = field()

    class SiteLabels(Projection(Site.row_source())):
        label = computed_field(Site.name)

    class EstateCatalog(TableGroup):
        options = TableGroupOptions(name="estate")
        sites = Site
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, Self

from kg_build_system.distribution.languages.annotations.service.internal import annotation_tuple
from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)
from kg_build_system.distribution.languages.asset.model.public import Asset
from kg_build_system.distribution.languages.expressions.model.public import (
    BoolExpression,
)
from kg_build_system.kernel.model.public.types import Shape, Struct as StructDeclaration
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



def is_concrete_table(cls: type[Any]) -> bool:
    """Return whether a class is a final table."""
    spec = vars(cls).get("_kg_declaration_spec")
    return spec is not None and spec.kind == "table" and spec.final


def is_table_group(cls: type[Any]) -> bool:
    """Return whether a class is a final table group."""
    spec = vars(cls).get("_kg_declaration_spec")
    return spec is not None and spec.kind == "table_group" and spec.final


class Table[AssetT: Asset](StructDeclaration, RowSource["Table[AssetT]"]):
    """A final logical table declaration read from one logical asset.

    The asset is part of the declaration: ``class Site(Table[Estate])`` states
    which logical unit of source data backs the relation. A concrete table
    without an asset parameter is refused.
    """

    options: ClassVar[TableOptions] = TableOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import prepare_table_declaration

        prepare_table_declaration(cls)

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
        from ...service._private.declarations import _derive

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
        from ...service.public.rows import projection_base

        return projection_base(cls.row_source())

    @classmethod
    def row_source(cls) -> RelationRowSource[Self]:
        """Return the relation row source for this table.

        Example:
            ```python
            sites = SiteTable.row_source()
            ```
        """
        return RelationRowSource(cls, cls)


class StructTemplate:
    """The template tier for ``Table``, ``Struct`` and ``ComputedStruct`` hosts.

    A template shares field slots and annotation flow with its hosts and never
    enters the blueprint DTO. It carries annotations only, no name or description.
    """

    options: ClassVar[Any] = StructOptionsTemplate()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        from ...service._private.declarations import require_struct_template_host

        require_struct_template_host(cls)
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import (
            prepare_struct_template_annotations,
        )

        prepare_struct_template_annotations(cls)


class Struct(StructDeclaration):
    """A nested-record declaration composed from source-backed fields."""

    options: ClassVar[StructOptions] = StructOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import prepare_struct_declaration

        prepare_struct_declaration(cls)


class ComputedStruct(StructDeclaration):
    """A value record whose members are expression-backed type witnesses."""

    options: ClassVar[StructOptions] = StructOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import (
            prepare_computed_struct_declaration,
        )

        prepare_computed_struct_declaration(cls)


class ProjectionMeta(type):
    """Make ``Projection(source)`` return a base pinned to a row source."""

    def __call__(cls, source: Any | None = None) -> type["Projection"]:
        from ...service._private.declarations import prepare_projection_type

        return prepare_projection_type(source)


class Projection(Shape, RowSource["Projection"], metaclass=ProjectionMeta):
    """A final named logical relation composed from typed expressions."""

    options: ClassVar[ProjectionOptions] = ProjectionOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import (
            prepare_projection_declaration,
        )

        prepare_projection_declaration(cls)

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
        from ...service._private.declarations import _derive

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
        from ...service.public.rows import projection_base

        return projection_base(cls.row_source())

    @classmethod
    def row_source(cls) -> RelationRowSource[Any]:
        """Return the relation row source for this projection.

        Example:
            ```python
            rows = SiteProjection.row_source()
            ```
        """
        return RelationRowSource(cls, cls.shape)


class TableGroup:
    """A final named catalog of concrete tables and nested table groups.

    A group is not a shape and not a row source. Each member table names its own
    asset; a group catalog does not bind a physical source.

    Example:
        ```python
        from kg_build_system import (
            Asset, AssetOptions, Field, Table, TableGroup, TableGroupOptions,
            field,
        )

        class Estate(Asset):
            options = AssetOptions(...)

        class Site(Table[Estate]):
            site_id: Field[str] = field()

        class Reading(Table[Estate]):
            reading_id: Field[str] = field()

        class EstateCatalog(TableGroup):
            options = TableGroupOptions(name="estate")
            sites = Site
            readings = Reading
        ```
    """

    options: ClassVar[TableGroupOptions] = TableGroupOptions()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import (
            prepare_table_group_declaration,
        )

        prepare_table_group_declaration(cls)


__all__ = [
    "ComputedStruct", "Projection", "ProjectionMeta", "ProjectionOptions",
    "Struct", "StructOptions", "StructOptionsTemplate", "StructTemplate",
    "Table", "TableGroup", "TableGroupOptions", "TableOptions",
    "is_concrete_table", "is_table_group",
]
