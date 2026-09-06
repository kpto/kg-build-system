"""The diagnostics service's own logic, without starting the real pyright.

The configuration it writes, the burst-coalescing, the state machine and the crash
recovery are all testable against the stub server from ``test_lsp.py``; the parts that
only the real server can answer are in ``test_lsp_live.py``.
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from studio_backend.diagnostics.lsp import LanguageServerClient, Notification, path_to_uri
from studio_backend.diagnostics.mapping import ANCHORS_RELATIVE_PATH
from studio_backend.diagnostics.problem import Problem
from studio_backend.diagnostics.service import (
    CONFIG_FILENAME,
    DiagnosticsError,
    DiagnosticsService,
    PyrightConfig,
    detect_python_version,
    discover_framework_venv,
    discover_server_command,
    write_pyright_config,
)

FAKE_SERVER = Path(__file__).with_name("fake_language_server.py")
DIAGNOSTIC = {
    "range": {"start": {"line": 14, "character": 13}, "end": {"line": 14, "character": 14}},
    "message": 'Argument of type "Literal[3]" cannot be assigned to parameter "city"',
    "severity": 1,
    "code": "reportArgumentType",
    "source": "Pyright",
}


class FakeStdin:
    """Captures every framed message the client writes."""

    def __init__(self) -> None:
        self.frames: list[bytes] = []

    def write(self, data: bytes) -> int:
        self.frames.append(data)
        return len(data)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        return None

    def methods(self) -> list[str]:
        """The ``method`` of every request/notification written, in order."""
        names: list[str] = []
        for frame in self.frames:
            payload = json.loads(frame.split(b"\r\n\r\n", 1)[1].decode("utf-8"))
            if "method" in payload:
                names.append(payload["method"])
        return names


class FakeProcess:
    """Stands in for ``Popen`` so the client's real write/receive paths run."""

    def __init__(self) -> None:
        self.stdin: FakeStdin = FakeStdin()
        self.stdout = None
        self.stderr = None
        self.returncode: int | None = None

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode or 0

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9

    def pid(self) -> int:
        return 424242


