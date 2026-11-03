"""Command-line integration for edit-time code generation."""
from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .engine import GenerationSession, generate
from ..internal.models import (
    GenerationAction, GenerationActionKind, GenerationError, GenerationResult,
    GenerationStatus,
)
from .watcher import watch

_LOGGER = logging.getLogger("kg_build_system.generation.code_generation")


def _report_action(action: GenerationAction) -> None:
    declaration = action.declaration_id or "<unknown>"
    if action.kind is GenerationActionKind.DECLARATION_ADDED:
        _LOGGER.info("Generation declaration added: %s. Processing...", declaration)
    elif action.kind is GenerationActionKind.DECLARATION_CHANGED:
        _LOGGER.info("Generation declaration changed: %s. Processing...", declaration)
    elif action.kind is GenerationActionKind.DECLARATION_DELETED:
        _LOGGER.info("Generation declaration deleted: %s. Processing...", declaration)


def _report_outputs(result: GenerationResult) -> None:
    for path in result.created_paths:
        _LOGGER.info("Created generated output %s.", path.as_posix())
    for path in result.updated_paths:
        _LOGGER.info("Updated generated output %s.", path.as_posix())
    for path in result.deleted_paths:
        _LOGGER.info("Deleted generated output %s.", path.as_posix())


async def _generate_and_report(operation: Callable[[], Awaitable[GenerationResult]]) -> None:
    """Run one watched pass without allowing an invalid edit to stop the watcher."""
    try:
        result = await operation()
    except (OSError, ValueError) as error:
        _LOGGER.error("Generation failed: %s", error)
        return
    _report_outputs(result)


def add_generate_command(commands: Any) -> None:
    """Register the ``generate`` command on the root CLI parser."""
    generate = commands.add_parser("generate", help="generate edit-time declaration code")
    generate.add_argument("--watch", action="store_true", help="watch project files for changes")
    generate.add_argument("--check", action="store_true", help="check generated files without changing them")
    generate.add_argument(
        "--regenerate", action="store_true",
        help="re-observe every source and regenerate every product, even current ones",
    )
    generate.add_argument("--project", type=Path, default=Path.cwd(), help="project directory to watch")
    generate.add_argument("--debounce", type=int, default=300, help="change debounce in milliseconds")
    generate.set_defaults(command_handler=run_generate)


async def _execute_pass(root: Path, *, check: bool, regenerate: bool = False) -> int:
    """Run one desired-state pass and render its outcome as a CLI status."""
    try:
        result = await generate(root, check=check, regenerate=regenerate)
    except (GenerationError, OSError) as error:
        _LOGGER.error("Generation failed: %s", error)
        return 1
    for diagnostic in result.diagnostics:
        _LOGGER.error("%s", diagnostic)
    _report_outputs(result)
    return 1 if result.status is GenerationStatus.STALE else 0


async def run_generate(arguments: argparse.Namespace) -> int:
    """Execute the ``generate`` command."""
    root = arguments.project.resolve()
    if arguments.watch and arguments.check:
        raise ValueError("--watch and --check cannot be combined")
    if arguments.watch and arguments.regenerate:
        raise ValueError("--regenerate is a single re-observation pass and cannot be combined with --watch")
    if not arguments.watch:
        return await _execute_pass(root, check=arguments.check, regenerate=arguments.regenerate)

    _LOGGER.info("Running initial generation pass for %s...", root)
    session = GenerationSession(root)
    try:
        try:
            initial = await session.start()
        except (OSError, ValueError) as error:
            _LOGGER.error("Initial generation pass failed: %s", error)
            _LOGGER.info("Watching %s for changes. Press Ctrl+C to stop.", root)
        else:
            _report_outputs(initial)
            _LOGGER.info("Initial generation pass complete. Watching %s for changes. Press Ctrl+C to stop.", root)
        async for changes in watch(root, debounce=arguments.debounce):
            await _generate_and_report(
                lambda changes=changes: session.handle(
                    (change.path for change in changes),
                    on_action=_report_action,
                )
            )
    except (asyncio.CancelledError, KeyboardInterrupt):
        _LOGGER.info("Stopped.")
    return 0


__all__ = ["add_generate_command", "run_generate"]
