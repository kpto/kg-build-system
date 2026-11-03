"""Ownership-manifest codec kept separate from the engine's desired-state logic."""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from ...model.internal.models import GenerationManifest
from ...model.public.errors import GenerationError

MANIFEST = ".kbs-generation.json"


def encode_manifest(manifest: GenerationManifest) -> dict[str, object]:
    return asdict(manifest)


def decode_manifest(value: object) -> GenerationManifest:
    if not isinstance(value, dict):
        raise ValueError("a generation manifest must be a JSON object")
    return GenerationManifest(
        format_version=str(value["format_version"]),
        request_id=str(value["request_id"]),
        request_source_package=str(value["request_source_package"]),
        provider_import=str(value["provider_import"]),
        provider_qualname=str(value["provider_qualname"]),
        provider_version=str(value["provider_version"]),
        request_fingerprint=str(value["request_fingerprint"]),
        source_digest=None if value.get("source_digest") is None else str(value["source_digest"]),
        owned_files=tuple(str(item) for item in value["owned_files"]),
        owned_directories=tuple(str(item) for item in value["owned_directories"]),
        owned_file_hashes=_string_map(value.get("owned_file_hashes", {})),
    )


def _string_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("owned_file_hashes must be an object")
    return {str(key): str(item) for key, item in value.items()}


def manifest_text(manifest: GenerationManifest) -> str:
    return json.dumps(encode_manifest(manifest), indent=2, sort_keys=True) + "\n"


def load_manifest(path: Path) -> GenerationManifest:
    try:
        return decode_manifest(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise GenerationError(f"invalid generation manifest {path}: {error}") from error


__all__ = ["MANIFEST", "decode_manifest", "encode_manifest", "load_manifest", "manifest_text"]
