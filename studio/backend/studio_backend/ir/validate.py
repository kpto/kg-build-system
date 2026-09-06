"""Structural validation of an IR document: referential integrity and naming.

This is the tier that can be checked without compiling anything: dangling refs,
duplicate identities, expressions pointing at sources that do not exist. Type
correctness is *not* checked here — pyright and ``create_blueprint`` are the
authorities for that, and duplicating their rules here would only produce
conflicting verdicts.
"""

from __future__ import annotations

from dataclasses import dataclass

from .document import (
    Binding,
    Component,
    NullableType,
    Expression,
    FieldExpression,
    ProjectDocument,
    StructType,
    Table,
    unwrap_nullable,
)
from .refs import ReferenceError, parse

#: Logical names must be unique across everything the framework resolves by name.
#: Two declarations sharing one logical name would silently merge in a blueprint.
_NAME_SPACES: tuple[tuple[str, str], ...] = (
    ("tables", "table"),
    ("structs", "struct"),
    ("projections", "projection"),
    ("components", "component"),
)


@dataclass(frozen=True, slots=True)
class Issue:
    path: str
    message: str
    ref: str | None = None
    #: Only ``error`` issues block a save. A warning is worth showing — a project
    #: with no target publishes nothing — but it must not prevent the edit that
    #: fixes it, and an empty document is a legitimate state to be in.
    severity: str = "error"


def blocking(issues: list[Issue]) -> list[Issue]:
    return [issue for issue in issues if issue.severity == "error"]


def validate_document(document: ProjectDocument, *, known_modules: set[str] | None = None) -> list[Issue]:
    issues: list[Issue] = []
    issues += _unique_ids(document)
    issues += _unique_names(document)
    issues += _unique_declaration_names(document)
    issues += _table_membership(document)
    issues += _sources(document)
    issues += _components(document)
    issues += _bindings(document)
    issues += _expressions(document)
    issues += _annotations(document)
    issues += _modules(document, known_modules)
    issues += _project_identity(document)
    return issues


def _unique_ids(document: ProjectDocument) -> list[Issue]:
    issues: list[Issue] = []
    for section in (
        "tables", "structs", "projections", "components", "bindings", "sources",
        "modules", "annotation_types",
    ):
        seen: dict[str, int] = {}
        for item in getattr(document, section):
            item_id = getattr(item, "id", None)
            if item_id is None:
                continue
            if item_id in seen:
                issues.append(Issue(section, f"duplicate id {item_id!r} in {section}"))
            seen[item_id] = 1
    return issues


def _unique_names(document: ProjectDocument) -> list[Issue]:
    issues: list[Issue] = []
    for section, kind in _NAME_SPACES:
        by_name: dict[str, list[str]] = {}
        for item in getattr(document, section):
            by_name.setdefault(item.name, []).append(item.id)
        for name, ids in sorted(by_name.items()):
            if len(ids) > 1:
                issues.append(
                    Issue(section, f"{kind} logical name {name!r} is declared by {', '.join(ids)}")
                )
    return issues


def _unique_declaration_names(document: ProjectDocument) -> list[Issue]:
    """Python class names must not collide across the whole project."""
    by_declaration: dict[str, list[str]] = {}
    sections = (
        ("tables", "table"), "structs", "projections", "components",
    )
    for entry in sections:
        section, label = entry if isinstance(entry, tuple) else (entry, entry[:-1])
        for item in getattr(document, section):
            by_declaration.setdefault(item.declaration_name, []).append(f"{label}:{item.id}")
    for annotation in document.annotation_types:
        by_declaration.setdefault(annotation.declaration_name, []).append(
            f"annotation_type:{annotation.id}"
        )
    return [
        Issue(section, f"declaration name {name!r} is used by {', '.join(owners)}")
        for name, owners in sorted(by_declaration.items())
        if len(owners) > 1
        for section in {owners[0].split(":")[0]}
    ]


def _table_membership(document: ProjectDocument) -> list[Issue]:
    issues: list[Issue] = []
    tables = document.tables_by_id
    for group in document.tables:
        if not group.is_group:
            continue
        for member in group.members:
            target = tables.get(member.ref)
            if target is None:
                issues.append(
                    Issue(f"table:{group.id}", f"group member {member.ref!r} is not a declared table", f"table:{group.id}")
                )
                continue
            if target.is_group:
                issues.append(
                    Issue(
                        f"table:{group.id}",
                        f"group member {member.ref!r} must be a table, not another group",
                        f"table:{group.id}",
                    )
                )
            if target.group != group.id:
                issues.append(
                    Issue(
                        f"table:{member.ref}",
                        f"member of {group.id!r} does not declare group={group.id!r} (it says {target.group!r})",
                        f"table:{member.ref}",
                    )
                )
    for table in document.tables:
        if table.group is not None and table.group not in tables:
            issues.append(
                Issue(f"table:{table.id}", f"declares an unknown parent group {table.group!r}", f"table:{table.id}")
            )
        if table.group == table.id:
            issues.append(Issue(f"table:{table.id}", "a group cannot contain itself", f"table:{table.id}"))
    return issues


