"""The project notebook command surface, mounted as ``kbs notebook``.

The notebook records the project's findings, proposals, change designs,
revisions and captured views. Project operations are declared as ``commands`` in
``notebook/config.json``; the notebook runs them and passes their JSON through, so
the console and a shell use the same contract.

The same command table is mounted in two places: ``kbs notebook`` from the main
CLI and ``build_parser`` for a direct invocation. A command reports one result;
human output is key/value text and ``--json`` prints the same result as JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from typing import Any, Sequence

from . import ledger, project_commands, relations, revisions
from .config import DATA_DIR_NAME, Project, load_project, write_config_file
from .snapshot import import_snapshot


def _action(arguments: argparse.Namespace) -> str:
    return str(getattr(arguments, "command", "") or "")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return str(value)


def _first_line(value: Any) -> str:
    return next((line.strip() for line in str(value or "").splitlines() if line.strip()), "")


def _compact(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{key}={_compact(item)}" for key, item in value.items())
    if isinstance(value, list):
        return f"{len(value)} items"
    return _text(value)


def _print_row(item: dict[str, Any], indent: int = 0) -> None:
    pad = "  " * indent
    parts: list[str] = []
    for key in ("id", "revision", "design_id"):
        if item.get(key):
            parts.append(str(item[key]))
            break
    for key in ("state", "status"):
        if item.get(key):
            parts.append(str(item[key]))
    label = (
        item.get("observation")
        or item.get("title")
        or item.get("summary")
        or item.get("instruction")
        or item.get("message")
    )
    if label:
        parts.append(_first_line(label))
    if not parts:
        parts.append(_compact(item))
    print(f"{pad}{'  '.join(parts)}")


def _print_mapping(mapping: dict[str, Any], indent: int = 0) -> None:
    pad = "  " * indent
    for key, value in mapping.items():
        if key in {"ok", "error"}:
            continue
        if value is None or value == "":
            continue
        if isinstance(value, dict):
            if not value:
                print(f"{pad}{key}: none")
                continue
            print(f"{pad}{key}:")
            _print_mapping(value, indent + 1)
        elif isinstance(value, list):
            print(f"{pad}{key}: {len(value)}")
            for item in value:
                if isinstance(item, dict):
                    _print_row(item, indent + 1)
                else:
                    print(f"{pad}  {_text(item)}")
        else:
            print(f"{pad}{key}: {_text(value)}")


def _print_relations(payload: dict[str, Any]) -> None:
    objects = payload.get("objects") or []
    events = payload.get("timeline") or []
    kinds: dict[str, int] = {}
    for item in objects:
        kind = str(item.get("kind") or "")
        kinds[kind] = kinds.get(kind, 0) + 1
    print(f"project: {payload.get('project', '')}")
    print(f"objects: {len(objects)}")
    if not kinds:
        print("kinds: none")
    else:
        print("kinds:")
        for kind in sorted(kinds):
            print(f"  {kind}: {kinds[kind]}")
    print(f"timeline: {len(events)}")
    for event in events:
        print(
            f"  {event.get('timestamp', '')}  {str(event.get('type', '')):<18} {event.get('title', '')}"
        )


def _print_snapshot(result: dict[str, Any]) -> None:
    print(f"snapshot: {result.get('snapshot', '')}")
    print(f"history: {result.get('snapshot_history', '')}")
    print(f"revision: {result.get('revision') or 'none'}")
    print(f"source: {result.get('source', '')}")
    print(f"saved_at: {result.get('saved_at', '')}")


def _print_findings(result: dict[str, Any]) -> None:
    rows = result.get("findings") or []
    print(f"findings: {len(rows)}")
    for row in rows:
        parts = [str(row.get("id") or ""), str(row.get("layer") or ""), str(row.get("state") or "")]
        label = _first_line(row.get("observation"))
        line = "  ".join(part for part in parts if part)
        print(f"  {line}  {label}".rstrip())
    errors = result.get("errors") or []
    if errors:
        print(f"errors: {len(errors)}")


def _print_revisions(result: dict[str, Any]) -> None:
    rows = result.get("revisions") or []
    print(f"revisions: {len(rows)}")
    for row in rows:
        counts = row.get("counts") or {}
        count_text = _compact(counts) if counts else ""
        line = f"  {row.get('revision', '')}  {row.get('recorded_at') or ''}".rstrip()
        print(f"{line}  {count_text}".rstrip())


def _print_revision_record(result: dict[str, Any]) -> None:
    facts = result.get("facts") or {}
    print(f"revision: {facts.get('revision', '')}")
    print(f"recorded_at: {facts.get('recorded_at', '')}")
    print(f"path: {result.get('path', '')}")
    print(f"event: {result.get('event', '')}")
    evaluation = facts.get("evaluation")
    if isinstance(evaluation, dict) and evaluation.get("status"):
        print(f"evaluation: {evaluation['status']}")


def _render(arguments: argparse.Namespace, result: Any) -> int:
    if result is None:
        return 0
    failed = isinstance(result, dict) and result.get("ok") is False
    if getattr(arguments, "json", False):
        print(json.dumps(result, indent=2, default=str, sort_keys=True))
        return 1 if failed else 0
    if failed:
        print(f"error: {result.get('error') or 'command failed'}", file=sys.stderr)
        return 1
    if not isinstance(result, dict):
        print(result)
        return 0
    action = _action(arguments)
    if action == "relations":
        _print_relations(result)
    elif action == "snapshot" and {"snapshot", "snapshot_history"} <= result.keys():
        _print_snapshot(result)
    elif action == "findings" and isinstance(result.get("findings"), list):
        _print_findings(result)
    elif action == "revisions" and isinstance(result.get("revisions"), list):
        _print_revisions(result)
    elif action == "revisions":
        _print_revision_record(result)
    else:
        _print_mapping(result)
    return 0


def _run(arguments: argparse.Namespace) -> int:
    handler = getattr(arguments, "handler", None)
    if handler is None:
        return 2
    try:
        result = handler(arguments)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return _render(arguments, result)


def _summary(project: Project, payload: dict[str, Any]) -> dict[str, Any]:
    objects = payload.get("objects", [])
    counts: dict[str, int] = {}
    for item in objects:
        counts[str(item.get("kind"))] = counts.get(str(item.get("kind")), 0) + 1
    return {
        "ok": True,
        "project": project.name,
        "root": str(project.root),
        "notebook": str(project.data_dir),
        "objects": len(objects),
        "timeline": len(payload.get("timeline", [])),
        "kinds": counts,
    }


def command_init(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root).ensure(write_config=True)
    write_config_file(project)
    return {
        "ok": True,
        "project": project.name,
        "root": str(project.root),
        "notebook": str(project.data_dir),
        "config": str(project.config_path),
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
    return relations.graph(load_project(args.root))


def command_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    if project_commands.command(project, "snapshot") is not None:
        return project_commands.run(project, "snapshot")
    return import_snapshot(
        project,
        source=args.source,
        command=args.snapshot_command,
        revision=args.revision,
        title=args.title,
    )


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
    return project.path(str(project.config.get("findings") or "notebook/records/findings"))


def _proposal_path(project: Project):
    return project.path(str(project.config.get("proposals") or "notebook/records/proposals"))


def command_findings(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    path = _proposal_path(project) if args.layer == "proposal" else _ledger_path(project)
    if args.action == "list":
        rows, errors = ledger.read_ledger(path)
        if args.state:
            rows = [row for row in rows if row.get("state") == args.state]
        return {"ok": True, "findings": rows, "errors": errors}
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
        "id": ledger.next_id(rows, prefix="P"),
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
        errors = [
            str(error).replace(
                f"finding {args.id} not found",
                f"finding or proposal {args.id} not found",
            )
            for error in result["errors"]
        ]
        return {"ok": False, "error": "; ".join(errors)}
    key = "proposal" if path == _proposal_path(project) else "finding"
    return {"ok": True, key: result["row"]}


def command_revisions(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    if args.action == "record":
        return revisions.record_revision(project, message=args.message)
    return revisions.list_revisions(project)


def command_compare(args: argparse.Namespace) -> dict[str, Any]:
    project = load_project(args.root)
    return revisions.compare_revisions(project, args.before, args.after)


def _project_argument(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--project",
        dest="root",
        metavar="PROJECT",
        default=".",
        help=f"project directory; its notebook is ./{DATA_DIR_NAME}",
    )
    command.add_argument("--root", dest="root", metavar="PROJECT", help=argparse.SUPPRESS)
    command.add_argument("--json", action="store_true", help="print JSON")


def _register(
    sub: Any,
    name: str,
    handler: Any,
    *,
    help: str,
) -> argparse.ArgumentParser:
    command = sub.add_parser(name, help=help)
    _project_argument(command)
    command.set_defaults(handler=handler, command_handler=_run)
    return command


def add_notebook_commands(sub: Any) -> None:
    """Add the notebook's commands to an existing subparser registry."""

    _register(
        sub, "repair", command_init,
        help="create the notebook directory, config and records if missing",
    )

    _register(sub, "status", command_status, help="show the project and notebook state")

    rel = sub.add_parser("relations", help="print the catalog and iteration timeline")
    rel.add_argument("action", nargs="?", choices=["list"], default="list")
    _project_argument(rel)
    rel.set_defaults(handler=command_relations, command_handler=_run)

    snapshot = sub.add_parser("snapshot", help="import the latest compiled viewer snapshot")
    snapshot.add_argument("--from", dest="source", help="snapshot, workflow plan or blueprint file")
    snapshot.add_argument(
        "--command", dest="snapshot_command",
        help="command that produces the snapshot",
    )
    snapshot.add_argument("--revision", help="revision id stored with the snapshot")
    snapshot.add_argument("--title", help="snapshot title")
    _project_argument(snapshot)
    snapshot.set_defaults(handler=command_snapshot, command_handler=_run)

    for name, handler, text in (
        ("validate", command_validate, "run the project's validate command"),
        ("build", command_build, "run the project's build command"),
        ("audit", command_audit, "run the project's audit command"),
    ):
        _register(sub, name, handler, help=text)

    evaluate = _register(sub, "eval", command_eval, help="run the project's evaluation command")
    mode = evaluate.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true")
    mode.add_argument("--full", action="store_true")

    findings = sub.add_parser("findings", help="append or list notebook findings")
    findings.add_argument("action", choices=["add", "list"])
    findings.add_argument("--layer")
    findings.add_argument("--observation")
    findings.add_argument("--evidence")
    findings.add_argument("--decision")
    findings.add_argument("--metric")
    findings.add_argument("--state")
    _project_argument(findings)
    findings.set_defaults(handler=command_findings, command_handler=_run)

    propose = _register(sub, "propose", command_propose, help="record a change proposal")
    propose.add_argument("--subject", required=True)
    propose.add_argument("--instruction", required=True)
    propose.add_argument("--evidence")
    propose.add_argument("--metric")

    proposal = _register(sub, "proposal", command_proposal, help="read one proposal")
    proposal.add_argument("--id", required=True)

    decide = _register(sub, "decide", command_decide, help="accept, reject or close a finding or proposal")
    decide.add_argument("--id", required=True)
    decision = decide.add_mutually_exclusive_group()
    decision.add_argument("--accept", action="store_true")
    decision.add_argument("--reject", action="store_true")
    decision.add_argument("--close", action="store_true")
    decide.add_argument("--note")

    rev = sub.add_parser("revisions", help="record or list revisions")
    rev.add_argument("action", choices=["record", "list"])
    rev.add_argument("--message", help="revision message")
    _project_argument(rev)
    rev.set_defaults(handler=command_revisions, command_handler=_run)

    compare = _register(sub, "compare", command_compare, help="compare two recorded revisions")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kbs notebook",
        description=(
            "Record findings, proposals, change designs, revisions and captured "
            "views for the project, and read the notebook catalog."
        ),
        epilog=(
            "The notebook lives in ./notebook. A project command is a JSON contract "
            "declared under 'commands' in notebook/config.json."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    add_notebook_commands(sub)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    return _run(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
