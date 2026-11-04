"""Render the asset blueprint DTO as authoring source."""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.service.internal.rendering import (
    class_name,
    render_annotation,
    render_static_value,
)
from kg_build_system.kernel import SourceFragment

from ...model.internal.dto.asset_dto import (
    AssetDTO,
    AssetGovernanceDTO,
    AssetLayoutDTO,
    AssetLicenseDTO,
    AssetPartDTO,
    AssetSemanticsDTO,
)
from ...model.public.options import AssetAuthority


def _strings_field(name: str, values: tuple[str, ...], indent: str) -> list[str]:
    if not values:
        return []
    return [
        f"{indent}{name}=(",
        *(f"{indent}    {item!r}," for item in values),
        f"{indent}),",
    ]


def _pairs_field(
    name: str, values: tuple[tuple[str, str], ...], indent: str,
) -> list[str]:
    if not values:
        return []
    return [
        f"{indent}{name}={render_static_value(dict(values))},",
    ]


def _license_lines(
    value: AssetLicenseDTO, imports: set[str], indent: str,
) -> list[str]:
    imports.add("from kg_build_system import AssetLicense")
    lines = [f"{indent}license=AssetLicense("]
    lines.append(f"{indent}    identifier={value.identifier!r},")
    if value.url is not None:
        lines.append(f"{indent}    url={value.url!r},")
    if value.attribution is not None:
        lines.append(f"{indent}    attribution={value.attribution!r},")
    lines.append(f"{indent}),")
    return lines


def _governance_is_default(value: AssetGovernanceDTO) -> bool:
    return value.license is None and value.owner is None and not value.metadata


def _governance_lines(
    value: AssetGovernanceDTO, imports: set[str], indent: str,
) -> list[str]:
    imports.add("from kg_build_system import AssetGovernance")
    lines = [f"{indent}governance=AssetGovernance("]
    if value.license is not None:
        lines.extend(
            _license_lines(value.license, imports, f"{indent}    ")
        )
    if value.owner is not None:
        lines.append(f"{indent}    owner={value.owner!r},")
    lines.extend(_pairs_field("metadata", value.metadata, f"{indent}    "))
    lines.append(f"{indent}),")
    return lines


def _layout_lines(
    value: AssetLayoutDTO, imports: set[str], indent: str,
) -> list[str]:
    imports.add("from kg_build_system import AssetLayout")
    lines = [f"{indent}layout=AssetLayout("]
    for name, item in (
        ("kind", value.kind),
        ("locator", value.locator),
        ("format", value.format),
        ("selector", value.selector),
    ):
        if item is not None:
            lines.append(f"{indent}    {name}={item!r},")
    lines.extend(_strings_field("partition_by", value.partition_by, f"{indent}    "))
    lines.extend(_pairs_field("members", value.members, f"{indent}    "))
    lines.extend(_pairs_field("properties", value.properties, f"{indent}    "))
    lines.append(f"{indent}),")
    return lines


def _semantics_lines(
    value: AssetSemanticsDTO, imports: set[str], indent: str,
) -> list[str]:
    imports.add("from kg_build_system import AssetAuthority")
    imports.add("from kg_build_system import AssetSemantics")
    authority = (
        value.authority
        if isinstance(value.authority, AssetAuthority)
        else AssetAuthority(value.authority)
    )
    lines = [f"{indent}semantics=AssetSemantics("]
    lines.append(f"{indent}    subject={value.subject!r},")
    lines.append(f"{indent}    coverage={value.coverage!r},")
    lines.append(f"{indent}    authority=AssetAuthority.{authority.name},")
    lines.append(f"{indent}    basis={value.basis!r},")
    lines.extend(_strings_field("claims", value.claims, f"{indent}    "))
    lines.extend(_strings_field("limitations", value.limitations, f"{indent}    "))
    if value.title is not None:
        lines.append(f"{indent}    title={value.title!r},")
    if value.description is not None:
        lines.append(f"{indent}    description={value.description!r},")
    lines.append(f"{indent}),")
    return lines


def _options_lines(value: AssetDTO, imports: set[str]) -> list[str]:
    imports.add("from kg_build_system import Asset")
    imports.add("from kg_build_system import AssetOptions")
    indent = "        "
    lines = ["    options = AssetOptions("]
    lines.extend(_semantics_lines(value.semantics, imports, indent))
    lines.append(f"{indent}name={value.name!r},")
    if value.website is not None:
        lines.append(f"{indent}website={value.website!r},")
    if value.version is not None:
        lines.append(f"{indent}version={value.version!r},")
    if value.layout is not None:
        lines.extend(_layout_lines(value.layout, imports, indent))
    if not _governance_is_default(value.governance):
        lines.extend(_governance_lines(value.governance, imports, indent))
    if value.annotations:
        lines.append(f"{indent}annotations=(")
        lines.extend(
            f"{indent}    {render_annotation(item, imports)},"
            for item in value.annotations
        )
        lines.append(f"{indent}),")
    lines.append("    )")
    return lines


def _class_source(value: AssetDTO, imports: set[str]) -> str:
    own_name = class_name(value.name, "Asset")
    lines = [f"class {own_name}(Asset):"]
    lines.extend(_options_lines(value, imports))
    return "\n".join(lines)


def render_asset_source(
    part: AssetPartDTO | AssetDTO, context: Any = None,
) -> SourceFragment:
    """Render an asset DTO as deterministic authoring source.

    Example:
        ```python
        from kg_build_system.distribution.languages.asset.model.internal import (
            AssetPartDTO,
        )
        from kg_build_system.distribution.languages.asset.service.internal import (
            render_asset_source,
        )

        assert render_asset_source(AssetPartDTO()).body == ""
        ```
    """
    del context
    if isinstance(part, AssetDTO):
        part = AssetPartDTO((part,))
    imports: set[str] = set()
    chunks = [
        _class_source(item, imports)
        for item in sorted(part.assets, key=lambda asset: asset.name)
    ]
    body = "\n\n\n".join(chunks)
    if body:
        body += "\n"
    return SourceFragment(
        kind="declaration", body=body, imports=tuple(sorted(imports)),
    )


__all__ = ["render_asset_source"]
