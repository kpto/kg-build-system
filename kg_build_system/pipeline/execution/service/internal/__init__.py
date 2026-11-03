"""Framework-internal interface of the build package.

The relation-service protocols are the names another package may depend on.
Build execution, instruction dispatch, the engine and storage are private
mechanisms.
"""
from __future__ import annotations

from .contract_codec import contract_from_document, contract_to_document
from .relations import RelationQueryResult, RelationRef, RelationService

__all__ = [
    "RelationQueryResult",
    "RelationRef",
    "RelationService",
    "contract_from_document",
    "contract_to_document",
]
