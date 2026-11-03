"""Assemble compiled contributions into the shared workflow contract.

Assembly rules live in :mod:`kg_build_system.pipeline.contract`; compilation
only supplies the declared contributions.
"""
from __future__ import annotations

from collections.abc import Sequence

from pydantic import JsonValue

from ....contract.internal import assemble_contract as _assemble_contract
from ....contract.public import ContributionDTO, WorkflowContractDTO


def assemble_contract(
    contributions: Sequence[ContributionDTO],
    provenance: JsonValue | None = None,
) -> WorkflowContractDTO:
    """Assemble instruction-carrying contributions into a contract."""
    return _assemble_contract(contributions, provenance=provenance)


__all__ = ["assemble_contract"]