def _sources(document: ProjectDocument) -> list[Issue]:
    issues: list[Issue] = []
    tables = document.tables_by_id
    for source in document.sources:
        table = tables.get(source.table)
        if table is None:
            issues.append(
                Issue(f"source:{source.id}", f"binds an unknown table {source.table!r}", f"source:{source.id}")
            )
            continue
        if table.is_group and not source.layout:
            issues.append(
                Issue(
                    f"source:{source.id}",
                    f"binds group {table.id!r} and must supply a layout template",
                    f"source:{source.id}",
                )
            )
        if not table.is_group and source.layout:
            issues.append(
                Issue(
                    f"source:{source.id}",
                    "a layout template is only meaningful for a table group",
                    f"source:{source.id}",
                )
            )
        if source.layout and (
            "{group_path}" not in source.layout or "{table_name}" not in source.layout
        ):
            issues.append(
                Issue(
                    f"source:{source.id}",
                    "a group layout must contain both {group_path} and {table_name}",
                    f"source:{source.id}",
                )
            )
    for table in document.tables:
        if table.is_group:
            continue
        if not document.sources_for_table(table.id) and not _group_source_covers(document, table):
            issues.append(
                Issue(f"table:{table.id}", "has no physical source bound to it", f"table:{table.id}")
            )
    return issues


def _group_source_covers(document: ProjectDocument, table: Table) -> bool:
    """A member table is supplied by its group's source when that source exists."""
    return table.group is not None and bool(document.sources_for_table(table.group))


def _components(document: ProjectDocument) -> list[Issue]:
    issues: list[Issue] = []
    components = document.components_by_id
    for component in document.components:
        ref = f"component:{component.id}"
        if component.parent is not None:
            parent = components.get(component.parent)
            if parent is None:
                issues.append(Issue(ref, f"names an unknown category parent {component.parent!r}", ref))
            elif parent.kind != component.kind:
                issues.append(
                    Issue(ref, f"parent {parent.id!r} is a {parent.kind}, not a {component.kind}", ref)
                )
            elif parent.tier == "template":
                issues.append(Issue(ref, f"parent {parent.id!r} is a template; a parent must be a category", ref))
        for mixin in component.mixins:
            template = components.get(mixin)
            if template is None:
                issues.append(Issue(ref, f"mixes in an unknown component {mixin!r}", ref))
                continue
            if template.kind != component.kind:
                issues.append(Issue(ref, f"mixin {mixin!r} is a {template.kind}", ref))
            if component.tier == "concrete" and template.tier != "template":
                issues.append(
                    Issue(ref, f"mixin {mixin!r} must be a template, not a {template.tier}", ref)
                )
        for slot in component.properties:
            if slot.optional and not isinstance(slot.logical_type, NullableType):
                issues.append(
                    Issue(
                        f"{ref}.property.{slot.name}",
                        f"{slot.name!r} opts out with a null default but is not nullable; "
                        "only a nullable slot can be left unbound",
                        f"{ref}.property.{slot.name}",
                    )
                )
        if component.kind == "edge" and component.tier != "template":
            for side in ("source", "target"):
                endpoint_id = getattr(component, side)
                endpoint = components.get(str(endpoint_id))
                if endpoint is None:
                    issues.append(Issue(ref, f"{side} endpoint {endpoint_id!r} is not declared", ref))
                elif endpoint.kind != "node":
                    issues.append(Issue(ref, f"{side} endpoint {endpoint_id!r} is not a node component", ref))
        labels = [
            (annotation.arguments.get("label"), annotation)
            for annotation in component.annotations
            if annotation.class_name in {"NodeLabel", "EdgeLabel"}
        ]
        if component.label and len(labels) > 1:
            issues.append(Issue(ref, "declares more than one semantic label", ref))
    return issues


