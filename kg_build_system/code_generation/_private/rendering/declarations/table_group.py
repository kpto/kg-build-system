"""Renderer for a generated ``TableGroup`` declaration."""
from __future__ import annotations

from ....internal.ir import GeneratedClass
from .common import render_class

KIND = "TableGroup"
IMPORTS = ("TableGroup", "TableGroupOptions")


def render(declaration: GeneratedClass) -> list[str]:
    return render_class(declaration, options_class="TableGroupOptions")


__all__ = ["IMPORTS", "KIND", "render"]
