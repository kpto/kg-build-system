"""Transcribe asset declarations into the asset blueprint DTO."""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.languages.annotations.service.internal import (
    annotation_dtos,
)

from ...model.internal.dto.asset_dto import (
    AssetDTO,
    AssetGovernanceDTO,
    AssetLayoutDTO,
    AssetLicenseDTO,
    AssetPartDTO,
    AssetSemanticsDTO,
)
from ...model.public.declarations import Asset
from ...model.public.options import (
    AssetGovernance,
    AssetLayout,
    AssetLicense,
    AssetSemantics,
)


def _pairs(value: Any) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(dict(value).items()))


def _license_dto(value: AssetLicense) -> AssetLicenseDTO:
    return AssetLicenseDTO(
        identifier=value.identifier,
        url=value.url,
        attribution=value.attribution,
    )


def _governance_dto(value: AssetGovernance) -> AssetGovernanceDTO:
    return AssetGovernanceDTO(
        license=None if value.license is None else _license_dto(value.license),
        owner=value.owner,
        metadata=_pairs(value.metadata),
    )


def _semantics_dto(value: AssetSemantics) -> AssetSemanticsDTO:
    return AssetSemanticsDTO(
        subject=value.subject,
        coverage=value.coverage,
        authority=value.authority,
        basis=value.basis,
        claims=tuple(value.claims),
        limitations=tuple(value.limitations),
        title=value.title,
        description=value.description,
    )


def _layout_dto(value: AssetLayout) -> AssetLayoutDTO:
    return AssetLayoutDTO(
        kind=value.kind,
        locator=value.locator,
        format=value.format,
        selector=value.selector,
        partition_by=tuple(value.partition_by),
        members=_pairs(value.members),
        properties=_pairs(value.properties),
    )


def asset_to_dto(value: type[Asset]) -> AssetDTO:
    """Turn one prepared asset declaration into its blueprint DTO."""
    options = value._asset_options
    return AssetDTO(
        name=value._asset_name,
        website=options.website,
        version=options.version,
        layout=None if options.layout is None else _layout_dto(options.layout),
        semantics=_semantics_dto(options.semantics),
        governance=_governance_dto(options.governance),
        annotations=annotation_dtos(options.annotations),
    )


def transcribe_asset_part(values: tuple[type[Asset], ...]) -> AssetPartDTO:
    """Turn a batch of asset declarations into the asset blueprint DTO."""
    assets = tuple(asset_to_dto(value) for value in values)
    return AssetPartDTO(assets=tuple(sorted(assets, key=lambda item: item.name)))


__all__ = ["asset_to_dto", "transcribe_asset_part"]
