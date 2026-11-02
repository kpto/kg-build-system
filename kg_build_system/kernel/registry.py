"""Language ordering and registry validation."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .build import BuildIR
from .language import Language, LanguageContext, Namespace


@dataclass(frozen=True, slots=True)
class Registry:
    languages: Sequence[Language]

    def __post_init__(self) -> None:
        names = tuple(language.name for language in self.languages)
        if len(names) != len(set(names)):
            raise ValueError("language names must be unique")
        for language in self.languages:
            unknown = set(language.requires) - set(names)
            if unknown:
                raise ValueError(
                    f"language {language.name!r} requires unknown "
                    f"{sorted(unknown)}"
                )
        object.__setattr__(self, "languages", tuple(self._ordered()))

    def _ordered(self) -> Sequence[Language]:
        by_name = {language.name: language for language in self.languages}
        result: list[Language] = []
        visiting: set[str] = set()
        done: set[str] = set()

        def visit(language: Language) -> None:
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

        for language in self.languages:
            visit(language)
        return tuple(result)

    def build(
        self,
        namespace: Namespace,
        declarations: Mapping[str, Sequence[object]] | None = None,
    ) -> BuildIR:
        parts: dict[str, Any] = {}
        context = _Context(parts)
        for language in self.languages:
            chosen = (
                declarations[language.name]
                if declarations is not None and language.name in declarations
                else language.collect(namespace)
            )
            value = language.lower(chosen, context)
            language.validate(value)
            parts[language.name] = value
        return BuildIR(parts)


@dataclass(frozen=True, slots=True)
class _Context:
    parts: Mapping[str, Any]

    def part(self, name: str) -> Any:
        return self.parts[name]


__all__ = ["Registry"]
