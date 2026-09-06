"""Graph bindings: ``bindings/`` mirroring ``topology/``, one call per binding.

Each binding renders the way the reference project writes one: the key stack, then
one stack per property, then the ``node_binding``/``edge_binding`` call that ties them
to a component. Naming the stacks after the binding (``site_key``, ``site_name``,
``site_city``) keeps the call itself narrow and puts the interesting part — the
expression — where both a diff and the anchor index can point at it.

The properties record is built as ``Target(name=…, city=…)``. Every slot the
framework's generated ``@dataclass(kw_only=True)`` declares must then be either
assigned here or left optional on the component: the shared ``**stamps`` idiom the
reference project uses needs a *value* for an inherited slot, and this document has
nowhere to state one, so an unbound slot is generated optional in ``topology.py``
rather than stamped with something invented here.
"""

from __future__ import annotations

from ..ir.document import Binding, Component, Expression, ProjectDocument
from ..ir.index import resolved_properties
from ..ir.refs import build as build_ref
from .annotations import annotation_calls, annotation_tuple
from .expressions import ExpressionWriter
from .layout import Layout
from .render import (
    AnchorHint,
    GenerationError,
    Imports,
    Lines,
    RenderedFile,
    generated_file,
    member_name,
    python_name,
)

#: A binding call reads as identity, keys, endpoints, properties, then the extras.
_ARGUMENT_ORDER = (
    "target",
    "build_key",
    "source_build_key",
    "target_build_key",
    "source_node",
    "target_node",
    "properties",
    "debug_name",
    "options",
)
_KEYWORD_PARTS = (
    "build_key",
    "source_build_key",
    "target_build_key",
    "source_node",
    "target_node",
    "debug_name",
    "options",
)


def render_bindings(document: ProjectDocument, layout: Layout) -> list[RenderedFile]:
    """One module per binding module, holding every binding assigned to it."""
    files: list[RenderedFile] = []
    for path, binding_ids in sorted(layout.binding_members.items()):
        location = layout.binding(binding_ids[0])
        files.append(
            _render_module(
                document,
                layout,
                path=path,
                module=location.module,
                bindings=[document.bindings_by_id[item] for item in binding_ids],
            )
        )
    return files


def _render_module(
    document: ProjectDocument,
    layout: Layout,
    *,
    path: str,
    module: str,
    bindings: list[Binding],
) -> RenderedFile:
    imports = Imports(layout.package, module)
    writer = ExpressionWriter(document, layout, imports)
    taken = {entry.class_name for entry in layout.sources()}
    body = Lines()
    anchors: list[AnchorHint] = []

    for binding in bindings:
        component = document.components_by_id.get(binding.component)
        if component is None:
            raise GenerationError(
                f"binding {binding.id!r} targets unknown component {binding.component!r}"
            )
        imports.add(layout.component(component.id).location.module, component.declaration_name)
        taken.add(component.declaration_name)
        if len(body):
            body.blank()
        lines, binding_anchors = _render_binding(
            document, layout, binding, component, imports, writer, taken
        )
        body.extend(lines)
        body.blank()
        anchors.extend(binding_anchors)

    targets = sorted(
        {
            document.components_by_id[binding.component].declaration_name
            for binding in bindings
            if binding.component in document.components_by_id
        }
    )
    return generated_file(
        path=path,
        module=module,
        docstring=f"Graph bindings for {' and '.join(targets)}." if targets else None,
        imports=imports,
        body=body,
        owner_refs=[build_ref("binding", item.id) for item in bindings],
        anchors=anchors,
    )


