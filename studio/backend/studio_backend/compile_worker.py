"""Compile or build a studio project in a disposable subprocess.

``create_blueprint`` and ``build`` import the generated project, which means their
module state would go stale the moment the studio regenerates it, and a failure
inside DuckDB or a target module would take the API process with it. Running each
pass in a short-lived subprocess keeps the server responsive, guarantees a clean
import graph per pass, and makes the result of a stale-generation race impossible
to cache by accident.

Usage (one JSON object on stdout):

    python -m studio_backend.compile_worker blueprint --project-root … --package … --module …
    python -m studio_backend.compile_worker plan …
    python -m studio_backend.compile_worker build … --output-directory …
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

from kg_build_system import build, compile as compile_contract, create_blueprint
from kg_build_system.compile.codec import encode_blueprint
from kg_build_system.modules import register_module
from kg_build_system.workflow.ir import WorkflowContractIR

from .catalog import instantiate_configuration, load_module_class
from .plan import project_plan


def _prepare_import(project_root: Path) -> None:
    """Make the generated package importable before anything touches it.

    A studio project keeps its generated package in a directory of its own inside the
    project root, beside ``data/`` and ``.kg-studio/``. The root therefore goes on
    ``sys.path``, and the namespace ``create_blueprint`` scans is the package itself.
    """
    root = str(project_root)
    if root not in sys.path:
        sys.path.insert(0, root)


def _registrations(specifications: list[str]):
    registrations = []
    for specification in specifications:
        payload = json.loads(specification)
        module_class = load_module_class(payload["import_module"], payload["class_qualname"])
        configuration = payload.get("configuration")
        instance = instantiate_configuration(module_class, configuration)
        registrations.append(
            register_module(module_class) if instance is None else register_module(module_class, instance)
        )
    return registrations


def _blueprint(project_root: Path, package: str, specifications: list[str]) -> dict[str, Any]:
    _prepare_import(project_root)
    modules = _registrations(specifications)
    blueprint = create_blueprint(namespace_path=project_root / package, modules=modules)
    return {"blueprint": encode_blueprint(blueprint), "summary": _summary(blueprint)}


def _summary(blueprint: Any) -> dict[str, int]:
    return {
        "tables": len(blueprint.tables),
        "structs": len(blueprint.structs),
        "projections": len(blueprint.projections),
        "components": len(blueprint.components),
        "bindings": len(blueprint.bindings),
        "sources": len(blueprint.sources),
        "modules": len(blueprint.modules),
    }


def _plan(project_root: Path, package: str, specifications: list[str]) -> dict[str, Any]:
    _prepare_import(project_root)
    modules = _registrations(specifications)
    contract: WorkflowContractIR = compile_contract(namespace_path=project_root / package, modules=modules)
    return {
        "plan": project_plan(contract),
        "fingerprint": contract.workflow_fingerprint,
        "contract": json.loads(contract.model_dump_json()),
    }


def _build(project_root: Path, package: str, specifications: list[str], output: Path) -> dict[str, Any]:
    _prepare_import(project_root)
    modules = _registrations(specifications)
    contract = compile_contract(namespace_path=project_root / package, modules=modules)
    output.mkdir(parents=True, exist_ok=True)
    build(contract, output_directory=output)
    # ``WorkflowReport`` is a frozen dataclass holding domain objects, so the report
    # the executor already wrote to disk is the serialisable form of it.
    report_path = output / "build_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    published = sorted(str(path.relative_to(output)) for path in output.rglob("*") if path.is_file())
    return {
        "report": payload,
        "published": published,
        "unresolved_failures": payload.get("unresolved_failures", []),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="studio-compile-worker")
    parser.add_argument("mode", choices=("blueprint", "plan", "build"))
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--package", required=True, help="the generated package inside the project root")
    parser.add_argument(
        "--module",
        action="append",
        default=[],
        help='a configured module as JSON: {"import_module":…,"class_qualname":…,"configuration":…}',
    )
    parser.add_argument("--output-directory", type=Path, default=None)
    arguments = parser.parse_args(argv)

    project_root = arguments.project_root.resolve()
    output = arguments.output_directory or project_root / "build"
    try:
        if arguments.mode == "blueprint":
            payload = _blueprint(project_root, arguments.package, arguments.module)
        elif arguments.mode == "plan":
            payload = _plan(project_root, arguments.package, arguments.module)
        else:
            payload = _build(project_root, arguments.package, arguments.module, output)
    except BaseException as error:  # noqa: BLE001 - the caller needs any failure as data
        json.dump(
            {
                "ok": False,
                "error": {
                    "type": type(error).__name__,
                    "message": str(error) or type(error).__name__,
                    "traceback": traceback.format_exc(limit=6),
                },
            },
            sys.stdout,
        )
        sys.stdout.write("\n")
        return 0
    payload["ok"] = True
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
