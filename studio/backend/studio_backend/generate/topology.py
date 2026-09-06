"""Topology: templates and categories in ``common.py``, components per package.

Slots are generated exactly as declared. A document whose bindings under-fill a
declaration is a document with a mistake, not a declaration to be softened: making an
unfilled slot optional, or a non-null slot nullable, would emit a project that
compiles while quietly permitting records with the property absent — the same class of
silent data loss the framework's nullability policy exists to prevent. The mismatch is
therefore reported as a :class:`SlotGap` by :func:`slot_gaps` and shown in the UI, and
the generated code stays faithful to the declaration so pyright and
``create_blueprint`` agree with what the author wrote.

Base order is the framework's authoring convention — template mixins first, then the
one category parent, then the terminal base — which is what lets ``dataclass_transform``
see every slot and keeps a declaration to a single abstract parent.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..ir.document import Component, LogicalType, NullableType, ProjectDocument, Property
from .annotations import annotation_calls, annotation_tuple
from .layout import TOPOLOGY_PACKAGE, Layout
from .render import (
    AnchorHint,
    GenerationError,
    Imports,
    Lines,
    RenderedFile,
    annotation_text,
    attribute_docstring_lines,
    declaration_name,
    docstring_lines,
    generated_file,
    member_name,
)

COMMON_FILE = "common.py"
COMMON_DOCSTRING = (
    "Topology vocabulary shared across node packages. Templates contribute property "
    "slots and annotations to every component that mixes them in and never reach the "
    "blueprint; categories are the graph-visible parents: they own a shared property, "
    "appear in the hierarchy, and let an edge declare its endpoint as a whole category."
)

_KIND_SUFFIX = {"node": "Node", "edge": "Edge"}
_TERMINAL_BASE = {
    ("node", "template"): "NodeTemplate",
    ("node", "category"): "AbstractNode",
    ("node", "concrete"): "Node",
    ("edge", "template"): "EdgeTemplate",
    ("edge", "category"): "AbstractEdge",
    ("edge", "concrete"): "Edge",
}


@dataclass(frozen=True)
class SlotPolicy:
    """How one declared slot is generated: as written."""

    nullable: bool = False
    optional: bool = False


@dataclass(frozen=True)
class SlotGap:
    """A declared slot the document's own bindings do not honour.

    Carried out through :class:`~studio_backend.generate.project.GenerationOutcome`
    so it reaches the UI as a problem on the component and the binding, rather than
    being smoothed over in the generated source.
    """

    component: str
    property: str
    kind: str
    message: str


@dataclass(frozen=True)
class SlotEvidence:
    """What the document's bindings deliver for one declared slot."""

    supplied_nullable: bool
    left_unfilled: bool


def render_topology(document: ProjectDocument, layout: Layout) -> list[RenderedFile]:
    """``topology/common.py`` plus one module per concrete component."""
    policies = slot_policies(document)
    common_path = f"{layout.package}/{TOPOLOGY_PACKAGE}/{COMMON_FILE}"
    files: list[RenderedFile] = []
    for path, component_ids in sorted(layout.component_members.items()):
        components = [document.components_by_id[item] for item in component_ids]
        location = layout.component(component_ids[0]).location
        files.append(
            _render_module(
                document,
                layout,
                path=path,
                module=location.module,
                components=components,
                policies=policies,
                docstring=COMMON_DOCSTRING if path == common_path else _relation_summary(components),
            )
        )
    return files


# ------------------------------------------------------------------ slot policies


def slot_policies(document: ProjectDocument) -> dict[tuple[str, str], SlotPolicy]:
    """``(declaring component id, property name)`` to how that slot is generated.

    Evidence is gathered over every concrete component that inherits the slot,
    because a binding fills the *effective* slot while the declaration that carries
    it may sit on a category or a template.
    """
    policies: dict[tuple[str, str], SlotPolicy] = {}
    for component in document.components:
        for declared in component.properties:
            policies[(component.id, declared.name)] = SlotPolicy(
                nullable=isinstance(declared.logical_type, NullableType),
                optional=declared.optional,
            )
    return policies


def slot_gaps(document: ProjectDocument) -> tuple[SlotGap, ...]:
    """Every slot a binding leaves unfilled or fills with a nullable expression."""
    evidence = slot_evidence(document)
    declared_types = {
        (component.id, slot.name): slot.logical_type
        for component in document.components
        for slot in component.properties
    }
    gaps: list[SlotGap] = []
    optional_slots = {
        (component.id, slot.name) for component in document.components for slot in component.properties if slot.optional
    }
    for (component_id, name), seen in sorted(evidence.items()):
        declared_nullable = isinstance(declared_types.get((component_id, name)), NullableType)
        # An optional slot is a stated permission to state nothing, so leaving it
        # unfilled is not a gap.
        if seen.left_unfilled and (component_id, name) not in optional_slots:
            gaps.append(
                SlotGap(
                    component=component_id,
                    property=name,
                    kind="unfilled",
                    message=(
                        f"{name!r} is declared on {component_id} and every binding of it must "
                        "supply a value, but a binding states none"
                    ),
                )
            )
        if seen.supplied_nullable and not declared_nullable:
            gaps.append(
                SlotGap(
                    component=component_id,
                    property=name,
                    kind="nullable_into_non_null",
                    message=(
                        f"{name!r} on {component_id} is not nullable, but a binding fills it "
                        "with an expression that can be null"
                    ),
                )
            )
    return tuple(gaps)


