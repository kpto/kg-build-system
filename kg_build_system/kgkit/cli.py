"""Command line entry point for the KG kit.

The package owns the generic surface: the relation catalog, snapshots, the
console, the findings ledger and revision pins. Project operations are declared
as ``commands`` in ``kgkit/config.json``; ``kgkit`` runs them and passes their
JSON through, so the console and a shell use the same contract.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from typing import Any

from . import ledger, project_commands, relations, revisions
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
        # The project owns the graph status; the package adds its own state.
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


def command_eval(args: argparse.Namespace) -> dict[str, Any]:
    mode = "--full" if args.full else "--quick"
    return _project_operation(args, "eval", mode=mode)


def _ledger_path(project: Project):
    return project.path(str(project.config.get("findings") or "kgkit/records/findings"))


def _proposal_path(project: Project):
    return project.path(str(project.config.get("proposals") or "kgkit/records/proposals"))


def command_findings(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    path = _proposal_path(project) if args.layer == "proposal" else _ledger_path(project)
    if args.action == "list":
        rows, errors = ledger.read_ledger(path)
        if args.state:
            rows = [row for row in rows if row.get("state") == args.state]
        return {"ok": True, "count": len(rows), "findings": rows, "errors": errors}
    if args.action != "add":
        return {"ok": False, "error": f"unknown findings action {args.action}"}
    if not args.observation:
        return {"ok": False, "error": "--observation is required"}
    rows, _errors = ledger.read_ledger(path) if path.exists() else ([], [])
    row = {
        "id": ledger.next_id(rows),
        "opened": datetime.now(UTC).isoformat(timespec="seconds"),
        "layer": args.layer or "unspecified",
        "observation": args.observation,
        "evidence": args.evidence or "",
        "decision": args.decision or "",
        "metric": args.metric or "",
        "state": args.state or "proposed",
    }
    result = ledger.append_finding(path, row)
    if result["status"] != "accepted":
        return {"ok": False, "error": "; ".join(result["errors"]), "finding": row}
    return {"ok": True, "finding": row}


def command_propose(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    path = _proposal_path(project)
    rows, _errors = ledger.read_ledger(path) if path.exists() else ([], [])
    row = {
        "id": ledger.next_id(rows),
        "opened": datetime.now(UTC).isoformat(timespec="seconds"),
        "layer": "proposal",
        "subject": args.subject or "",
        "observation": args.instruction,
        "evidence": args.evidence or "",
        "decision": "",
        "metric": args.metric or "",
        "state": "proposed",
    }
    result = ledger.append_finding(path, row)
    if result["status"] != "accepted":
        return {"ok": False, "error": "; ".join(result["errors"]), "proposal": row}
    return {"ok": True, "proposal": row}


def command_proposal(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    rows, _errors = ledger.read_ledger(_proposal_path(project))
    for row in rows:
        if row.get("id") == args.id:
            return {"ok": True, "proposal": row}
    return {"ok": False, "error": f"proposal {args.id} not found"}


def command_decide(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    if args.close:
        state = "closed"
    elif args.reject:
        state = "rejected"
    else:
        state = "accepted"
    path = _ledger_path(project)
    if path.is_dir() and not (path / f"{args.id}.json").is_file():
        candidate = _proposal_path(project)
        if (candidate / f"{args.id}.json").is_file():
            path = candidate
    result = ledger.update_state(path, args.id, state, note=args.note)
    if result["status"] != "accepted":
        return {"ok": False, "error": "; ".join(result["errors"])}
    return {"ok": True, "proposal": result["row"]}


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
        prog="kgkit",
        description="A relational console and project command surface for knowledge graph projects.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def root_argument(command: argparse.ArgumentParser) -> None:
        command.add_argument(
            "--root",
            default=".",
            help=f"project root; its runtime data goes under ./{DATA_DIR_NAME}",
        )
        command.add_argument("--json", action="store_true", help="print JSON")

    init = sub.add_parser("init", help="create kgkit and configure the project")
    root_argument(init)
    init.set_defaults(handler=command_init)

    status = sub.add_parser("status", help="show graph and project state")
    root_argument(status)
    status.set_defaults(handler=command_status)

    rel = sub.add_parser("relations", help="read the relational catalog")
    rel.add_argument("action", choices=["list"])
    rel.add_argument("--root", default=".")
    rel.add_argument("--json", action="store_true")
    rel.set_defaults(handler=command_relations)


    snapshot = sub.add_parser("snapshot", help="import a compiled viewer snapshot")
    snapshot.add_argument("--root", default=".")
    snapshot.add_argument("--from", dest="source", help="snapshot, workflow plan or blueprint file")
    snapshot.add_argument("--command", help="command that produces the snapshot")
    snapshot.add_argument("--revision", help="revision id stored with the snapshot")
    snapshot.add_argument("--title", help="snapshot title")
    snapshot.add_argument("--json", action="store_true")
    snapshot.set_defaults(handler=command_snapshot)

    console = sub.add_parser("console", help="serve the standalone relational console")
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

    evaluate = sub.add_parser("eval", help="run the project evaluation")
    root_argument(evaluate)
    mode = evaluate.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true")
    mode.add_argument("--full", action="store_true")
    evaluate.set_defaults(handler=command_eval)

    findings = sub.add_parser("findings", help="append or list design findings")
    findings.add_argument("action", choices=["add", "list"])
    findings.add_argument("--root", default=".")
    findings.add_argument("--json", action="store_true")
    findings.add_argument("--layer")
    findings.add_argument("--observation")
    findings.add_argument("--evidence")
    findings.add_argument("--decision")
    findings.add_argument("--metric")
    findings.add_argument("--state")
    findings.set_defaults(handler=command_findings)

    propose = sub.add_parser("propose", help="record a design proposal")
    root_argument(propose)
    propose.add_argument("--subject", required=True)
    propose.add_argument("--instruction", required=True)
    propose.add_argument("--evidence")
    propose.add_argument("--metric")
    propose.set_defaults(handler=command_propose)

    proposal = sub.add_parser("proposal", help="read one proposal")
    root_argument(proposal)
    proposal.add_argument("--id", required=True)
    proposal.set_defaults(handler=command_proposal)

    decide = sub.add_parser("decide", help="accept or reject a proposal")
    root_argument(decide)
    decide.add_argument("--id", required=True)
    decision = decide.add_mutually_exclusive_group()
    decision.add_argument("--accept", action="store_true")
    decision.add_argument("--reject", action="store_true")
    decision.add_argument("--close", action="store_true")
    decide.add_argument("--note")
    decide.set_defaults(handler=command_decide)

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
        "propose",
        "proposal",
        "decide",
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
