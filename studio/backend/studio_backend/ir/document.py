"""The Studio project IR document: the source of truth for a KG project.

Key naming deliberately mirrors ``kg_build_system``'s blueprint JSON (``name``,
``logical_type``, ``fields``, ``properties``, ``source``/``target``,
``annotations``) so the document, the generated code, and the compiled blueprint
all speak one vocabulary.

Two subsections are framework IR verbatim, validated through the framework's own
codecs: ``logical_type`` values and ``Expression`` trees. ``logical_type`` on an
expression is derived by the backend and never trusted from a client; struct
references inside field types are repaired by :mod:`studio_backend.ir.normalize`.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Annotated, Any, ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION: Final = 1
DOCUMENT_FILENAME: Final = "project.ir.json"

RefKind = Literal[
    "table", "struct", "projection", "component", "binding", "source", "module",
    "annotation_type",
]
UnitName = Literal["bool", "int", "float", "str", "date", "time", "timestamp", "uuid"]


class _Model(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    def updated(self, **changes: Any) -> Any:
        """A revalidated copy with the given fields replaced.

        Every model is frozen, so edits are expressed as copies. Validation runs,
        which is what keeps a patched nested item from carrying an inconsistent
        shape into the document.
        """
        merged = {**self.model_dump(mode="json"), **deepcopy(changes)}
        return type(self).model_validate(merged)


# --------------------------------------------------------------------------- types


class UnitType(_Model):
    kind: Literal["unit"] = "unit"
    name: UnitName


class ArrayType(_Model):
    kind: Literal["array"] = "array"
    item: "LogicalType"


class StructType(_Model):
    """A reference to a struct declaration, addressed by its generated location."""

    kind: Literal["struct"] = "struct"
    module: str
    qualname: str


class NullableType(_Model):
    kind: Literal["nullable"] = "nullable"
    value: "NonNullableLogicalType"


NonNullableLogicalType = Annotated[UnitType | ArrayType | StructType, Field(discriminator="kind")]
LogicalType = Annotated[
    UnitType | ArrayType | StructType | NullableType, Field(discriminator="kind")
]


def unit(name: UnitName, *, nullable: bool = False) -> LogicalType:
    inner: NonNullableLogicalType = UnitType(name=name)
    return NullableType(value=inner) if nullable else inner


def array(item: LogicalType, *, nullable: bool = False) -> LogicalType:
    inner: NonNullableLogicalType = ArrayType(item=item)
    return NullableType(value=inner) if nullable else inner


def nullable(value: NonNullableLogicalType) -> NullableType:
    return NullableType(value=value)


def unwrap_nullable(value: LogicalType) -> NonNullableLogicalType:
    return value.value if isinstance(value, NullableType) else value


def is_nullable(value: LogicalType) -> bool:
    return isinstance(value, NullableType)


# --------------------------------------------------------------------- annotations


class Annotation(_Model):
    """One annotation instance attached to a declaration.

    ``annotation_type`` names an ``AnnotationType`` declared by this document,
    which the generator emits into ``<package>.annotations``. Exactly one of
    ``annotation_type`` and ``import_module`` is set; the latter targets a
    framework annotation class such as ``NodeLabel``.
    """

    annotation_type: str | None = None
    import_module: str | None = None
    class_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _one_owner(self) -> Annotation:
        custom = self.annotation_type is not None
        external = self.import_module is not None and self.class_name is not None
        if custom == external:
            raise ValueError(
                "an annotation names either an annotation_type or an imported class"
            )
        return self


class AnnotationField(_Model):
    name: str
    logical_type: LogicalType
    description: str | None = None


class AnnotationType(_Model):
    """A project-owned ``Annotation`` subclass generated into ``<pkg>/annotations.py``."""

    id: str
    declaration_name: str
    namespace: str
    annotation_id: str
    description: str | None = None
    fields: tuple[AnnotationField, ...] = ()


# ----------------------------------------------------------------------- expressions


class LiteralExpression(_Model):
    kind: Literal["literal"] = "literal"
    value: Any
    logical_type: LogicalType


class FieldExpression(_Model):
    kind: Literal["field"] = "field"
    #: A table, projection or group-qualified table name.
    source: str
    path: tuple[str, ...]
    logical_type: LogicalType


class OperationExpression(_Model):
    kind: Literal["operation"] = "operation"
    operator: str
    arguments: tuple["Expression", ...] = ()
    parameters: dict[str, Any] = Field(default_factory=dict)
    logical_type: LogicalType


Expression = Annotated[
    LiteralExpression | FieldExpression | OperationExpression, Field(discriminator="kind")
]


# --------------------------------------------------------------------------- table


class DataField(_Model):
    """One table or struct member: the unified ``Field[T]`` descriptor."""

    name: str
    logical_type: LogicalType
    description: str | None = None
    external_name: str | None = None
    #: How far a non-nullability is trusted; see SOURCE_SCHEMA_TRUST_AND_NULLABILITY_SPEC.
    nullability: Literal["declared", "enforced", "defaulted"] = "defaulted"
    #: The physical schema path the member was inferred from, for provenance lines.
    schema_path: str = ""
    annotations: tuple[Annotation, ...] = ()


class TableGroupMember(_Model):
    python_name: str
    #: A table id for a member, or a group id for a nested group.
    ref: str


class Struct(_Model):
    id: str
    declaration_name: str
    name: str
    description: str | None = None
    fields: tuple[DataField, ...] = ()
    annotations: tuple[Annotation, ...] = ()


class Table(_Model):
    id: str
    declaration_name: str
    name: str
    description: str | None = None
    fields: tuple[DataField, ...] = ()
    #: Non-empty for a ``TableGroup``: the nested catalogue this group owns.
    members: tuple[TableGroupMember, ...] = ()
    annotations: tuple[Annotation, ...] = ()
    #: The parent group id when this table is a member of a group.
    group: str | None = None

    @property
    def is_group(self) -> bool:
        return bool(self.members)


class ProjectionField(_Model):
    name: str
    expression: Expression
    description: str | None = None


class Projection(_Model):
    id: str
    declaration_name: str
    name: str
    description: str | None = None
    fields: tuple[ProjectionField, ...] = ()
    annotations: tuple[Annotation, ...] = ()


# ------------------------------------------------------------------------ topology


class Property(_Model):
    """One ``PropertySlot[T]`` declaration."""

    name: str
    logical_type: LogicalType
    description: str | None = None
    #: ``property(default=None)``: a binding may leave this slot unfilled.
    optional: bool = False
    annotations: tuple[Annotation, ...] = ()


ComponentTier = Literal["template", "category", "concrete"]
ComponentKind = Literal["node", "edge"]


class Component(_Model):
    """A graph component across all three topology tiers.

    ``template`` never reaches the blueprint and contributes slots and annotations;
    ``category`` is a graph-visible abstract parent; ``concrete`` is bindable.
    ``parent`` is the single category parent and ``mixins`` the templates mixed in.
    ``source``/``target`` name the declared endpoints of an edge and may name a
    category, in which case every binding of that edge supplies an endpoint token.
    """

    id: str
    kind: ComponentKind
    tier: ComponentTier
    declaration_name: str
    name: str
    description: str | None = None
    #: Sugar for the target-neutral ``NodeLabel``/``EdgeLabel`` annotation.
    label: str | None = None
    parent: str | None = None
    mixins: tuple[str, ...] = ()
    source: str | None = None
    target: str | None = None
    properties: tuple[Property, ...] = ()
    annotations: tuple[Annotation, ...] = ()

    @property
    def is_abstract(self) -> bool:
        return self.tier == "category"

    @model_validator(mode="after")
    def _tier_shape(self) -> Component:
        if self.kind == "edge" and self.tier != "template" and (
            self.source is None or self.target is None
        ):
            raise ValueError(f"edge component {self.id!r} must declare both endpoints")
        if self.kind == "node" and (self.source is not None or self.target is not None):
            raise ValueError(f"node component {self.id!r} has no endpoints")
        if self.tier == "concrete" and self.parent is None:
            raise ValueError(
                f"concrete component {self.id!r} requires a category parent (use 'unnamed')"
            )
        return self


# ------------------------------------------------------------------------- bindings


class PropertyBinding(_Model):
    name: str
    expression: Expression


class Binding(_Model):
    """A ``node_binding``/``edge_binding`` call.

    ``source``/``target`` are endpoint tokens, required exactly when the component
    declares that side as a category.
    """

    id: str
    kind: ComponentKind
    component: str
    debug_name: str | None = None
    build_key: Expression
    source_build_key: Expression | None = None
    target_build_key: Expression | None = None
    source: str | None = None
    target: str | None = None
    properties: tuple[PropertyBinding, ...] = ()
    annotations: tuple[Annotation, ...] = ()

    @model_validator(mode="after")
    def _kind_shape(self) -> Binding:
        if self.kind == "edge" and (
            self.source_build_key is None or self.target_build_key is None
        ):
            raise ValueError(
                f"edge binding {self.id!r} needs source_build_key and target_build_key"
            )
        if self.kind == "node" and (self.source_build_key or self.target_build_key):
            raise ValueError(f"node binding {self.id!r} has no endpoint keys")
        return self


# --------------------------------------------------------------------------- source


class Source(_Model):
    """A ``bind_source``: the physical location behind a table or table group."""

    id: str
    table: str
    #: Relative to the project root; the generator renders it against ``__file__``.
    location: str
    format: Literal["csv", "json", "parquet"]
    #: Group sources template ``{group_path}`` and ``{table_name}``.
    layout: str | None = None
    version: str | None = None
    credential_reference: str | None = None
    annotations: tuple[Annotation, ...] = ()


class Module(_Model):
    """A configured workflow module, resolved through the backend module catalogue."""

    id: str
    configuration: dict[str, Any] | None = None
    enabled: bool = True


# ---------------------------------------------------------------------------- views


class Point(_Model):
    x: float = 0.0
    y: float = 0.0


class Views(_Model):
    #: Canvas positions keyed by IR ref. The plan view is always auto-laid-out.
    topology: dict[str, Point] = Field(default_factory=dict)


# -------------------------------------------------------------------------- project


class Project(_Model):
    name: str = "project"
    package: str = "kg_project"
    description: str | None = None
    #: Data files live here and are inputs the studio never owns.
    data_directory: str = "data"


class ProjectDocument(_Model):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = SCHEMA_VERSION
    #: Backend-owned; incremented on every accepted patch.
    revision: int = 0
    project: Project = Project()

    annotation_types: tuple[AnnotationType, ...] = ()
    structs: tuple[Struct, ...] = ()
    tables: tuple[Table, ...] = ()
    projections: tuple[Projection, ...] = ()
    components: tuple[Component, ...] = ()
    bindings: tuple[Binding, ...] = ()
    sources: tuple[Source, ...] = ()
    modules: tuple[Module, ...] = ()
    views: Views = Views()

    # -- lookup helpers ------------------------------------------------------

    @property
    def tables_by_id(self) -> dict[str, Table]:
        return {item.id: item for item in self.tables}

    @property
    def structs_by_id(self) -> dict[str, Struct]:
        return {item.id: item for item in self.structs}

    @property
    def components_by_id(self) -> dict[str, Component]:
        return {item.id: item for item in self.components}

    @property
    def projections_by_id(self) -> dict[str, Projection]:
        return {item.id: item for item in self.projections}

    @property
    def bindings_by_id(self) -> dict[str, Binding]:
        return {item.id: item for item in self.bindings}

    @property
    def sources_by_id(self) -> dict[str, Source]:
        return {item.id: item for item in self.sources}

    @property
    def annotation_types_by_id(self) -> dict[str, AnnotationType]:
        return {item.id: item for item in self.annotation_types}

    def sources_for_table(self, table_id: str) -> tuple[Source, ...]:
        return tuple(item for item in self.sources if item.table == table_id)

    def bindings_for_component(self, component_id: str) -> tuple[Binding, ...]:
        return tuple(item for item in self.bindings if item.component == component_id)

    def replaced(self, section: str, item: Any) -> ProjectDocument:
        """Return a copy with one item replaced by id, or appended when new."""
        items = list(getattr(self, section))
        for index, existing in enumerate(items):
            if existing.id == item.id:
                items[index] = item
                break
        else:
            items.append(item)
        return self.updated(**{section: items})

    def removed(self, section: str, item_id: str) -> ProjectDocument:
        items = [item for item in getattr(self, section) if item.id != item_id]
        return self.updated(**{section: items})


ArrayType.model_rebuild()
NullableType.model_rebuild()
OperationExpression.model_rebuild()
DataField.model_rebuild()
Struct.model_rebuild()
Table.model_rebuild()
ProjectionField.model_rebuild()
Projection.model_rebuild()
Property.model_rebuild()
Component.model_rebuild()
Binding.model_rebuild()
ProjectDocument.model_rebuild()
