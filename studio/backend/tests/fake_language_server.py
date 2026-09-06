"""A stub language server used by ``tests/test_lsp.py``.

It speaks the same ``Content-Length`` framing as a real one and is driven by the
method names the client sends, so the tests exercise the client's real framing,
correlation and dispatch code against a real subprocess rather than a mock.

Behaviour is selected by the request method:

``initialize``
    echoes the params back inside its result, so a test can assert what the client
    actually sent on the wire.
``emit_split_notification``
    writes one ``publishDiagnostics`` frame in three pieces with flushes between them,
    which is what proves the client never hands out a half-read message.
``emit_server_request`` / ``unknown_server_request`` / ``configuration_request``
    send a server-initiated *request* and report, in their own reply, what the client
    answered — a client that ignored them would leave the server waiting forever.
``echo_later``
    answers after a delay taken from its params, so out-of-order replies happen.
``crash_after_notify``
    publishes one diagnostic and exits with a status, without a shutdown.
``shutdown`` / ``exit``
    the graceful path; ``wedged`` mode ignores both so the client's kill path runs.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, BinaryIO

_PAUSE = 0.02

DIAGNOSTICS: dict[str, Any] = {
    "uri": "file:///workspace/demo.py",
    "version": 1,
    "diagnostics": [
        {
            "range": {"start": {"line": 3, "character": 4}, "end": {"line": 3, "character": 9}},
            "message": 'Argument of type "int" cannot be assigned to parameter "city"',
            "severity": 1,
            "code": "reportArgumentType",
            "source": "Pyright",
        }
    ],
}


def read_message(stream: BinaryIO) -> dict[str, Any] | None:
    """One framed message, or ``None`` at end of input."""
    length = None
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            break
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"content-length":
            length = int(value.strip())
    if length is None:
        return None
    body = b""
    while len(body) < length:
        chunk = stream.read(length - len(body))
        if not chunk:
            return None
        body += chunk
    return json.loads(body.decode("utf-8"))


def write(message: dict[str, Any]) -> None:
    body = json.dumps(message).encode("utf-8")
    sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    sys.stdout.buffer.flush()


def write_result(message_id: Any, result: Any) -> None:
    write({"jsonrpc": "2.0", "id": message_id, "result": result})


def write_error(message_id: Any, code: int, text: str) -> None:
    write({"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": text}})


def notify(method: str, params: Any) -> None:
    write({"jsonrpc": "2.0", "method": method, "params": params})


def wait_for_reply(stdin: BinaryIO, expected_id: int, timeout: float) -> dict[str, Any]:
    """Read client messages until the reply to ``expected_id`` arrives."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        message = read_message(stdin)
        if message is None:
            return {"eof": True}
        if message.get("id") == expected_id:
            return {"result": message.get("result"), "error": message.get("error")}
    return {"timeout": True}


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
    sentinel = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"/tmp/kg-studio-stub-{os.getpid()}.sentinel")
    stdin = sys.stdin.buffer
    methods: list[str] = []
    documents: list[dict[str, Any]] = []

    while True:
        message = read_message(stdin)
        if message is None:
            return 0
        method = message.get("method")
        params = message.get("params") or {}
        message_id = message.get("id")
        if isinstance(method, str):
            methods.append(method)

        if method == "initialize":
            write_result(
                message_id,
                {
                    "capabilities": {"textDocumentSync": 2, "definitionProvider": True},
                    "echo": params,
                },
            )
        elif method == "initialized":
            notify("window/logMessage", {"type": 3, "message": f"stub in {mode} mode"})
            if mode == "crash_after_notify" and not sentinel.exists():
                # The sentinel makes the crash happen once, so a restarted client can
                # talk to a healthy stub.
                sentinel.write_text("crashed", encoding="utf-8")
                notify("textDocument/publishDiagnostics", DIAGNOSTICS)
                time.sleep(_PAUSE)
                os._exit(3)
        elif method == "emit_split_notification":
            frame = json.dumps(
                {"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics", "params": DIAGNOSTICS}
            ).encode("utf-8")
            third = len(frame) // 3
            sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(frame) + frame[:third])
            sys.stdout.buffer.flush()
            time.sleep(_PAUSE)
            sys.stdout.buffer.write(frame[third : 2 * third])
            sys.stdout.buffer.flush()
            time.sleep(_PAUSE)
            sys.stdout.buffer.write(frame[2 * third :])
            sys.stdout.buffer.flush()
            write_result(message_id, {"split_bytes": len(frame)})
        elif method == "emit_server_request":
            write(
                {
                    "jsonrpc": "2.0",
                    "id": 9001,
                    "method": "client/registerCapability",
                    "params": {"registrations": []},
                }
            )
            write_result(message_id, {"client_answer": wait_for_reply(stdin, 9001, timeout=8.0)})
        elif method == "unknown_server_request":
            write({"jsonrpc": "2.0", "id": 9002, "method": "window/notARealMethod", "params": {}})
            write_result(message_id, {"client_answer": wait_for_reply(stdin, 9002, timeout=8.0)})
        elif method == "configuration_request":
            write(
                {
                    "jsonrpc": "2.0",
                    "id": 9003,
                    "method": "workspace/configuration",
                    "params": {"items": [{"section": "python.analysis"}]},
                }
            )
            write_result(message_id, {"client_answer": wait_for_reply(stdin, 9003, timeout=8.0)})
        elif method == "echo_later":
            delay = float(params.get("delay", 0.0))
            time.sleep(delay)
            write_result(message_id, {"id": message_id, "delay": delay, "echo": params})
        elif method == "document_log":
            write_result(message_id, {"methods": methods, "documents": documents})
        elif method in {"textDocument/didOpen", "textDocument/didChange", "textDocument/didClose"}:
            documents.append(params)
        elif method == "shutdown":
            if mode == "wedged":
                time.sleep(30.0)
                return 0
            write_result(message_id, None)
        elif method == "exit":
            return 0
        elif message_id is not None:
            write_error(message_id, -32601, f"{method} is not implemented")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
