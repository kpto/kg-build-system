"""Module loading and compilation pipeline.

The pipeline reads the blueprint, decomposes it into the kernel's in-memory build,
runs each module compiler and hands the compiled contributions to contract
assembly.
"""
from __future__ import annotations

from .....contract.model.public import ContributionDTO, StepDTO
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
