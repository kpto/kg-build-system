"""Framework-internal generation discovery and ownership models."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..public.requests import GenerationRequest


@dataclass(frozen=True, slots=True)
class GenerationLocation:
    """Where one asset contract was declared and the identity it received.

    ``project_root`` and ``source_path`` locate the author-owned asset module;
    ``line`` and ``column`` point at the ``@asset_contract`` decorator.
    ``request_id`` is the asset name, and ``source_package`` is the package
    containing the asset module.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system.generation.code_generation.model.internal import GenerationLocation

        location = GenerationLocation(
            Path("."), Path("contracts/assets.py"), 4, 1,
            "people", "contracts",
        )
        ```
    """

    project_root: Path
    source_path: Path
    line: int
    column: int
    request_id: str
    source_package: str


@dataclass(frozen=True, slots=True)
class DiscoveredGeneration:
    """One request, its location, and the product it owns.

    ``product_path`` is ``<package as a path>/<asset name>`` below the project
    root; when the root is itself a package, its leading package segment is not
    repeated on disk. ``package_import`` is the full product import name. The
    rule is fixed so an asset's package is readable from its declaration alone.

    Example:
        ```python
        from kg_build_system.generation.code_generation import discover

        request = discover(".")[0]
        request.product_path, request.package_import
        ```
    """

    request: GenerationRequest
    location: GenerationLocation
    product_path: Path
    package_import: str


@dataclass(frozen=True, slots=True)
class GenerationManifest:
    """The ownership record stored in a product's ``.kbs-generation.json``.

    The request fingerprint covers the declaration, configuration, provider
    identity and format version; ``source_digest`` is provider provenance only.
    ``owned_files`` and ``owned_directories`` are normalized relative POSIX
    paths.

    Example:
        ```python
        from kg_build_system.generation.code_generation import discover

        product = discover(".")[0].product_path
        manifest_path = product / ".kbs-generation.json"
        ```
    """

    format_version: str
    request_id: str
    request_source_package: str
    provider_import: str
    provider_qualname: str
    provider_version: str
    request_fingerprint: str
    source_digest: str | None
    owned_files: tuple[str, ...]
    owned_directories: tuple[str, ...]
    owned_file_hashes: dict[str, str] = field(default_factory=dict)


__all__ = ["DiscoveredGeneration", "GenerationLocation", "GenerationManifest"]
