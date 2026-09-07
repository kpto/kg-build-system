"""The workspace's type-tier diagnostics: pyright's output, in the problem model.

Owns three things:

1. ``<project_root>/pyrightconfig.json`` — written before the server starts, and
   rewritten on every start, so studio's view of the project is reproducible rather
   than whatever a previous tool left behind.
2. the language server process — one per workspace, every owned Python file opened,
   buffers refreshed with ``didChange`` across regenerations (never closed and
   reopened — see DESIGN.md §3), restart with backoff after a crash
   (:mod:`studio_backend.diagnostics.lsp`).
3. the debounced snapshot — pyright publishes per file as it analyses, which for a
   whole regeneration is a burst; subscribers get one merged snapshot per quiet
   period instead of one event per file. :meth:`DiagnosticsService.reopen` is what
   the generation step calls, and :attr:`DiagnosticsService.state` plus
   :meth:`~DiagnosticsService.status` are what the status model reads.

What ``pyrightconfig.json`` must contain to resolve ``kg_build_system`` was
established by running pyright 1.1.411 against a generated-looking project, not by
reading its documentation:

``pythonPath``
    **Rejected.** pyright prints ``Config contains unrecognized setting
    "pythonPath".`` and ignores it — it is a VS Code setting, not a config-file
    key. ``--pythonpath`` on the command line works for the ``pyright`` CLI but is
    ignored by ``pyright-langserver``, which kept reporting
    ``reportMissingImports`` for ``kg_build_system``.
``venvPath`` + ``venv``
    **Works, and is what is written here.** With ``venvPath`` pointing at the
    framework checkout and ``venv`` at ``.venv``, pyright adds
    ``.venv/lib/python3.12/site-packages`` (and ``lib64``) to its search paths and
    follows the editable-install ``.pth``, so ``import kg_build_system`` resolves.
    Both are resolved to absolute paths first, because ``venvPath`` is interpreted
    relative to the *config file's* directory — which here is the project root,
    typically nowhere near the framework venv.
``pythonVersion``
    Pinned to the venv's own version. Without it pyright logged ``Assuming Python
    version 3.14.4.final.0``, the interpreter on ``PATH``, and would have type-checked
    the generated code against a newer standard library than the one that runs it.

``include`` is the generated package only, ``typeCheckingMode`` is ``basic``, the
package is listed in ``strict`` (the generated code is expected to be fully typed,
and ``strict`` is what enforces that about *our* output while leaving dependencies
alone), and ``reportMissingTypeStubs`` is off because duckdb and friends ship none.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal

from ..ir.document import ProjectDocument
from .lsp import (
    LanguageServerClient,
    LspError,
    Notification,
    path_to_uri,
    uri_to_path,
)
from .mapping import ANCHORS_RELATIVE_PATH, Anchors, annotate, load_anchors
from .problem import Problem, make_problem, severity_from_lsp

__all__ = [
    "DiagnosticsError",
    "DiagnosticsService",
    "PyrightConfig",
    "discover_framework_venv",
    "discover_server_command",
    "write_pyright_config",
]

#: Quiet period that coalesces a burst of publishes into one snapshot.
DEFAULT_DEBOUNCE_SECONDS: Final = 0.25

#: The file this module owns inside the project.
CONFIG_FILENAME: Final = "pyrightconfig.json"

#: The framework checkout, used as the default ``venvPath`` parent.
DEFAULT_FRAMEWORK_ROOT: Final = Path(__file__).resolve().parents[4]

State = Literal["starting", "ready", "error"]


class DiagnosticsError(RuntimeError):
    """The workspace's diagnostics pipeline could not be brought up."""


