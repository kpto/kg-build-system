"""Framework-internal interface of the shared workflow contract.

Assembly reads declared contributions and produces a contract; document
conversion writes and reads that contract at a boundary.
"""
from __future__ import annotations

from .service import (
    assemble_contract,
    contract_from_document,
    contract_to_document,
)

__all__ = [
    "assemble_contract",
    "contract_from_document",
    "contract_to_document",
]
