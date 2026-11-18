"""The notebook command line, invoked as ``kbs notebook``.

The package owns the project surface: the relation catalog, the design gate,
evaluations, revisions, snapshots, findings and the console. Project operations
are declared as ``commands`` in ``kgkit/config.json``; the notebook runs them and
passes their JSON through, so the console and a shell use the same contract.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import designs, evaluations, findings, ledger, project_commands, relations, revisions
from .config import DATA_DIR_NAME, Project, load_project, write_config_file
from .snapshot import import_snapshot


def _emit(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, default=str, sort_keys=True))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            print(f"{key}: {item}")
    elif isinstance(value, list):
        for item in value:
            print(item)
    else:
        print(value)


def _summary(project: Project, payload: dict[str, Any]) -> dict[str, Any]:
    objects = payload.get("objects", [])
    counts: dict[str, int] = {}
    for item in objects:
        counts[str(item.get("kind"))] = counts.get(str(item.get("kind")), 0) + 1
    return {
        "ok": True,
        "project": project.name,
        "root": str(project.root),
        "data_dir": str(project.data_dir),
        "objects": len(objects),
        "timeline": len(payload.get("timeline", [])),
        "kinds": counts,
    }


def command_init(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root).ensure(write_config=True)
    write_config_file(project)
    payload = relations.graph(project)
    return {
        "ok": True,
        "project": project.name,
        "root": str(project.root),
        "data_dir": str(project.data_dir),
        "config": str(project.config_path),
        "objects": len(payload["objects"]),
        "timeline": len(payload["timeline"]),
    }


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    payload = relations.graph(project)
    views = [
        item
        for item in payload["objects"]
        if item.get("kind") == "revision" and item.get("view_file")
    ]
    summary = {**_summary(project, payload), "views": len(views)}
    status = project_commands.run(project, "status")
    if status and "error" not in status:
        return {**summary, **status}
    return summary


def command_relations(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    payload = relations.graph(project)
    if args.json:
        return payload
    summary = _summary(project, payload)
    print(f"project: {summary['project']}")
    print(f"data: {summary['data_dir']}")
    print(f"objects: {summary['objects']}")
    for kind, count in sorted(summary["kinds"].items()):
        print(f"  {kind}: {count}")
    print(f"timeline: {summary['timeline']}")
    for event in payload.get("timeline", []):
        print(
            f"  {event.get('timestamp', '')}  {event.get('type', ''):<18} {event.get('title', '')}"
        )
    return payload


def command_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    if project_commands.command(project, "snapshot") is not None:
        return project_commands.run(project, "snapshot")
    return import_snapshot(
        project,
        source=args.source,
        command=args.command,
        revision=args.revision,
        title=args.title,
    )


def command_console(args: argparse.Namespace) -> dict[str, Any]:
    from .console import DEFAULT_VIEWER_URL, serve

    project = load_project(args.root)
    viewer_url = (
        args.viewer_url
        or str(project.config.get("viewer_url") or "")
        or DEFAULT_VIEWER_URL
    )
    serve(project, host=args.host, port=args.port, viewer_url=viewer_url)
    return {"ok": True, "host": args.host, "port": args.port, "viewer_url": viewer_url}


def _project_operation(args: argparse.Namespace, name: str, **parameters: object) -> dict[str, Any]:
    return project_commands.run(load_project(args.root), name, **parameters)


def command_validate(args: argparse.Namespace) -> dict[str, Any]:
    return _project_operation(args, "validate")


def command_build(args: argparse.Namespace) -> dict[str, Any]:
    return _project_operation(args, "build")


def command_audit(args: argparse.Namespace) -> dict[str, Any]:
    return _project_operation(args, "audit")


def _newest_report(project: Project) -> Path | None:
    candidates = [
        path
        for path in project.paths(project.config.get("evaluation_reports"))
        if path.is_file()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def command_eval(args: argparse.Namespace) -> dict[str, Any]:
    mode = "--full" if args.full else "--quick"
    project = load_project(args.root)
    result = project_commands.run(project, "eval", mode=mode)
    if result.get("ok") is False:
        return result
    report = _newest_report(project)
    if report is None:
        return {**result, "evaluation": None, "warning": "the project wrote no evaluation report"}
    evaluation = evaluations.add(project, report=report)
    return {**result, "evaluation": evaluation}


def command_findings(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    if args.action == "list":
        rows, errors = findings.list_findings(project)
        return {"ok": True, "count": len(rows), "findings": rows, "errors": errors}
    try:
        result = findings.add(
            project,
            layer=args.layer or "unspecified",
            observation=args.observation or "",
            evidence=args.evidence or "",
            decision=args.decision or "",
            metric=args.metric or "",
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "finding": result}


def command_design_new(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    try:
        design = designs.propose(
            project,
            title=args.title,
            summary=args.summary or "",
            findings=args.finding or (),
            supersedes=args.supersedes or (),
            related=args.related or (),
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "design": design}


def command_design_list(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    rows = designs.read_designs(project)
    return {"ok": True, "count": len(rows), "designs": rows, "gate": designs.gate(project)}


def command_design_show(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    design = designs.read_design(project, args.id)
    if design is None:
        return {"ok": False, "error": f"design {args.id} does not exist"}
    payload = relations.graph(project)
    row = next((item for item in payload["objects"] if item["id"] == args.id), None)
    return {
        "ok": True,
        "design": design,
        "catalog": row,
        "revision_links": revisions.linked_revisions(project, args.id),
    }


def command_design_resolve(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    try:
        design = designs.set_state(
            project, args.id, args.target_state, by=getattr(args, "by", None)
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "design": design}


def command_design_link(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    try:
        design = designs.link(project, args.source, args.target, args.role)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "design": design}


def command_evaluations(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    if args.action == "list":
        rows = evaluations.read_evaluations(project)
        return {"ok": True, "count": len(rows), "evaluations": rows}
    try:
        evaluation = evaluations.add(
            project,
            report=args.source,
            mode=args.mode,
            status=args.status,
            revision=args.revision,
            design=args.design,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "evaluation": evaluation}


def command_revisions(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    if args.action == "record":
        return revisions.record_revision(project, message=args.message)
    return revisions.list_revisions(project)


def command_compare(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    return revisions.compare_revisions(project, args.before, args.after)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kbs notebook",
        description="The project notebook: designs, findings, evaluations, revisions and the console.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def root_argument(command: argparse.ArgumentParser) -> None:
        command.add_argument(
            "--root",
            default=".",
            help=f"project root; its runtime data goes under ./{DATA_DIR_NAME}",
        )
        command.add_argument("--json", action="store_true", help="print JSON")

    init = sub.add_parser("init", help="create the notebook and configure the project")
    root_argument(init)
    init.set_defaults(handler=command_init)

    status = sub.add_parser("status", help="show graph and notebook state")
    root_argument(status)
    status.set_defaults(handler=command_status)

    rel = sub.add_parser("relations", help="read the relational catalog")
    rel.add_argument("action", choices=["list"])
    rel.add_argument("--root", default=".")
    rel.add_argument("--json", action="store_true")
    rel.set_defaults(handler=command_relations)

    snapshot = sub.add_parser("snapshot", help="import the latest compiled viewer snapshot")
    snapshot.add_argument("--root", default=".")
    snapshot.add_argument("--from", dest="source", help="snapshot, workflow plan or blueprint file")
    snapshot.add_argument("--command", help="command that produces the snapshot")
    snapshot.add_argument("--revision", help="revision id stored with the snapshot")
    snapshot.add_argument("--title", help="snapshot title")
    snapshot.add_argument("--json", action="store_true")
    snapshot.set_defaults(handler=command_snapshot)

    console = sub.add_parser("console", help="serve the standalone notebook console")
    console.add_argument("--root", default=".")
    console.add_argument("--host", default="127.0.0.1")
    console.add_argument("--port", type=int, default=8787)
    console.add_argument("--viewer-url", default="")
    console.add_argument("--json", action="store_true")
    console.set_defaults(handler=command_console)

    for name, handler, text in (
        ("validate", command_validate, "validate the declarations"),
        ("build", command_build, "build the graph and sidecars"),
        ("audit", command_audit, "audit the built graph"),
    ):
        command = sub.add_parser(name, help=text)
        root_argument(command)
        command.set_defaults(handler=handler)

    evaluate = sub.add_parser("eval", help="run the project evaluation and record it")
    root_argument(evaluate)
    mode = evaluate.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true")
    mode.add_argument("--full", action="store_true")
    evaluate.set_defaults(handler=command_eval)

    finding = sub.add_parser("findings", help="append or list design findings")
    finding.add_argument("action", choices=["add", "list"])
    finding.add_argument("--root", default=".")
    finding.add_argument("--json", action="store_true")
    finding.add_argument("--layer")
    finding.add_argument("--observation")
    finding.add_argument("--evidence")
    finding.add_argument("--decision")
    finding.add_argument("--metric")
    finding.set_defaults(handler=command_findings)

    design = sub.add_parser("design", help="propose and resolve change designs")
    design_sub = design.add_subparsers(dest="action", required=True)

    new = design_sub.add_parser("new", help="propose a change design")
    root_argument(new)
    new.add_argument("--title", required=True)
    new.add_argument("--summary")
    new.add_argument("--finding", action="append", help="finding id that motivates the design")
    new.add_argument("--supersedes", action="append", help="design id this design supersedes")
    new.add_argument("--related", action="append", help="related design id")
    new.set_defaults(handler=command_design_new)

    listing = design_sub.add_parser("list", help="list designs and the revise gate")
    root_argument(listing)
    listing.set_defaults(handler=command_design_list)

    show = design_sub.add_parser("show", help="show one design, its links and revisions")
    root_argument(show)
    show.add_argument("--id", required=True)
    show.set_defaults(handler=command_design_show)

    for name, state in (("adopt", "adopted"), ("abandon", "abandoned")):
        resolve = design_sub.add_parser(name, help=f"resolve a design as {state}")
        root_argument(resolve)
        resolve.add_argument("--id", required=True)
        resolve.set_defaults(handler=command_design_resolve, target_state=state)

    supersede = design_sub.add_parser("supersede", help="resolve a design as superseded")
    root_argument(supersede)
    supersede.add_argument("--id", required=True)
    supersede.add_argument("--by", required=True, help="the design that supersedes it")
    supersede.set_defaults(handler=command_design_resolve, target_state="superseded")

    link = design_sub.add_parser("link", help="link one design to another")
    root_argument(link)
    link.add_argument("--from", dest="source", required=True)
    link.add_argument("--to", dest="target", required=True)
    link.add_argument("--role", choices=list(designs.LINK_ROLES), required=True)
    link.set_defaults(handler=command_design_link)

    evaluation = sub.add_parser("evaluations", help="add or list evaluations")
    evaluation.add_argument("action", choices=["add", "list"])
    evaluation.add_argument("--root", default=".")
    evaluation.add_argument("--json", action="store_true")
    evaluation.add_argument("--from", dest="source", help="project evaluation report")
    evaluation.add_argument("--mode")
    evaluation.add_argument("--status")
    evaluation.add_argument("--revision")
    evaluation.add_argument("--design")
    evaluation.set_defaults(handler=command_evaluations)

    rev = sub.add_parser("revisions", help="record or list revisions")
    rev.add_argument("action", choices=["record", "list"])
    rev.add_argument("--root", default=".")
    rev.add_argument("--json", action="store_true")
    rev.add_argument("--message", help="commit-style revision message")
    rev.set_defaults(handler=command_revisions)

    compare = sub.add_parser("compare", help="compare two recorded revisions")
    root_argument(compare)
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    compare.set_defaults(handler=command_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2
    result = handler(args)
    if result is None:
        return 0
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, default=str, sort_keys=True))
    elif isinstance(result, dict) and args.command in {
        "init",
        "status",
        "snapshot",
        "validate",
        "build",
        "audit",
        "eval",
        "findings",
        "design",
        "evaluations",
        "revisions",
        "compare",
    }:
        for key, value in result.items():
            print(f"{key}: {value}")
    if isinstance(result, dict) and result.get("ok") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
