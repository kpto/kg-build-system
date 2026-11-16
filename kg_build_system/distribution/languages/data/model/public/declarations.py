"""Author-facing logical data declarations and their options.

A graph author subclasses ``SourceRelation``, ``Struct``, ``ComputedStruct``,
``DerivedRelation`` or ``SourceRelationGroup``. While the class is created, its fields and
options are transcribed into a frozen ``DeclarationSpec`` stored on the class; the
``data`` language reads that spec, never a private authoring attribute.

Example:
    ```python
    from kg_build_system import (
        Asset, AssetOptions, Field, DerivedRelation, SourceRelation, SourceRelationGroup,
        SourceRelationGroupOptions, computed_field, field,
    )

    class Estate(Asset):
        options = AssetOptions(...)

    class Site(SourceRelation[Estate]):
        site_id: Field[str] = field()
        name: Field[str] = field()

    class SiteLabels(DerivedRelation(Site.row_source())):
        label = computed_field(Site.name)

    class EstateCatalog(SourceRelationGroup):
        options = SourceRelationGroupOptions(name="estate")
        sites = Site
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Generic, Self, TypeVar, cast

from kg_build_system.distribution.languages.annotations.service.internal import annotation_tuple
from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)
from kg_build_system.distribution.languages.meaning.model.public import (
    Omitted,
    is_omitted,
    require_declaration_meaning,
)
from kg_build_system.distribution.languages.asset.model.public import Asset
from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.kernel.model.public.types import Shape, Struct as StructDeclaration
from .contract import Contract, Definition
from .row_sources import (
    DerivedRowSource, RelationRowSource, RowSource, RowSourceProvider,
    StageRowSource,
)

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.meaning.model.public import (
        Meaning,
    )



@dataclass(frozen=True, slots=True)
class SourceRelationOptions:
    name: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()
    contract: Contract | type[Omitted] = field(kw_only=True)

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("source relation names must be non-empty")
        if not is_omitted(self.contract) and not isinstance(
            self.contract, Contract,
        ):
            raise TypeError(
                "a declared contract requires a Definition and a Meaning, or "
                "contract=Omitted"
            )
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
    annotations: tuple[Annotation, ...] | list[Annotation] = ()
    meaning: Meaning | type[Omitted] = field(kw_only=True)

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("struct names must be non-empty")
        require_declaration_meaning(self.meaning)
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True, slots=True)
class DerivedRelationOptions:
    contract: Contract
    name: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("derived relation names must be non-empty")
        if not isinstance(self.contract, Contract):
            raise TypeError(
                "a derived relation requires a Contract with a Definition "
                "and a Meaning"
            )
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True, slots=True)
class StageOptions:
    definition: Definition
    name: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("stage names must be non-empty")
        if not isinstance(self.definition, Definition):
            raise TypeError("a stage requires a Definition")
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))


@dataclass(frozen=True, slots=True)
class SourceRelationGroupOptions:
    members: tuple[
        type[SourceRelation[Asset]] | type[SourceRelationGroup], ...
    ] = ()
    name: str | None = None
    annotations: tuple[Annotation, ...] | list[Annotation] = ()

    def __post_init__(self) -> None:
        if self.name is not None and not self.name:
            raise ValueError("source relation group names must be non-empty")
        object.__setattr__(self, "annotations", annotation_tuple(self.annotations))



def is_concrete_source_relation(cls: type[object]) -> bool:
    """Return whether a class is a final source relation."""
    spec = vars(cls).get("_kg_declaration_spec")
    return spec is not None and spec.kind == "source_relation" and spec.final


def is_source_relation_group(cls: type[object]) -> bool:
    """Return whether a class is a final source relation group."""
    spec = vars(cls).get("_kg_declaration_spec")
    return spec is not None and spec.kind == "source_relation_group" and spec.final


AssetT_co = TypeVar("AssetT_co", bound=Asset, covariant=True)


class SourceRelation(
    RowSourceProvider,
    Shape,
    RowSource["SourceRelation[AssetT_co]"],
    Generic[AssetT_co],
):
    """A final source relation declaration read from one logical asset.

    The asset is part of the declaration: ``class Site(SourceRelation[Estate])`` states
    which logical unit of source data backs the relation. A concrete source
    relation without an asset parameter is refused.
    """

    options: ClassVar[SourceRelationOptions] = SourceRelationOptions(
        contract=Omitted,
    )

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import prepare_source_relation_declaration

        prepare_source_relation_declaration(cls)

    @classmethod
    def where(
        cls, predicate: Callable[[Self], Selection[bool]],
    ) -> DerivedRowSource[Self]:
        """Keep the rows of this source relation that satisfy ``predicate``.

        The predicate receives a symbolic instance of the source relation and must return
        a ``Selection[bool]``.

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
    def row_source(cls) -> RelationRowSource[Self]:
        """Return the relation row source for this source relation.

        Example:
            ```python
            sites = SiteTable.row_source()
            ```
        """
        return RelationRowSource(cls, cls)


class StructTemplate:
    """The template tier for ``SourceRelation``, ``Struct`` and ``ComputedStruct`` hosts.

    A template shares field slots and annotation flow with its hosts and never
    enters the blueprint DTO. It carries annotations only, no name.
    """

    options: ClassVar[StructOptions | StructOptionsTemplate] = StructOptionsTemplate()

    def __init_subclass__(cls, **kwargs: object) -> None:
        from ...service._private.declarations import require_struct_template_host

        require_struct_template_host(cls)
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import (
            prepare_struct_template_annotations,
        )

        prepare_struct_template_annotations(cls)


