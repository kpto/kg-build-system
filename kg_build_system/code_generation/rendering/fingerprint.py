"""The request fingerprint: authoring identity, not observed data."""
from __future__ import annotations

from hashlib import sha256
import json

from ..models import DiscoveredGeneration
from .constants import FORMAT_VERSION


def generation_fingerprint(request: DiscoveredGeneration, provider_version: str) -> str:
    """The authoring identity of one request: what it declares, not what it observes.

    The fingerprint covers the request and its provider only. Data sources are
    references the provider observes on demand, never tracked inputs, so their
    bytes — or any digest of them — deliberately do not enter this value.
    """
    normalized = {
        "configuration": request.request.configuration,
        "config_type": f"{request.request.config_module}.{request.request.config_qualname}",
        "format_version": FORMAT_VERSION,
        "provider": f"{request.request.provider_module}.{request.request.provider_qualname}",
        "provider_version": provider_version,
        "request_id": request.location.request_id,
        "request_source_package": request.location.source_package,
    }
    return sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


__all__ = ["generation_fingerprint"]
