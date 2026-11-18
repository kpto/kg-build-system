"""Compose dev commands, kbs-owned data paths and one reverse proxy."""

from __future__ import annotations

import signal
from urllib.parse import urlsplit
import webbrowser

from kg_build_system.notebook.config import Project
from kg_build_system.notebook.console import data_response

from .env import load_dev_config
from .proxy import LocalData, Route, make_proxy_server
from .session import DevSession

DEFAULT_PORT = 8000
PORT_ATTEMPTS = 11


def _display_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::", "[::]"} else host


def _bind(
    host: str,
    port: int | None,
    local: LocalData,
    routes: list[Route],
):
    candidates = [port] if port is not None else list(
        range(DEFAULT_PORT, DEFAULT_PORT + PORT_ATTEMPTS)
    )
    last: OSError | None = None
    for candidate in candidates:
        try:
            return make_proxy_server(host, int(candidate), local, routes)
        except OSError as error:
            last = error
            if port is not None:
                raise OSError(
                    f"cannot bind dev proxy to {host}:{port}: {error}"
                ) from error
    raise OSError(
        f"cannot bind dev proxy in {DEFAULT_PORT}-"
        f"{DEFAULT_PORT + PORT_ATTEMPTS - 1}: {last}"
    )


def _run(server, session: DevSession) -> int:
    previous = None
    try:
        import signal as _signal

        def stop(signum: int, frame: object) -> None:
            raise KeyboardInterrupt

        previous = _signal.getsignal(_signal.SIGTERM)
        _signal.signal(_signal.SIGTERM, stop)
    except (ImportError, OSError, ValueError):
        previous = None
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        session.stop()
        if previous is not None:
            try:
                signal.signal(signal.SIGTERM, previous)
            except (OSError, ValueError):
                pass
    return 0


def serve_view_dev(
    snapshot: bytes,
    snapshot_type: str,
    *,
    host: str = "127.0.0.1",
    port: int | None = None,
    no_open: bool = False,
) -> int:
    """Start the viewer dev command and proxy it beside the kbs snapshot."""

    config = load_dev_config()
    session = DevSession()
    try:
        viewer = session.start(
            "viewer",
            config.command("viewer"),
            config.cwd,
            health_path="/",
        )
        def local(path: str) -> tuple[int, str, bytes] | None:
            if urlsplit(path).path in {"/snapshot", "/api/snapshot"}:
                return 200, snapshot_type, snapshot
            return None

        routes = [
            Route(
                "/",
                "127.0.0.1",
                viewer.port,
                f"http://127.0.0.1:{viewer.port}",
            )
        ]
        server = _bind(host, port, local, routes)
        url = f"http://{_display_host(host)}:{server.server_port}/"
        print(f"kbs dev viewer: {url}", flush=True)
        print(f"viewer -> 127.0.0.1:{viewer.port}", flush=True)
        if not no_open:
            webbrowser.open(url)
        return _run(server, session)
    except Exception:
        session.stop()
        raise


def serve_console_dev(
    project: Project,
    *,
    host: str = "127.0.0.1",
    port: int | None = None,
) -> int:
    """Start the viewer and console dev commands and proxy them beside kbs."""

    project.ensure()
    config = load_dev_config()
    session = DevSession()
    try:
        viewer = session.start(
            "viewer",
            config.command("viewer"),
            config.cwd,
            health_path="/",
        )
        console = session.start(
            "console",
            config.command("console"),
            config.cwd,
            health_path="/console/",
        )
        def local(path: str) -> tuple[int, str, bytes] | None:
            return data_response(project, path)

        routes = [
            Route(
                "/console",
                "127.0.0.1",
                console.port,
                f"http://127.0.0.1:{console.port}",
            ),
            Route(
                "/",
                "127.0.0.1",
                viewer.port,
                f"http://127.0.0.1:{viewer.port}",
            ),
        ]
        server = _bind(host, port, local, routes)
        display = _display_host(host)
        print(f"kbs dev console: http://{display}:{server.server_port}/console/", flush=True)
        print(f"viewer -> 127.0.0.1:{viewer.port}", flush=True)
        print(f"console -> 127.0.0.1:{console.port}", flush=True)
        return _run(server, session)
    except Exception:
        session.stop()
        raise
