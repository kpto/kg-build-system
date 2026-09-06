"""A minimal JSON-RPC 2.0 client for a stdio language server.

This exists because pyright is the only type checker studio uses (DESIGN.md §3)
and it speaks LSP, not Python. Nothing here is pyright-specific: the server
command is a parameter, so tests drive it with a fake subprocess while production
drives ``pyright-langserver --stdio``.

Wire facts verified against the real ``pyright-langserver`` 1.1.411 rather than
assumed (see ``tests/test_lsp_live.py``):

* Frames are ``Content-Length: <n>\\r\\n\\r\\n<payload>``; pyright sends no
  ``Content-Type`` and the header block always ends with a blank line.
* ``initialize`` must be answered before anything else; pyright then logs via
  ``window/logMessage`` and loads ``pyrightconfig.json`` from the workspace root.
* Diagnostics arrive as ``textDocument/publishDiagnostics`` notifications whose
  params carry ``uri``, sometimes ``version``, and ``diagnostics``. An empty list
  means "this file is clean now" and must clear the previous set.
* Every diagnostic carries its rule in ``code`` (e.g. ``"reportArgumentType"``).
  ``data`` appears only when pyright attaches code actions or marks a diagnostic
  unnecessary, and only that variant contains ``rule`` — so reading ``data.rule``
  alone would lose every real error. Callers get both fields untouched.
* Positions are 0-based (LSP); conversion to the contract's 1-based positions is
  the caller's job (:mod:`studio_backend.diagnostics.service`).
* ``didClose`` makes pyright republish an empty list for that URI.
* Unrecognised command-line arguments are ignored by the server, so an unknown
  flag is not a startup failure — and ``--pythonpath`` is one of them: it only
  affects the ``pyright`` CLI, not this server.

Threading: one daemon reader thread does nothing but split frames off ``stdout``
and push complete messages onto a queue; a second daemon dispatch thread pops that
queue and routes replies to waiting callers and notifications to the handler.
Splitting them means a slow handler cannot stall frame parsing, and no caller ever
sees a half-written message.
"""

from __future__ import annotations

import atexit
import errno
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Any, Final
from urllib.parse import unquote, urlsplit

__all__ = [
    "LanguageServerClient",
    "LspError",
    "LspServerCrash",
    "LspStartupError",
    "LspTimeout",
    "Notification",
    "default_server_command",
    "path_to_uri",
    "uri_to_path",
]

#: How many bytes one reader ``read`` asks for; the loop is byte-exact so this is
#: purely about syscall frequency.
_READ_CHUNK: Final = 65536

_HEADER_SEPARATOR: Final = b"\r\n\r\n"

#: How long a server must stay up before a later crash restart forgets the
#: backoff it had accumulated.
_STABLE_UPTIME: Final = 30.0


class LspError(RuntimeError):
    """A JSON-RPC error response, or a client-side protocol failure."""


class LspTimeout(LspError):
    """A request the server did not answer in time."""


class LspServerCrash(LspError):
    """The server process died; its outstanding requests can never be answered."""


class LspStartupError(LspError):
    """The server could not be launched or never finished ``initialize``."""


def path_to_uri(path: Path | str) -> str:
    """An ``file://`` URI for a filesystem path.

    Absolute-but-unresolved: ``Path.resolve`` follows symlinks, and a URI the
    server echoes back must round-trip to the same path the caller passed, since
    callers compare it against their own project root.
    """
    return Path(os.path.abspath(os.fspath(path))).as_uri()


def uri_to_path(uri: str) -> Path:
    """The filesystem path a ``file://`` URI addresses."""
    parts = urlsplit(uri)
    if parts.scheme != "file":
        raise LspError(f"not a file URI: {uri!r}")
    # ``netloc`` is an optional host; only the path is a POSIX-style absolute path
    # with percent escapes (including a leading slash before a Windows drive).
    return Path(unquote(parts.path))


@dataclass
class _Pending:
    """One in-flight request waiting for its correlated reply."""

    event: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: BaseException | None = None


@dataclass(frozen=True, slots=True)
class Notification:
    """A server-push notification, handed to the client's callback verbatim."""

    method: str
    params: Any


