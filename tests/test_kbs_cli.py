from __future__ import annotations

import json
from pathlib import Path

import pytest

from kg_build_system.cli import main as kbs_main


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    assert kbs_main(["notebook", "repair", "--project", str(root)]) == 0
    return root


def test_top_level_help_describes_one_product(capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        kbs_main(["--help"])
    assert stopped.value.code == 0
    out = " ".join(capsys.readouterr().out.split())
    assert "record findings, proposals, designs, evaluations and revisions" in out
    assert "serve the project console; it embeds the design viewer" in out


def test_notebook_help_lists_its_commands(capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        kbs_main(["notebook", "--help"])
    assert stopped.value.code == 0
    out = capsys.readouterr().out
    assert "usage: kbs notebook" in out
    assert "==SUPPRESS==" not in out
    for command in ("repair", "status", "relations", "findings", "propose", "revisions"):
        assert command in out


def test_notebook_leaf_help_is_namespaced(capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        kbs_main(["notebook", "status", "--help"])
    assert stopped.value.code == 0
    out = capsys.readouterr().out
    assert "usage: kbs notebook status" in out
    assert "--project PROJECT" in out
    assert "--root" not in out


def test_notebook_status_uses_one_directory_flag(tmp_path: Path, capsys) -> None:
    root = _project(tmp_path)
    capsys.readouterr()
    assert kbs_main(["notebook", "status", "--project", str(root), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["notebook"] == str(root / "notebook")

    assert kbs_main(["notebook", "status", "--root", str(root), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["project"] == root.name


def test_human_output_has_no_machine_status_line(tmp_path: Path, capsys) -> None:
    root = _project(tmp_path)
    capsys.readouterr()
    assert kbs_main(["notebook", "status", "--project", str(root)]) == 0
    out = capsys.readouterr().out
    assert not any(line.startswith("ok:") for line in out.splitlines())
    assert f"notebook: {root / 'notebook'}" in out
    assert "kinds:" in out


def test_a_failed_command_writes_an_error_to_stderr(tmp_path: Path, capsys) -> None:
    root = _project(tmp_path)
    capsys.readouterr()
    assert kbs_main(["notebook", "decide", "--project", str(root), "--id", "NOPE", "--accept"]) == 1
    streams = capsys.readouterr()
    assert streams.out == ""
    assert "error: finding or proposal NOPE not found" in streams.err


def test_console_is_top_level_only(tmp_path: Path, capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        kbs_main(["notebook", "console", "--project", str(tmp_path)])
    assert stopped.value.code == 2
    assert "invalid choice: 'console'" in capsys.readouterr().err


def test_init_is_top_level_only(tmp_path: Path, capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        kbs_main(["notebook", "init", "--project", str(tmp_path)])
    assert stopped.value.code == 2
    assert "invalid choice: 'init'" in capsys.readouterr().err


def test_relations_accepts_the_leaf_form_and_the_list_alias(tmp_path: Path, capsys) -> None:
    root = _project(tmp_path)
    capsys.readouterr()
    assert kbs_main(["notebook", "relations", "--project", str(root)]) == 0
    first = capsys.readouterr().out
    assert "project:" in first
    assert "timeline:" in first
    assert kbs_main(["notebook", "relations", "list", "--project", str(root)]) == 0
    assert capsys.readouterr().out == first


def test_console_help_is_top_level_and_has_no_json_flag(capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        kbs_main(["console", "--help"])
    assert stopped.value.code == 0
    out = capsys.readouterr().out
    assert "usage: kbs console" in out
    assert "--project PROJECT" in out
    assert "--api-only" in out
    assert "--viewer-url" not in out
    assert "--json" not in out


def test_snapshot_human_output_is_not_a_raw_result(tmp_path: Path, capsys) -> None:
    root = _project(tmp_path)
    capsys.readouterr()
    (root / "data" / "snapshots").mkdir(parents=True)
    (root / "data" / "snapshots" / "current.snapshot.json").write_text(
        json.dumps(
            {
                "format": "kg-viewer-snapshot",
                "version": 1,
                "name": "demo",
                "title": "Demo",
                "workflow": {"steps": [], "connections": [], "components": []},
            }
        ),
        encoding="utf-8",
    )
    assert kbs_main([
        "notebook", "snapshot", "--project", str(root),
        "--from", "data/snapshots/current.snapshot.json", "--revision", "r1",
    ]) == 0
    out = capsys.readouterr().out
    assert "snapshot:" in out
    assert "history:" in out
    assert "snapshot_file:" not in out
