"""The exact-duplicate removal module's configuration."""
from __future__ import annotations

from dataclasses import dataclass

from ..registration import ModuleRegistrationConfiguration


@dataclass(frozen=True)
class DeduplicationConfiguration(ModuleRegistrationConfiguration):
    """The operator has no configurable behaviour."""


__all__ = ["DeduplicationConfiguration"]