def _bindings(document: ProjectDocument) -> list[Issue]:
    issues: list[Issue] = []
    components = document.components_by_id
    for binding in document.bindings:
        ref = f"binding:{binding.id}"
        component = components.get(binding.component)
        if component is None:
            issues.append(Issue(ref, f"targets an undeclared component {binding.component!r}", ref))
            continue
        if component.kind != binding.kind:
            issues.append(Issue(ref, f"is a {binding.kind} binding for a {component.kind} component", ref))
        if component.tier != "concrete":
            issues.append(Issue(ref, f"targets {component.id!r}, which is {component.tier} and not bindable", ref))
        for side in ("source", "target"):
            supplied = getattr(binding, side)
            declared = getattr(component, side)
            if binding.kind != "edge" or component is None:
                continue
            if supplied is None:
                if declared is None:
                    issues.append(Issue(ref, f"declares no {side} endpoint", ref))
                continue
            token = components.get(supplied)
            if token is None:
                issues.append(Issue(ref, f"{side} endpoint token {supplied!r} is undeclared", ref))
            elif token.tier != "concrete":
                issues.append(Issue(ref, f"{side} endpoint token {supplied!r} must name a concrete node", ref))
    return issues


def _expressions(document: ProjectDocument) -> list[Issue]:
    issues: list[Issue] = []
    sources = _selectable_names(document)
    for projection in document.projections:
        for field in projection.fields:
            issues += _expression_sources(field.expression, sources, f"projection:{projection.id}.field.{field.name}")
    for binding in document.bindings:
        issues += _expression_sources(binding.build_key, sources, f"binding:{binding.id}.build_key")
        for side in ("source_build_key", "target_build_key"):
            value = getattr(binding, side)
            if value is not None:
                issues += _expression_sources(value, sources, f"binding:{binding.id}.{side}")
        for property_binding in binding.properties:
            issues += _expression_sources(
                property_binding.expression, sources, f"binding:{binding.id}.property.{property_binding.name}"
            )
    return issues


def _selectable_names(document: ProjectDocument) -> dict[str, object]:
    """Every name an expression may reference, mapped to its declaration."""
    names: dict[str, object] = {}
    for table in document.tables:
        names[table.name] = table
    for projection in document.projections:
        names[projection.name] = projection
    return names


def _expression_sources(
    expression: Expression, sources: dict[str, object], path: str
) -> list[Issue]:
    issues: list[Issue] = []
    for node in _walk(expression):
        if isinstance(node, FieldExpression):
            if node.source not in sources:
                issues.append(
                    Issue(path, f"references source {node.source!r}, which is not a declared table or projection", path)
                )
            if not node.path:
                issues.append(Issue(path, "has an empty field path", path))
        if isinstance(node, StructType):
            pass
    return issues


def _walk(expression: Expression):
    yield expression
    for attribute in ("arguments",):
        for child in getattr(expression, attribute, ()) or ():
            yield from _walk(child)  # type: ignore[arg-type]


def _annotations(document: ProjectDocument) -> list[Issue]:
    issues: list[Issue] = []
    declared = document.annotation_types_by_id
    for annotation in document.annotation_types:
        if not annotation.namespace or not annotation.annotation_id:
            issues.append(
                Issue(f"annotation_type:{annotation.id}", "needs both a namespace and an annotation_id", f"annotation_type:{annotation.id}")
            )
    for section, items in (
        ("tables", document.tables),
        ("structs", document.structs),
        ("projections", document.projections),
        ("components", document.components),
        ("bindings", document.bindings),
        ("sources", document.sources),
    ):
        for item in items:
            for instance in _annotation_tree(item):
                if instance.annotation_type and instance.annotation_type not in declared:
                    issues.append(
                        Issue(
                            f"{section[:-1]}:{item.id}",
                            f"uses annotation type {instance.annotation_type!r}, which is not declared",
                            f"{section[:-1]}:{item.id}",
                        )
                    )
    return issues


def _annotation_tree(item: object):
    for annotation in getattr(item, "annotations", ()) or ():
        yield annotation
    for collection in ("fields", "properties", "members"):
        for child in getattr(item, collection, ()) or ():
            for annotation in getattr(child, "annotations", ()) or ():
                yield annotation


def _modules(document: ProjectDocument, known_modules: set[str] | None) -> list[Issue]:
    if known_modules is None:
        return []
    issues: list[Issue] = []
    for module in document.modules:
        if module.id not in known_modules:
            issues.append(Issue(f"module:{module.id}", f"is not a module the backend knows about", f"module:{module.id}"))
    if not any(module.enabled for module in document.modules):
        issues.append(
            Issue(
                "modules",
                "the project configures no target, so a build would publish nothing",
                severity="warning",
            )
        )
    return issues


def _project_identity(document: ProjectDocument) -> list[Issue]:
    issues: list[Issue] = []
    package = document.project.package
    if not package.isidentifier():
        issues.append(Issue("project", f"package {package!r} is not a valid Python identifier"))
    elif package in {"table", "topology", "bindings", "build", "sources"}:
        issues.append(Issue("project", f"package {package!r} would shadow a generated module name"))
    if not document.project.name.strip():
        issues.append(Issue("project", "needs a name"))
    return issues