@dataclass(frozen=True, slots=True)
class PyrightConfig:
    """The content of the pyrightconfig.json studio writes.

    :meth:`as_json` emits exactly the keys pyright accepts at the top level of a
    config file; anything else would produce a startup warning in the log.
    """

    package: str
    venv_path: Path
    python_version: str
    report_missing_type_stubs: bool = False

    @property
    def venv_name(self) -> str:
        """The venv directory name, relative to :attr:`venv_path`."""
        return self.venv_path.name

    def as_json(self) -> dict[str, Any]:
        return {
            "include": [self.package],
            "exclude": [f"{self.package}/**/__pycache__"],
            "typeCheckingMode": "basic",
            "strict": [self.package],
            "reportMissingTypeStubs": self.report_missing_type_stubs,
            # Absolute, because pyright resolves venvPath against the config file's
            # directory and the project root is not near the framework checkout.
            "venvPath": str(Path(self.venv_path).parent),
            "venv": self.venv_name,
            "pythonVersion": self.python_version,
        }


def write_pyright_config(
    project_root: Path | str,
    package: str,
    config_path: Path | str | None = None,
    *,
    framework_venv: Path | str | None = None,
    python_version: str | None = None,
) -> Path:
    """Write the project's pyrightconfig.json and return its path.

    The file is replaced rather than merged: keeping a stale key from an older
    studio version would change what pyright reports in ways nothing can see.
    """
    root = Path(project_root)
    target = Path(config_path) if config_path is not None else root / CONFIG_FILENAME
    venv = Path(framework_venv) if framework_venv is not None else discover_framework_venv()
    version = python_version or detect_python_version(venv)
    config = PyrightConfig(package=package, venv_path=venv, python_version=version)
    _validate_python_version(version)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config.as_json(), indent=2) + "\n", encoding="utf-8")
    return target


def discover_framework_venv() -> Path:
    """The venv that can ``import kg_build_system``, in the order it is sought.

    1. ``KG_STUDIO_PYRIGHT_VENV``, so a deployment with its own environment can
       point pyright at it without a code change;
    2. the venv this backend runs in, which has the framework installed (it is what
       makes ``import kg_build_system`` work for studio itself);
    3. ``../.venv`` of the checkout the backend was installed from.

    A candidate only wins if it looks like a real environment carrying the framework:
    pyright silently ignores a dangling ``venvPath`` and then reports every framework
    import as unresolved, which is a far more confusing failure than raising here.
    """
    override = os.environ.get("KG_STUDIO_PYRIGHT_VENV")
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override))
    if sys.prefix != sys.base_prefix:
        candidates.append(Path(sys.prefix))
    candidates.append(DEFAULT_FRAMEWORK_ROOT / ".venv")
    for candidate in candidates:
        if _venv_provides(candidate, "kg_build_system"):
            return candidate
    raise DiagnosticsError(
        "no Python environment containing kg_build_system was found for pyright; set "
        "KG_STUDIO_PYRIGHT_VENV to a virtualenv that has it installed"
    )


def _site_packages(venv: Path) -> tuple[Path, ...]:
    """Every ``site-packages`` directory a venv could have on this platform."""
    return tuple(venv.glob("lib/python*/site-packages")) + tuple(venv.glob("lib64/python*/site-packages"))


def _venv_provides(venv: Path, distribution: str) -> bool:
    """True when ``distribution`` is installed in ``venv``.

    Matches the dist-info directory as well as an editable-install ``.pth``, which is
    how the framework is installed in this checkout.
    """
    if not (venv / "pyvenv.cfg").is_file():
        return False
    for site in _site_packages(venv):
        if any(site.glob(f"{distribution}*")) or any(site.glob(f"_editable_impl_{distribution}*")):
            return True
    return False


def discover_server_command(venv: Path | None = None) -> list[str]:
    """The ``pyright-langserver --stdio`` command for this workspace.

    pyright is a *dev* dependency of the framework, so it is not necessarily in the
    environment studio runs in, and its executable name is not on ``PATH`` in a
    packaged install. Each candidate environment is asked for its own
    ``bin/pyright-langserver`` before falling back to ``PATH``.

    Raises :class:`DiagnosticsError` when nothing is found; the message says what to
    install, because "the type tier is red" is otherwise undiagnosable.
    """
    override = os.environ.get("KG_STUDIO_PYRIGHT_LANGSERVER")
    if override:
        return [override, "--stdio"]
    candidates: list[Path] = []
    if venv is not None:
        candidates.append(venv)
    if sys.prefix != sys.base_prefix:
        candidates.append(Path(sys.prefix))
    candidates.append(DEFAULT_FRAMEWORK_ROOT / ".venv")
    for candidate in candidates:
        for name in ("pyright-langserver", "pyright-langserver.exe"):
            executable = candidate / "bin" / name
            if executable.is_file():
                return [str(executable), "--stdio"]
    found = shutil.which("pyright-langserver")
    if found is not None:
        return [found, "--stdio"]
    raise DiagnosticsError(
        "pyright-langserver is not installed in any of the checked environments "
        f"({', '.join(str(item) for item in candidates)}); install pyright (uv add --dev pyright)"
    )


