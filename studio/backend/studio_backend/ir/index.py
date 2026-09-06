"""The derived authoring index: everything the editor may offer, computed from the document.

``GET /api/index`` serves this so the UI never decides for itself what is selectable or
which properties a component really has — those are the framework's answers, and
computing them server-side is what keeps the composer from offering something the
generator cannot emit (``studio/docs/API.md`` §"Authoring index", ``studio/DESIGN.md``
§5).

Ordering is part of the contract, not an accident: the payload is cached, diffed and
rendered as a list, so every collection follows the document's own declaration order
(``selectable`` tables then projections, each with its fields depth-first;
``components`` in declaration order; ``operators`` in catalogue order). No set or
locally-built dict is ever iterated for output, so one document always produces
byte-identical JSON.

Entries the framework would reject are left out, and ``build_index`` names the rule for
each. Beyond those the index is deliberately tolerant: a document is edited
incrementally, so an output that cannot be typed yet is dropped rather than taking the
index — and with it the whole editor — down.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, computed_field

from .document import (
    Binding,
    Component,
    LogicalType,
    NonNullableLogicalType,
    NullableType,
    ProjectDocument,
    Projection,
    StructType,
    Table,
    is_nullable,
    unwrap_nullable,
)
from .infer import (
    OPERATION_CATALOGUE,
    InferenceError,
    catalog_path,
    infer_expression,
    is_group_only,
    resolve_struct,
)
from .refs import build as ref

__all__ = [
    "AuthoringIndex",
    "ComponentEntry",
    "EndpointIsCategory",
    "OperatorEntry",
    "ResolvedProperty",
    "Selectable",
    "SelectablePath",
    "binding_targets_without_bindings",
    "build_index",
    "declared_endpoints",
    "endpoint_is_category",
    "lineage",
    "operator_entries",
    "property_slot",
    "resolved_properties",
    "unbound_required_slots",
]


# --------------------------------------------------------------------- the payload
#
# Pydantic, like the document itself: the API layer serves
# ``build_index(document).model_dump(mode="json")``, so these models *are* the response;
# declared fields carry the documented keys in the documented order, and the computed
# ``ref``/``address`` follow them. Every entry also carries the
# ``ref`` and ``declaration_name`` the diagnostics mapper needs — ``DESIGN.md`` §3
# resolves a framework error that names ``SiteNode.city`` to an IR reference "through
# the derived index", which is only possible if the index publishes both spellings.


class _Entry(BaseModel):
    """An index entry: immutable, and exact about the JSON it produces."""

    model_config: ConfigDict = ConfigDict(extra="forbid", frozen=True)


class SelectablePath(_Entry):
    """One field path an expression stack may start from."""

    path: tuple[str, ...]
    logical_type: LogicalType
    nullable: bool
    description: str | None = None


class Selectable(_Entry):
    """A source a stack may read: one concrete table, or one projection.

    ``name`` is what a field reference stores in ``source`` and is always the bare
    logical name, because that is what the framework compiles a group member to
    (``Table._table_name`` ignores the group). ``group`` and ``address`` carry the
    studio's own ``<group>.<member>`` spelling alongside it, so a picker can show the
    qualified name without the expression ever having to store one.
    """

    kind: Literal["table", "projection"]
    id: str
    name: str
    declaration_name: str
    #: The dotted catalogue path of the owning groups, outermost first
    #: (``readings.mechanical``), or ``None`` for a table outside any group.
    group: str | None = None
    description: str | None = None
    paths: tuple[SelectablePath, ...] = ()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ref(self) -> str:
        return ref(self.kind, self.id)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def address(self) -> str:
        """The studio's address for this source: ``<group>.<member>``, else the name."""
        return self.name if self.group is None else f"{self.group}.{self.name}"


class ResolvedProperty(_Entry):
    """One property slot of a component, after inheritance."""

    name: str
    logical_type: LogicalType
    optional: bool
    #: The component — template, category or this one — whose declaration this slot
    #: came from, so the UI can say where the promise a binding must keep was made.
    declared_by: str
    description: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ref(self) -> str:
        return ref("component", self.declared_by, "property", self.name)


