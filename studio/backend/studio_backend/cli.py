"""``kg-studio`` command line.

    kg-studio serve --project ../../studio_test_project [--port 8700]
    kg-studio generate --project <dir>     # one-shot, for CI and debugging
    kg-studio validate --project <dir>     # normalize + validate, report problems
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import uvicorn

from .api.app import create_app
from .ir.store import DocumentStore
from .workspace import Workspace


def _project(argument: str) -> Path:
    path = Path(argument).expanduser().resolve()
    if not path.is_dir():
        raise SystemExit(f"project directory does not exist: {path}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kg-studio", description="Visual authoring studio for kg_build_system")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="run the studio API and watch the project")
    serve.add_argument("--project", required=True, help="project directory holding .kg-studio/project.ir.json")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8700)
    serve.add_argument("--reload", action="store_true", help="reload the API process on backend changes")

    generate = commands.add_parser("generate", help="write the project once from its document")
    generate.add_argument("--project", required=True)

    validate = commands.add_parser("validate", help="report document problems and exit non-zero if any")
    validate.add_argument("--project", required=True)

    arguments = parser.parse_args(argv)

    if arguments.command == "serve":
        return _serve(arguments)
    if arguments.command == "generate":
        return _generate(_project(arguments.project))
    return _validate(_project(arguments.project))


def _serve(arguments: argparse.Namespace) -> int:
    project_root = _project(arguments.project)
    workspace = Workspace(project_root)
    if not workspace.store.exists:
        print(f"no project document at {workspace.store.document_path}", file=sys.stderr)
        print("create one with: kg-studio serve … then POST /api/workspace", file=sys.stderr)
    workspace.start()
    app = create_app(workspace)
    try:
        uvicorn.run(app, host=arguments.host, port=arguments.port, log_level="warning")
    finally:
        workspace.stop()
    return 0


def _generate(project_root: Path) -> int:
    from .generate.project import write_project

    store = DocumentStore(project_root)
    document = store.load()
    outcome = write_project(document, project_root, state_dir=store.state_directory)
    print(json.dumps({"changed": list(outcome.changed), "written": list(getattr(outcome, "written", ()))}, indent=2))
    return 0


def _validate(project_root: Path) -> int:
    from .ir.normalize import NormalizationError, normalize_document
    from .ir.validate import validate_document

    document = DocumentStore(project_root).load()
    try:
        normalized = normalize_document(document)
    except NormalizationError as error:
        for issue in error.issues:
            print(f"inference: {issue}")
        return 1
    issues = validate_document(normalized)
    for issue in issues:
        print(f"{issue.ref or issue.path}: {issue.message}")
    print(f"{len(issues)} document problems")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
