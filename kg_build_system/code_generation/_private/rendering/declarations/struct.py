"""Renderer for a generated ``Struct`` declaration."""
from __future__ import annotations

from ....internal.ir import GeneratedClass
from .common import render_class

KIND = "Struct"
IMPORTS = ("Struct",)


def render(declaration: GeneratedClass) -> list[str]:
    return render_class(declaration)


__all__ = ["IMPORTS", "KIND", "render"]
