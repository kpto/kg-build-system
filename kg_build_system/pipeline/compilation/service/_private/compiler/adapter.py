"""Validate the contract contribution a module compiler returns.

Distribution module compilers author contract contributions directly: every step
already carries its own opaque instruction. Compilation only checks that boundary
and never converts a legacy contribution shape.
"""
from __future__ import annotations

from .....contract.model.public import (
    ContributionDTO,
    InstructionDTO,
    StepDTO,
)


def wrap_contribution(contribution: ContributionDTO) -> ContributionDTO:
    """Return a contract contribution after checking every step owns an instruction."""
    if not isinstance(contribution, ContributionDTO):
        raise TypeError(
            "module compilers must return a contract ContributionDTO"
        )
    for step in contribution.steps:
        if not isinstance(step, StepDTO):
            raise TypeError("contract contributions require StepDTO steps")
        if not isinstance(step.instruction, InstructionDTO):
            raise TypeError("every contract step requires an InstructionDTO")
    return contribution


__all__ = ["wrap_contribution"]
