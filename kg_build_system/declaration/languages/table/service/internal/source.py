"""Render the table language DTO back to authoring source.

The renderer lives in the package's private zone; each name here is a thin
delegation kept for the internal service path.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.declaration.model.internal import SourceFragment

from ...model.internal.dto.blueprint_dto import DataPartDTO


def render_data(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
) -> SourceFragment:
    """Render a table DTO as authoring source.

    Example:
        ```python
        from kg_build_system.declaration.languages.table.model.internal.dto import (
            DataPartDTO,
        )
        from kg_build_system.declaration.languages.table.service.internal.source import (
            render_data,
        )

        fragment = render_data(DataPartDTO((), (), (), ()))
        assert fragment.body == ""
        ```
    """
    from .._private.source import render_data as render

    return render(data, context, class_names=class_names)


def data_to_fragment(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
) -> SourceFragment:
    """Alias of :func:`render_data` named for the DTO-to-fragment direction."""
    from .._private.source import data_to_fragment as fragment

    return fragment(data, context, class_names=class_names)


def render(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
) -> SourceFragment:
    """Render the table DTO to authoring source."""
    from .._private.source import render as source

    return source(data, context, class_names=class_names)


__all__ = ["SourceFragment", "data_to_fragment", "render", "render_data"]
