"""Renderer for a generated ``SourceRelation`` declaration."""
from __future__ import annotations

from .....model._private.generated import GeneratedClass
from .common import render_class

KIND = "SourceRelation"
IMPORTS = ("SourceRelation", "SourceRelationOptions")


def render(declaration: GeneratedClass) -> list[str]:
    return render_class(declaration, options_class="SourceRelationOptions")


__all__ = ["IMPORTS", "KIND", "render"]
