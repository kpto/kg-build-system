"""Source-binding interface for the table language."""
from __future__ import annotations

from ...model.public.sources import (
    BoundSource, DataSourceConfig, SourceBindingOptions,
)


def bind_source(
    *,
    target: type,
    config: DataSourceConfig,
    options: SourceBindingOptions | None = None,
) -> BoundSource:
    """Bind one final table or table group to its physical source."""
    from .._private.sources import make_bound_source

    return make_bound_source(target=target, config=config, options=options)


__all__ = ["bind_source"]
