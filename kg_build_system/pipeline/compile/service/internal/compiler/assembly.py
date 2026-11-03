"""Assemble compiled contributions into the shared workflow contract.

Compilation owns the assembly rules; this wrapper keeps the internal compiler
path stable and delegates to the private compiler.
"""
from __future__ import annotations

from collections.abc import Sequence

from pydantic import JsonValue

from .....contract.model.public import ContributionDTO, WorkflowContractDTO


def assemble_contract(
    contributions: Sequence[ContributionDTO],
    provenance: JsonValue | None = None,
) -> WorkflowContractDTO:
    """Assemble instruction-carrying contributions into a contract."""
    from ..._private.compiler.assembly import assemble_contract as _assemble_contract

    return _assemble_contract(contributions, provenance=provenance)


__all__ = ["assemble_contract"]
