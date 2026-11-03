"""Registry interface: ordering and composition over language protocols.

The implementation lives in ``service._private``; these functions delegate with
function-local imports so importing this module does not load a private engine.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ...model.public.build import Build


def order_languages(languages: Sequence[Any]) -> tuple[Any, ...]:
    """Validate names and dependencies, then return a dependency order."""
    from .._private.ordering import order_languages as implementation

    return implementation(languages)


def compose(
    languages: Sequence[Any],
    namespace: Any,
    declarations: Mapping[str, Sequence[object]] | None = None,
) -> Build:
    """Collect, transcribe and validate one part per language, then freeze them."""
    from .._private.pipeline import compose as implementation

    return implementation(languages, namespace, declarations)


__all__ = ["compose", "order_languages"]
