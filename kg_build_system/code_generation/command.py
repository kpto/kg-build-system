"""Command-line integration for edit-time code generation."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

from .watcher import watch


_LOGGER = logging.getLogger("kg_build_system.code_generation")


def add_generate_command(commands: Any) -> None:
    """Register the ``generate`` command on the root CLI parser."""
    generate = commands.add_parser("generate", help="generate edit-time declaration code")
    generate.add_argument("--watch", action="store_true", help="watch project files for changes")
    generate.add_argument("--project", type=Path, default=Path.cwd(), help="project directory to watch")
    generate.add_argument("--debounce", type=int, default=300, help="change debounce in milliseconds")
    generate.set_defaults(command_handler=run_generate)


def run_generate(arguments: argparse.Namespace) -> int:
    """Execute the ``generate`` command."""
    if not arguments.watch:
        raise ValueError("generate currently requires --watch")

    root = arguments.project.resolve()
    _LOGGER.info("Watching %s for code-generation inputs. Press Ctrl+C to stop.", root)
    try:
        for changes in watch(root, debounce=arguments.debounce):
            for change in changes:
                _LOGGER.info("%s %s", change.kind.value, change.path.as_posix())
    except KeyboardInterrupt:
        _LOGGER.info("Stopped.")
    return 0
