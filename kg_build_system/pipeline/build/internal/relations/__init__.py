"""Relation-service protocols used by build services and instruction executors.

The protocol is shared with the engine and with supplied module executors, so it
is defined once in :mod:`protocols` rather than restated. A second copy would
make two ``RelationRef`` classes that an engine cannot treat as the same value.
"""
from __future__ import annotations

from .protocols import RelationQueryResult, RelationRef, RelationService

__all__ = ["RelationQueryResult", "RelationRef", "RelationService"]
