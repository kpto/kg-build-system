"""The JSON-RPC client's framing, correlation and dispatch.

Every test drives a real subprocess (``fake_language_server.py``), so the byte
handling, the id correlation and the notification routing are exercised as they will
be against pyright — only the peer is fake. The real one is covered by
``tests/test_lsp_live.py``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from studio_backend.diagnostics.lsp import (
    LanguageServerClient,
    LspError,
    LspServerCrash,
    LspStartupError,
    LspTimeout,
    Notification,
    _take_frame,
    path_to_uri,
    uri_to_path,
)

FAKE_SERVER = Path(__file__).with_name("fake_language_server.py")


def command(*mode: str) -> list[str]:
    return [sys.executable, str(FAKE_SERVER), *mode]


def crash_command(sentinel: Path) -> list[str]:
    """A stub that crashes once, then behaves normally for the restarted client."""
    return command("crash_after_notify", str(sentinel))


class Recorder:
    """Collects notifications and crash reports delivered on the dispatch thread."""

    def __init__(self) -> None:
        self.notifications: list[Notification] = []
        self.exit_codes: list[int | None] = []
        self._wake = threading.Event()

    def on_notification(self, notification: Notification) -> None:
        self.notifications.append(notification)
        self._wake.set()

    def on_exit(self, code: int | None) -> None:
        self.exit_codes.append(code)
        self._wake.set()

    def wait_for(self, method: str, timeout: float = 8.0) -> Notification | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            for item in list(self.notifications):
                if item.method == method:
                    return item
            self._wake.wait(0.05)
            self._wake.clear()
        return None

    def wait_for_exit(self, timeout: float = 8.0) -> list[int | None]:
        deadline = time.time() + timeout
        while time.time() < deadline and not self.exit_codes:
            self._wake.wait(0.05)
            self._wake.clear()
        return list(self.exit_codes)


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()


@pytest.fixture
def client(tmp_path: Path, recorder: Recorder):
    """A started client, always stopped and reaped even when a test fails."""
    instance = LanguageServerClient(
        command(),
        tmp_path,
        initialization_options={"typeCheckingMode": "basic"},
        on_notification=recorder.on_notification,
        on_exit=recorder.on_exit,
        request_timeout=6.0,
    )
    instance.start()
    try:
        yield instance
    finally:
        instance.stop(timeout=2.0)
        assert not instance.alive


def process_alive(pid: int | None) -> bool:
    """True while ``pid`` is a live process we can signal."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # pragma: no cover - cannot happen for our own children
        return True
    return True


def own_children() -> list[int]:
    """Pids of direct children of this test process."""
    listing = subprocess.run(
        ["ps", "-o", "pid=,comm=", "--ppid", str(os.getpid())],
        capture_output=True,
        text=True,
        check=False,
    )
    if listing.returncode != 0:
        pytest.skip("ps does not report child processes here")
    pids: list[int] = []
    for line in listing.stdout.splitlines():
        fields = line.split()
        # ``ps`` is itself a child of this process, and counting it would make every
        # snapshot disagree with the last.
        if len(fields) >= 2 and fields[1] != "ps":
            pids.append(int(fields[0]))
    return sorted(pids)


# ---------------------------------------------------------------------- framing