def slot_evidence(document: ProjectDocument) -> dict[tuple[str, str], SlotEvidence]:
    """For each declared slot, whether a binding supplies nulls and whether one skips it.

    A slot no concrete component ever binds has no evidence either way: the
    declaration is a promise a future binding will be asked to keep, so it stays
    exactly as written.
    """
    inheritors = _inheritors(document)
    evidence: dict[tuple[str, str], SlotEvidence] = {}
    for component in document.components:
        for declared in component.properties:
            supplied_nullable = False
            left_unfilled = False
            for concrete_id in inheritors.get(component.id, ()):
                binding_properties = [
                    binding.properties
                    for binding in document.bindings_for_component(concrete_id)
                ]
                if not binding_properties:
                    continue
                for properties in binding_properties:
                    filled = [item for item in properties if item.name == declared.name]
                    if not filled:
                        left_unfilled = True
                    supplied_nullable = supplied_nullable or any(
                        isinstance(item.expression.logical_type, NullableType)
                        for item in filled
                    )
            evidence[(component.id, declared.name)] = SlotEvidence(
                supplied_nullable=supplied_nullable, left_unfilled=left_unfilled
            )
    return evidence


def _inheritors(document: ProjectDocument) -> dict[str, tuple[str, ...]]:
    """For every component, the concrete components that inherit its slots."""
    buckets: dict[str, list[str]] = {}
    for component in document.components:
        if component.tier != "concrete":
            continue
        for ancestor in (component.id, *_ancestors(document, component, ())):
            buckets.setdefault(ancestor, []).append(component.id)
    return {key: tuple(sorted(set(value))) for key, value in buckets.items()}


def _ancestors(
    document: ProjectDocument, component: Component, trail: tuple[str, ...]
) -> tuple[str, ...]:
    by_id = document.components_by_id
    found: list[str] = []
    for ancestor_id in (component.parent, *component.mixins):
        if ancestor_id is None:
            continue
        if ancestor_id in trail or ancestor_id == component.id:
            raise GenerationError(
                f"component inheritance cycles at {ancestor_id!r} through {component.id!r}"
            )
        ancestor = by_id.get(ancestor_id)
        if ancestor is None:
            raise GenerationError(f"component {component.id!r} names unknown {ancestor_id!r}")
        found.append(ancestor_id)
        found.extend(_ancestors(document, ancestor, (*trail, component.id)))
    return tuple(dict.fromkeys(found))


# ------------------------------------------------------------------------ modules


def _relation_summary(components: list[Component]) -> str | None:
    """``Site -[:HAS_UNIT]-> Unit.``, so an edge file says which relation it holds."""
    if len(components) != 1 or components[0].kind != "edge":
        return None
    edge = components[0]
    label = edge.label or edge.name.upper()
    return (
        f"{_title(edge.source or '')} -[:{label}]-> {_title(edge.target or '')}, "
        "declared by the studio project document."
    )


def _title(component_id: str) -> str:
    return " ".join(part.title() for part in component_id.split("_"))


def _render_module(
    document: ProjectDocument,
    layout: Layout,
    *,
    path: str,
    module: str,
    components: list[Component],
    policies: dict[tuple[str, str], SlotPolicy],
    docstring: str | None,
) -> RenderedFile:
    imports = Imports(layout.package, module)
    body = Lines()
    anchors: list[AnchorHint] = []
    for index, component in enumerate(components):
        if index:
            body.blank()
        lines, component_anchors = _render_component(
            document, layout, component, module, imports, policies
        )
        body.extend(lines)
        body.blank()
        anchors.extend(component_anchors)
    return generated_file(
        path=path,
        module=module,
        docstring=docstring,
        imports=imports,
        body=body,
        owner_refs=[f"component:{component.id}" for component in components],
        anchors=anchors,
    )


def _render_component(
    document: ProjectDocument,
    layout: Layout,
    component: Component,
    module: str,
    imports: Imports,
    policies: dict[tuple[str, str], SlotPolicy],
) -> tuple[list[str], list[AnchorHint]]:
    bases = _bases(document, layout, component, imports)
    body = Lines()
    body.add(f"class {component.declaration_name}({', '.join(bases)}):")
    if component.description:
        body.extend(docstring_lines(component.description, level=1))
        body.blank()
    options = _options_lines(document, layout, component, imports)
    body.extend(options)
    anchors = [AnchorHint("class", f"component:{component.id}", component.declaration_name)]
    for declared in component.properties:
        body.blank()
        body.extend(
            _property_lines(document, layout, component, declared, module, imports, policies)
        )
        anchors.append(
            AnchorHint(
                "property",
                f"component:{component.id}.property.{declared.name}",
                f"{component.declaration_name}.{member_name(declared.name)}",
            )
        )
    if not options and not component.properties:
        body.blank()
        body.add("pass", level=1)
    body.blank()
    return body.items, anchors


