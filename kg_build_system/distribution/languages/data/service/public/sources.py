"""Authoring function wrapper for physical source binding."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..internal.sources import bind_source as bind_source_impl

if TYPE_CHECKING:
    from ...model.public.sources import (
        BoundSource, DataSourceConfig, SourceBindingOptions,
    )


def bind_source(
    *,
    target: type,
    config: "DataSourceConfig",
    options: "SourceBindingOptions | None" = None,
) -> "BoundSource":
    """Bind one final table or table group to its physical source.

    The target must be a final ``Table`` or ``TableGroup``; a projection is not
    a source target. A group binding carries the ``layout`` that resolves each
    member table.

    Example:
        ```python
        from kg_build_system import DataSourceConfig, InputFormat, bind_source

        source = bind_source(
            target=SiteTable,
            config=DataSourceConfig(
                location="data/sites.json", format=InputFormat.JSON,
            ),
        )
        ```
    """
    return bind_source_impl(target=target, config=config, options=options)


__all__ = ["bind_source"]
