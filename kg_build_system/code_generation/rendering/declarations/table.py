"""Renderer for a generated ``Table`` declaration."""
from __future__ import annotations

from ...ir import GeneratedClass
from .common import render_class

KIND = "Table"
IMPORTS = ("Table", "TableOptions")


def render(declaration: GeneratedClass) -> list[str]:
    return render_class(declaration, options_class="TableOptions")


__all__ = ["IMPORTS", "KIND", "render"]
