"""Language ordering and validation.

Private implementation behind the toolchain and the temporary registry. Not an
import surface for another package.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def order_languages(languages: Sequence[Any]) -> tuple[Any, ...]:
    """Validate names and dependencies, then return a dependency order.

    Duplicate names, unknown dependencies and cycles raise ``ValueError``.
    """
    names = tuple(language.name for language in languages)
    if len(names) != len(set(names)):
        raise ValueError("language names must be unique")
    for language in languages:
        unknown = set(language.requires) - set(names)
        if unknown:
            raise ValueError(
                f"language {language.name!r} requires unknown {sorted(unknown)}"
            )

    by_name = {language.name: language for language in languages}
    result: list[Any] = []
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(language: Any) -> None:
        if language.name in done:
            return
        if language.name in visiting:
            raise ValueError(f"language cycle at {language.name!r}")
        visiting.add(language.name)
        for dependency in language.requires:
            visit(by_name[dependency])
        visiting.remove(language.name)
        done.add(language.name)
        result.append(language)

    for language in languages:
        visit(language)
    return tuple(result)


__all__ = ["order_languages"]
