"""Deprecated compatibility shim for the former topology IR module.

Import from :mod:`kg_build_system.topology.internal.ir` instead.
"""
from __future__ import annotations

from .internal.ir import ComponentIR, PropertyIR

__deprecated__ = "Use kg_build_system.topology.internal.ir"

__all__ = ["ComponentIR", "PropertyIR"]
