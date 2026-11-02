"""Registry of declaration renderers keyed by declaration kind, not by isinstance."""
from __future__ import annotations

from collections.abc import Iterable

from ...ir import GeneratedClass
from ...models import GenerationError
from . import plain, struct, table, table_group

_RENDERERS = {
    plain.KIND: plain,
    table.KIND: table,
    struct.KIND: struct,
    table_group.KIND: table_group,
}


def render_declaration(declaration: GeneratedClass) -> list[str]:
    """Render one declaration through the renderer for its kind."""
    renderer = _RENDERERS.get(declaration.base)
    if renderer is None:
        raise GenerationError(
            f"generated declaration {declaration.name!r} has unknown kind {declaration.base!r}"
        )
    return renderer.render(declaration)


def declaration_imports(declarations: Iterable[GeneratedClass]) -> set[str]:
    """The framework names a file's declarations need imported."""
    imports: set[str] = set()
    for declaration in declarations:
        renderer = _RENDERERS.get(declaration.base)
        if renderer is None:
            raise GenerationError(
                f"generated declaration {declaration.name!r} has unknown kind {declaration.base!r}"
            )
        imports.update(renderer.IMPORTS)
    return imports


__all__ = ["declaration_imports", "render_declaration"]
