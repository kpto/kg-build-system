"""Command-line integration for edit-time code generation."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from collections.abc import Callable
from typing import Any

from .engine import GenerationSession, generate
from .models import GenerationAction, GenerationActionKind, GenerationError, GenerationResult, GenerationStatus
from .watcher import watch


_LOGGER = logging.getLogger("kg_build_system.code_generation")


def _report_action(action: GenerationAction) -> None:
    sources = ", ".join(path.as_posix() for path in action.source_paths)
    if action.kind is GenerationActionKind.DECLARATION:
        _LOGGER.info(
            "Detected a generated declaration change in %s; regenerating %s.",
            action.trigger_path.as_posix(),
            sources,
        )
    else:
        _LOGGER.info(
            "Detected a provider dependency change in %s; regenerating %s.",
            action.trigger_path.as_posix(),
            sources,
        )


def _generate_and_report(operation: Callable[[], GenerationResult]) -> None:
    """Run one watched pass without allowing an invalid edit to stop the watcher."""
    try:
        result = operation()
    except (OSError, ValueError) as error:
        _LOGGER.error("Generation failed: %s", error)
        return
    for action in result.actions:
        _report_action(action)
    for path in result.changed_paths:
        _LOGGER.info("Updated generation output %s.", path.as_posix())
    if result.actions and not result.changed_paths:
        _LOGGER.info("Generated output is already current.")


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
        try:
            result = generate(root, check=arguments.check)
        except (GenerationError, OSError) as error:
            _LOGGER.error("Generation failed: %s", error)
            return 1
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
            _generate_and_report(lambda changes=changes: session.handle(change.path for change in changes))
    except KeyboardInterrupt:
        _LOGGER.info("Stopped.")
    return 0
