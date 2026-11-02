"""Renderer for a generated declaration with no framework base."""
from __future__ import annotations

from ....internal.ir import GeneratedClass
from .common import render_class

KIND: str | None = None
IMPORTS: tuple[str, ...] = ()


def render(declaration: GeneratedClass) -> list[str]:
    return render_class(declaration)


__all__ = ["IMPORTS", "KIND", "render"]