class EndpointIsCategory(_Entry):
    """Whether each declared edge endpoint names a category.

    ``binding/factories.py`` requires ``source_node=``/``target_node=`` on an
    ``edge_binding`` exactly when the declared side is abstract, so this pair decides
    whether the binding form demands an endpoint token. A node component has no
    endpoints and answers ``False`` on both.
    """

    source: bool = False
    target: bool = False


class ComponentEntry(_Entry):
    """A component with its effective slots and its edge endpoint shapes."""

    id: str
    kind: Literal["node", "edge"]
    tier: Literal["template", "category", "concrete"]
    declaration_name: str
    name: str
    description: str | None = None
    resolved_properties: tuple[ResolvedProperty, ...] = ()
    endpoint_is_category: EndpointIsCategory = Field(default_factory=EndpointIsCategory)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ref(self) -> str:
        return ref("component", self.id)


class OperatorEntry(_Entry):
    """One catalogue entry in the API document's operator-array form.

    The catalogue's ``produces`` object is flattened so the frontend switches on the
    single documented string, with the rule name and its sentence kept beside it for
    explaining where a result type came from. ``render`` is included because the array
    is also the block spelling: ``concat`` renders as two different authoring methods,
    and the frontend cannot recover that from the operator name.
    """

    operator: str
    label: str
    requires: dict[str, Any] = Field(default_factory=dict)
    produces: str
    produces_type_rule: str
    produces_description: str
    arity: int
    group: str
    docs: str
    render: str


class AuthoringIndex(_Entry):
    """The whole ``GET /api/index`` payload."""

    selectable: tuple[Selectable, ...] = ()
    components: tuple[ComponentEntry, ...] = ()
    operators: tuple[OperatorEntry, ...] = ()


# --------------------------------------------------------------- lineage and slots


class _LineageError(ValueError):
    """A component lineage Python could not linearise (a cycle, or an inconsistent one)."""


def _bases(document: ProjectDocument, component: Component) -> tuple[Component, ...]:
    """The component's bases in authoring order: mixins, then the category parent.

    The generator emits ``class SiteNode(ProvenancedNodeTemplate,
    DocumentedAbstractNode, Node)`` — templates first, then the parent, exactly as
    ``reference_project/topology/site/__init__.py`` writes it — and the framework
    composes inherited slots off that base list, so the studio's order has to match it
    or a slot's declaring component disagrees with the generated class. Unknown ids are
    skipped: they are a document fault the validator reports.
    """
    bases: list[Component] = []
    for mixin_id in component.mixins:
        mixin = document.components_by_id.get(mixin_id)
        if mixin is not None:
            bases.append(mixin)
    if component.parent is not None:
        parent = document.components_by_id.get(component.parent)
        if parent is not None:
            bases.append(parent)
    return tuple(bases)


def _merge(sequences: list[list[str]]) -> tuple[str, ...]:
    """The C3 merge of already-linearised base lineages."""
    result: list[str] = []
    pending = [item for item in sequences if item]
    while pending:
        for sequence in pending:
            head = sequence[0]
            if not any(head in other[1:] for other in pending):
                break
        else:
            raise _LineageError("inconsistent component lineage")
        result.append(head)
        for sequence in pending:
            while sequence and sequence[0] == head:
                sequence.pop(0)
        pending = [item for item in pending if item]
    return tuple(dict.fromkeys(result))


