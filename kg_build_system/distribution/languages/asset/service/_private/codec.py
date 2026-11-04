"""Canonical JSON codec for the asset blueprint DTO."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from kg_build_system.distribution.languages.annotations.service.internal import (
    annotation_from_document,
    annotation_to_document,
)

from ...model.internal.dto.asset_dto import (
    AssetDTO,
    AssetGovernanceDTO,
    AssetLayoutDTO,
    AssetLicenseDTO,
    AssetPartDTO,
    AssetSemanticsDTO,
)
from ...model.public.options import AssetAuthority


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _array(value: Any, context: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{context} must be an array")
    return value


def _text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"{key!r} must be a non-empty string")
    return result


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    result = value.get(key)
    if result is not None and (not isinstance(result, str) or not result):
        raise ValueError(f"{key!r} must be null or a non-empty string")
    return result


def _strings(value: Mapping[str, Any], key: str) -> tuple[str, ...]:
    result = tuple(_array(value.get(key, ()), key))
    if any(not isinstance(item, str) or not item for item in result):
        raise ValueError(f"{key!r} must contain non-empty strings")
    return result


def _pairs(value: Mapping[str, Any], key: str) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for name, item in _object(value.get(key, {}), key).items():
        if not isinstance(name, str) or not name:
            raise ValueError(f"{key!r} keys must be non-empty strings")
        if not isinstance(item, str) or not item:
            raise ValueError(f"{key!r} values must be non-empty strings")
        result.append((name, item))
    return tuple(sorted(result))


def _encode_pairs(value: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return {name: item for name, item in sorted(value)}


def _license_to_document(value: AssetLicenseDTO) -> dict[str, Any]:
    return {
        "identifier": value.identifier,
        "url": value.url,
        "attribution": value.attribution,
    }


def _license_from_document(value: Mapping[str, Any]) -> AssetLicenseDTO:
    return AssetLicenseDTO(
        identifier=_text(value, "identifier"),
        url=_optional_text(value, "url"),
        attribution=_optional_text(value, "attribution"),
    )


def _governance_to_document(value: AssetGovernanceDTO) -> dict[str, Any]:
    return {
        "license": (
            None if value.license is None else _license_to_document(value.license)
        ),
        "owner": value.owner,
        "metadata": _encode_pairs(value.metadata),
    }


def _governance_from_document(value: Mapping[str, Any]) -> AssetGovernanceDTO:
    license = value.get("license")
    return AssetGovernanceDTO(
        license=(
            None if license is None
            else _license_from_document(_object(license, "license"))
        ),
        owner=_optional_text(value, "owner"),
        metadata=_pairs(value, "metadata"),
    )


def _layout_to_document(value: AssetLayoutDTO) -> dict[str, Any]:
    return {
        "kind": value.kind,
        "locator": value.locator,
        "format": value.format,
        "selector": value.selector,
        "partition_by": list(value.partition_by),
        "members": _encode_pairs(value.members),
        "properties": _encode_pairs(value.properties),
    }


def _layout_from_document(value: Mapping[str, Any]) -> AssetLayoutDTO:
    return AssetLayoutDTO(
        kind=_optional_text(value, "kind"),
        locator=_optional_text(value, "locator"),
        format=_optional_text(value, "format"),
        selector=_optional_text(value, "selector"),
        partition_by=_strings(value, "partition_by"),
        members=_pairs(value, "members"),
        properties=_pairs(value, "properties"),
    )


def _semantics_to_document(value: AssetSemanticsDTO) -> dict[str, Any]:
    return {
        "subject": value.subject,
        "coverage": value.coverage,
        "authority": str(value.authority),
        "basis": value.basis,
        "claims": list(value.claims),
        "limitations": list(value.limitations),
        "title": value.title,
        "description": value.description,
    }


def _semantics_from_document(value: Mapping[str, Any]) -> AssetSemanticsDTO:
    try:
        authority = AssetAuthority(_text(value, "authority"))
    except ValueError:
        raise ValueError(
            f"unknown asset authority {value.get('authority')!r}"
        ) from None
    return AssetSemanticsDTO(
        subject=_text(value, "subject"),
        coverage=_text(value, "coverage"),
        authority=authority,
        basis=_text(value, "basis"),
        claims=_strings(value, "claims"),
        limitations=_strings(value, "limitations"),
        title=_optional_text(value, "title"),
        description=_optional_text(value, "description"),
    )


def _asset_to_document(value: AssetDTO) -> dict[str, Any]:
    return {
        "name": value.name,
        "website": value.website,
        "version": value.version,
        "layout": (
            None if value.layout is None
            else _layout_to_document(value.layout)
        ),
        "semantics": _semantics_to_document(value.semantics),
        "governance": _governance_to_document(value.governance),
        "annotations": [
            annotation_to_document(item) for item in value.annotations
        ],
    }


def _asset_from_document(value: Mapping[str, Any]) -> AssetDTO:
    layout = value.get("layout")
    return AssetDTO(
        name=_text(value, "name"),
        website=_optional_text(value, "website"),
        version=_optional_text(value, "version"),
        layout=(
            None if layout is None
            else _layout_from_document(_object(layout, "layout"))
        ),
        semantics=_semantics_from_document(
            _object(value.get("semantics"), "semantics")
        ),
        governance=_governance_from_document(
            _object(value.get("governance", {}), "governance")
        ),
        annotations=tuple(
            annotation_from_document(_object(item, "annotation"))
            for item in _array(value.get("annotations", ()), "annotations")
        ),
    )


def assets_to_document(part: AssetPartDTO) -> list[dict[str, Any]]:
    """Encode the asset part as an array of JSON-compatible objects.

    Example:
        ```python
        from kg_build_system.distribution.languages.asset.model.internal import (
            AssetPartDTO,
        )
        from kg_build_system.distribution.languages.asset.service.internal import (
            assets_to_document,
        )

        assert assets_to_document(AssetPartDTO()) == []
        ```
    """
    return [_asset_to_document(item) for item in part.assets]


def assets_from_document(value: Any) -> AssetPartDTO:
    """Rebuild the asset part from its JSON-compatible array.

    Example:
        ```python
        from kg_build_system.distribution.languages.asset.service.internal import (
            assets_from_document,
        )

        part = assets_from_document([])
        assert part.assets == ()
        ```
    """
    document = value
    if isinstance(document, Mapping):
        document = document.get("assets", ())
    return AssetPartDTO(
        assets=tuple(
            _asset_from_document(_object(item, "asset"))
            for item in _array(document, "assets")
        ),
    )


__all__ = ["assets_from_document", "assets_to_document"]
