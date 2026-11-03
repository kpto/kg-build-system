"""Framework-internal wrappers for the contract document codec.

The codec mechanism lives in ``_private``; these wrappers keep the internal
service path stable.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...public import WorkflowContractDTO


def contract_to_document(contract: WorkflowContractDTO) -> dict[str, Any]:
    """Write a contract as its canonical JSON-compatible document."""
    from ..._private import codec

    return codec.contract_to_document(contract)


def contract_from_document(document: Mapping[str, Any]) -> WorkflowContractDTO:
    """Read a contract from its canonical JSON-compatible document."""
    from ..._private import codec

    return codec.contract_from_document(document)


__all__ = ["contract_from_document", "contract_to_document"]
