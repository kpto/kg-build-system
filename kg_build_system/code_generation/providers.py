"""Provider registration and loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Protocol

from .models import GeneratedModule, GenerationRequest


@dataclass(frozen=True, slots=True)
class ProviderContext:
    project_root: Path
    declaration_path: Path
    request: GenerationRequest

    def resolve_path(self, value: str) -> Path:
        """Resolve a provider-owned project path without assigning it semantics."""
        path = (self.declaration_path.parent / value).resolve()
        try:
            path.relative_to(self.project_root)
        except ValueError as error:
            raise ValueError(f"code-generation path is outside the project: {path}") from error
        return path


class CodeGenerationProvider(Protocol):
    ID: ClassVar[str]
    VERSION: ClassVar[str]

    def dependencies(self, context: ProviderContext) -> tuple[Path, ...]: ...

    def generate(self, context: ProviderContext, *, generated_name: str) -> GeneratedModule: ...


_PROVIDERS: dict[str, CodeGenerationProvider] = {}


def register_provider(provider: CodeGenerationProvider, *, replace: bool = False) -> None:
    if not provider.ID or not provider.VERSION:
        raise ValueError("providers require non-empty ID and VERSION values")
    if provider.ID in _PROVIDERS and not replace:
        raise ValueError(f"code-generation provider {provider.ID!r} is already registered")
    _PROVIDERS[provider.ID] = provider


def get_provider(provider_id: str) -> CodeGenerationProvider:
    try:
        return _PROVIDERS[provider_id]
    except KeyError as error:
        raise ValueError(f"unknown code-generation provider {provider_id!r}") from error
