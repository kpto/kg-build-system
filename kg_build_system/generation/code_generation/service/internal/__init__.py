"""Framework-internal generation service interface.

Provider loading and CLI registration are thin wrappers whose mechanisms live
in :mod:`kg_build_system.generation.code_generation.service._private`.
"""
from __future__ import annotations

from .adapters import load_provider, resolve_provider_path
from .functions import add_generate_command

__all__ = ["add_generate_command", "load_provider", "resolve_provider_path"]
