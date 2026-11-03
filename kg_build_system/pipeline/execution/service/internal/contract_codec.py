"""Framework-internal interface for the contract document codec.

The codec implementation lives in ``service._private.contract_codec``.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kg_build_system.pipeline.contract.model.public import WorkflowContractDTO


def contract_to_document(contract: WorkflowContractDTO) -> dict[str, Any]:
    """Write a contract as its canonical JSON-compatible document."""
    from .._private import contract_codec

    return contract_codec.contract_to_document(contract)


def contract_from_document(document: Mapping[str, Any]) -> WorkflowContractDTO:
    """Read a contract from its canonical JSON-compatible document."""
    from .._private import contract_codec

    return contract_codec.contract_from_document(document)


__all__ = ["contract_from_document", "contract_to_document"]
