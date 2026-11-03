"""Framework-internal generation discovery and ownership models."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..public.requests import GenerationRequest


@dataclass(frozen=True, slots=True)
class GenerationLocation:
    """Where one request was declared and the identity it received.

    ``project_root`` and ``source_path`` locate the author-owned ``__init__.py``;
    ``line`` and ``column`` point at the assignment. ``request_id`` is the
    assignment name, and ``source_package`` is the package containing it.

    Example:
        ```python
        from pathlib import Path

        from kg_build_system.generation.code_generation.model.internal import GenerationLocation

        location = GenerationLocation(
            Path("."), Path("contracts/__init__.py"), 4, 1,
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

    ``product_path`` is the sibling directory of the author-owned
    ``__init__.py``; ``package_import`` is the import name of the generated
    package.

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
