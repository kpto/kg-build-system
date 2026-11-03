"""Shared assembly of one generated declaration body."""
from __future__ import annotations

from .....model._private.generated import GeneratedClass, GeneratedField, GeneratedMember, Nullability
from ..types import field_annotation


def render_field(field: GeneratedField) -> str:
    nullable = field.nullability is Nullability.DEFAULTED
    annotation = f"Field[{field_annotation(field.value_type, nullable=nullable)}]"
    arguments: list[str] = [f"name={field.external_name!r}"]
    if field.description is not None:
        arguments.append(f"description={field.description!r}")
    if field.annotations:
        arguments.append(
            "annotations=("
            + ", ".join(f"{item.class_name}(**{item.arguments!r})" for item in field.annotations)
            + ",)"
        )
    return f"    {field.python_name}: {annotation} = field({', '.join(arguments)})"


def render_member(member: GeneratedMember) -> str:
    return f"    {member.python_name} = {member.declaration_name}"


def render_class(declaration: GeneratedClass, *, options_class: str | None = None) -> list[str]:
    """Render one declaration as class lines, without surrounding blank lines."""
    base = f"({declaration.base})" if declaration.base else ""
    lines = [f"class {declaration.name}{base}:"]
    if declaration.description:
        lines.append(f"    {declaration.description!r}")
    if declaration.declaration_name is not None and options_class is not None:
        lines.append(f"    options = {options_class}(name={declaration.declaration_name!r})")
    lines.extend(render_field(field) for field in declaration.fields)
    lines.extend(render_member(member) for member in declaration.members)
    if (
        not declaration.fields
        and not declaration.members
        and not declaration.description
        and declaration.declaration_name is None
    ):
        lines.append("    pass")
    return lines


__all__ = ["render_class", "render_field", "render_member"]
