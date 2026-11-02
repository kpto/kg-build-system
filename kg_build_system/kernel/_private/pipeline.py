"""Build pipeline helpers.

Private implementation behind ``Registry.build``. Not an import surface for
another package.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..public.build import BuildIR
from ..public.language import Language, Namespace


@dataclass(frozen=True, slots=True)
class PartContext:
    """Expose already-lowered parts to a language during lowering."""

    parts: Mapping[str, Any]

    def part(self, name: str) -> Any:
        return self.parts[name]


def compose(
    languages: Sequence[Language],
    namespace: Namespace,
    declarations: Mapping[str, Sequence[object]] | None = None,
) -> BuildIR:
    """Collect, lower and validate one part per language, then freeze them."""
    parts: dict[str, Any] = {}
    context = PartContext(parts)
    for language in languages:
        chosen = (
            declarations[language.name]
            if declarations is not None and language.name in declarations
            else language.collect(namespace)
        )
        value = language.lower(chosen, context)
        language.validate(value)
        parts[language.name] = value
    return BuildIR(parts)


__all__ = ["PartContext", "compose"]
