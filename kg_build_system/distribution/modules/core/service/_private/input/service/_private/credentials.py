"""Credential references carried by a physical source."""
from __future__ import annotations

from kg_build_system.distribution.languages.data.model.internal import SourceDTO


def credential_reference(source: SourceDTO) -> str | None:
    """The credential reference a source declares, if any."""
    return source.credential_reference


__all__ = ["credential_reference"]
