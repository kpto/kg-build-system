"""DTOs for the asset language's blueprint part.

Mappings are tuples of pairs so a DTO is frozen and has a canonical document
order. The codec sorts pairs by key when it writes a JSON object.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from kg_build_system.distribution.languages.annotations.model.internal import AnnotationDTO

from ...public.options import AssetAuthority


@dataclass(frozen=True, slots=True)
class AssetLayoutDTO:
    """Optional descriptive layout metadata in the blueprint."""

    kind: str | None = None
    locator: str | None = None
    format: str | None = None
    selector: str | None = None
    partition_by: tuple[str, ...] = ()
    members: tuple[tuple[str, str], ...] = ()
    properties: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class AssetLicenseDTO:
    """The license an asset is distributed under."""

    identifier: str
    url: str | None = None
    attribution: str | None = None


@dataclass(frozen=True, slots=True)
class AssetGovernanceDTO:
    """License, owner and metadata in the blueprint."""

    license: AssetLicenseDTO | None = None
    owner: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class AssetSemanticsDTO:
    """What an asset represents and the limits of that representation."""

    subject: str
    coverage: str
    authority: AssetAuthority
    basis: str
    claims: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    title: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class AssetDTO:
    """One asset declaration in the blueprint."""

    name: str
    semantics: AssetSemanticsDTO
    website: str | None = None
    version: str | None = None
    layout: AssetLayoutDTO | None = None
    governance: AssetGovernanceDTO = field(default_factory=AssetGovernanceDTO)
    annotations: tuple[AnnotationDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class AssetPartDTO:
    """The complete asset part of a blueprint."""

    assets: tuple[AssetDTO, ...] = ()

    def __post_init__(self) -> None:
        names = tuple(item.name for item in self.assets)
        if len(names) != len(set(names)):
            raise ValueError("asset names must be unique")


__all__ = [
    "AssetDTO", "AssetGovernanceDTO", "AssetLayoutDTO", "AssetLicenseDTO",
    "AssetPartDTO", "AssetSemanticsDTO",
]
