"""Internal generation service functions."""
from __future__ import annotations


def add_generate_command(commands: object) -> None:
    """Register the ``kbs generate`` subcommand on an argparse registry."""
    from .._private.command import add_generate_command as implementation

    implementation(commands)


__all__ = ["add_generate_command"]