def _bases(
    document: ProjectDocument, layout: Layout, component: Component, imports: Imports
) -> list[str]:
    by_id = document.components_by_id
    bases: list[str] = []
    for mixin_id in component.mixins:
        mixin = by_id.get(mixin_id)
        if mixin is None:
            raise GenerationError(f"component {component.id!r} mixes unknown {mixin_id!r}")
        if mixin.tier != "template":
            raise GenerationError(
                f"component {component.id!r} mixes {mixin_id!r}, which is not a template: "
                "only the template tier is a mixin"
            )
        bases.append(_reference(layout, mixin, imports))
    if component.parent is not None:
        parent = by_id.get(component.parent)
        if parent is None:
            raise GenerationError(
                f"component {component.id!r} names unknown parent {component.parent!r}"
            )
        if parent.tier != "category":
            raise GenerationError(
                f"component {component.id!r} parent {parent.id!r} is not a category: "
                "a declaration has exactly one abstract category parent"
            )
        bases.append(_reference(layout, parent, imports))
    bases.append(_terminal_base(document, layout, component, imports))
    return bases


def _reference(layout: Layout, component: Component, imports: Imports) -> str:
    """The class name of another component, imported from the module that holds it."""
    imports.add(layout.component(component.id).location.module, component.declaration_name)
    return component.declaration_name


def _terminal_base(
    document: ProjectDocument,
    layout: Layout,
    component: Component,
    imports: Imports,
) -> str:
    key = (component.kind, component.tier)
    if key not in _TERMINAL_BASE:
        raise GenerationError(
            f"component {component.id!r} is a {component.tier} {component.kind}, "
            "which has no terminal base"
        )
    name = _TERMINAL_BASE[key]
    imports.add_framework(name)
    if component.kind == "node" or component.tier == "template":
        return name
    endpoints = []
    for side in (component.source, component.target):
        endpoint = document.components_by_id.get(side or "")
        if endpoint is None:
            raise GenerationError(
                f"edge component {component.id!r} names unknown endpoint {side!r}"
            )
        if endpoint.kind != "node":
            raise GenerationError(f"endpoint {side!r} of {component.id!r} is not a node")
        endpoints.append(_reference(layout, endpoint, imports))
    return f"{name}[{', '.join(endpoints)}]"


def _options_lines(
    document: ProjectDocument,
    layout: Layout,
    component: Component,
    imports: Imports,
) -> list[str]:
    """``options = …`` carrying the label sugar, annotations and an odd logical name.

    A template's options carry no name: the tier reaches no blueprint, so only the
    annotations it flows to its hosts are worth writing down.
    """
    kind_suffix = _KIND_SUFFIX[component.kind]
    tier = "abstract" if component.tier == "category" else component.tier
    suffixes = (f"Abstract{kind_suffix}", kind_suffix) if tier == "abstract" else (kind_suffix,)
    annotations: list[str] = []
    if component.label:
        label_class = "NodeLabel" if component.kind == "node" else "EdgeLabel"
        imports.add_framework(label_class)
        annotations.append(f"{label_class}({component.label!r})")
    annotations.extend(annotation_calls(document, layout, component.annotations, imports))

    arguments: list[str] = []
    if (
        component.tier != "template"
        and declaration_name(component.declaration_name, suffixes=suffixes) != component.name
    ):
        arguments.append(f"name={component.name!r}")
    if annotations:
        arguments.append(f"annotations={annotation_tuple(annotations)}")
    if not arguments:
        return []
    if component.tier == "template":
        options_class = "NodeOptionsTemplate" if component.kind == "node" else "EdgeOptionsTemplate"
    else:
        options_class = "NodeOptions" if component.kind == "node" else "EdgeOptions"
    imports.add_framework(options_class)
    body = Lines()
    body.add(f"options = {options_class}({', '.join(arguments)})", level=1)
    return body.items


def _property_lines(
    document: ProjectDocument,
    layout: Layout,
    component: Component,
    declared: Property,
    module: str,
    imports: Imports,
    policies: dict[tuple[str, str], SlotPolicy],
) -> list[str]:
    """``name: PropertySlot[T] = property()``, its description written underneath."""
    imports.add_framework("PropertySlot", "property")
    policy = policies.get(
        (component.id, declared.name), SlotPolicy(nullable=False, optional=False)
    )
    value: LogicalType = declared.logical_type
    if policy.nullable and not isinstance(value, NullableType):
        value = NullableType(value=value)
    annotation = annotation_text(value, imports, current_module=module)
    arguments: list[str] = []
    if declared.annotations:
        calls = annotation_calls(document, layout, declared.annotations, imports)
        arguments.append(f"annotations={annotation_tuple(calls)}")
    if policy.optional:
        arguments.append("default=None")
    body = Lines()
    body.add(
        f"{member_name(declared.name)}: PropertySlot[{annotation}] = property({', '.join(arguments)})",
        level=1,
    )
    body.extend(attribute_docstring_lines(declared.description or ""))
    return body.items
