"""Render the data language DTO back to authoring source.

The renderer lives in the package's private zone; each name here is a thin
delegation kept for the internal service path.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from kg_build_system.distribution.languages.expressions.model.internal.dto.operation_dto import (
    OperationDTO,
)
from kg_build_system.kernel import SourceFragment

from ...model.internal.dto.blueprint_dto import DataPartDTO


def render_data(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
    operations: Iterable[OperationDTO] = (),
) -> SourceFragment:
    """Render a data DTO as authoring source.

    ``operations`` is the expression composition the data part refers to; it
    supplies each operation's declared row effect.

    Example:
        ```python
        from kg_build_system.distribution.languages.data.model.internal.dto import (
            DataPartDTO,
        )
        from kg_build_system.distribution.languages.data.service.internal.source import (
            render_data,
        )

        fragment = render_data(DataPartDTO((), (), ()))
        assert fragment.body == ""
        ```
    """
    from .._private.source import render_data as render

    return render(
        data, context, class_names=class_names, operations=operations,
    )


def data_to_fragment(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
    operations: Iterable[OperationDTO] = (),
) -> SourceFragment:
    """Alias of :func:`render_data` named for the DTO-to-fragment direction."""
    from .._private.source import data_to_fragment as fragment

    return fragment(
        data, context, class_names=class_names, operations=operations,
    )


def render(
    data: DataPartDTO,
    context: Any = None,
    *,
    class_names: Mapping[str, str] | None = None,
    operations: Iterable[OperationDTO] = (),
) -> SourceFragment:
    """Render the data DTO to authoring source."""
    from .._private.source import render as source

    return source(
        data, context, class_names=class_names, operations=operations,
    )


__all__ = ["SourceFragment", "data_to_fragment", "render", "render_data"]
