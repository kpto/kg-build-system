"""Credential resolution used by a workflow execution."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ....model.public.services import CredentialResolver


@dataclass(frozen=True, slots=True)
class MappingCredentialResolver:
    """Credential resolution backed by an in-memory mapping."""

    credentials: Mapping[str, str]

    def resolve(self, reference: str) -> str:
        """Resolve one credential reference."""
        return self.credentials[reference]


__all__ = ["CredentialResolver", "MappingCredentialResolver"]
