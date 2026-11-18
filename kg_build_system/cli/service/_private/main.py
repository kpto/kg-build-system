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
from kg_build_system.kgkit.cli import add_notebook_commands

from .init import add_init_command
from .manifest_command import add_manifest_commands
from .view import add_view_command


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


def _run_console(arguments: argparse.Namespace) -> int:
    from kg_build_system.kgkit.config import load_project
    from kg_build_system.kgkit.console import DEFAULT_VIEWER_URL, serve

    project = load_project(arguments.project)
    viewer_url = (
        arguments.viewer_url
        or str(project.config.get("viewer_url") or "")
        or DEFAULT_VIEWER_URL
    )
    serve(project, host=arguments.host, port=arguments.port, viewer_url=viewer_url)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kbs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "command groups:\n"
            "  model     generate, init, blueprint, workflow, check, run\n"
            "  read      view (design viewer), console (project console)\n"
            "  notebook  kbs notebook status|relations|snapshot|findings|propose|"
            "decide|revisions|compare|eval\n"
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    add_generate_command(commands)
    add_init_command(commands)
    add_manifest_commands(commands)
    add_view_command(commands)

    notebook = commands.add_parser(
        "notebook",
        help="record findings, proposals, designs, evaluations and revisions",
        description=(
            "Record findings, proposals, change designs, revisions and captured "
            "views for the project, and read the notebook catalog."
        ),
        epilog=(
            "The notebook lives in ./kgkit. A project command is a JSON contract "
            "declared under 'commands' in kgkit/config.json."
        ),
    )
    notebook_sub = notebook.add_subparsers(dest="command", required=True)
    add_notebook_commands(notebook_sub)

    console = commands.add_parser(
        "console",
        help="serve the project console; it embeds the design viewer",
    )
    console.add_argument(
        "--project", dest="project", metavar="PROJECT", default=".",
        help="project directory",
    )
    console.add_argument(
        "--root", dest="project", metavar="PROJECT", help=argparse.SUPPRESS,
    )
    console.add_argument("--host", default="127.0.0.1", help="bind address")
    console.add_argument("--port", type=int, default=8787, help="console port")
    console.add_argument(
        "--viewer-url", default="", help="design viewer URL to embed",
    )
    console.set_defaults(command_handler=_run_console)
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
