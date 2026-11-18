"""Command-line access to a project's declarative manifest."""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from typing import Any

from kg_build_system.api import compile, create_blueprint, execute
from kg_build_system.distribution.interpreter import GraphBlueprint
from kg_build_system.distribution.interpreter.service.internal.codec import (
    blueprint_to_document,
)
from kg_build_system.distribution.model.public.manifest import Blueprint, Workflow
from kg_build_system.kernel import WorkflowPlan
from kg_build_system.kernel.service.internal.report_codec import (
    workflow_report_to_document,
)
from kg_build_system.kernel.service.internal.workflow_codec import (
    workflow_plan_to_document,
)

MANIFEST = "manifest.py"


def load_manifest(project: Path) -> ModuleType:
    """Import ``<project>/manifest.py`` without running a build."""
    root = project.resolve()
    path = root / MANIFEST
    if not path.is_file():
        raise ValueError(
            f"no {MANIFEST} in {root}: a project states its blueprint and "
            "workflow in a manifest"
        )
    parent = str(root.parent)
    sys.path.insert(0, parent)
    try:
        if (root / "__init__.py").is_file():
            importlib.import_module(root.name)
            name = f"{root.name}.{path.stem}"
        else:
            digest = sha256(str(path).encode("utf-8")).hexdigest()[:12]
            name = f"_kbs_manifest_{digest}"
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ValueError(f"cannot import {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(parent)


def _one(values: list[Any], kind: type, path: Path) -> Any:
    if len(values) > 1:
        raise ValueError(f"{path} declares more than one {kind.__name__}")
    return values[0] if values else None


def read_manifest(project: Path) -> tuple[Blueprint, Workflow | None]:
    """Return the one blueprint and optional workflow a manifest declares."""
    module = load_manifest(project)
    public = [
        value for name, value in vars(module).items()
        if not name.startswith("_")
    ]
    blueprint = _one(
        [value for value in public if isinstance(value, Blueprint)],
        Blueprint, project,
    )
    workflow = _one(
        [value for value in public if isinstance(value, Workflow)],
        Workflow, project,
    )
    if workflow is not None and blueprint is None:
        blueprint = workflow.blueprint
    if blueprint is None:
        raise ValueError(
            f"{project / MANIFEST} declares no Blueprint and no Workflow"
        )
    return blueprint, workflow


def build_blueprint(declaration: Blueprint) -> GraphBlueprint:
    """Create the blueprint a manifest declares."""
    return create_blueprint(
        namespace_path=declaration.namespace_path,
        bindings=declaration.bindings,
        languages=declaration.languages,
    )


def compile_manifest(
    blueprint: Blueprint, workflow: Workflow | None, project: Path,
) -> WorkflowPlan:
    """Compile the workflow a manifest declares."""
    if workflow is None:
        raise ValueError(f"{project / MANIFEST} declares no Workflow to compile")
    return compile(
        blueprint=build_blueprint(blueprint),
        planners=workflow.planners,
        toolchain=workflow.toolchain,
    )


def _write(document: Any, output: Path | None) -> None:
    text = json.dumps(document, indent=2, sort_keys=True, default=str)
    if output is None:
        print(text)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")


def run_blueprint(arguments: argparse.Namespace) -> int:
    """Implement ``kbs blueprint``."""
    blueprint, _ = read_manifest(arguments.project)
    _write(blueprint_to_document(build_blueprint(blueprint)), arguments.output)
    return 0


def run_workflow(arguments: argparse.Namespace) -> int:
    """Implement ``kbs workflow``."""
    blueprint, workflow = read_manifest(arguments.project)
    plan = compile_manifest(blueprint, workflow, arguments.project)
    _write(workflow_plan_to_document(plan), arguments.output)
    return 0


def run_workflow_plan(arguments: argparse.Namespace) -> int:
    """Implement ``kbs run``: compile and execute one manifest."""
    blueprint, workflow = read_manifest(arguments.project)
    plan = compile_manifest(blueprint, workflow, arguments.project)
    assert workflow is not None
    output_directory = (
        arguments.output_directory
        or workflow.output_directory
        or arguments.project / "build"
    )
    report = execute(
        plan, output_directory=output_directory, toolchain=workflow.toolchain,
    )
    text = json.dumps(
        workflow_report_to_document(report), indent=2, sort_keys=True,
        default=lambda value: (
            value.model_dump(mode="json")
            if hasattr(value, "model_dump") else str(value)
        ),
    )
    print(text)
    return 0 if report.succeeded else 1


def _meaning_text(meaning: object, field: str) -> str:
    if meaning is None:
        return ""
    value = getattr(meaning, field, None)
    if value is None:
        return ""
    return getattr(value, "text", "") or ""


def run_check(arguments: argparse.Namespace) -> int:
    """Implement ``kbs check``: print the authored argument for review."""
    declaration, _ = read_manifest(arguments.project)
    model = build_blueprint(declaration)
    lines: list[str] = [f"Project: {model.graph_declaration.name if model.graph_declaration else '(no graph declaration)'}"]

    graph_meaning = (
        model.graph_declaration.meaning
        if model.graph_declaration is not None else None
    )
    graph_purpose = _meaning_text(graph_meaning, "purpose")
    lines.append("")
    lines.append("Graph purpose:")
    lines.append(f"  {graph_purpose or '(none)'}")
    for limitation in getattr(getattr(graph_meaning, "purpose", None), "limitations", ()) or ():
        lines.append(f"  limitation: {getattr(limitation, 'text', '')}")
    for claim in getattr(graph_meaning, "claims", ()) or ():
        lines.append(f"  claim: {getattr(claim, 'text', '')}")

    lines.append("")
    lines.append(f"Nodes ({len(model.graph.nodes)}):")
    for node in model.graph.nodes:
        purpose = _meaning_text(node.meaning, "purpose")
        lines.append(f"  {node.name}{' [abstract]' if node.abstract else ''}: {purpose or '(no purpose)'}")
    lines.append("")
    lines.append(f"Edges ({len(model.graph.edges)}):")
    for edge in model.graph.edges:
        purpose = _meaning_text(edge.meaning, "purpose")
        lines.append(f"  {edge.name}: {purpose or '(no purpose)'}")

    lines.append("")
    lines.append(f"Source relations ({len(model.data.source_relations)}):")
    for relation in model.data.source_relations:
        definition = relation.definition
        grain = getattr(definition, "grain", "") if definition else ""
        purpose = _meaning_text(relation.meaning, "purpose")
        lines.append(f"  {relation.name}: {grain or '(no definition)'}; {purpose or '(claims only)'}")
    lines.append("")
    lines.append(f"Derived relations ({len(model.data.derived_relations)}):")
    for relation in model.data.derived_relations:
        definition = relation.definition
        grain = getattr(definition, "grain", "") if definition else ""
        purpose = _meaning_text(relation.meaning, "purpose")
        lines.append(f"  {relation.name} [{relation.visibility}]: {grain or '(no definition)'}; {purpose or '(no purpose)'}")

    lines.append("")
    lines.append(f"Bindings ({len(model.bindings)}):")
    bound_names: set[str] = set()
    for binding in model.bindings:
        component = getattr(binding, "component", "?")
        bound_names.add(component)
        purpose = _meaning_text(binding.meaning, "purpose")
        lines.append(f"  {component}: {purpose or '(no purpose)'}")
        for limitation in getattr(getattr(binding.meaning, "purpose", None), "limitations", ()) or ():
            lines.append(f"    limitation: {getattr(limitation, 'text', '')}")

    warnings: list[str] = []
    if not graph_purpose:
        warnings.append("the graph declaration has no purpose")
    node_records = {node.name: node for node in model.graph.nodes}
    edge_records = {edge.name: edge for edge in model.graph.edges}
    for name in sorted(bound_names & (set(node_records) | set(edge_records))):
        record = node_records.get(name) or edge_records.get(name)
        if not _meaning_text(getattr(record, "meaning", None), "purpose"):
            warnings.append(f"the bound record {name!r} states no purpose")
    for relation in model.data.derived_relations:
        if relation.visibility == "public" and relation.definition is None:
            warnings.append(f"the published derived relation {relation.name!r} has no definition")
        if relation.visibility == "public" and not _meaning_text(relation.meaning, "purpose"):
            warnings.append(f"the published derived relation {relation.name!r} states no purpose")
    for binding in model.bindings:
        purpose = _meaning_text(binding.meaning, "purpose")
        if not purpose:
            warnings.append(f"the binding {getattr(binding, 'component', '?')!r} states no purpose")
        elif purpose.startswith(("Supply ", "Populate ", "Fulfil ")) or " from each row's " in purpose:
            warnings.append(f"the binding {getattr(binding, 'component', '?')!r} reads like a row recipe")
    names = {
        column.name
        for relation in (
            *model.data.source_relations, *model.data.derived_relations,
        )
        for column in relation.columns
    }
    names.update(operation.name for operation in model.operations.operations)
    if any("threshold" in name.lower() for name in names) and not any(
        "direction" in name.lower() for name in names
    ):
        warnings.append(
            "a threshold is modelled without a comparison direction; state "
            "whether the adverse side is a minimum or a maximum"
        )

    lines.append("")
    lines.append("Review notes:")
    if warnings:
        lines.extend(f"  - {warning}" for warning in warnings)
    else:
        lines.append("  - no structural review notes")
    lines.append("")
    lines.append("This report states the authored argument. It does not prove a")
    lines.append("fulfilment; the project's tests and a cold-reader review do.")
    print("\n".join(lines))
    return 0


def add_manifest_commands(commands: Any) -> None:
    """Register ``blueprint``, ``workflow`` and ``run`` on the CLI registry."""
    blueprint = commands.add_parser(
        "blueprint", help="build a project's semantic blueprint",
    )
    blueprint.add_argument(
        "--project", type=Path, default=Path.cwd(),
        help="project directory that holds manifest.py",
    )
    blueprint.add_argument(
        "--output", type=Path, default=None,
        help="write the blueprint document here instead of stdout",
    )
    blueprint.set_defaults(command_handler=run_blueprint)

    workflow = commands.add_parser(
        "workflow", help="compile a project's workflow plan",
    )
    workflow.add_argument(
        "--project", type=Path, default=Path.cwd(),
        help="project directory that holds manifest.py",
    )
    workflow.add_argument(
        "--output", type=Path, default=None,
        help="write the workflow plan document here instead of stdout",
    )
    workflow.set_defaults(command_handler=run_workflow)

    check = commands.add_parser(
        "check", help="print the authored semantic argument for review",
    )
    check.add_argument(
        "--project", type=Path, default=Path.cwd(),
        help="project directory that holds manifest.py",
    )
    check.set_defaults(command_handler=run_check)

    run = commands.add_parser("run", help="compile and execute a project workflow")
    run.add_argument(
        "--project", type=Path, default=Path.cwd(),
        help="project directory that holds manifest.py",
    )
    run.add_argument(
        "--output-directory", type=Path, default=None,
        help="where the run writes, instead of the workflow's output directory",
    )
    run.set_defaults(command_handler=run_workflow_plan)


__all__ = ["add_manifest_commands", "read_manifest", "run_check"]
