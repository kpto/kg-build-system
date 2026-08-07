"""Command-line integration for edit-time code generation."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from collections.abc import Callable
from typing import Any

from .engine import GenerationSession, generate
from .models import GenerationResult, GenerationStatus
from .watcher import watch


_LOGGER = logging.getLogger("kg_build_system.code_generation")


def _generate_and_report(operation: Callable[[], GenerationResult]) -> None:
    """Run one watched pass without allowing an invalid edit to stop the watcher."""
    try:
        result = operation()
    except (OSError, ValueError) as error:
        _LOGGER.error("Generation failed: %s", error)
        return
    for path in result.changed_paths:
        _LOGGER.info("generated %s", path.as_posix())


def add_generate_command(commands: Any) -> None:
    """Register the ``generate`` command on the root CLI parser."""
    generate = commands.add_parser("generate", help="generate edit-time declaration code")
    generate.add_argument("--watch", action="store_true", help="watch project files for changes")
    generate.add_argument("--check", action="store_true", help="check generated files without changing them")
    generate.add_argument("--project", type=Path, default=Path.cwd(), help="project directory to watch")
    generate.add_argument("--debounce", type=int, default=300, help="change debounce in milliseconds")
    generate.set_defaults(command_handler=run_generate)


def run_generate(arguments: argparse.Namespace) -> int:
    """Execute the ``generate`` command."""
    root = arguments.project.resolve()
    if arguments.watch and arguments.check:
        raise ValueError("--watch and --check cannot be combined")
    if not arguments.watch:
        result = generate(root, check=arguments.check)
        for diagnostic in result.diagnostics:
            _LOGGER.error("%s", diagnostic)
        for path in result.changed_paths:
            _LOGGER.info("generated %s", path.as_posix())
        return 1 if result.status is GenerationStatus.STALE else 0

    _LOGGER.info("Watching %s for code-generation inputs. Press Ctrl+C to stop.", root)
    session = GenerationSession(root)
    try:
        _generate_and_report(session.start)
        for changes in watch(root, debounce=arguments.debounce):
            for change in changes:
                _LOGGER.info("%s %s", change.kind.value, change.path.as_posix())
            _generate_and_report(lambda changes=changes: session.handle(change.path for change in changes))
    except KeyboardInterrupt:
        _LOGGER.info("Stopped.")
    return 0
