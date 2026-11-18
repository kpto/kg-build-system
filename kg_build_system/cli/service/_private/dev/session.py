"""Start dev commands, read their first-line port, and stop the process group."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import os
import re
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request

READY_TIMEOUT = 30.0
HEALTH_TIMEOUT = 30.0


@dataclass
class DevServer:
    role: str
    port: int
    process: subprocess.Popen[str]


def _popen(command: str, cwd: Path) -> subprocess.Popen[str]:
    options: dict[str, object] = {
        "cwd": str(cwd),
        "shell": True,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
    }
    if os.name == "posix":
        options["start_new_session"] = True
    else:
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(command, **options)  # type: ignore[arg-type]


class DevSession:
    """The set of child processes owned by one kbs dev invocation."""

    def __init__(self) -> None:
        self.servers: list[DevServer] = []

    def start(
        self,
        role: str,
        command: str,
        cwd: Path,
        *,
        health_path: str = "/",
    ) -> DevServer:
        process = _popen(command, cwd)
        ready = threading.Event()
        state: dict[str, object] = {"port": None, "error": None}
        recent: deque[str] = deque(maxlen=20)

        def read() -> None:
            try:
                for line in process.stdout or ():
                    text = line.strip()
                    recent.append(text)
                    if state["port"] is None and state["error"] is None:
                        try:
                            port = int(text)
                        except ValueError:
                            state["error"] = (
                                f"{role} command must print its port on the first "
                                f"line, got {text!r}"
                            )
                            ready.set()
                            return
                        if not 1 <= port <= 65535:
                            state["error"] = (
                                f"{role} command printed an invalid port {port!r}"
                            )
                            ready.set()
                            return
                        state["port"] = port
                        print(f"[{role}] port {port}", flush=True)
                        ready.set()
                    else:
                        print(f"[{role}] {line.rstrip()}", flush=True)
            finally:
                ready.set()

        threading.Thread(target=read, name=f"kbs-dev-{role}", daemon=True).start()
        if not ready.wait(READY_TIMEOUT):
            self._stop_one(process)
            raise RuntimeError(
                f"{role} did not print a port within {READY_TIMEOUT:.0f}s"
            )
        error = state["error"]
        if error:
            self._stop_one(process)
            raise RuntimeError(str(error))
        port = state["port"]
        if not isinstance(port, int):
            self._stop_one(process)
            raise RuntimeError(f"{role} exited before printing a port")

        deadline = time.monotonic() + HEALTH_TIMEOUT
        url = f"http://127.0.0.1:{port}{health_path}"
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self._stop_one(process)
                output = "\n".join(line for line in recent if line)
                if "Another next dev server is already running" in output:
                    existing = re.search(r"existing server at (http://[^\s,]+)", output)
                    where = f" at {existing.group(1)}" if existing else ""
                    raise RuntimeError(
                        f"{role} dev server is already running{where}; stop the "
                        "existing Next dev server or kbs dev session first"
                    )
                raise RuntimeError(
                    f"{role} exited with {process.returncode} before becoming ready"
                    + (f"\n{output}" if output else "")
                )
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    if response.status < 500:
                        server = DevServer(role=role, port=port, process=process)
                        self.servers.append(server)
                        print(f"[{role}] ready at http://127.0.0.1:{port}", flush=True)
                        return server
            except (urllib.error.URLError, OSError):
                time.sleep(0.2)
        self._stop_one(process)
        output = "\n".join(line for line in recent if line)
        raise RuntimeError(
            f"{role} did not answer {url} within {HEALTH_TIMEOUT:.0f}s"
            + (f"\n{output}" if output else "")
        )

    def stop(self) -> None:
        for server in reversed(self.servers):
            self._stop_one(server.process)
        self.servers.clear()

    @staticmethod
    def _stop_one(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.terminate()
        except (OSError, ProcessLookupError):
            return
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                if os.name == "posix":
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                else:
                    process.kill()
            except (OSError, ProcessLookupError):
                pass
        try:
            if process.stdout is not None:
                process.stdout.close()
        except OSError:
            pass
