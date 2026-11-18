"""The ``kbs`` command-line interface."""
from __future__ import annotations

import argparse
import asyncio
import inspect
import logging
import sys
from collections.abc import Coroutine
from typing import Any, Sequence, cast

from kg_build_system.generation.code_generation.service.internal import (
    add_generate_command,
)

from .init import add_init_command
from .manifest_command import add_manifest_commands
from .view import add_view_command
from kg_build_system.kgkit.cli import main as notebook_main


def _configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    ))
    logger = logging.getLogger("kg_build_system")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kbs")
    commands = parser.add_subparsers(dest="command", required=True)
    add_generate_command(commands)
    add_init_command(commands)
    add_manifest_commands(commands)
    add_view_command(commands)

    notebook = commands.add_parser(
        "notebook", help="run a kgkit notebook or console command",
    )
    notebook.add_argument(
        "args", nargs=argparse.REMAINDER,
        help="a kgkit command and its arguments, for example: status --json",
    )
    notebook.set_defaults(
        command_handler=lambda arguments: notebook_main(arguments.args),
    )

    console = commands.add_parser(
        "console", help="serve the kgkit notebook console",
    )
    console.add_argument("--root", default=".")
    console.add_argument("--host", default="127.0.0.1")
    console.add_argument("--port", type=int, default=8787)
    console.add_argument("--viewer-url", default="")
    console.add_argument("--json", action="store_true")
    console.set_defaults(
        command_handler=lambda arguments: notebook_main([
            "console", "--root", arguments.root, "--host", arguments.host,
            "--port", str(arguments.port), "--viewer-url",
            arguments.viewer_url,
        ] + (["--json"] if arguments.json else [])),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_logging()
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        result = arguments.command_handler(arguments)
        if inspect.isawaitable(result):
            return asyncio.run(cast(Coroutine[Any, Any, int], result))
        return result
    except KeyboardInterrupt:
        logging.getLogger("kg_build_system").info("Stopped.")
        return 0
    except ValueError as error:
        parser.error(str(error))


__all__ = ["main"]
