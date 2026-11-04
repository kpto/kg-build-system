"""Options an author assigns to an asset declaration.

The options describe what the source data means, where it is laid out and how it
is governed. They deliberately carry no content model, adapter or code-generation
request. Mappings are normalised to sorted, read-only mappings so the authoring
value compares and renders deterministically.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)
from kg_build_system.distribution.languages.annotations.service.internal import (
    annotation_tuple,
)


class AssetAuthority(StrEnum):
    """How an asset relates to the claims it supports.

    Example:
        ```python
        from kg_build_system import AssetAuthority

        assert AssetAuthority.PRIMARY.value == "primary"
        ```
    """

    PRIMARY = "primary"
    DERIVED = "derived"
    REFERENCE = "reference"
    INFERRED = "inferred"


@dataclass(frozen=True, slots=True)
class AssetLicense:
    """The license an asset is distributed under.

    Example:
        ```python
        from kg_build_system import AssetLicense

        license = AssetLicense("CC-BY-4.0", url="https://example.test/license")
        ```
    """

    identifier: str
    url: str | None = None
    attribution: str | None = None

    def __post_init__(self) -> None:
        from ...service._private.options import optional_text, required_text

        required_text(self.identifier, "an asset license identifier")
        optional_text(self.url, "an asset license URL")
        optional_text(self.attribution, "an asset license attribution")


@dataclass(frozen=True, slots=True)
class AssetGovernance:
    """License, owner and portable metadata for an asset.

    Example:
        ```python
        from kg_build_system import AssetGovernance, AssetLicense

        governance = AssetGovernance(
            license=AssetLicense("CC-BY-4.0"),
            owner="genomics-team",
            metadata={"review": "quarterly"},
        )
        ```
    """

    license: AssetLicense | None = None
    owner: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        from ...service._private.options import (
            frozen_mapping, optional_text,
        )

        if self.license is not None and not isinstance(self.license, AssetLicense):
            raise TypeError("asset governance license must be an AssetLicense")
        optional_text(self.owner, "an asset governance owner")
        object.__setattr__(
            self,
            "metadata",
            frozen_mapping(self.metadata, "asset governance metadata"),
        )


@dataclass(frozen=True, slots=True)
class AssetSemantics:
    """What an asset represents and the limits of that representation.

    Example:
        ```python
        from kg_build_system import AssetAuthority, AssetSemantics

        semantics = AssetSemantics(
            subject="gene-disease associations",
            coverage="all curated evidence",
            authority=AssetAuthority.PRIMARY,
            basis="Open Targets Platform release",
        )
        ```
    """

    subject: str
    coverage: str
    authority: AssetAuthority
    basis: str
    claims: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    title: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        from ...service._private.options import (
            optional_text, required_text, text_tuple,
        )

        required_text(self.subject, "an asset semantics subject")
        required_text(self.coverage, "an asset semantics coverage")
        required_text(self.basis, "an asset semantics basis")
        if not isinstance(self.authority, AssetAuthority):
            raise TypeError(
                "asset semantics authority must be an AssetAuthority"
            )
        object.__setattr__(
            self, "claims", text_tuple(self.claims, "asset semantics claims"),
        )
        object.__setattr__(
            self,
            "limitations",
            text_tuple(self.limitations, "asset semantics limitations"),
        )
        optional_text(self.title, "an asset semantics title")
        optional_text(self.description, "an asset semantics description")


@dataclass(frozen=True, slots=True)
class AssetLayout:
    """Optional descriptive layout metadata for an asset.

    Layout is general: it names open format and locator strings, an optional
    selector, semantic partition keys and optional member paths. It is not a
    catalog, schema or storage-style model.

    Example:
        ```python
        from kg_build_system import AssetLayout

        layout = AssetLayout(
            kind="parquet",
            locator="s3://example/targets",
            format="parquet",
            selector="{table}.parquet",
            members={"targets": "targets.parquet"},
        )
        ```
    """

    kind: str | None = None
    locator: str | None = None
    format: str | None = None
    selector: str | None = None
    partition_by: tuple[str, ...] = ()
    members: Mapping[str, str] = field(default_factory=dict)
    properties: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        from ...service._private.options import (
            frozen_mapping, optional_text, text_tuple,
        )

        optional_text(self.kind, "an asset layout kind")
        optional_text(self.locator, "an asset layout locator")
        optional_text(self.format, "an asset layout format")
        optional_text(self.selector, "an asset layout selector")
        object.__setattr__(
            self,
            "partition_by",
            text_tuple(self.partition_by, "asset layout partition keys"),
        )
        object.__setattr__(
            self,
            "members",
            frozen_mapping(self.members, "asset layout members"),
        )
        object.__setattr__(
            self,
            "properties",
            frozen_mapping(self.properties, "asset layout properties"),
        )


@dataclass(frozen=True, slots=True)
class AssetOptions:
    """Everything an author states about one asset.

    Example:
        ```python
        from kg_build_system import (
            Asset, AssetAuthority, AssetLicense, AssetOptions, AssetSemantics,
            AssetGovernance,
        )

        class OpenTargets(Asset):
            options = AssetOptions(
                semantics=AssetSemantics(
                    subject="gene-disease associations",
                    coverage="all curated evidence",
                    authority=AssetAuthority.PRIMARY,
                    basis="Open Targets Platform release",
                ),
                governance=AssetGovernance(
                    license=AssetLicense("CC-BY-4.0"),
                ),
            )
        ```
    """

    semantics: AssetSemantics
    name: str | None = None
    website: str | None = None
    version: str | None = None
    layout: AssetLayout | None = None
    governance: AssetGovernance = field(default_factory=AssetGovernance)
    annotations: tuple[Annotation, ...] = ()

    def __post_init__(self) -> None:
        from ...service._private.options import optional_text

        if not isinstance(self.semantics, AssetSemantics):
            raise TypeError("asset options semantics must be AssetSemantics")
        if self.layout is not None and not isinstance(self.layout, AssetLayout):
            raise TypeError("asset options layout must be an AssetLayout")
        if not isinstance(self.governance, AssetGovernance):
            raise TypeError("asset options governance must be AssetGovernance")
        optional_text(self.name, "an asset name")
        optional_text(self.website, "an asset website")
        optional_text(self.version, "an asset version")
        object.__setattr__(
            self, "annotations", annotation_tuple(self.annotations),
        )


__all__ = [
    "AssetAuthority", "AssetGovernance", "AssetLayout", "AssetLicense",
    "AssetOptions", "AssetSemantics",
]
