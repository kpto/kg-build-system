"""Framework-internal wrapper for contract assembly.

The assembly rules live in ``_private``; this wrapper keeps the internal service
path stable.
"""
from __future__ import annotations

from collections.abc import Sequence

from pydantic import JsonValue

from ...public import ContributionDTO, WorkflowContractDTO


def assemble_contract(
    contributions: Sequence[ContributionDTO],
    provenance: JsonValue | None = None,
) -> WorkflowContractDTO:
    """Assemble declared contributions into a workflow contract."""
    from ..._private import assembly

    return assembly.assemble_contract(contributions, provenance=provenance)


__all__ = ["assemble_contract"]
