from __future__ import annotations

import os
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev-server.mjs"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(
    NODE is None or not SCRIPT.is_file(),
    reason="the shared dev server needs node and scripts/dev-server.mjs",
)


FAKE_NEXT = """\
import http from "node:http";
const args = process.argv.slice(2);
const port = Number(args[args.indexOf("--port") + 1]);
const server = http.createServer((request, response) => {
  response.writeHead(200, { "Content-Type": "text/plain" });
  response.end(`fake next on ${port}\\n`);
});
server.listen(port, "127.0.0.1");
const stop = () => {
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 300).unref();
};
process.on("SIGTERM", stop);
process.on("SIGINT", stop);
"""


def _fake_app(root: Path) -> Path:
    app = root / "app"
    binary = app / "node_modules" / ".bin"
    binary.mkdir(parents=True)
    fake = root / "fake-next.mjs"
    fake.write_text(FAKE_NEXT, encoding="utf-8")
    wrapper = binary / "next"
    wrapper.write_text(
        f'#!/bin/sh\nexec "{NODE}" "{fake}" "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return app


def _environment() -> dict[str, str]:
    env = dict(os.environ)
    node_dir = str(Path(NODE).parent)
    env["PATH"] = f"{node_dir}{os.pathsep}{env.get('PATH', '')}"
    return env


def _start(root: Path) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [str(NODE), str(SCRIPT), "app"],
        cwd=root,
        env=_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def _read_line(process: subprocess.Popen[str], timeout: float = 30) -> str:
    result: dict[str, str] = {}

    def read() -> None:
        result["line"] = process.stdout.readline() if process.stdout else ""

    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError("the dev server did not print a port")
    return result.get("line", "").strip()


def _stop(process: subprocess.Popen[str], sig: int = signal.SIGTERM) -> None:
    if process.poll() is not None:
        return
    process.send_signal(sig)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _serves(port: int, timeout: float = 1) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/", timeout=0.5) as response:
                return response.status == 200
        except OSError:
            time.sleep(0.1)
    return False


def _wait_down(port: int, timeout: float = 8) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _serves(port, 0.5):
            return
        time.sleep(0.2)
    raise AssertionError(f"the dev server on {port} did not stop")


def test_two_clients_share_one_server_and_the_last_lease_stops_it(
    tmp_path: Path,
) -> None:
    _fake_app(tmp_path)
    first = _start(tmp_path)
    second: subprocess.Popen[str] | None = None
    try:
        first_port = int(_read_line(first))
        assert _serves(first_port)

        second = _start(tmp_path)
        second_port = int(_read_line(second))
        assert second_port == first_port
        assert _serves(second_port)

        _stop(first)
        assert _serves(second_port, timeout=2), (
            "stopping one kbs session killed a server still leased by another"
        )

        _stop(second)
        _wait_down(second_port)
        state = tmp_path / ".kbs" / "dev"
        assert not list(state.glob("*.json"))
        assert not list(state.glob("*.lock"))
    finally:
        _stop(first)
        if second is not None:
            _stop(second)


def test_a_killed_client_releases_its_lease(tmp_path: Path) -> None:
    _fake_app(tmp_path)
    first = _start(tmp_path)
    second: subprocess.Popen[str] | None = None
    try:
        port = int(_read_line(first))
        assert _serves(port)
        second = _start(tmp_path)
        assert int(_read_line(second)) == port

        _stop(second, signal.SIGKILL)
        time.sleep(0.5)
        assert _serves(port, timeout=2)

        _stop(first)
        _wait_down(port)
    finally:
        _stop(first)
        if second is not None:
            _stop(second)


def test_stop_command_stops_the_shared_server(tmp_path: Path) -> None:
    _fake_app(tmp_path)
    process = _start(tmp_path)
    try:
        port = int(_read_line(process))
        assert _serves(port)

        result = subprocess.run(
            [str(NODE), str(SCRIPT), "stop", "app"],
            cwd=tmp_path,
            env=_environment(),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        _wait_down(port)
        state = tmp_path / ".kbs" / "dev"
        assert not list(state.glob("*.json"))
    finally:
        _stop(process)
