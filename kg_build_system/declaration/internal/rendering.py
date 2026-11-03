"""Stable import surface for the source forms shared by declaration languages.

The mechanism is private to the declaration system; this module forwards the
names a language renderer may depend on.
"""
from __future__ import annotations

from .._private.rendering import (
    annotation_class,
    class_name,
    member_name,
    pascal_case,
    render_annotation,
    render_docstring,
    render_logical_type,
    render_static_value,
    snake_case,
)

__all__ = [
    "annotation_class", "class_name", "member_name", "pascal_case",
    "render_annotation", "render_docstring", "render_logical_type",
    "render_static_value", "snake_case",
]