class LanguageServerClient:
    """Spawn, drive and tear down one stdio language server.

    Lifecycle: :meth:`start` (spawn plus ``initialize``/``initialized``), document
    calls (:meth:`open_file`, :meth:`change_file`, :meth:`close_file`,
    :meth:`reopen`), then :meth:`stop`. The instance is reusable — :meth:`start`
    after :meth:`stop`, or :meth:`restart` after a crash, launches a fresh server
    and replays every document it was told about, because the server itself holds
    no state worth preserving.

    ``on_notification`` and ``on_exit`` run on the dispatch thread, so handlers
    must not block; ``on_exit`` fires only for a crash, never for :meth:`stop`.
    """

    def __init__(
        self,
        command: Sequence[str],
        workspace_root: Path | str,
        *,
        initialization_options: dict[str, Any] | None = None,
        client_info: dict[str, Any] | None = None,
        on_notification: Callable[[Notification], None] | None = None,
        on_exit: Callable[[int | None], None] | None = None,
        request_timeout: float = 30.0,
        env: dict[str, str] | None = None,
    ) -> None:
        self._command = list(command)
        self._workspace_root = Path(workspace_root)
        self._initialization_options = dict(initialization_options or {})
        self._client_info = client_info or {"name": "kg-studio", "version": "0.1.0"}
        self._on_notification = on_notification
        self._on_exit = on_exit
        self._request_timeout = request_timeout
        self._env = dict(env) if env is not None else None

        self._lock = threading.RLock()
        self._process: subprocess.Popen[bytes] | None = None
        self._inbox: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._pending: dict[int, _Pending] = {}
        self._next_id = 0
        self._reader: threading.Thread | None = None
        self._dispatcher: threading.Thread | None = None
        self._stopping = False
        self._ready = False
        self._generation = 0
        self._server_capabilities: dict[str, Any] = {}
        self._initialize_result: dict[str, Any] = {}
        self._read_failure: BaseException | None = None
        #: Documents the server is holding buffers for, so a restart can replay
        #: them and ``change_file`` can number versions monotonically.
        self._open_documents: dict[str, str] = {}
        self._document_versions: dict[str, int] = {}
        self._restart_delay = 1.0
        self._max_restart_delay = 30.0
        self._last_start: float | None = None
        atexit.register(self._kill_quietly)

    # -- lifecycle ---------------------------------------------------------

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    @property
    def ready(self) -> bool:
        """True between a successful ``initialize`` and the server going away."""
        with self._lock:
            return self._ready

    @property
    def alive(self) -> bool:
        """True while the spawned process is still running."""
        with self._lock:
            process = self._process
        return process is not None and process.poll() is None

    @property
    def server_capabilities(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._server_capabilities)

    @property
    def initialize_result(self) -> dict[str, Any]:
        """The whole ``initialize`` result, kept for capability-driven behaviour."""
        with self._lock:
            return dict(self._initialize_result)

    @property
    def process_id(self) -> int | None:
        """The server's pid, or ``None`` once it has been reaped."""
        with self._lock:
            process = self._process
        return None if process is None else process.pid

    @property
    def restart_delay(self) -> float:
        """The delay the next :meth:`restart` will wait before relaunching."""
        return self._restart_delay

    def set_restart_delay(self, seconds: float) -> None:
        """Override the backoff, for tests and for an operator-driven immediate retry."""
        self._restart_delay = seconds

    @property
    def open_documents(self) -> tuple[str, ...]:
        """URIs the server currently holds buffers for."""
        with self._lock:
            return tuple(self._open_documents)

    @classmethod
    def resolve_command(cls, command: Sequence[str]) -> list[str]:
        """Absolute path for a server command, looked up on ``PATH`` when needed.

        Raises :class:`LspStartupError` rather than letting ``Popen`` produce its
        own ``FileNotFoundError`` deep inside a restart loop.
        """
        found = shutil.which(command[0])
        if found is None:
            raise LspStartupError(f"language server executable not found: {command[0]!r}")
        return [found, *command[1:]]

    def start(self) -> None:
        """Launch the server and complete the LSP handshake.

        Raises :class:`LspStartupError` when the process cannot be spawned or the
        handshake fails; either way the process is killed before returning, so a
        failed start never leaks one.
        """
        with self._lock:
            if self.alive:
                raise LspError("language server is already running")
            self._stopping = False
            self._read_failure = None
            # A generation stamp: the dying reader thread of a crashed server must
            # not be able to poison the queue of the one that replaces it.
            self._generation += 1
            generation = self._generation
            inbox: queue.Queue[dict[str, Any] | None] = queue.Queue()
            self._inbox = inbox
            self._pending = {}
            try:
                process = subprocess.Popen(  # noqa: S603 - the command comes from the operator
                    self._command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    cwd=str(self._workspace_root),
                    env=self._env,
                )
            except OSError as error:
                raise LspStartupError(f"could not start {self._command[0]!r}: {error}") from error
            self._process = process
            self._ready = False
            self._initialize_result = {}
            self._reader = threading.Thread(
                target=self._read_loop, args=(process, inbox, generation), name="lsp-reader", daemon=True
            )
            self._dispatcher = threading.Thread(
                target=self._dispatch_loop, args=(inbox, generation), name="lsp-dispatch", daemon=True
            )
            self._reader.start()
            self._dispatcher.start()

        try:
            self._handshake()
        except LspError as error:
            # Whatever went wrong during the handshake, the caller's problem is the
            # same: the server is not up. Anything else propagates untouched.
            self._kill_process()
            raise LspStartupError(f"{self._command[0]!r} did not finish initializing: {error}") from error
        except BaseException:
            self._kill_process()
            raise
        with self._lock:
            self._last_start = time.monotonic()
        self._replay_open_documents()

    def _handshake(self) -> None:
        root_uri = path_to_uri(self._workspace_root)
        result = self.request(
            "initialize",
            {
                "processId": os.getpid(),
                "clientInfo": self._client_info,
                "locale": "en",
                "rootUri": root_uri,
                "rootPath": str(self._workspace_root),
                "capabilities": _client_capabilities(),
                "initializationOptions": self._initialization_options,
                "workspaceFolders": [{"uri": root_uri, "name": self._workspace_root.name}],
            },
        )
        if not isinstance(result, dict):
            failure = self._read_failure
            detail = f": {failure}" if failure is not None else ""
            raise LspStartupError(f"initialize returned no result{detail}")
        with self._lock:
            capabilities = result.get("capabilities")
            self._server_capabilities = capabilities if isinstance(capabilities, dict) else {}
            self._initialize_result = result
            self._ready = True
        self.notify("initialized", {})

    def stop(self, timeout: float = 5.0) -> None:
        """Ask the server to shut down, then make sure the process is gone.

        ``shutdown`` plus ``exit`` is the graceful path; a server that ignores
        either within ``timeout`` is terminated and then killed. This never raises
        for a server that is already dead, because it is also what the crash
        recovery path and :mod:`atexit` call.
        """
        with self._lock:
            process = self._process
            self._stopping = True
            ready = self._ready
        if process is None:
            return
        if process.poll() is None and ready:
            try:
                self.request("shutdown", None, timeout=timeout)
                self.notify("exit", None)
            except LspError:
                # A server that will not answer its shutdown is killed below; the
                # reason it did not answer is not actionable at that point.
                pass
        if _wait(process, timeout):
            self._reap(process)
            return
        process.terminate()
        if _wait(process, max(timeout / 2.0, 0.5)):
            self._reap(process)
            return
        process.kill()
        _wait(process, timeout)
        self._reap(process)

    def restart(self) -> None:
        """Restart after a crash, waiting out the current backoff interval.

        The interval doubles on every consecutive restart up to 30 s and forgets
        itself once the server has stayed up for 30 s, so a server that cannot
        start at all is retried slowly instead of in a hot loop. This blocks for
        the interval: call it from a supervisor thread, never from a notification
        handler.
        """
        with self._lock:
            last_start = self._last_start
        if last_start is not None and time.monotonic() - last_start >= _STABLE_UPTIME:
            self._restart_delay = 1.0
        delay = self._restart_delay
        self._restart_delay = min(self._restart_delay * 2.0, self._max_restart_delay)
        self.stop(timeout=2.0)
        time.sleep(delay)
        self.start()

    # -- documents ---------------------------------------------------------

    def open_file(self, path: Path | str, text: str | None = None) -> str:
        """``didOpen`` one file, reading it from disk when ``text`` is not given.

        Opening a document that is already open raises: LSP forbids a second
        ``didOpen`` for one URI, and silently double-opening would make the
        server's diagnostics for that file meaningless. Use :meth:`reopen`.
        """
        file_path = Path(path)
        uri = path_to_uri(file_path)
        body = file_path.read_text(encoding="utf-8") if text is None else text
        with self._lock:
            if uri in self._open_documents:
                raise LspError(f"{uri} is already open; use change_file() or reopen()")
            version = self._document_versions.get(uri, 0) + 1
            self._document_versions[uri] = version
            self._open_documents[uri] = body
        self.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": "python",
                    "version": version,
                    "text": body,
                }
            },
        )
        return uri

    def change_file(self, path: Path | str, text: str) -> str:
        """``didChange`` one document with a whole-document replacement.

        pyright advertises incremental sync (``textDocumentSync: 2``) but accepts a
        change event with no ``range``, which LSP defines as the complete new text;
        that was verified against the live server, and it keeps studio free of a
        diffing implementation it would only have to get right in two places.
        """
        uri = path_to_uri(path)
        with self._lock:
            if uri not in self._open_documents:
                raise LspError(f"{uri} is not open")
            version = self._document_versions.get(uri, 0) + 1
            self._document_versions[uri] = version
            self._open_documents[uri] = text
        self.notify(
            "textDocument/didChange",
            {"textDocument": {"uri": uri, "version": version}, "contentChanges": [{"text": text}]},
        )
        return uri

    def close_file(self, path: Path | str) -> str:
        """``didClose`` one document (pyright then publishes an empty list for it)."""
        uri = path_to_uri(path)
        with self._lock:
            self._open_documents.pop(uri, None)
        self.notify("textDocument/didClose", {"textDocument": {"uri": uri}})
        return uri

    def reopen(self, paths: Iterable[Path | str]) -> tuple[str, ...]:
        """Close then re-open documents so the server re-reads them from disk.

        This is the regeneration path (DESIGN.md §3): the files on disk changed, so
        any buffer held for them is stale. Files the server never had open are
        simply opened.
        """
        reopened: list[str] = []
        for path in paths:
            uri = path_to_uri(path)
            with self._lock:
                was_open = uri in self._open_documents
            if was_open:
                self.close_file(path)
            self.open_file(path)
            reopened.append(uri)
        return tuple(reopened)

    def forget(self, path: Path | str) -> None:
        """Drop a document the project no longer contains, without talking to the server.

        A pruned generated file cannot be re-read from disk, so it must leave the
        replay list or the next restart would fail on it.
        """
        with self._lock:
            self._open_documents.pop(path_to_uri(path), None)

    def _replay_open_documents(self) -> None:
        """Re-``didOpen`` everything this client was told about, from disk."""
        with self._lock:
            uris = list(self._open_documents)
            self._open_documents.clear()
        for uri in uris:
            self.open_file(uri_to_path(uri))

    # -- transport ---------------------------------------------------------

    def request(self, method: str, params: Any, timeout: float | None = None) -> Any:
        """Send a request and block until its correlated reply arrives.

        Raises :class:`LspError` for an error response, :class:`LspTimeout` when
        the deadline passes, and :class:`LspServerCrash` if the server dies while
        the request is outstanding.
        """
        with self._lock:
            sent = self._send({"method": method, "params": params})
        if sent is None:  # pragma: no cover - expect_reply defaults to True
            raise LspError("internal error: request was not filed")
        message_id, pending = sent
        deadline = self._request_timeout if timeout is None else timeout
        if not pending.event.wait(deadline):
            with self._lock:
                self._pending.pop(message_id, None)
            raise LspTimeout(f"{method} timed out after {deadline:.1f}s")
        if pending.error is not None:
            raise pending.error
        return pending.result

    def notify(self, method: str, params: Any) -> None:
        """Send a notification (a message with no id, so nothing to await)."""
        with self._lock:
            self._send({"method": method, "params": params}, expect_reply=False)

    def _send(self, payload: dict[str, Any], *, expect_reply: bool = True) -> tuple[int, _Pending] | None:
        """Frame and write one message; the caller holds ``self._lock``.

        Returns the correlation id and its waiter for a request, ``None`` for a
        notification.
        """
        process = self._process
        if process is None or process.poll() is not None or process.stdin is None:
            failure = self._read_failure
            detail = f": {failure}" if failure is not None else ""
            raise LspServerCrash(f"language server is not running{detail}")
        pending: _Pending | None = None
        message_id = -1
        if expect_reply:
            self._next_id += 1
            message_id = self._next_id
            message: dict[str, Any] = {"jsonrpc": "2.0", "id": message_id, **payload}
            pending = _Pending()
            self._pending[message_id] = pending
        else:
            message = {"jsonrpc": "2.0", **payload}
        try:
            self._write(message)
        except OSError as error:
            if pending is not None:
                self._pending.pop(message_id, None)
            self._ready = False
            if error.errno == errno.EPIPE:
                raise LspServerCrash("language server closed its stdin") from error
            raise
        return None if pending is None else (message_id, pending)

    def _write(self, message: dict[str, Any]) -> None:
        """Write one framed message; the caller holds ``self._lock``."""
        process = self._process
        if process is None or process.stdin is None:
            raise LspServerCrash("language server is not running")
        body = json.dumps(message).encode("utf-8")
        process.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        process.stdin.flush()

    def _read_loop(
        self, process: subprocess.Popen[bytes], inbox: queue.Queue[dict[str, Any] | None], generation: int
    ) -> None:
        """Split ``Content-Length``-framed messages and queue them.

        Reads are byte-exact against the announced length, so a message that
        arrives in pieces is held in the buffer until whole and never handed to a
        handler half-written.
        """
        stream = process.stdout
        buffer = bytearray()
        if stream is None:
            inbox.put(None)
            return
        try:
            while True:
                chunk = _read_available(stream)
                if not chunk:
                    break
                buffer += chunk
                while True:
                    frame, consumed = _take_frame(buffer)
                    if frame is None:
                        break
                    del buffer[:consumed]
                    inbox.put(frame)
                if self._stopping:
                    break
        except (OSError, ValueError, LspError) as error:
            # A dead pipe during shutdown/kill is expected; anything the reader
            # could not parse is reported through ``_read_failure``.
            self._read_failure = error
        finally:
            inbox.put(None)

    def _dispatch_loop(self, inbox: queue.Queue[dict[str, Any] | None], generation: int) -> None:
        """Route queued messages: replies to their waiters, notifications onward."""
        while True:
            message = inbox.get()
            if generation != self._generation:
                return  # superseded by a restart; this generation's state is gone
            if message is None:
                with self._lock:
                    was_ready = self._ready
                    self._ready = False
                    process = self._process
                code = None if process is None else process.poll()
                self._fail_pending(LspServerCrash(f"language server exited with status {code}"))
                if was_ready and not self._stopping:
                    callback = self._on_exit
                    if callback is not None:
                        callback(code)
                return
            if "method" in message and "id" in message:
                self._handle_server_request(message)
            elif "id" in message:
                self._resolve(message)
            else:
                handler = self._on_notification
                method = message.get("method")
                if handler is not None and isinstance(method, str):
                    handler(Notification(method=method, params=message.get("params")))

    def _handle_server_request(self, message: dict[str, Any]) -> None:
        """Answer a server-initiated request instead of leaving it hanging.

        A client that never replies stalls the server, so the subset a
        diagnostics-only client can honour is answered and everything else is
        refused with LSP's ``MethodNotFound``.
        """
        method = message.get("method")
        message_id = message.get("id")
        if not isinstance(method, str) or message_id is None:
            return
        if method in {"window/workDoneProgress/create", "client/registerCapability", "client/unregisterCapability"}:
            self._respond(message_id, None)
            return
        if method == "workspace/configuration":
            params = message.get("params")
            items = params.get("items", []) if isinstance(params, dict) else []
            self._respond(message_id, [None] * len(items))
            return
        if method == "workspace/workspaceFolders":
            root_uri = path_to_uri(self._workspace_root)
            self._respond(
                message_id,
                [{"uri": root_uri, "name": self._workspace_root.name}],
            )
            return
        self._respond(message_id, None, error={"code": -32601, "message": f"method {method} is not supported"})

    def _respond(self, message_id: int | str, result: Any, error: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": message_id}
        if error is not None:
            message["error"] = error
        else:
            message["result"] = result
        with self._lock:
            if self._process is None:
                return
            try:
                self._write(message)
            except (LspError, OSError):
                return  # the peer is gone; an answer to nothing is not an error

    def _resolve(self, message: dict[str, Any]) -> None:
        message_id = message.get("id")
        with self._lock:
            pending = self._pending.pop(message_id, None) if isinstance(message_id, int) else None
        if pending is None:
            return
        error = message.get("error")
        if isinstance(error, dict):
            pending.error = LspError(f"server error {error.get('code')}: {error.get('message', 'unknown error')}")
        else:
            pending.result = message.get("result")
        pending.event.set()

    def _fail_pending(self, error: BaseException) -> None:
        with self._lock:
            pending, self._pending = self._pending, {}
        for waiter in pending.values():
            waiter.error = error
            waiter.event.set()

    # -- reclamation -------------------------------------------------------

    def _reap(self, process: subprocess.Popen[bytes]) -> None:
        """Join the reader, close the pipes and reap. No fd or process survives."""
        reader = self._reader
        if reader is not None and reader.is_alive() and reader is not threading.current_thread():
            reader.join(timeout=2.0)
        for pipe in (process.stdin, process.stdout):
            if pipe is not None:
                try:
                    pipe.close()
                except OSError:
                    pass
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:  # pragma: no cover - kill was already issued
            process.kill()
            process.wait(timeout=2.0)
        with self._lock:
            if self._process is process:
                self._process = None
            self._ready = False

    def _kill_process(self) -> None:
        with self._lock:
            process = self._process
        if process is None:
            return
        process.kill()
        self._reap(process)

    def _kill_quietly(self) -> None:
        """Best-effort kill for interpreter shutdown; it must never raise."""
        try:
            self._kill_process()
        except (OSError, subprocess.SubprocessError):
            # Nothing can be done at this point and propagating out of ``atexit``
            # only prints a confusing traceback during teardown.
            pass

    def __del__(self) -> None:  # pragma: no cover - depends on collection timing
        try:
            self._kill_quietly()
        except Exception:  # noqa: BLE001 - __del__ cannot propagate anything
            pass

    def __enter__(self) -> LanguageServerClient:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.stop()


def _take_frame(buffer: bytearray) -> tuple[dict[str, Any] | None, int]:
    """Pop one complete framed message off ``buffer``.

    Returns ``(None, 0)`` when the buffer does not hold a whole message yet, which
    is what keeps a partially written message from ever reaching a handler.
    """
    header_end = buffer.find(_HEADER_SEPARATOR)
    if header_end < 0:
        return None, 0
    header = bytes(buffer[:header_end]).decode("ascii", errors="replace")
    length: int | None = None
    for line in header.split("\r\n"):
        name, _, value = line.partition(":")
        if name.strip().lower() == "content-length":
            try:
                length = int(value.strip())
            except ValueError:
                raise LspError(f"malformed Content-Length header: {line!r}") from None
    if length is None:
        raise LspError(f"frame without a Content-Length header: {header!r}")
    start = header_end + len(_HEADER_SEPARATOR)
    if len(buffer) < start + length:
        return None, 0
    body = bytes(buffer[start : start + length])
    try:
        return json.loads(body.decode("utf-8")), start + length
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LspError(f"malformed JSON-RPC frame: {error}") from error


def _read_available(stream: Any) -> bytes:
    """One blocking read that returns as soon as *anything* has arrived.

    ``BufferedReader.read(n)`` is unusable here: it keeps reading until it has
    exactly ``n`` bytes, so a 200-byte ``initialize`` reply would sit in the
    buffer forever. ``read1`` performs a single raw read, and ``os.read`` is the
    equivalent for a stream that is not buffered.
    """
    read1 = getattr(stream, "read1", None)
    if read1 is not None:
        return read1(_READ_CHUNK)
    return os.read(stream.fileno(), _READ_CHUNK)


def _wait(process: subprocess.Popen[bytes], timeout: float) -> bool:
    """True when the process exited within ``timeout`` seconds."""
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        return False
    return True


def _client_capabilities() -> dict[str, Any]:
    """Client capabilities for a diagnostics consumer.

    ``textDocument/publishDiagnostics`` is server-push, so no client capability is
    needed to receive it. What is declared here only tunes the payload:
    ``versionSupport`` asks for the document version to be echoed with each publish
    (pyright sends it regardless), and ``tagSupport`` keeps the "unnecessary code"
    diagnostics the server otherwise drops for a client that cannot show the tag —
    they are real dead code in generated output, so studio wants them.
    """
    return {
        "workspace": {
            "workspaceFolders": True,
            "configuration": False,
            "didChangeWatchedFiles": {"dynamicRegistration": False},
        },
        "textDocument": {
            "publishDiagnostics": {
                "relatedInformation": True,
                "versionSupport": True,
                "tagSupport": {"valueSet": [1, 2]},
                "codeDescriptionSupport": True,
                "dataSupport": True,
            },
        },
    }


def default_server_command(venv_root: Path | str | None = None) -> list[str]:
    """``pyright-langserver --stdio``, preferring the one inside ``venv_root/bin``.

    Falls back to ``PATH`` so a developer's own global install keeps working.
    """
    if venv_root is not None:
        for name in ("pyright-langserver", "pyright-langserver.exe"):
            candidate = Path(venv_root) / "bin" / name
            if candidate.is_file():
                return [str(candidate), "--stdio"]
    return ["pyright-langserver", "--stdio"]