def _render_binding(
    document: ProjectDocument,
    layout: Layout,
    binding: Binding,
    component: Component,
    imports: Imports,
    writer: ExpressionWriter,
    taken: set[str],
) -> tuple[list[str], list[AnchorHint]]:
    binding_ref = build_ref("binding", binding.id)
    variable = _unique(python_name(binding.id), taken)
    stem = _unique(_stem(binding), taken)
    stacks = Lines()
    anchors: list[AnchorHint] = []

    def stack(suffix: str, expression: Expression, owner_ref: str) -> str:
        return _stack(stacks, anchors, writer, f"{stem}_{suffix}", expression, owner_ref, taken)

    arguments: dict[str, str] = {
        "target": component.declaration_name,
        "build_key": stack("key", binding.build_key, f"{binding_ref}.build_key"),
    }
    if binding.kind == "edge":
        if binding.source_build_key is None or binding.target_build_key is None:
            raise GenerationError(
                f"edge binding {binding.id!r} must supply both endpoint keys"
            )
        arguments["source_build_key"] = stack(
            "source_key", binding.source_build_key, f"{binding_ref}.source_build_key"
        )
        arguments["target_build_key"] = stack(
            "target_key", binding.target_build_key, f"{binding_ref}.target_build_key"
        )
    if binding.source is not None:
        arguments["source_node"] = _endpoint(document, layout, binding.source, imports)
    if binding.target is not None:
        arguments["target_node"] = _endpoint(document, layout, binding.target, imports)
    properties = _property_stacks(document, binding, component, stem, stacks, anchors, writer, taken)
    if binding.debug_name is not None:
        arguments["debug_name"] = repr(binding.debug_name)
    if binding.annotations:
        imports.add_framework("BindingOptions")
        calls = annotation_calls(document, layout, binding.annotations, imports)
        arguments["options"] = f"BindingOptions(annotations={annotation_tuple(calls)})"

    factory = "edge_binding" if binding.kind == "edge" else "node_binding"
    imports.add_framework(factory)

    body = Lines()
    body.extend(stacks.items)
    body.blank()
    body.add(f"{variable} = {factory}(")
    for name in _ARGUMENT_ORDER:
        if name == "properties":
            _render_properties(body, component.declaration_name, properties)
            continue
        if name in arguments:
            body.add(f"{name}={arguments[name]},", level=1)
    body.add(")")
    body.blank()

    anchors.append(AnchorHint("assignment", binding_ref, variable))
    for name in _KEYWORD_PARTS:
        if name in arguments:
            anchors.append(
                AnchorHint("keyword", f"{binding_ref}.{name}", variable, keyword=name)
            )
    return body.items, anchors


def _render_properties(body: Lines, target: str, properties: list[tuple[str, str]]) -> None:
    """``properties=Target(name=…, city=…)``, one slot per line."""
    if not properties:
        body.add(f"properties={target}(),", level=1)
        return
    body.add(f"properties={target}(", level=1)
    for attribute, variable in properties:
        body.add(f"{attribute}={variable},", level=2)
    body.add("),", level=1)


def _property_stacks(
    document: ProjectDocument,
    binding: Binding,
    component: Component,
    stem: str,
    stacks: Lines,
    anchors: list[AnchorHint],
    writer: ExpressionWriter,
    taken: set[str],
) -> list[tuple[str, str]]:
    """``Target(name=…, city=…)``, each value a named stack rendered above the call.

    A binding fills the component's *effective* slots, inherited ones included: the
    framework's ``binding/factories.py`` checks a property record against the target's
    effective properties, so ``summary`` inherited from a category is exactly as
    binding as ``name`` declared on the node itself.
    """
    declared = {item.name for item in resolved_properties(document, component)}
    binding_ref = build_ref("binding", binding.id)
    values: list[tuple[str, str]] = []
    for item in binding.properties:
        if item.name not in declared:
            raise GenerationError(
                f"binding {binding.id!r} fills {item.name!r}, which "
                f"{component.declaration_name} does not declare"
            )
        attribute = member_name(item.name)
        variable = _stack(
            stacks,
            anchors,
            writer,
            f"{stem}_{attribute}",
            item.expression,
            f"{binding_ref}.property.{item.name}",
            taken,
        )
        values.append((attribute, variable))
        anchors.append(
            AnchorHint(
                "keyword",
                f"{binding_ref}.property.{item.name}",
                python_name(binding.id),
                keyword=attribute,
            )
        )
    return values


def _stack(
    stacks: Lines,
    anchors: list[AnchorHint],
    writer: ExpressionWriter,
    variable: str,
    expression: Expression,
    owner_ref: str,
    taken: set[str],
) -> str:
    """Render one expression into a named module-level stack, returning its name."""
    name = _unique(variable, taken)
    stacks.add(f"{name} = {writer.render(expression).text()}")
    stacks.blank()
    anchors.append(AnchorHint("expression", owner_ref, name))
    return name


def _endpoint(
    document: ProjectDocument, layout: Layout, component_id: str, imports: Imports
) -> str:
    imports.add_framework("endpoint")
    endpoint = document.components_by_id.get(component_id)
    if endpoint is None:
        raise GenerationError(f"binding names unknown endpoint component {component_id!r}")
    imports.add(layout.component(endpoint.id).location.module, endpoint.declaration_name)
    return f"endpoint({endpoint.declaration_name})"


def _stem(binding: Binding) -> str:
    """The readable prefix for one binding's stacks."""
    name = python_name(binding.id)
    return name[: -len("_binding")] if name.endswith("_binding") else name


def _unique(name: str, taken: set[str]) -> str:
    candidate = name
    while candidate in taken:
        candidate = f"{candidate}_x"
    taken.add(candidate)
    return candidate