def lineage(document: ProjectDocument, component: Component) -> tuple[Component, ...]:
    """The component and its ancestors in C3 order, most derived first.

    ``topology/models.py`` reads inherited properties off ``cls.__mro__``
    (``properties_for``), so the studio has to linearise the same way for
    ``resolved_properties`` to name the declaring component the generated class names.
    A lineage Python itself would reject — a cycle through a mixin, or bases no
    consistent MRO can order — falls back to a depth-first walk, which keeps the index
    computable on a document that is still being edited.
    """
    memo: dict[str, tuple[str, ...]] = {}

    def linearise(target: Component, visiting: frozenset[str]) -> tuple[str, ...]:
        known = memo.get(target.id)
        if known is not None:
            return known
        if target.id in visiting:
            raise _LineageError(f"component lineage cycle at {target.id!r}")
        bases = _bases(document, target)
        if not bases:
            order = (target.id,)
        else:
            order = (
                target.id,
                *_merge([list(linearise(base, visiting | {target.id})) for base in bases]),
            )
        memo[target.id] = order
        return order

    try:
        ids = linearise(component, frozenset())
    except _LineageError:
        ids = _depth_first(document, component)
    return tuple(
        document.components_by_id[item] for item in ids if item in document.components_by_id
    )


def _depth_first(document: ProjectDocument, component: Component) -> tuple[str, ...]:
    """The fallback ordering: the component, then its bases depth-first."""
    order: list[str] = []
    seen: set[str] = set()

    def visit(target: Component) -> None:
        if target.id in seen:
            return
        seen.add(target.id)
        order.append(target.id)
        for base in _bases(document, target):
            visit(base)

    visit(component)
    return tuple(order)


def resolved_properties(
    document: ProjectDocument, component: Component
) -> tuple[ResolvedProperty, ...]:
    """The component's effective slots, in the order the generated record has them.

    ``topology/models.py`` builds them in two steps and both have to be reproduced,
    because the order is what a binding record and the generated dataclass expose:

    1. ``properties_for(cls)`` walks ``reversed(cls.__mro__)`` so the furthest ancestor
       contributes first; a slot re-declared closer to the class replaces the earlier
       declaration but keeps its position in the dict;
    2. the dataclass is composed over ``cls.__annotations__``, which starts with the
       class's *own* slots and then takes the remaining inherited ones — which is why
       the reference project's ``SiteNode`` record reads
       ``['name', 'city', 'summary', 'source_version']`` (own, then category, then
       mixin) rather than pure MRO order.
    """
    declared: dict[str, ResolvedProperty] = {}
    for owner in reversed(lineage(document, component)):
        for slot in owner.properties:
            declared[slot.name] = ResolvedProperty(
                name=slot.name,
                logical_type=slot.logical_type,
                optional=slot.optional,
                declared_by=owner.id,
                description=slot.description,
            )
    own = [slot.name for slot in component.properties]
    return tuple(
        declared[name] for name in [*own, *(name for name in declared if name not in own)]
    )


def property_slot(
    document: ProjectDocument, component_id: str, name: str
) -> ResolvedProperty | None:
    """The effective slot a component property name addresses, inherited ones included.

    This is what types a property binding: ``binding/factories.py`` checks a binding
    against the target's *effective* properties, so a slot the component only inherits
    is exactly as binding as one it declares. ``None`` means the name addresses no slot
    — the "binding must map every declared component property exactly once" mismatch
    (``compile/validation.py``).
    """
    component = document.components_by_id.get(component_id)
    if component is None:
        return None
    return next((item for item in resolved_properties(document, component) if item.name == name), None)


def declared_endpoints(document: ProjectDocument, component: Component) -> tuple[str | None, str | None]:
    """The component's endpoints, inherited from its edge parent when undeclared.

    ``topology/models.py`` (``_resolve_edge_endpoints``) lets a concrete edge inherit
    the endpoints of the abstract edge it descends from instead of restating them, so a
    binding of the child resolves its endpoint tokens against the inherited declaration.
    """
    current: Component | None = component
    seen: set[str] = set()
    while current is not None and current.id not in seen:
        if current.source is not None or current.target is not None:
            return current.source, current.target
        seen.add(current.id)
        current = (
            document.components_by_id.get(current.parent) if current.parent is not None else None
        )
    return component.source, component.target


