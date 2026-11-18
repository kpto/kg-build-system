"""``kbs init``: copy the packaged project template into a new workspace."""
from __future__ import annotations

import argparse
import shutil
from importlib import resources
from importlib.metadata import PackageNotFoundError, distribution
import json
from pathlib import Path
from typing import Any

from kg_build_system.kgkit.config import load_project


def _source_template() -> Path | None:
    """The template in a source checkout, if the CLI is running from one."""
    repository = Path(__file__).resolve().parents[4]
    candidate = repository / "templates" / "project"
    return candidate if candidate.is_dir() else None


def _template_root() -> Path:
    """The project template, from the checkout first, then the package."""
    source = _source_template()
    if source is not None:
        return source
    resource = resources.files("kg_build_system").joinpath(
        "templates", "project"
    )
    with resources.as_file(resource) as path:
        if not path.is_dir():
            raise ValueError(
                "the installed package has no project template; reinstall "
                "kg-build-system or copy templates/project from a checkout"
            )
        return Path(path)


def _rewrite_pyproject(target: Path) -> None:
    """Point the copied project at the framework that initialised it."""
    path = target / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    source = _source_template()
    if source is not None:
        repository = source.parent.parent
        text = text.replace(
            "# The template lives inside the framework checkout. `kbs init` rewrites this to\n"
            "# the framework location used by the project; if you copy the template by hand,\n"
            "# point this at your kg-build-system checkout or remove it after installing the\n"
            "# package.",
            "# Written by kbs init: this project reads the framework from this checkout.",
        )
        text = text.replace(
            'kg-build-system = { path = "../.." }',
            f'kg-build-system = {{ path = {str(repository)!r} }}',
        )
    else:
        # A wheel installation does not carry the repository layout. The
        # project depends on the installed distribution instead.
        lines: list[str] = []
        skipping = False
        for line in text.splitlines():
            if line.strip() == "[tool.uv.sources]":
                skipping = True
                continue
            if skipping:
                if line.startswith("[") and line.strip() != "[tool.uv.sources]":
                    skipping = False
                else:
                    continue
            lines.append(line)
        text = "\n".join(lines).rstrip() + "\n"
        try:
            metadata = distribution("kg-build-system")
            direct = metadata.read_text("direct_url.json")
        except (PackageNotFoundError, FileNotFoundError):
            direct = None
        if direct:
            url = json.loads(direct).get("url", "")
            if url.startswith("file://"):
                wheel = Path(url.removeprefix("file://"))
                if wheel.is_file():
                    text = text.rstrip() + (
                        "\n\n[tool.uv.sources]\n"
                        f"kg-build-system = {{ path = {str(wheel)!r} }}\n"
                    )
    path.write_text(text, encoding="utf-8")


def run_init(arguments: argparse.Namespace) -> int:
    """Implement ``kbs init``."""
    target = arguments.path.resolve()
    if target.exists() and any(target.iterdir()) and not arguments.force:
        raise ValueError(
            f"{target} is not empty; choose an empty directory or pass --force"
        )
    template = _template_root()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        template, target, dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            ".venv", "build", "__pycache__", ".pytest_cache", "uv.lock",
        ),
    )
    _rewrite_pyproject(target)
    load_project(target).ensure(write_config=True)
    print(f"Initialised a kg-build-system project in {target}")
    print(f"Notebook: {target / 'kgkit'}")
    print("Next:")
    print(f"  cd {target}")
    print("  uv sync")
    print("  uv run pytest")
    print("  uv run kbs check --project project")
    return 0


def add_init_command(commands: Any) -> None:
    """Register ``init`` on the CLI registry."""
    parser = commands.add_parser(
        "init", help="copy the project template and create the notebook",
    )
    parser.add_argument(
        "path", nargs="?", type=Path, default=Path.cwd(),
        help="empty directory to initialise; defaults to the current directory",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="copy into a non-empty directory, overwriting template files",
    )
    parser.set_defaults(command_handler=run_init)


__all__ = ["add_init_command", "run_init"]
