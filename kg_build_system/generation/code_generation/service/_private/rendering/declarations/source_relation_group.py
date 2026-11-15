"""Renderer for a generated ``SourceRelationGroup`` declaration."""
from __future__ import annotations

from .....model._private.generated import GeneratedClass
from .common import render_class

KIND = "SourceRelationGroup"
IMPORTS = ("SourceRelationGroup", "SourceRelationGroupOptions")


def render(declaration: GeneratedClass) -> list[str]:
    return render_class(declaration, options_class="SourceRelationGroupOptions")


__all__ = ["IMPORTS", "KIND", "render"]