class Struct(StructDeclaration):
    """A nested-record declaration composed from source-backed fields."""

    options: ClassVar[StructOptions] = StructOptions(meaning=Omitted)

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import prepare_struct_declaration

        prepare_struct_declaration(cls)


class ComputedStruct(StructDeclaration):
    """A value record whose members are expression-backed type witnesses."""

    options: ClassVar[StructOptions] = StructOptions(meaning=Omitted)

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import (
            prepare_computed_struct_declaration,
        )

        prepare_computed_struct_declaration(cls)


class DerivedRelationMeta(type):
    """Make ``DerivedRelation(source)`` return a base pinned to a row source."""

    def __call__[S: Shape](
        cls, source: RowSource[S] | None = None,
    ) -> type["DerivedRelation"]:
        from ...service._private.declarations import prepare_derived_relation_type

        return prepare_derived_relation_type(source)


class DerivedRelation(RowSourceProvider, Shape, RowSource["DerivedRelation"], metaclass=DerivedRelationMeta):
    """A final named derived relation composed from typed expressions."""

    options: ClassVar[DerivedRelationOptions | None] = None

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import (
            prepare_derived_relation_declaration,
        )

        prepare_derived_relation_declaration(cls)

    @classmethod
    def where(
        cls, predicate: Callable[[Self], Selection[bool]],
    ) -> DerivedRowSource[Self]:
        """Keep the rows of this derived relation that satisfy ``predicate``.

        The predicate receives a symbolic instance of the derived relation and must
        return a ``BoolExpression``.

        Example:
            ```python
            active = SiteProjection.where(
                lambda derived_relation: derived_relation.label.alter_rows().drop_null()
                .expression.equals("Depot")
            )
            ```
        """
        from ...service._private.declarations import _derive

        return _derive(cls, predicate)


    @classmethod
    def row_source(cls) -> RelationRowSource[Self]:
        """Return the relation row source for this derived relation.

        Example:
            ```python
            rows = SiteProjection.row_source()
            ```
        """
        # The generated view carries the same field selections as the
        # declaration; the cast states the read contract, not identity.
        return RelationRowSource(cls, cast("type[Self]", cls.shape))


class StageMeta(type):
    """Make ``Stage(source)`` return a base pinned to a row source."""

    def __call__[S: Shape](
        cls, source: RowSource[S] | None = None,
    ) -> type["Stage"]:
        from ...service._private.declarations import prepare_stage_type

        return prepare_stage_type(source)


class Stage(RowSourceProvider, Shape, metaclass=StageMeta):
    """A private computed relation pinned to one row source.

    A stage carries a ``Definition`` and no ``Meaning``. It is not a consumer
    relation: ``Stage.row_source()`` returns a ``StageRowSource``, which a
    binding refuses.

    Example:
        ```python
        from kg_build_system import (
            Definition, Stage, StageOptions, computed_field,
        )

        class SiteStage(Stage(Site.row_source())):
            options = StageOptions(
                definition=Definition(
                    grain="One row per site.", identity=("site_id",),
                ),
            )
            site_id = computed_field(Site.site_id)
        ```
    """

    options: ClassVar[StageOptions | None] = None
    shape: type[Shape]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import (
            prepare_stage_declaration,
        )

        prepare_stage_declaration(cls)

    @classmethod
    def row_source(cls) -> StageRowSource[Self]:
        """Return the private row source of this stage.

        Example:
            ```python
            rows = SiteStage.row_source()
            ```
        """
        # The generated view carries the same field selections as the
        # declaration; the cast states the read contract, not identity.
        return StageRowSource(cls, cast("type[Self]", cls.shape))


class SourceRelationGroup:
    """A final named catalog of source relations and nested source relation groups.

    A group is not a shape and not a row source. Each member source relation names
    its own asset; a group catalog does not bind a physical source.

    Example:
        ```python
        from kg_build_system import (
            Asset, AssetOptions, Field, SourceRelation, SourceRelationGroup, SourceRelationGroupOptions,
            field,
        )

        class Estate(Asset):
            options = AssetOptions(...)

        class Site(SourceRelation[Estate]):
            site_id: Field[str] = field()

        class Reading(SourceRelation[Estate]):
            reading_id: Field[str] = field()

        class EstateCatalog(SourceRelationGroup):
            options = SourceRelationGroupOptions(name="estate")
            sites = Site
            readings = Reading
        ```
    """

    options: ClassVar[SourceRelationGroupOptions] = SourceRelationGroupOptions()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        from ...service._private.declarations import (
            prepare_source_relation_group_declaration,
        )

        prepare_source_relation_group_declaration(cls)


__all__ = [
    "ComputedStruct", "DerivedRelation", "DerivedRelationMeta", "DerivedRelationOptions",
    "Struct", "StructOptions", "StructOptionsTemplate", "StructTemplate",
    "SourceRelation", "SourceRelationGroup", "SourceRelationGroupOptions", "SourceRelationOptions",
    "Stage", "StageMeta", "StageOptions",
    "is_concrete_source_relation", "is_source_relation_group",
]
