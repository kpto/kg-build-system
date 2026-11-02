"""Deprecated compatibility shim for the former binding IR module.

Import from :mod:`kg_build_system.binding.internal.ir` instead.
"""
from __future__ import annotations

from .internal.ir import BindingIR, EdgeBindingIR, NodeBindingIR

__deprecated__ = "Use kg_build_system.binding.internal.ir"

__all__ = ["BindingIR", "EdgeBindingIR", "NodeBindingIR"]