def detect_python_version(venv: Path | str) -> str:
    """``major.minor`` of a venv's interpreter, from its own ``pyvenv.cfg``.

    Never the running interpreter's version: the value must describe the environment
    pyright is being told to use, and reading ``pyvenv.cfg`` avoids launching a
    subprocess just to ask.
    """
    config = Path(venv) / "pyvenv.cfg"
    try:
        lines = config.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise DiagnosticsError(f"cannot read {config}: {error}") from error
    version = ""
    for line in lines:
        name, _, value = line.partition("=")
        if name.strip() in {"version_info", "version"}:
            version = value.strip()
            break
    match = _VERSION.match(version)
    if match is None:
        raise DiagnosticsError(f"{config} does not state a usable Python version (read {version!r})")
    return f"{match.group('major')}.{match.group('minor')}"


_VERSION: Final = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?")


def _validate_python_version(value: str) -> None:
    if _VERSION.match(value) is None:
        raise DiagnosticsError(f"{value!r} is not a major.minor Python version")


@dataclass
class _FileState:
    """Raw diagnostics for one file, as the server last published them."""

    version: int | None = None
    diagnostics: list[dict[str, Any]] = field(default_factory=list)


class DiagnosticsService:
    """One pyright server per workspace, publishing IR-resolved problems.

    ``document_provider`` and the anchor path are read lazily at flush time, so the
    pipeline always annotates against the document and index that match the code on
    disk — a snapshot computed from a document revision that has been replaced would
    light up the wrong cards.

    Threading: ``subscribe`` callbacks run on the service's own timer or dispatch
    thread, so they must not call back into :meth:`snapshot` and must not block.
    """

    def __init__(
        self,
        project_root: Path | str,
        package: str,
        config_path: Path | str | None = None,
        *,
        anchors_path: Path | str | None = None,
        document_provider: Callable[[], ProjectDocument | None] | None = None,
        framework_venv: Path | str | None = None,
        server_command: Sequence[str] | None = None,
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
        client_factory: Callable[[Callable[[Notification], None], Callable[[int | None], None]], LanguageServerClient]
        | None = None,
    ) -> None:
        self._project_root = Path(project_root)
        self._package = package
        self._config_path = Path(config_path) if config_path is not None else self._project_root / CONFIG_FILENAME
        self._anchors_path = (
            Path(anchors_path)
            if anchors_path is not None
            else self._project_root / ANCHORS_RELATIVE_PATH
        )
        self._document_provider = document_provider
        self._framework_venv = framework_venv
        self._server_command = list(server_command) if server_command is not None else None
        self._debounce_seconds = debounce_seconds
        self._client_factory = client_factory

        self._lock = threading.RLock()
        self._client: LanguageServerClient | None = None
        self._files: dict[str, _FileState] = {}
        self._subscribers: list[Callable[[list[Problem]], None]] = []
        self._timer: threading.Timer | None = None
        self._dirty = False
        self._problems: list[Problem] = []
        self._state: State = "starting"
        self._state_message: str | None = None
        self._stopped = False
        self._anchors: Anchors | None = None
        self._anchors_stamp: tuple[int, int] | None = None
        self._restarting = False

    # -- introspection -----------------------------------------------------

    @property
    def project_root(self) -> Path:
        return self._project_root

    @property
    def package(self) -> str:
        return self._package

    @property
    def config_path(self) -> Path:
        return self._config_path

    @property
    def state(self) -> State:
        """``starting`` until the handshake is done, ``ready`` while serving, ``error`` after a death or a failed start."""
        with self._lock:
            return self._state

    @property
    def state_message(self) -> str | None:
        """The failure text behind ``state == "error"``."""
        with self._lock:
            return self._state_message

    @property
    def files_open(self) -> int:
        client = self._client
        return 0 if client is None else len(client.open_documents)

    def status(self) -> dict[str, Any]:
        """The ``status.types`` object of API.md §Status model."""
        with self._lock:
            errors = sum(1 for item in self._problems if item.severity == "error")
            warnings = sum(1 for item in self._problems if item.severity == "warning")
        return {"errors": errors, "warnings": warnings, "state": self.state}

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        """Write the config, bring the server up and open every owned file.

        Records a failure in :attr:`state` / :attr:`state_message` instead of
        raising, because the caller is a server request path that must still answer
        with an empty problem list.
        """
        with self._lock:
            self._stopped = False
            self._set_state("starting", None)
        try:
            write_pyright_config(
                self._project_root,
                self._package,
                self._config_path,
                framework_venv=self._framework_venv,
            )
        except (DiagnosticsError, OSError) as error:
            with self._lock:
                self._set_state("error", f"could not write {self._config_path.name}: {error}")
            return

        try:
            client = self._build_client()
            client.start()
        except (LspError, OSError) as error:
            with self._lock:
                self._set_state("error", str(error))
            return
        with self._lock:
            self._client = client
            self._set_state("ready", None)
            self._files.clear()
            self._dirty = True
        self.open_owned_files()
        self._flush()

    def stop(self, timeout: float = 5.0) -> None:
        """Shut the server down and stop publishing. Idempotent."""
        with self._lock:
            self._stopped = True
            client = self._client
            self._client = None
            timer = self._timer
            self._timer = None
        if timer is not None:
            timer.cancel()
        if client is not None:
            client.stop(timeout=timeout)

    def restart(self) -> None:
        """Bring the server back after a crash, honouring the client's backoff.

        Safe to call from the crash callback's own thread; a second concurrent call
        is ignored rather than queueing a second restart.
        """
        with self._lock:
            if self._stopped or self._restarting:
                return
            self._restarting = True
            client = self._client
        try:
            with self._lock:
                self._set_state("starting", "restarting pyright after it exited")
            if client is not None:
                client.restart()
            with self._lock:
                if self._client is not client:
                    return  # stop()/start() took over while we were backing off
                self._set_state("ready", None)
                self._files.clear()
                self._dirty = True
            self.open_owned_files()
            self._flush()
        except (LspError, OSError) as error:
            with self._lock:
                if not self._stopped:
                    self._set_state("error", str(error))
        finally:
            with self._lock:
                self._restarting = False

    def _build_client(self) -> LanguageServerClient:
        if self._client_factory is not None:
            return self._client_factory(self._on_notification, self._on_exit)
        command = self._server_command or discover_server_command(self._type_environment())
        return LanguageServerClient(
            LanguageServerClient.resolve_command(command),
            self._project_root,
            initialization_options={"typeCheckingMode": "basic", "indexing": False, "failOnWarnings": False},
            on_notification=self._on_notification,
            on_exit=self._on_exit,
        )

    def _type_environment(self) -> Path | None:
        """The venv the config is pointed at.

        Handed to :func:`discover_server_command` first, so the checker and the type
        environment are the same environment whenever that one also has pyright in it.
        """
        if self._framework_venv is not None:
            return Path(self._framework_venv)
        try:
            return discover_framework_venv()
        except DiagnosticsError:
            return None

    # -- documents ---------------------------------------------------------

    def owned_files(self) -> tuple[Path, ...]:
        """Every Python file of the generated package, sorted, ``__pycache__`` excluded.

        Generation owns a manifest, but the package directory is what pyright needs
        buffers for, and listing it directly keeps this module independent of the
        generator.
        """
        package_root = self._project_root / self._package
        if not package_root.is_dir():
            return ()
        return tuple(
            sorted(
                path
                for path in package_root.rglob("*.py")
                if "__pycache__" not in path.parts
            )
        )

    def open_owned_files(self, paths: Iterable[Path | str] | None = None) -> int:
        """``didOpen`` the owned files, from disk. Returns how many were opened."""
        client = self._client
        if client is None:
            return 0
        opened = 0
        for path in (self.owned_files() if paths is None else (Path(item) for item in paths)):
            try:
                client.open_file(path)
            except (LspError, OSError):
                # A file that vanished between listing and opening has nothing to
                # report; the next regeneration will re-list it.
                continue
            opened += 1
        return opened

    def reopen(self, changed: Sequence[str] | None = None) -> None:
        """Re-open the project after a regeneration.

        The buffers pyright holds are the text studio sent *before* the write, so
        after generation every affected file is refreshed from disk (DESIGN.md §3).
        Files that disappeared are closed and dropped, or the next crash restart would
        try to replay a path that no longer exists. ``changed`` is a list of
        project-relative paths; ``None`` means "the whole package".
        """
        client = self._client
        if client is None:
            return
        on_disk = {path_to_uri(path): path for path in self.owned_files()}
        if changed is None:
            targets = list(on_disk.values())
        else:
            targets = []
            for relative in changed:
                # Unresolved, because ``path_to_uri`` does not resolve symlinks either
                # and a resolved path would be a different document to the server.
                path = self._project_root / relative
                if path.is_file():
                    targets.append(path)
        gone = [uri for uri in client.open_documents if uri not in on_disk]
        for uri in gone:
            client.forget(uri_to_path(uri))
            with self._lock:
                self._files.pop(uri, None)
            client.close_file(uri_to_path(uri))
        if targets:
            client.reopen(targets)
        # A regeneration can also add files the server has never seen.
        self.open_owned_files()
        with self._lock:
            self._dirty = True
            self._anchors_stamp = None
        self._schedule_flush()

    # -- publishing --------------------------------------------------------

    def subscribe(self, callback: Callable[[list[Problem]], None]) -> Callable[[], None]:
        """Register a listener for merged snapshots; the returned callable unsubscribes."""
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def snapshot(self) -> list[Problem]:
        """The current problems, flushing anything the debounce has not merged yet."""
        with self._lock:
            pending = self._dirty
        if pending:
            self._flush()
        with self._lock:
            return list(self._problems)

    def problems(self) -> list[dict[str, Any]]:
        """:meth:`snapshot` as the JSON the API returns."""
        return [problem.as_json() for problem in self.snapshot()]

    def _on_notification(self, notification: Notification) -> None:
        if notification.method != "textDocument/publishDiagnostics":
            return
        params = notification.params
        if not isinstance(params, dict):
            return
        uri = params.get("uri")
        raw = params.get("diagnostics")
        if not isinstance(uri, str) or not isinstance(raw, list):
            return
        version = params.get("version")
        with self._lock:
            if raw:
                self._files[uri] = _FileState(
                    version=version if isinstance(version, int) else None,
                    diagnostics=[item for item in raw if isinstance(item, dict)],
                )
            else:
                # An empty publish means "clean"; keeping the old entries would leave
                # a fixed error on screen.
                self._files.pop(uri, None)
            self._dirty = True
        self._schedule_flush()

    def _on_exit(self, _code: int | None) -> None:
        """Restart off-thread: the backoff sleep must not block the reporter."""
        with self._lock:
            if self._stopped:
                return
        supervisor = threading.Thread(target=self.restart, name="diagnostics-restart", daemon=True)
        supervisor.start()

    def _schedule_flush(self) -> None:
        """Reset the quiet-period timer; a burst of publishes collapses into one flush."""
        with self._lock:
            if self._stopped:
                return
            if self._timer is not None:
                self._timer.cancel()
            timer = threading.Timer(self._debounce_seconds, self._flush)
            timer.daemon = True
            self._timer = timer
        timer.start()

    def _flush(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            raw = {uri: list(state.diagnostics) for uri, state in self._files.items()}
            self._dirty = False
        problems = [
            problem
            for uri, items in raw.items()
            for problem in self._to_problems(uri, items)
        ]
        annotated = annotate(problems, self._load_anchors(), self._document())
        # pyright publishes per file as it gets to them, so without this the list
        # reorders itself between snapshots and the problems panel jumps around.
        annotated.sort(key=lambda item: (item.file or "", item.line or 0, item.column or 0, item.code or "", item.message))
        with self._lock:
            self._problems = annotated
            subscribers = list(self._subscribers)
        for callback in subscribers:
            callback(list(annotated))

    def _to_problems(self, uri: str, items: Sequence[dict[str, Any]]) -> list[Problem]:
        """LSP diagnostics of one file, converted to the problem model."""
        path = uri_to_path(uri)
        try:
            relative = path.relative_to(self._project_root).as_posix()
        except ValueError:
            relative = path.as_posix()
        problems: list[Problem] = []
        for item in items:
            start, end = _range_of(item)
            problems.append(
                make_problem(
                    tier="types",
                    severity=severity_from_lsp(item.get("severity")),
                    message=str(item.get("message", "")),
                    code=_code_of(item),
                    file=relative,
                    line=None if start is None else start[0] + 1,
                    column=None if start is None else start[1] + 1,
                    end_line=None if end is None else end[0] + 1,
                    end_column=None if end is None else end[1] + 1,
                )
            )
        return problems

    def _document(self) -> ProjectDocument | None:
        if self._document_provider is None:
            return None
        return self._document_provider()

    def _load_anchors(self) -> Anchors | None:
        """The anchor index, re-read when the file changes and dropped when unreadable.

        A generation that produced an index this reader cannot parse must not leave
        the previous, now wrong, index in place: refs would be attached to positions
        from the file it replaced.
        """
        try:
            stat = self._anchors_path.stat()
        except OSError:
            with self._lock:
                self._anchors = None
                self._anchors_stamp = None
            return None
        stamp = (stat.st_mtime_ns, stat.st_size)
        with self._lock:
            if self._anchors is not None and self._anchors_stamp == stamp:
                return self._anchors
        try:
            anchors = load_anchors(self._anchors_path)
        except ValueError:
            with self._lock:
                self._anchors = None
                self._anchors_stamp = stamp
            return None
        with self._lock:
            self._anchors = anchors
            self._anchors_stamp = stamp
        return anchors

    def _set_state(self, state: State, message: str | None) -> None:
        """Assign :attr:`state`; the caller holds ``self._lock``."""
        self._state = state
        self._state_message = message

    def __enter__(self) -> DiagnosticsService:
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()

    def __del__(self) -> None:  # pragma: no cover - depends on collection timing
        # A teardown path cannot propagate anything usefully, so the failure modes
        # are narrowed to the ones reclamation can actually hit.
        try:
            self.stop(timeout=0.5)
        except (OSError, subprocess.SubprocessError, LspError):
            pass


def _range_of(item: dict[str, Any]) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """``((start line, start char), (end line, end char))`` in LSP's 0-based form."""
    raw = item.get("range")
    if not isinstance(raw, dict):
        return (None, None)

    def corner(name: str) -> tuple[int, int] | None:
        value = raw.get(name)
        if not isinstance(value, dict):
            return None
        line, character = value.get("line"), value.get("character")
        if not isinstance(line, int) or not isinstance(character, int):
            return None
        return (line, character)

    return (corner("start"), corner("end"))


def _code_of(item: dict[str, Any]) -> str | None:
    """The pyright rule name.

    ``data.rule`` is only present on the subset of diagnostics pyright attaches
    actions or "unnecessary" marks to; ``code`` carries the rule for everything else.
    Checking ``code`` first and ``data.rule`` second would be wrong in the other
    direction, so both are consulted with the more specific one winning.
    """
    data = item.get("data")
    if isinstance(data, dict):
        rule = data.get("rule")
        if isinstance(rule, str) and rule:
            return rule
    code = item.get("code")
    if isinstance(code, str) and code:
        return code
    if isinstance(code, int):
        return str(code)
    return None