def endpoint_is_category(document: ProjectDocument, component: Component) -> EndpointIsCategory:
    """Whether each declared endpoint names a category, inherited endpoints included.

    An endpoint naming an unknown component answers ``False``: no binding form can be
    built against it either way, and the dangling reference is the document validator's
    report, not this one.
    """
    source_id, target_id = declared_endpoints(document, component)
    sides: dict[str, bool] = {}
    for side, endpoint_id in (("source", source_id), ("target", target_id)):
        endpoint = (
            document.components_by_id.get(endpoint_id) if endpoint_id is not None else None
        )
        sides[side] = bool(endpoint is not None and endpoint.is_abstract)
    return EndpointIsCategory(**sides)


# ---------------------------------------------------------------------- selectable


FieldRow = tuple[str, LogicalType, str | None]


def _table_rows(table: Table) -> tuple[FieldRow, ...]:
    return tuple((item.name, item.logical_type, item.description) for item in table.fields)


def _projection_rows(document: ProjectDocument, projection: Projection) -> tuple[FieldRow, ...]:
    """A projection's outputs, each typed by inferring its implementation.

    ``table/projections.py`` hands out a reference to the materialised output whose
    logical type is the compiled implementation's, so the index cannot take the type
    sitting on the document's expression on trust — it has to derive it, which is also
    what makes a client-supplied type on a projection output meaningless. An output
    whose expression does not compile yet is dropped: it is not selectable, and the
    document's own problem list says why.
    """
    rows: list[FieldRow] = []
    for item in projection.fields:
        try:
            inferred = infer_expression(document, item.expression)
        except InferenceError:
            continue
        rows.append((item.name, inferred.logical_type, item.description))
    return tuple(rows)


def _selectable_paths(document: ProjectDocument, fields: Sequence[FieldRow]) -> tuple[SelectablePath, ...]:
    """Every declared path of a source, depth-first, with nullability propagated.

    Each path is emitted before its own children, so the composer can start a stack at
    a nested record and narrow from there, or at a list and offer ``expand``. Descent
    stops at a list — a field path cannot step into a list's items, the same rule
    ``infer.field_path_type`` enforces — and at a struct this document does not uniquely
    declare, for the reason in ``infer.resolve_struct``. A struct that reaches itself
    again stops there too, so a nested record cannot loop the index.
    """
    paths: list[SelectablePath] = []

    def walk(
        prefix: tuple[str, ...],
        value: LogicalType,
        description: str | None,
        ancestors: tuple[tuple[str, str], ...],
    ) -> None:
        paths.append(
            SelectablePath(
                path=prefix,
                logical_type=value,
                nullable=is_nullable(value),
                description=description,
            )
        )
        base = unwrap_nullable(value)
        if not isinstance(base, StructType):
            return
        key = (base.module, base.qualname)
        if key in ancestors:
            return
        declared = resolve_struct(document, base)
        if declared is None:
            return
        below = (*ancestors, key)
        for field in declared.fields:
            member_type = field.logical_type
            if is_nullable(value) and not is_nullable(member_type):
                member_type = NullableType(value=cast(NonNullableLogicalType, member_type))
            walk((*prefix, field.name), member_type, field.description, below)

    for name, logical_type, description in fields:
        walk((name,), logical_type, description, ())
    return tuple(paths)


def _claimed_names(document: ProjectDocument) -> frozenset[str]:
    """Logical source names claimed more than once, so no declaration can offer them."""
    counts: dict[str, int] = {}
    for item in (*document.tables, *document.projections):
        if isinstance(item, Table) and is_group_only(item):
            continue
        counts[item.name] = counts.get(item.name, 0) + 1
    return frozenset(name for name, total in counts.items() if total > 1)


# --------------------------------------------------------------------- build_index


