"""Core-module handling for runtime source credential options."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, JsonValue

from ...workflow.services import ExecutionServices


class CoreSourceCredentialOptions(BaseModel):
    """Secret runtime options understood only by the core source reader."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    filesystem_options: dict[str, JsonValue]


def configure_source_credentials(
    services: ExecutionServices,
    *,
    location: str,
    credential_reference: str,
) -> None:
    """Resolve and apply core-owned filesystem options for one source."""
    resolved = services.credentials.resolve(credential_reference)
    options = CoreSourceCredentialOptions.model_validate_json(resolved)
    protocol = urlsplit(location).scheme
    if not protocol:
        raise ValueError("credentialed source locations require a URI scheme")

    import fsspec

    filesystem = fsspec.filesystem(
        protocol,
        **_thaw_json(options.filesystem_options),
    )
    services.relations.register_filesystem(filesystem)


def _thaw_json(value: JsonValue) -> Any:
    if isinstance(value, dict):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_thaw_json(item) for item in value]
    return value


__all__ = ["CoreSourceCredentialOptions", "configure_source_credentials"]
