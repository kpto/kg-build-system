"""Output, working and credential storage."""
from __future__ import annotations

from .credentials import CredentialResolver, MappingCredentialResolver
from .working import (
    LocalTemporaryStorage,
    LocalWorkingStorage,
    WorkingStorage,
)

__all__ = [
    "CredentialResolver",
    "LocalTemporaryStorage",
    "LocalWorkingStorage",
    "MappingCredentialResolver",
    "WorkingStorage",
]