def build_index(document: ProjectDocument) -> AuthoringIndex:
    """Compute the authoring index for one document.

    What is left out, and the framework rule that leaves it out:

    *   **a table that only owns a catalogue** — a ``TableGroup`` compiles to one
        blueprint table per member (``table/declarations.py``, ``group_tables``) and
        declares no fields of its own, so it is an address rather than a source. Its
        members are published individually.
    *   **a projection with no usable outputs** — ``table/models.py`` refuses such a
        declaration outright ("projections must declare at least one projection_field").
    *   **a name claimed twice** — ``compile/validation.py`` requires logical source
        names to be unique across tables and projections, so an ambiguous name is
        offered as neither; the collision is validation's to report.

    A group member is published under its own logical name in ``name`` — what a compiled
    field reference stores — with the group's dotted path in ``group`` and the studio's
    ``<group>.<member>`` address in ``address``, so the two spellings never have to be
    guessed apart.
    """
    claimed = _claimed_names(document)
    selectable: list[Selectable] = []
    for table in document.tables:
        if is_group_only(table) or table.name in claimed:
            continue
        selectable.append(
            Selectable(
                kind="table",
                id=table.id,
                name=table.name,
                declaration_name=table.declaration_name,
                group=_group_of(document, table),
                description=table.description,
                paths=_selectable_paths(document, _table_rows(table)),
            )
        )
    for projection in document.projections:
        if projection.name in claimed:
            continue
        rows = _projection_rows(document, projection)
        if not rows:
            continue
        selectable.append(
            Selectable(
                kind="projection",
                id=projection.id,
                name=projection.name,
                declaration_name=projection.declaration_name,
                group=None,
                description=projection.description,
                paths=_selectable_paths(document, rows),
            )
        )
    return AuthoringIndex(
        selectable=tuple(selectable),
        components=tuple(_component_entry(document, item) for item in document.components),
        operators=operator_entries(),
    )


def _group_of(document: ProjectDocument, table: Table) -> str | None:
    parts = catalog_path(document, table)
    return ".".join(parts[:-1]) if len(parts) > 1 else None


def _component_entry(document: ProjectDocument, component: Component) -> ComponentEntry:
    return ComponentEntry(
        id=component.id,
        kind=component.kind,
        tier=component.tier,
        declaration_name=component.declaration_name,
        name=component.name,
        description=component.description,
        resolved_properties=resolved_properties(document, component),
        endpoint_is_category=endpoint_is_category(document, component),
    )


def operator_entries() -> tuple[OperatorEntry, ...]:
    """``OPERATION_CATALOGUE`` rendered as the API document's operator array."""
    return tuple(
        OperatorEntry(
            operator=operator,
            label=spec["label"],
            requires=dict(spec["requires"]),
            produces=spec["produces"]["shape"],
            produces_type_rule=spec["produces"]["type_rule"],
            produces_description=spec["produces"]["description"],
            arity=spec["arity"],
            group=spec["group"],
            docs=spec["docs"],
            render=spec["render"],
        )
        for operator, spec in OPERATION_CATALOGUE.items()
    )


# ---------------------------------------------------------------- binding helpers


def binding_targets_without_bindings(document: ProjectDocument) -> tuple[Component, ...]:
    """Bindable components no binding targets yet, in document order.

    Only ``concrete`` components appear: ``binding/factories.py`` refuses an abstract
    category ("target must be a concrete node component, not X") and a template never
    reaches the blueprint at all. These are the entries a binding picker still owes.
    """
    bound = {binding.component for binding in document.bindings}
    return tuple(
        component
        for component in document.components
        if component.tier == "concrete" and component.id not in bound
    )


def unbound_required_slots(
    document: ProjectDocument, binding: Binding
) -> tuple[ResolvedProperty, ...]:
    """The slots this binding still has to fill, in the record's own order.

    A binding must cover its component's effective properties: a missing non-optional
    slot is the framework's "must be assigned a value selection or expression"
    (``binding/factories.py``). A slot declared ``property(default=None)`` is not
    reported, because the generated record defaults it and the factory fills in a typed
    null. Names the binding uses that the component does not declare are left to
    validation, which reports them as the "map every declared property exactly once"
    mismatch.
    """
    component = document.components_by_id.get(binding.component)
    if component is None:
        return ()
    filled = {item.name for item in binding.properties}
    return tuple(
        slot
        for slot in resolved_properties(document, component)
        if slot.name not in filled and not slot.optional
    )