def test_take_frame_waits_for_the_whole_body() -> None:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}).encode("utf-8")
    partial = bytearray(b"Content-Length: %d\r\n\r\n" % len(body)) + body[: len(body) // 2]
    assert _take_frame(partial) == (None, 0)


def test_take_frame_waits_for_the_header_terminator() -> None:
    assert _take_frame(bytearray(b"Content-Length: 12\r\n")) == (None, 0)


def test_take_frame_pops_one_message_and_reports_its_size() -> None:
    first = json.dumps({"jsonrpc": "2.0", "method": "a"}).encode("utf-8")
    second = json.dumps({"jsonrpc": "2.0", "method": "b"}).encode("utf-8")
    header = b"Content-Length: %d\r\n\r\n"
    buffer = bytearray(header % len(first) + first + header % len(second) + second)

    message, consumed = _take_frame(buffer)
    assert message is not None and message["method"] == "a"
    assert consumed == len(header % len(first)) + len(first)

    rest, second_size = _take_frame(buffer[consumed:])
    assert rest is not None and rest["method"] == "b"
    assert consumed + second_size == len(buffer)


def test_a_frame_without_a_content_length_is_an_error() -> None:
    with pytest.raises(LspError, match="Content-Length"):
        _take_frame(bytearray(b"X-Other: 1\r\n\r\n{}"))


def test_a_frame_whose_body_is_not_json_is_an_error() -> None:
    with pytest.raises(LspError, match="malformed JSON-RPC"):
        _take_frame(bytearray(b'Content-Length: 6\r\n\r\n{"a": '))


def test_a_content_length_spanning_the_header_boundary_is_honoured() -> None:
    """The body may arrive with the header, in one piece, and must not be re-read."""
    body = json.dumps({"jsonrpc": "2.0", "method": "a"}).encode("utf-8")
    frame = bytearray(b"content-length:   %d  \r\n\r\n" % len(body) + body)
    message, consumed = _take_frame(frame)
    assert message is not None and message["method"] == "a"
    assert consumed == len(frame)


def test_uris_round_trip_through_paths(tmp_path: Path) -> None:
    path = tmp_path / "kg project" / "with space.py"
    uri = path_to_uri(path)
    assert uri.startswith("file:///")
    assert "%20" in uri
    assert uri_to_path(uri) == path


def test_path_to_uri_does_not_resolve_symlinks(tmp_path: Path) -> None:
    """The server echoes the URI back, so it must match the path we were handed."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    assert path_to_uri(link / "a.py") == "file://" + str(link / "a.py")


def test_uri_to_path_rejects_other_schemes() -> None:
    with pytest.raises(LspError, match="not a file URI"):
        uri_to_path("vscode-notebook-cell:/tmp/x.ipynb")


def test_resolve_command_reports_a_missing_executable() -> None:
    with pytest.raises(LspStartupError, match="not found"):
        LanguageServerClient.resolve_command(["definitely-not-a-language-server", "--stdio"])


# -------------------------------------------------------------------- handshake


def test_initialize_sends_the_workspace_and_options(tmp_path: Path) -> None:
    instance = LanguageServerClient(
        command(),
        tmp_path,
        initialization_options={"typeCheckingMode": "basic"},
        client_info={"name": "kg-studio-test", "version": "0"},
        request_timeout=6.0,
    )
    try:
        instance.start()
        sent = instance.initialize_result["echo"]
        assert sent["clientInfo"]["name"] == "kg-studio-test"
        assert sent["rootUri"] == path_to_uri(tmp_path)
        assert sent["processId"] == os.getpid()
        assert sent["rootPath"] == str(tmp_path)
        assert sent["initializationOptions"] == {"typeCheckingMode": "basic"}
        assert sent["workspaceFolders"] == [{"uri": path_to_uri(tmp_path), "name": tmp_path.name}]
        assert "publishDiagnostics" in sent["capabilities"]["textDocument"]
        assert instance.server_capabilities["textDocumentSync"] == 2
        assert instance.ready
    finally:
        instance.stop(timeout=2.0)


def test_initialized_follows_the_initialize_reply(tmp_path: Path) -> None:
    instance = LanguageServerClient(command(), tmp_path, request_timeout=6.0)
    try:
        instance.start()
        methods = instance.request("document_log", None)["methods"]
        assert methods[:2] == ["initialize", "initialized"]
    finally:
        instance.stop(timeout=2.0)


def test_starting_twice_is_refused(client: LanguageServerClient) -> None:
    with pytest.raises(LspError, match="already running"):
        client.start()


def test_start_reports_a_server_that_never_answers(tmp_path: Path) -> None:
    instance = LanguageServerClient(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        tmp_path,
        request_timeout=0.5,
    )
    with pytest.raises(LspStartupError):
        instance.start()
    assert not instance.alive, "a failed start must not leave the process running"


def test_start_reports_a_reply_that_is_not_a_result(tmp_path: Path) -> None:
    """The peer answers with an empty object and then goes quiet."""
    script = (
        "import sys,time\n"
        "body=b'{\"a\": 1}'\n"
        "sys.stdout.buffer.write(b'Content-Length: %d\\r\\n\\r\\n' % len(body) + body)\n"
        "sys.stdout.flush()\n"
        "time.sleep(5)\n"
    )
    instance = LanguageServerClient(
        [sys.executable, "-c", script], tmp_path, request_timeout=2.0
    )
    with pytest.raises(LspStartupError):
        instance.start()
    assert not instance.alive


def test_start_reports_a_missing_executable(tmp_path: Path) -> None:
    instance = LanguageServerClient(["definitely-not-a-language-server", "--stdio"], tmp_path)
    with pytest.raises(LspStartupError, match="could not start"):
        instance.start()


# ------------------------------------------------------------------ correlation


def test_concurrent_requests_get_their_own_answers(client: LanguageServerClient) -> None:
    """Replies come back out of order; each caller must still see its own result."""
    answers: dict[int, dict] = {}
    lock = threading.Lock()

    def call(index: int) -> None:
        answer = client.request("echo_later", {"delay": 0.3 if index % 2 else 0.01, "index": index})
        with lock:
            answers[index] = answer

    threads = [threading.Thread(target=call, args=(index,)) for index in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20.0)

    assert len(answers) == 6
    assert {item["echo"]["index"] for item in answers.values()} == set(range(6))
    ids = [item["id"] for item in answers.values()]
    assert len(set(ids)) == 6, "every reply must belong to exactly one request"
    by_index = {item["echo"]["index"]: item for item in answers.values()}
    for index, answer in by_index.items():
        assert answer["delay"] == (0.3 if index % 2 else 0.01)


def test_error_responses_raise(client: LanguageServerClient) -> None:
    with pytest.raises(LspError, match="is not implemented"):
        client.request("no/such/method", {})


def test_a_timed_out_request_does_not_wedge_the_connection(client: LanguageServerClient) -> None:
    with pytest.raises(LspTimeout):
        client.request("echo_later", {"delay": 2.0}, timeout=0.2)
    # The late reply for the abandoned id is ignored rather than mis-delivered.
    assert client.request("echo_later", {"delay": 0.0})["echo"] == {"delay": 0.0}


def test_notifications_carry_method_and_params(client: LanguageServerClient, recorder: Recorder) -> None:
    log = recorder.wait_for("window/logMessage")
    assert log is not None
    assert log.params["message"].startswith("stub in")


# -------------------------------------------------------------- notifications


def test_a_frame_written_in_pieces_is_delivered_once(
    client: LanguageServerClient, recorder: Recorder
) -> None:
    result = client.request("emit_split_notification", {})
    assert result["split_bytes"] > 0
    publish = recorder.wait_for("textDocument/publishDiagnostics")
    assert publish is not None
    diagnostics = publish.params["diagnostics"]
    assert len(diagnostics) == 1
    assert diagnostics[0]["code"] == "reportArgumentType"
    assert diagnostics[0]["severity"] == 1
    time.sleep(0.2)
    delivered = [item for item in recorder.notifications if item.method == "textDocument/publishDiagnostics"]
    assert len(delivered) == 1, "a reassembled frame must be dispatched once"


def test_server_initiated_requests_are_answered(client: LanguageServerClient) -> None:
    """A client that ignored these would leave the server blocked forever."""
    answer = client.request("emit_server_request", {})["client_answer"]
    assert answer.get("error") is None
    assert answer.get("result") is None


def test_configuration_requests_are_answered(client: LanguageServerClient) -> None:
    answer = client.request("configuration_request", {})["client_answer"]
    assert answer.get("error") is None
    assert answer.get("result") == [None]


def test_unknown_server_requests_are_refused_rather_than_hung(client: LanguageServerClient) -> None:
    answer = client.request("unknown_server_request", {})["client_answer"]
    assert answer["error"]["code"] == -32601


# -------------------------------------------------------------- document sync


def test_open_change_close_sends_the_expected_sequence(
    client: LanguageServerClient, tmp_path: Path
) -> None:
    path = tmp_path / "kg_project" / "module.py"
    path.parent.mkdir(parents=True)
    path.write_text("value: int = 1\n", encoding="utf-8")

    uri = client.open_file(path)
    client.change_file(path, "value: int = 2\n")
    client.close_file(path)

    logged = client.request("document_log", None)["documents"]
    assert [item["textDocument"]["uri"] for item in logged] == [uri, uri, uri]
    assert logged[0]["textDocument"]["text"] == "value: int = 1\n"
    assert logged[0]["textDocument"]["languageId"] == "python"
    assert logged[0]["textDocument"]["version"] == 1
    assert logged[1]["textDocument"]["version"] == 2
    # Whole-document change: LSP spells that as a content change with no range.
    assert logged[1]["contentChanges"] == [{"text": "value: int = 2\n"}]
    assert client.open_documents == ()


def test_open_reads_from_disk_unless_text_is_given(
    client: LanguageServerClient, tmp_path: Path
) -> None:
    path = tmp_path / "a.py"
    path.write_text("x = 1\n", encoding="utf-8")
    client.open_file(path)
    client.open_file(tmp_path / "b.py", text="y = 2\n")
    logged = client.request("document_log", None)["documents"]
    assert logged[0]["textDocument"]["text"] == "x = 1\n"
    assert logged[1]["textDocument"]["text"] == "y = 2\n"


def test_versions_keep_increasing_across_reopens(
    client: LanguageServerClient, tmp_path: Path
) -> None:
    path = tmp_path / "pkg.py"
    path.write_text("x = 1\n", encoding="utf-8")
    client.open_file(path)
    client.close_file(path)
    client.open_file(path)
    logged = client.request("document_log", None)["documents"]
    opened = [item for item in logged if "version" in item["textDocument"]]
    assert [item["textDocument"]["version"] for item in opened] == [1, 2]


def test_reopen_refreshes_an_open_document_with_didchange(
    client: LanguageServerClient, tmp_path: Path
) -> None:
    """An already-open document is refreshed with ``didChange``, not close+open.

    Measured against pyright 1.1.411: when a file returns to bytes the server has
    already analysed in this session — what applying and then removing a UI edit
    produces — a ``didClose``/``didOpen`` pair leaves the error from the broken
    generation as the server's *final* published state for that file, indefinitely,
    even though a fresh ``pyright`` process over the same bytes reports nothing. No
    close/open schedule avoids it: not the file alone, not the file with its
    dependency, not the whole package. ``didChange`` is re-checked and clears it.
    """
    path = tmp_path / "pkg.py"
    path.write_text("x = 1\n", encoding="utf-8")
    client.open_file(path)
    path.write_text("x = 2\n", encoding="utf-8")

    reopened = client.reopen([path])

    logged = client.request("document_log", None)
    document_methods = [name for name in logged["methods"] if name.startswith("textDocument/")]
    assert reopened == (path_to_uri(path),)
    assert document_methods == ["textDocument/didOpen", "textDocument/didChange"], (
        f"reopen must not close and reopen an open document: {document_methods}"
    )
    change = logged["documents"][-1]
    assert change["contentChanges"] == [{"text": "x = 2\n"}], "didChange must carry the disk text"
    assert client._open_documents[path_to_uri(path)] == "x = 2\n"  # noqa: SLF001 - cache honesty


def test_reopen_keeps_the_document_open_and_the_version_rising(
    client: LanguageServerClient, tmp_path: Path
) -> None:
    """The refresh leaves the server holding the document, at a newer version.

    A version that never rose would let the server treat a later publish as
    unremarkable; a document left closed would drop it out of the restart replay list.
    """
    path = tmp_path / "pkg.py"
    path.write_text("x = 1\n", encoding="utf-8")
    client.open_file(path)
    before = client._document_versions[path_to_uri(path)]  # noqa: SLF001

    path.write_text("x = 2\n", encoding="utf-8")
    client.reopen([path])
    path.write_text("x = 3\n", encoding="utf-8")
    client.reopen([path])

    uri = path_to_uri(path)
    assert client.open_documents == (uri,), "reopen must leave the document open"
    assert client._document_versions[uri] > before  # noqa: SLF001
    versions = [
        item["textDocument"]["version"]
        for item in client.request("document_log", None)["documents"]
        if "version" in item["textDocument"]
    ]
    assert versions == sorted(versions) and len(set(versions)) == len(versions), versions


def test_reopen_opens_a_file_the_server_never_had(client: LanguageServerClient, tmp_path: Path) -> None:
    path = tmp_path / "new.py"
    path.write_text("z = 3\n", encoding="utf-8")
    assert client.reopen([path]) == (path_to_uri(path),)
    assert client.open_documents == (path_to_uri(path),)


def test_reopen_of_a_document_closed_underneath_still_refreshes_it(
    client: LanguageServerClient, tmp_path: Path
) -> None:
    """The refresh must not raise when the buffer disappeared between the check and the send."""
    path = tmp_path / "pkg.py"
    path.write_text("x = 1\n", encoding="utf-8")
    client.open_file(path)
    uri = path_to_uri(path)
    with client._lock:  # noqa: SLF001 - simulating the server forgetting the document
        client._open_documents.pop(uri)
    path.write_text("x = 2\n", encoding="utf-8")

    assert client.reopen([path]) == (uri,)

    assert client._open_documents[uri] == "x = 2\n"  # noqa: SLF001
    logged = client.request("document_log", None)["documents"]
    assert logged[-1]["textDocument"]["text"] == "x = 2\n"


def test_opening_the_same_file_twice_is_refused(client: LanguageServerClient, tmp_path: Path) -> None:
    path = tmp_path / "pkg.py"
    path.write_text("x = 1\n", encoding="utf-8")
    client.open_file(path)
    with pytest.raises(LspError, match="already open"):
        client.open_file(path)


def test_changing_an_unopened_file_is_refused(client: LanguageServerClient, tmp_path: Path) -> None:
    with pytest.raises(LspError, match="not open"):
        client.change_file(tmp_path / "never.py", "x = 1\n")


def test_forget_drops_a_deleted_file_without_talking_to_the_server(
    client: LanguageServerClient, tmp_path: Path
) -> None:
    path = tmp_path / "gone.py"
    path.write_text("x = 1\n", encoding="utf-8")
    client.open_file(path)
    client.forget(path)
    assert client.open_documents == ()
    methods = client.request("document_log", None)["methods"]
    assert "textDocument/didClose" not in methods


# ------------------------------------------------------------------ resilience


def test_a_crash_reports_the_exit_code(tmp_path: Path, recorder: Recorder) -> None:
    instance = LanguageServerClient(
        crash_command(tmp_path / "sentinel"),
        tmp_path,
        on_notification=recorder.on_notification,
        on_exit=recorder.on_exit,
        request_timeout=6.0,
    )
    instance.start()
    assert recorder.wait_for("textDocument/publishDiagnostics") is not None
    assert recorder.wait_for_exit() == [3]
    assert not instance.alive
    assert not instance.ready
    with pytest.raises(LspServerCrash):
        instance.request("document_log", None)
    instance.stop(timeout=1.0)


def test_pending_requests_fail_when_the_server_dies(tmp_path: Path, recorder: Recorder) -> None:
    instance = LanguageServerClient(
        crash_command(tmp_path / "sentinel"),
        tmp_path,
        on_notification=recorder.on_notification,
        on_exit=recorder.on_exit,
        request_timeout=6.0,
    )
    instance.start()
    assert recorder.wait_for("textDocument/publishDiagnostics") is not None
    outcome: list[BaseException] = []

    def call() -> None:
        try:
            instance.request("echo_later", {"delay": 5.0}, timeout=5.0)
        except BaseException as error:  # noqa: BLE001 - recorded and asserted below
            outcome.append(error)

    thread = threading.Thread(target=call)
    thread.start()
    thread.join(timeout=10.0)
    assert isinstance(outcome[0], LspServerCrash), "death must be reported, not waited out"
    instance.stop(timeout=1.0)


def test_a_clean_shutdown_is_not_reported_as_a_crash(
    tmp_path: Path, recorder: Recorder
) -> None:
    instance = LanguageServerClient(
        command(),
        tmp_path,
        on_notification=recorder.on_notification,
        on_exit=recorder.on_exit,
        request_timeout=6.0,
    )
    instance.start()
    instance.stop(timeout=3.0)
    assert recorder.exit_codes == []


def test_restart_replays_open_documents(tmp_path: Path, recorder: Recorder) -> None:
    instance = LanguageServerClient(
        crash_command(tmp_path / "sentinel"),
        tmp_path,
        on_notification=recorder.on_notification,
        on_exit=recorder.on_exit,
        request_timeout=6.0,
    )
    path = tmp_path / "pkg.py"
    path.write_text("x = 1\n", encoding="utf-8")
    instance.start()
    instance.open_file(path)
    assert recorder.wait_for("textDocument/publishDiagnostics") is not None
    time.sleep(0.3)

    instance._restart_delay = 0.05
    instance.restart()
    try:
        logged = instance.request("document_log", None)["documents"]
        assert logged[0]["textDocument"]["uri"] == path_to_uri(path)
        assert logged[0]["textDocument"]["version"] == 2, "the replay re-reads from disk"
    finally:
        instance.stop(timeout=2.0)


def test_backoff_doubles_and_resets_after_a_stable_run(tmp_path: Path) -> None:
    instance = LanguageServerClient(command(), tmp_path, request_timeout=6.0)
    instance.start()
    try:
        assert instance.restart_delay == 1.0
        # Pretend the previous run crashed immediately twice, then restart once:
        # the delay must carry on growing rather than resetting.
        instance._restart_delay = 4.0
        instance._last_start = time.monotonic()
        started = time.monotonic()
        instance.set_restart_delay(0.05)
        instance.restart()
        assert time.monotonic() - started >= 0.04
        assert instance.restart_delay == 0.1, "an unhealthy restart keeps backing off"
    finally:
        instance.stop(timeout=2.0)


# ----------------------------------------------------------------- reclamation


def test_stop_terminates_the_process_gracefully(tmp_path: Path) -> None:
    instance = LanguageServerClient(command(), tmp_path, request_timeout=6.0)
    instance.start()
    pid = instance.process_id
    assert pid is not None and process_alive(pid)
    instance.stop(timeout=3.0)
    assert not process_alive(pid), "the server process must be reaped, not orphaned"
    assert instance.process_id is None
    assert not instance.ready


def test_stop_kills_a_server_that_ignores_shutdown(tmp_path: Path) -> None:
    instance = LanguageServerClient(command("wedged"), tmp_path, request_timeout=6.0)
    instance.start()
    pid = instance.process_id
    started = time.monotonic()
    instance.stop(timeout=0.4)
    elapsed = time.monotonic() - started
    assert not process_alive(pid)
    assert elapsed < 8.0, f"a wedged server must be killed, not waited for ({elapsed:.1f}s)"


def test_double_stop_is_harmless(client: LanguageServerClient) -> None:
    client.stop(timeout=2.0)
    client.stop(timeout=2.0)


def test_stopping_an_unstarted_client_is_harmless(tmp_path: Path) -> None:
    LanguageServerClient(command(), tmp_path).stop()


def test_notifications_after_stop_are_not_delivered(
    client: LanguageServerClient, recorder: Recorder
) -> None:
    client.stop(timeout=2.0)
    count = len(recorder.notifications)
    time.sleep(0.2)
    assert len(recorder.notifications) == count


def test_context_manager_stops_the_client(tmp_path: Path) -> None:
    with LanguageServerClient(command(), tmp_path, request_timeout=6.0) as instance:
        pid = instance.process_id
        assert instance.ready
    assert not process_alive(pid)


def test_no_child_process_survives(tmp_path: Path) -> None:
    """The leak check this whole file exists to make honest."""
    before = own_children()
    instance = LanguageServerClient(command(), tmp_path, request_timeout=6.0)
    instance.start()
    assert len(own_children()) == len(before) + 1
    instance.stop(timeout=3.0)
    deadline = time.time() + 5.0
    while time.time() < deadline and len(own_children()) > len(before):
        time.sleep(0.05)
    assert own_children() == before
