"""Framework-internal interface of the build package.

The relation-service protocols are the names another package may depend on.
Build execution, instruction dispatch, the engine and storage are private
mechanisms.
"""
from __future__ import annotations

from .relations import RelationQueryResult, RelationRef, RelationService

__all__ = ["RelationQueryResult", "RelationRef", "RelationService"]
