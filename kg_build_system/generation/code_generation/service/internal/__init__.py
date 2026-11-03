"""Framework-internal generation service interface.

Provider loading and CLI registration are thin wrappers whose mechanisms live
in :mod:`kg_build_system.generation.code_generation.service._private`.
"""
from __future__ import annotations

from .adapters import load_provider, resolve_provider_path


def add_generate_command(commands: object) -> None:
    """Register the ``kbs generate`` subcommand on an argparse registry."""
    from .._private.command import add_generate_command as implementation

    implementation(commands)


__all__ = ["add_generate_command", "load_provider", "resolve_provider_path"]
