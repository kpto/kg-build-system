"""Framework-internal interface of the build package.

The relation-service protocols are the data and protocol names another package
may depend on. Build execution, instruction dispatch, the engine and storage are
private mechanisms. The author-facing surface is
:mod:`kg_build_system.pipeline.build.public`.
"""
from __future__ import annotations

from .relations import RelationQueryResult, RelationRef, RelationService

__all__ = ["RelationQueryResult", "RelationRef", "RelationService"]
