"""Build pipeline helpers.

Private implementation behind ``Registry.build``. Not an import surface for
another package.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ...model.public.build import Build


@dataclass(frozen=True, slots=True)
class PartContext:
    """Expose already-transcribed parts to a language during transcription."""

    parts: Mapping[str, Any]

    def part(self, name: str) -> Any:
        return self.parts[name]


def compose(
    languages: Sequence[Any],
    namespace: Any,
    declarations: Mapping[str, Sequence[object]] | None = None,
) -> Build:
    """Collect, transcribe and validate one part per language, then freeze them."""
    parts: dict[str, Any] = {}
    context = PartContext(parts)
    for language in languages:
        chosen = (
            declarations[language.name]
            if declarations is not None and language.name in declarations
            else language.collect(namespace)
        )
        value = language.transcribe(chosen, context)
        language.validate(value)
        parts[language.name] = value
    return Build(parts)


__all__ = ["PartContext", "compose"]