class StubClient(LanguageServerClient):
    """A client with no subprocess: same state machine, no pipes to pyright.

    Only ``start``/``stop`` are replaced, so document bookkeeping (URI mapping,
    version numbers, the open set, the replay list) is the production code.
    """

    def __init__(self, workspace_root: Path, **kwargs: object) -> None:
        super().__init__([sys.executable, str(FAKE_SERVER)], workspace_root, **kwargs)  # type: ignore[arg-type]
        self.started = 0
        self.stopped = 0
        self.server = FakeProcess()

    def start(self) -> None:
        self.started += 1
        self._stopping = False
        self.server = FakeProcess()
        with self._lock:
            self._process = self.server  # type: ignore[assignment]
            self._ready = True

    def stop(self, timeout: float = 5.0) -> None:
        self.stopped += 1
        with self._lock:
            self._ready = False
            self._stopping = True
            process = self._process
            self._process = None
        if process is not None:
            self.server.kill()

    def publish(self, uri: str, diagnostics: list[dict]) -> None:
        """Feed a publish through the client's real notification callback."""
        handler = self._on_notification
        assert handler is not None
        handler(
            Notification(method="textDocument/publishDiagnostics", params={"uri": uri, "diagnostics": diagnostics})
        )

    def crash(self, code: int | None = 1) -> None:
        """Report the server dying, exactly as the dispatch thread would."""
        with self._lock:
            self._ready = False
            alive = self._process is not None
        if alive:
            self.server.returncode = code if code is not None else 1
        callback = self._on_exit
        assert callback is not None
        callback(code)

    def message_pairs(self) -> tuple[set[str], set[str]]:
        """The URIs closed and the URIs opened, in the frames written so far."""
        closed: set[str] = set()
        opened: set[str] = set()
        for frame in self.frames.frames:
            payload = json.loads(frame.split(b"\r\n\r\n", 1)[1].decode("utf-8"))
            method = payload.get("method")
            uri = (payload.get("params") or {}).get("textDocument", {}).get("uri")
            if method == "textDocument/didClose" and uri:
                closed.add(uri)
            elif method == "textDocument/didOpen" and uri:
                opened.add(uri)
        return closed, opened

    @property
    def frames(self) -> FakeStdin:
        """The messages this client has written to its (imaginary) server."""
        return self.server.stdin


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "estate"
    package = root / "kg_project"
    (package / "bindings" / "site").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "build.py").write_text("from kg_project import bindings\n", encoding="utf-8")
    (package / "bindings" / "__init__.py").write_text("", encoding="utf-8")
    binding = package / "bindings" / "site" / "__init__.py"
    binding.write_text(
        "site_binding = None\n\n\n\n\n\n\n\n\n\n\n\nproperties = object()\n  city = 3\n",
        encoding="utf-8",
    )
    (root / ANCHORS_RELATIVE_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / ANCHORS_RELATIVE_PATH).write_text(
        json.dumps(
            {
                "format_version": 1,
                "revision": 3,
                "document_fingerprint": "sha256-x",
                "files": {
                    "kg_project/bindings/site/__init__.py": [
                        {
                            "ref": "binding:site_binding.property.city",
                            "line": 15,
                            "end_line": 15,
                            "column": 3,
                            "end_column": 20,
                            "node": "keyword",
                        },
                        {
                            "ref": "binding:site_binding",
                            "line": 1,
                            "end_line": 16,
                            "column": 1,
                            "end_column": 1,
                            "node": "file",
                        },
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    return root


# ---------------------------------------------------------------- the config file


def test_the_config_is_written_before_the_server_starts(project: Path) -> None:
    seen: list[bool] = []

    def factory(on_notification, on_exit) -> LanguageServerClient:
        # The config must already exist when the server is launched, or pyright reads
        # whatever the previous tool left in the project.
        seen.append((project / CONFIG_FILENAME).is_file())
        return StubClient(project, on_notification=on_notification, on_exit=on_exit)

    service = DiagnosticsService(
        project, "kg_project", framework_venv=discover_framework_venv(), client_factory=factory
    )
    service.start()
    try:
        assert service.state == "ready", service.state_message
        assert seen == [True]
        config = json.loads((project / CONFIG_FILENAME).read_text(encoding="utf-8"))
        assert config["include"] == ["kg_project"]
        assert config["strict"] == ["kg_project"]
        assert config["typeCheckingMode"] == "basic"
        assert config["reportMissingTypeStubs"] is False
        assert config["venv"] == ".venv"
        assert Path(config["venvPath"]).is_absolute()
        assert (Path(config["venvPath"]) / config["venv"] / "pyvenv.cfg").is_file()
    finally:
        service.stop()


def test_the_config_replaces_what_was_there(project: Path) -> None:
    (project / CONFIG_FILENAME).write_text('{"oldKey": 1, "include": ["elsewhere"]}', encoding="utf-8")
    write_pyright_config(project, "kg_project", framework_venv=discover_framework_venv())
    config = json.loads((project / CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert "oldKey" not in config
    assert config["include"] == ["kg_project"]


def test_a_stale_config_path_is_honoured(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "pkg").mkdir(parents=True)
    target = tmp_path / "elsewhere" / "pyrightconfig.json"
    write_pyright_config(root, "pkg", target, framework_venv=discover_framework_venv())
    assert target.is_file()
    assert not (root / CONFIG_FILENAME).exists()


def test_the_config_json_shape() -> None:
    config = PyrightConfig(package="kg_project", venv_path=Path("/opt/envs/.venv"), python_version="3.12")
    assert config.as_json()["venvPath"] == "/opt/envs"
    assert config.as_json()["venv"] == ".venv"
    assert config.as_json()["pythonVersion"] == "3.12"
    assert config.venv_name == ".venv"


def test_an_unusable_venv_is_reported_not_written(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    with pytest.raises(DiagnosticsError):
        detect_python_version(tmp_path / "not-a-venv")


def test_python_version_comes_from_the_venv_itself(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\nversion_info = 3.11.9\n", encoding="utf-8")
    assert detect_python_version(venv) == "3.11"


def test_a_venv_without_a_version_is_an_error(tmp_path: Path) -> None:
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    with pytest.raises(DiagnosticsError, match="does not state"):
        detect_python_version(venv)


def test_server_discovery_reports_a_missing_pyright(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KG_STUDIO_PYRIGHT_LANGSERVER", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr("sys.prefix", sys.base_prefix)
    monkeypatch.setattr("studio_backend.diagnostics.service.DEFAULT_FRAMEWORK_ROOT", tmp_path)
    with pytest.raises(DiagnosticsError, match="pyright-langserver is not installed"):
        discover_server_command(tmp_path / "nope")


def test_the_server_command_override_is_used(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KG_STUDIO_PYRIGHT_LANGSERVER", "/opt/custom/pyright-langserver")
    assert discover_server_command() == ["/opt/custom/pyright-langserver", "--stdio"]


# ------------------------------------------------------------------- the pipeline


def published_for(root: Path, relative: str = "kg_project/bindings/site/__init__.py") -> tuple[str, list[dict]]:
    return path_to_uri(root / relative), [dict(DIAGNOSTIC)]


def test_snapshot_maps_publishes_onto_refs(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    try:
        uri, diagnostics = published_for(project)
        client.publish(uri, diagnostics)
        problems = wait_for(lambda: service.snapshot())
        assert problems is not None
        [problem] = problems
        assert problem.tier == "types"
        assert problem.severity == "error"
        assert problem.code == "reportArgumentType"
        assert problem.file == "kg_project/bindings/site/__init__.py"
        assert (problem.line, problem.column) == (15, 14)
        assert (problem.end_line, problem.end_column) == (15, 15)
        assert problem.ref == "binding:site_binding.property.city"
        assert problem.ref_trusted == "anchor"
        assert problem.hint and "city" in problem.hint
    finally:
        service.stop()


def test_severity_and_hint_tiers_map(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    try:
        uri, _ = published_for(project)
        client.publish(
            uri,
            [
                {"range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
                 "message": "Import is not accessed", "severity": 4, "code": "reportUnusedImport"},
                {"range": {"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 1}},
                 "message": "Unreachable", "severity": 2, "code": "reportUnreachable"},
                {"range": {"start": {"line": 2, "character": 0}, "end": {"line": 2, "character": 1}},
                 "message": "Deprecated", "severity": 3, "code": "reportDeprecated"},
            ],
        )
        problems = wait_for(lambda: len(service.snapshot()) >= 3 and service.snapshot())
        assert problems is not None
        by_code = {item.code: item for item in problems}
        # LSP 1=error, 2=warning, 3=info, 4=hint; the contract has no hint band.
        assert by_code["reportUnusedImport"].severity == "info"
        assert by_code["reportUnreachable"].severity == "warning"
        assert by_code["reportDeprecated"].severity == "info"
    finally:
        service.stop()


def test_the_rule_in_data_rule_wins_over_the_generic_code(project: Path) -> None:
    """pyright only fills ``data.rule`` for some diagnostics; both spellings arrive."""
    service = make_service(project)
    client = start_with_stub(service)
    try:
        uri, _ = published_for(project)
        client.publish(
            uri,
            [
                {
                    "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
                    "message": "Import is not accessed",
                    "severity": 4,
                    "code": "reportUnusedImport",
                    "data": {"rule": "reportUnusedImport", "category": 4},
                },
                {
                    "range": {"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 1}},
                    "message": "no rule here",
                    "severity": 1,
                },
            ],
        )
        problems = wait_for(lambda: len(service.snapshot()) >= 2 and service.snapshot())
        assert problems is not None
        assert {item.code for item in problems} == {"reportUnusedImport", None}
    finally:
        service.stop()


def test_a_burst_of_publishes_becomes_one_snapshot(project: Path) -> None:
    service = make_service(project, debounce_seconds=0.3)
    client = start_with_stub(service)
    events: list[int] = []
    service.subscribe(lambda problems: events.append(len(problems)))
    try:
        uri, diagnostics = published_for(project)
        for index in range(6):
            client.publish(uri, [dict(diagnostics[0], message=f"burst {index}")])
        time.sleep(0.9)
        assert len(events) == 1, f"expected one coalesced snapshot, got {events}"
        assert events[0] == 1
    finally:
        service.stop()


def test_snapshot_flushes_without_waiting_for_the_quiet_period(project: Path) -> None:
    service = make_service(project, debounce_seconds=30.0)
    client = start_with_stub(service)
    try:
        uri, diagnostics = published_for(project)
        client.publish(uri, diagnostics)
        assert service.snapshot(), "snapshot() must not have to wait out the debounce"
    finally:
        service.stop()


def test_an_empty_publish_clears_the_file(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    try:
        uri, diagnostics = published_for(project)
        client.publish(uri, diagnostics)
        assert wait_for(lambda: service.snapshot())
        client.publish(uri, [])
        deadline = time.time() + 5.0
        while time.time() < deadline and service.snapshot():
            time.sleep(0.05)
        assert service.snapshot() == []
    finally:
        service.stop()


def test_unsubscribing_stops_delivery(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    events: list[int] = []
    unsubscribe = service.subscribe(lambda problems: events.append(len(problems)))
    try:
        unsubscribe()
        uri, diagnostics = published_for(project)
        client.publish(uri, diagnostics)
        time.sleep(0.4)
        assert events == []
    finally:
        service.stop()


def test_status_counts_and_state(project: Path) -> None:
    service = make_service(project)
    assert service.state == "starting"
    client = start_with_stub(service)
    try:
        assert service.state == "ready"
        uri, diagnostics = published_for(project)
        client.publish(uri, diagnostics)
        assert wait_for(lambda: service.snapshot())
        deadline = time.time() + 5.0
        while time.time() < deadline and service.status()["errors"] == 0:
            time.sleep(0.05)
        assert service.status() == {"errors": 1, "warnings": 0, "state": "ready"}
    finally:
        service.stop()


def test_problems_returns_json(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    try:
        uri, diagnostics = published_for(project)
        client.publish(uri, diagnostics)
        assert wait_for(lambda: service.problems())
        [payload] = service.problems()
        assert payload["tier"] == "types"
        assert payload["ref"] == "binding:site_binding.property.city"
        assert set(payload) == {
            "id", "tier", "severity", "message", "code", "file", "line", "column",
            "end_line", "end_column", "ref", "ref_trusted", "hint",
        }
    finally:
        service.stop()


# ---------------------------------------------------------------- the file set


def test_every_owned_python_file_is_opened(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    try:
        assert client.frames.methods().count("textDocument/didOpen") == 4
        assert service.files_open == len(service.owned_files()) == 4
        opened_uris = {uri for uri in client.open_documents}
        assert all(uri.endswith(".py") for uri in opened_uris)
    finally:
        service.stop()


def test_reopen_reopens_changed_files_and_drops_deleted_ones(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    binding = project / "kg_project" / "bindings" / "site" / "__init__.py"
    vanished = project / "kg_project" / "build.py"
    try:
        assert path_to_uri(binding) in client.open_documents
        vanished.unlink()
        client.frames.frames.clear()
        service.reopen(["kg_project/bindings/site/__init__.py"])

        closed, opened = client.message_pairs()
        # The vanished file is closed and never reopened; the changed one is closed
        # and reopened from disk.
        assert path_to_uri(vanished) in closed
        assert path_to_uri(vanished) not in opened
        assert path_to_uri(binding) in closed and path_to_uri(binding) in opened
        assert path_to_uri(vanished) not in client.open_documents
        assert path_to_uri(binding) in client.open_documents
    finally:
        service.stop()


def test_reopen_without_a_file_list_reopens_the_package(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    try:
        owned = set(client.open_documents)
        client.frames.frames.clear()
        service.reopen()
        closed, opened = client.message_pairs()
        assert closed == opened == owned, "every owned buffer must be closed then reopened"
    finally:
        service.stop()


def test_a_new_anchor_index_is_picked_up_without_a_restart(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    try:
        uri, diagnostics = published_for(project)
        client.publish(uri, diagnostics)
        assert wait_for(lambda: service.snapshot())
        assert service.snapshot()[0].ref_trusted == "anchor"

        # Rewrite the index so the position no longer falls in a range: the next
        # snapshot must fall back to the file's owner rather than reuse the old map.
        (project / ANCHORS_RELATIVE_PATH).write_text(
            json.dumps(
                {
                    "format_version": 1,
                    "revision": 4,
                    "document_fingerprint": "sha256-y",
                    "files": {
                        "kg_project/bindings/site/__init__.py": [
                            {
                                "ref": "binding:site_binding",
                                "line": 1,
                                "end_line": 16,
                                "column": 1,
                                "end_column": 1,
                                "node": "file",
                            }
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
        time.sleep(0.05)
        client.publish(uri, [])
        client.publish(uri, [dict(DIAGNOSTIC, message="re-published after regeneration")])
        problems = wait_for(
            lambda: [
                item
                for item in service.snapshot()
                if item.message == "re-published after regeneration"
            ]
        )
        assert problems is not None
        assert problems[0].ref == "binding:site_binding"
        assert problems[0].ref_trusted == "file"
    finally:
        service.stop()


def test_an_unreadable_anchor_index_degrades_to_name_matching(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    try:
        (project / ANCHORS_RELATIVE_PATH).write_text("{ broken", encoding="utf-8")
        uri, diagnostics = published_for(project)
        client.publish(uri, diagnostics)
        problems = wait_for(lambda: service.snapshot())
        assert problems is not None
        # No anchors at all, and the message names no declaration: unmappable, and
        # the UI must be able to show it as such.
        assert problems[0].ref is None
        assert problems[0].ref_trusted is None
    finally:
        service.stop()


# ------------------------------------------------------------- crash and startup


def test_a_failed_start_is_recorded_not_raised(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "kg_project").mkdir(parents=True)
    service = DiagnosticsService(root, "kg_project", server_command=[str(root / "no-such-server")])
    service.start()
    try:
        assert service.state == "error"
        assert "no-such-server" in (service.state_message or "")
        assert service.snapshot() == []
        assert service.status()["state"] == "error"
    finally:
        service.stop()


def test_an_unusable_environment_is_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "project"
    (root / "kg_project").mkdir(parents=True)
    monkeypatch.setenv("KG_STUDIO_PYRIGHT_VENV", str(tmp_path / "definitely-not-a-venv"))
    monkeypatch.setattr("sys.prefix", sys.base_prefix)  # no interpreter venv either
    monkeypatch.setattr(
        "studio_backend.diagnostics.service.DEFAULT_FRAMEWORK_ROOT", tmp_path / "no-checkout"
    )
    service = DiagnosticsService(root, "kg_project")
    service.start()
    try:
        assert service.state == "error"
        assert "kg_build_system" in (service.state_message or "")
    finally:
        service.stop()


def test_a_crash_restarts_the_server_and_clears_stale_problems(project: Path) -> None:
    service = make_service(project, debounce_seconds=0.05)
    client = start_with_stub(service)
    try:
        uri, diagnostics = published_for(project)
        client.publish(uri, diagnostics)
        assert wait_for(lambda: service.snapshot())
        assert service.state == "ready"
        client.set_restart_delay(0.01)

        client.crash(1)
        assert wait_for(lambda: client.started == 2), "the server must be relaunched exactly once"
        assert wait_for(lambda: service.snapshot() == []), "a restart must not keep old problems"
        assert service.state == "ready", service.state_message
        assert service.files_open == 4, "every owned file must be reopened after a crash"

        # ...and the pipeline still works afterwards.
        client.publish(uri, diagnostics)
        assert wait_for(lambda: service.snapshot())
    finally:
        service.stop()


def test_stop_is_idempotent(project: Path) -> None:
    service = make_service(project)
    start_with_stub(service)
    service.stop()
    service.stop()
    assert service.state == "ready"


def make_service(root: Path, *, debounce_seconds: float = 0.05) -> DiagnosticsService:
    clients: list[StubClient] = []

    def factory(
        on_notification: Callable[[Notification], None], on_exit: Callable[[int | None], None]
    ) -> LanguageServerClient:
        client = StubClient(root, on_notification=on_notification, on_exit=on_exit)
        clients.append(client)
        return client

    service = DiagnosticsService(
        root,
        "kg_project",
        framework_venv=discover_framework_venv(),
        client_factory=factory,
        debounce_seconds=debounce_seconds,
    )
    service.clients = clients  # type: ignore[attr-defined]
    return service


def start_with_stub(service: DiagnosticsService) -> StubClient:
    """Start the service and hand back the stub client it built."""
    service.start()
    clients: list[StubClient] = service.clients  # type: ignore[attr-defined]
    assert clients, "the service never built a client"
    return clients[-1]


def wait_for(predicate, timeout: float = 6.0, interval: float = 0.05):
    """Poll until ``predicate`` returns something truthy, then hand it back."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return None


def test_problems_are_sorted_and_deterministic(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    try:
        uri, diagnostics = published_for(project)
        second = dict(diagnostics[0], message="a second one", code="reportGeneralTypeIssues")
        client.publish(uri, [second, diagnostics[0]])
        problems = wait_for(lambda: len(service.snapshot()) >= 2 and service.snapshot())
        assert problems is not None
        keys = [(item.file, item.line, item.column, item.code) for item in problems]
        assert keys == sorted(keys)
    finally:
        service.stop()


def test_an_unopened_file_reports_its_path_when_outside_the_root(project: Path, tmp_path: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    try:
        outside = tmp_path / "elsewhere.py"
        outside.write_text("x = 1\n", encoding="utf-8")
        client.publish(path_to_uri(outside), [dict(DIAGNOSTIC)])
        problems = wait_for(lambda: service.snapshot())
        assert problems is not None
        assert problems[0].file == outside.as_posix()
        assert problems[0].ref is None
    finally:
        service.stop()


def test_problem_ids_are_stable_across_snapshots(project: Path) -> None:
    service = make_service(project)
    client = start_with_stub(service)
    try:
        uri, diagnostics = published_for(project)
        client.publish(uri, diagnostics)
        first = wait_for(lambda: service.snapshot())
        assert first is not None
        client.publish(uri, [])
        deadline = time.time() + 5.0
        while time.time() < deadline and service.snapshot():
            time.sleep(0.05)
        client.publish(uri, diagnostics)
        second = wait_for(lambda: len(service.snapshot()) == 1 and service.snapshot())
        assert second is not None
        assert first[0].id == second[0].id
    finally:
        service.stop()


def test_problem_json_round_trips() -> None:
    problem = Problem(
        id="x",
        tier="types",
        severity="error",
        message="m",
        code=None,
        file=None,
        line=None,
        column=None,
        end_line=None,
        end_column=None,
        ref=None,
        ref_trusted=None,
        hint=None,
    )
    assert json.loads(json.dumps(problem.as_json()))["tier"] == "types"
