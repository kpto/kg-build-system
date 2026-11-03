"""Validate the contract contribution a module compiler returns.

Distribution module compilers author contract contributions directly: every step
already carries its own opaque instruction. Compilation only checks that boundary
and never converts a legacy contribution shape. The check lives in ``_private``.
"""
from __future__ import annotations

from .....contract.model.public import ContributionDTO


def wrap_contribution(contribution: ContributionDTO) -> ContributionDTO:
    """Return a contract contribution after checking every step owns an instruction."""
    from ..._private.compiler.adapter import wrap_contribution as _wrap_contribution

    return _wrap_contribution(contribution)


__all__ = ["wrap_contribution"]
