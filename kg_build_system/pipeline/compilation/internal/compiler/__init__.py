"""Module loading and compilation pipeline wrappers.

The pipeline mechanism lives in ``_private.compiler``; these wrappers keep the
internal compiler path stable.
"""
from __future__ import annotations

from ....contract.public import ContributionDTO, StepDTO
from .adapter import wrap_contribution
from .assembly import assemble_contract
from .blueprint import GraphBlueprint, decompose
from .pipeline import compile_blueprint

__all__ = [
    "ContributionDTO",
    "GraphBlueprint",
    "StepDTO",
    "assemble_contract",
    "compile_blueprint",
    "decompose",
    "wrap_contribution",
]
