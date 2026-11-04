"""Author-facing edit-time generation requests.

A graph author attaches ``@asset_contract(AssetContractOptions(...))`` to an
``Asset`` subclass and runs ``kbs generate`` or ``generate``/``watch`` here. The
provider extension contract is
:mod:`kg_build_system.generation.code_generation.model.internal`; the
generated-declaration render model is
:mod:`kg_build_system.generation.code_generation.model._private.generated`.
"""
from __future__ import annotations

from .model.public import (
    AssetContractOptions, FileChange, FileChangeKind, GenerationError,
    GenerationRequest, GenerationResult, GenerationStatus,
)
from .service.public import (
    GenerationSession, asset_contract, discover, discover_file, generate, watch,
)

__all__ = [
    "AssetContractOptions",
    "FileChange",
    "FileChangeKind",
    "GenerationError",
    "GenerationRequest",
    "GenerationResult",
    "GenerationSession",
    "GenerationStatus",
    "asset_contract",
    "discover",
    "discover_file",
    "generate",
    "watch",
]
