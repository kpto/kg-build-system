"""One workspace: the document, the generated project, and the passes between them.

Every edit follows the same chain, and the chain is serialised on one worker thread
so a fast sequence of UI changes cannot interleave two generations:

    document commit → write project → reopen pyright buffers → compile → plan

Each pass publishes an event; the WebSocket hub forwards them. Compiling runs in a
subprocess (see :mod:`studio_backend.compile_worker`) because the framework imports
the generated package, and a regenerated package must never be served from a stale
``sys.modules`` entry.
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .catalog import load_module_class, module_catalogue
from .diagnostics.mapping import annotate_problems
from .diagnostics.service import DiagnosticsService
from .generate.project import write_project
from .ir.document import ProjectDocument
from .ir.normalize import NormalizationError, normalize_document
from .ir.store import DocumentInvalid, DocumentStore, RevisionConflict
from .ir.validate import Issue, validate_document
from .plan import project_plan

Event = dict[str, Any]
Listener = Callable[[Event], None]

_BLUEPRINT_TIMEOUT_SECONDS = 120.0


class DocumentRejected(Exception):
    """A proposed edit that could not be normalized or validated."""

    def __init__(self, problems: list[dict[str, Any]]) -> None:
        super().__init__("the document change was rejected")
        self.problems = problems


@dataclass
class Status:
    revision: int = 0
    generation: dict[str, Any] = field(default_factory=lambda: {"state": "never", "at": None, "changed": [], "error": None})
    blueprint: dict[str, Any] = field(default_factory=lambda: {"state": "never", "ok": None, "errors": 0})
    types: dict[str, Any] = field(default_factory=lambda: {"state": "starting", "errors": 0, "warnings": 0})
    build: dict[str, Any] = field(default_factory=lambda: {"state": "never"})

    def as_json(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "generation": self.generation,
            "blueprint": self.blueprint,
            "types": self.types,
            "build": self.build,
            "project_root": str(self.project_root) if getattr(self, "project_root", None) else None,
        }


@dataclass(frozen=True)
class _NullDiagnostics:
    """Stand-in used when the type tier is switched off."""

    state: str = "disabled"

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def subscribe(self, _callback: Any) -> Callable[[], None]:
        return lambda: None

    def snapshot(self) -> list[dict[str, Any]]:
        return []

    def reopen(self, _paths: Any = None) -> None:
        return None


class Workspace:
    """Serialised ownership of one project directory."""

    def __init__(self, project_root: Path, *, enable_diagnostics: bool = True) -> None:
        """``enable_diagnostics`` off skips the pyright language server entirely.

        The type tier is the slowest part of a workspace and is covered by its own
        integration test, so API and generation tests run without it.
        """
        self.project_root = Path(project_root).resolve()
        self._enable_diagnostics = enable_diagnostics
        self.store = DocumentStore(self.project_root)
        self._listeners: list[Listener] = []
        self._listener_lock = threading.Lock()
        self._jobs: queue.Queue[str] = queue.Queue()
        self._pending: set[str] = set()
        self._worker: threading.Thread | None = None
        self._stopping = threading.Event()
        self._pass_lock = threading.Lock()
        self.status = Status()
        self.status.project_root = self.project_root  # type: ignore[attr-defined]
        self._diagnostics: DiagnosticsService | None = None
        self._blueprint_cache: dict[str, Any] | None = None
        self._blueprint_document: dict[str, Any] | None = None
        self._plan_cache: dict[str, Any] | None = None
        self._plan_lock = threading.Lock()
        self._generation_fingerprint: str | None = None
        self._blueprint_error: dict[str, Any] | None = None
        self._blueprint_summary: dict[str, Any] = {}
        self._generation_gaps: tuple[Any, ...] = ()

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        if self._worker is not None:
            return
        self._worker = threading.Thread(target=self._run, name="studio-pipeline", daemon=True)
        self._worker.start()
        if self._enable_diagnostics:
            self.diagnostics.start()
        self.status.revision = self.document.revision
        self.request("pipeline")

    def stop(self) -> None:
        self._stopping.set()
        if self._diagnostics is not None:
            self._diagnostics.stop()
        self.request("wake")

    @property
    def document(self) -> ProjectDocument:
        return self.store.load()

    @property
    def diagnostics(self) -> DiagnosticsService:
        if not self._enable_diagnostics:
            return _NullDiagnostics()
        if self._diagnostics is None:
            self._diagnostics = DiagnosticsService(
                project_root=self.project_root, package=self.document.project.package
            )
            self._diagnostics.subscribe(self._on_diagnostics)
        return self._diagnostics

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        with self._listener_lock:
            self._listeners.append(listener)

        def unsubscribe() -> None:
            with self._listener_lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return unsubscribe

    def emit(self, type_: str, **payload: Any) -> None:
        event: Event = {"type": type_, **payload}
        with self._listener_lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception:  # noqa: BLE001 - a broken subscriber must not stop the pipeline
                continue

    # -- document editing ----------------------------------------------------

    def apply_document(
        self, candidate: ProjectDocument, *, expected_revision: int | None = None
    ) -> ProjectDocument:
        """Normalize, validate and commit a document, then queue regeneration.

        Raises :class:`DocumentRejected` with problem objects when the change cannot
        be made, and ``RevisionConflict`` when the client is behind.
        """
        with self._pass_lock:
            try:
                staged = self.store.stage(
                    candidate,
                    expected_revision=expected_revision,
                    known_modules=self.known_module_ids(),
                    normalize=lambda document: normalize_document(document),
                )
            except NormalizationError as error:
                raise DocumentRejected(_inference_problems(list(error.issues))) from error
            if staged.issues:
                raise DocumentRejected([_issue_problem(issue) for issue in staged.issues])
            if not staged.changed:
                # Nothing to write: the caller's edit was a no-op, so the current
                # document is returned unchanged at its existing revision.
                return self.store.load()
            committed = self.store.commit(staged)
            self.status.revision = committed.revision
            self._blueprint_cache = None
            self._blueprint_document = None
            self._plan_cache = None
            self.emit("document", revision=committed.revision, document=committed.model_dump(mode="json"))
            self.request("pipeline")
            return committed

    def initialize_project(self, *, package: str, name: str) -> ProjectDocument:
        document = ProjectDocument(project={"name": name, "package": package})
        if self.store.exists:
            return self.store.load()
        created = self.store.initialize(document)
        self.status.revision = created.revision
        self.emit("document", revision=created.revision, document=created.model_dump(mode="json"))
        self.request("pipeline")
        return created

    def known_module_ids(self) -> set[str]:
        return {entry.id for entry in module_catalogue()}

    # -- job queue -----------------------------------------------------------

    def request(self, kind: str) -> None:
        """Queue a pass, coalescing repeats of the same kind."""
        with self._listener_lock:
            if kind in self._pending:
                return
            self._pending.add(kind)
        self._jobs.put(kind)

    def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                kind = self._jobs.get(timeout=0.5)
            except queue.Empty:
                continue
            with self._listener_lock:
                self._pending.discard(kind)
            try:
                if kind == "pipeline":
                    self._pipeline()
                elif kind == "compile":
                    self.compile_pass()
            except Exception as error:  # noqa: BLE001 - the pipeline must survive any pass failing
                self.emit("log", level="error", text=f"{kind} pass failed: {error}")

    # -- passes --------------------------------------------------------------

    def _pipeline(self) -> None:
        document = self.document
        fingerprint = self.store.fingerprint
        if fingerprint == self._generation_fingerprint and self.status.generation["state"] == "clean":
            self.compile_pass()
            return
        started = time.monotonic()
        self.status.generation = {"state": "running", "at": None, "changed": [], "error": None}
        self.emit("generation", state="running", changed=[], error=None)
        try:
            outcome = write_project(document, self.project_root, state_dir=self.store.state_directory)
        except Exception as error:  # noqa: BLE001 - a generation failure is data for the UI
            self.status.generation = {"state": "failed", "at": _now(), "changed": [], "error": str(error)}
            self.emit("generation", state="failed", changed=[], error=str(error), elapsed_ms=_elapsed(started))
            return
        self._generation_fingerprint = fingerprint
        self._generation_gaps = tuple(getattr(outcome, "gaps", ()))
        self.status.generation = {
            "state": "clean",
            "at": _now(),
            "changed": list(outcome.changed),
            "error": None,
        }
        self.emit(
            "generation",
            state="done",
            changed=list(outcome.changed),
            error=None,
            elapsed_ms=_elapsed(started),
        )
        self.diagnostics.reopen(outcome.changed or None)
        self.compile_pass()
        self._refresh_problems()

    def compile_pass(self) -> dict[str, Any]:
        """Run the framework's blueprint pass and cache its plan."""
        result = self._worker_call("plan")
        if not result.get("ok"):
            error = result.get("error", {})
            problems = self.blueprint_problems(error)
            self._blueprint_error = error
            self.status.blueprint = {"state": "failed", "ok": False, "errors": len(problems)}
            self._blueprint_cache = None
            with self._plan_lock:
                self._plan_cache = None
            self.emit("blueprint", ok=False, errors=_wire_problems(problems), summary={})
            self.emit("plan", plan=None, errors=_wire_problems(problems))
            self._refresh_problems()
            return {"ok": False, "errors": problems}
        plan = result["plan"]
        with self._plan_lock:
            self._plan_cache = plan
        self._blueprint_cache = result.get("contract")
        self._blueprint_error = None
        self.status.blueprint = {"state": "clean", "ok": True, "errors": 0}
        self.emit("blueprint", ok=True, errors=[], summary=_blueprint_summary(self._blueprint_cache))
        self.emit("plan", plan=plan)
        self._refresh_problems()
        return {"ok": True, "plan": plan}

    def blueprint_problems(self, error: dict[str, Any]) -> list[dict[str, Any]]:
        from .diagnostics.blueprint_errors import map_blueprint_error

        message = str(error.get("message", ""))
        problem = map_blueprint_error(message, self.document)
        if problem is None:
            return [
                {
                    "id": _problem_id("blueprint", "", "", message),
                    "tier": "blueprint",
                    "severity": "error",
                    "message": message,
                    "code": error.get("type"),
                    "file": None,
                    "line": None,
                    "column": None,
                    "end_line": None,
                    "end_column": None,
                    "ref": None,
                    "ref_trusted": None,
                    "hint": "The generated project did not compile; check the newest change.",
                }
            ]
        # `map_blueprint_error` hands back a Problem mapping; everything downstream —
        # both event payloads and the JSON endpoints — is a `json.dumps` away, so the
        # mapping is flattened here rather than at each of its five call sites.
        return _wire_problems([problem])

    # -- reads ---------------------------------------------------------------

    def plan(self, *, refresh: bool = False) -> dict[str, Any]:
        if refresh or self._plan_cache is None:
            outcome = self.compile_pass()
            if not outcome.get("ok"):
                return {"plan": None, "errors": outcome.get("errors", [])}
        with self._plan_lock:
            return {"plan": self._plan_cache, "errors": []}

    def blueprint(self, *, refresh: bool = False) -> dict[str, Any]:
        """The compiled blueprint, distinct from the workflow contract.

        ``compile`` produces the executable contract; ``create_blueprint`` produces the
        portable definition the UI summarises (components, bindings, sources). The plan
        pass caches the contract, so asking for the blueprint runs the other pass.
        """
        if refresh or self._blueprint_document is None:
            result = self._worker_call("blueprint")
            if not result.get("ok"):
                return {"blueprint": None, "errors": self.blueprint_problems(result.get("error", {}))}
            self._blueprint_document = result.get("blueprint")
            self._blueprint_summary = result.get("summary", {})
        return {"blueprint": self._blueprint_document, "summary": self._blueprint_summary, "errors": []}

    def index(self) -> dict[str, Any]:
        from .ir.index import build_index

        return build_index(self.document).model_dump(mode="json")

    def problems(self) -> list[dict[str, Any]]:
        return self._current_problems()

    def build(self) -> dict[str, Any]:
        self.status.build = {"state": "running"}
        self.emit("build", state="running")
        result = self._worker_call("build")
        if not result.get("ok"):
            problems = self.blueprint_problems(result.get("error", {}))
            self.status.build = {"state": "failed", "problems": len(problems)}
            self.emit("build", state="failed", ok=False, problems=problems, artifacts=[])
            return {"ok": False, "problems": problems}
        self.status.build = {"state": "done", "at": _now()}
        artifacts = [str(item) for item in result.get("published", [])]
        self.emit("build", state="done", ok=True, artifacts=artifacts, problems=[], report=result.get("report"))
        return {"ok": True, "artifacts": artifacts, "report": result.get("report")}

    def source_for_ref(self, reference: str) -> dict[str, Any] | None:
        """The generated file and line a reference produced, for "view code"."""
        anchors = self._anchors()
        if anchors is None:
            return None
        best: tuple[int, dict[str, Any], str] | None = None
        for path, entries in anchors.get("files", {}).items():
            for entry in entries:
                if entry.get("ref") == reference:
                    size = int(entry.get("end_line", 0)) - int(entry.get("line", 0))
                    if best is None or size < best[0]:
                        best = (size, entry, path)
        if best is None:
            return None
        _, entry, path = best
        file_path = self.project_root / path
        if not file_path.is_file():
            return None
        return {
            "ref": reference,
            "path": path,
            "line": entry.get("line"),
            "text": file_path.read_text(encoding="utf-8"),
        }

    def state_snapshot(self) -> dict[str, Any]:
        document = self.document
        return {
            "document": document.model_dump(mode="json"),
            "revision": document.revision,
            "status": self.status_json(),
            "project_root": str(self.project_root),
        }

    def status_json(self) -> dict[str, Any]:
        payload = {
            "revision": self.status.revision,
            "generation": self.status.generation,
            "blueprint": self.status.blueprint,
            "types": self.status.types,
            "build": self.status.build,
            "project_root": str(self.project_root),
        }
        return payload

    # -- subprocess ----------------------------------------------------------

    def _worker_call(self, mode: str) -> dict[str, Any]:
        arguments = [
            sys.executable,
            "-m",
            "studio_backend.compile_worker",
            mode,
            "--project-root",
            str(self.project_root),
            "--package",
            self.document.project.package,
        ]
        arguments += _module_arguments(self.document)
        arguments += ["--output-directory", str(self.project_root / "build")]
        try:
            completed = subprocess.run(
                arguments,
                cwd=str(Path(__file__).resolve().parent.parent),
                capture_output=True,
                text=True,
                timeout=_BLUEPRINT_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": {"type": "Timeout", "message": "the compile pass timed out"}}
        payload = _last_json_line(completed.stdout)
        if payload is None:
            return {
                "ok": False,
                "error": {
                    "type": "WorkerFailure",
                    "message": (completed.stderr or completed.stdout or "the compile worker produced no output").strip(),
                },
            }
        return payload

    # -- problems ------------------------------------------------------------

    def _current_problems(self) -> list[dict[str, Any]]:
        anchors = self._anchors()
        typed = [dict(problem) for problem in self.diagnostics.snapshot()]
        annotated = annotate_problems(typed, anchors, self.document) if anchors is not None else typed
        blueprint_problems: list[dict[str, Any]] = []
        if self.status.blueprint["state"] == "failed" and self._blueprint_error is not None:
            blueprint_problems = self.blueprint_problems(self._blueprint_error)
        document_problems = [_issue_problem(issue) for issue in validate_document(self.document, known_modules=self.known_module_ids())]
        return _wire_problems(
            [*annotated, *blueprint_problems, *document_problems, *self._gap_problems()]
        )

    def _gap_problems(self) -> list[dict[str, Any]]:
        """Slots the generator refused to soften, as problems on the declaration.

        The generator renders a slot exactly as declared, so an under-filling binding
        would otherwise only appear as a compile failure. Naming it here points at the
        component property the author needs to either fill or mark optional.
        """
        problems: list[dict[str, Any]] = []
        for gap in self._generation_gaps:
            reference = f"component:{gap.component}.property.{gap.property}"
            problems.append(
                {
                    "id": _problem_id("document", reference, gap.kind, gap.message),
                    "tier": "document",
                    "severity": "error",
                    "message": gap.message,
                    "code": gap.kind,
                    "file": None,
                    "line": None,
                    "column": None,
                    "end_line": None,
                    "end_column": None,
                    "ref": reference,
                    "ref_trusted": "name",
                    "hint": (
                        "Fill it in a binding, or declare the slot optional so an absent "
                        "value is a stated choice rather than a silent one."
                    ),
                }
            )
        return problems

    def _refresh_problems(self) -> None:
        problems = self._current_problems()
        errors = [problem for problem in problems if problem.get("severity") == "error"]
        self.status.types = {
            "state": self.diagnostics.state,
            "errors": sum(1 for problem in problems if problem.get("tier") == "types" and problem.get("severity") == "error"),
            "warnings": sum(1 for problem in problems if problem.get("tier") == "types" and problem.get("severity") == "warning"),
        }
        self.emit("diagnostics", problems=problems, pyright={"state": self.diagnostics.state})
        self.emit("log", level="info", text=f"{len(errors)} problems")

    def _on_diagnostics(self, _snapshot: Any) -> None:
        self.request("problems")
        threading.Thread(target=self._refresh_problems, name="studio-problems", daemon=True).start()

    def _anchors(self) -> dict[str, Any] | None:
        return self.store.read_json(self.store.anchors_path)


def _module_arguments(document: ProjectDocument) -> list[str]:
    catalogue = {entry.id: entry for entry in module_catalogue()}
    arguments: list[str] = []
    for module in document.modules:
        if not module.enabled:
            continue
        entry = catalogue.get(module.id)
        if entry is None:
            continue
        arguments += [
            "--module",
            json.dumps(
                {
                    "import_module": entry.import_module,
                    "class_qualname": entry.class_qualname,
                    "configuration": module.configuration,
                }
            ),
        ]
    return arguments


def _wire_problems(problems: list[Any]) -> list[dict[str, Any]]:
    """Plain JSON dicts for the wire, whatever a problem is modelled as internally.

    ``diagnostics.problem.Problem`` is a ``Mapping`` with extra behaviour, and it is
    easy for one tier to hand back the class rather than a dict; json.dumps would then
    fail inside the response, turning a diagnosable problem into a 500. Normalising
    here means the API can only ever emit the contract shape.
    """
    wire: list[dict[str, Any]] = []
    for problem in problems:
        if isinstance(problem, dict):
            wire.append(problem)
        elif hasattr(problem, "as_json"):
            wire.append(problem.as_json())
        else:
            wire.append(dict(problem))
    return wire


def _issue_problem(issue: Issue) -> dict[str, Any]:
    return {
        "id": _problem_id("document", issue.path or "", "", issue.message),
        "tier": "document",
        "severity": issue.severity,
        "message": issue.message,
        "code": "document",
        "file": None,
        "line": None,
        "column": None,
        "end_line": None,
        "end_column": None,
        "ref": issue.ref,
        "ref_trusted": "name",
        "hint": None,
    }


def _inference_problems(issues: list[str]) -> list[dict[str, Any]]:
    problems = []
    for issue in issues:
        location, _, message = issue.partition(": ")
        problems.append(
            {
                "id": _problem_id("document", location, "", message or issue),
                "tier": "document",
                "severity": "error",
                "message": message or issue,
                "code": "inference",
                "file": None,
                "line": None,
                "column": None,
                "end_line": None,
                "end_column": None,
                "ref": location if ":" in location else None,
                "ref_trusted": "name",
                "hint": None,
            }
        )
    return problems


def _problem_id(*parts: str) -> str:
    import hashlib

    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _blueprint_summary(contract: Any) -> dict[str, int]:
    if not isinstance(contract, dict):
        return {}
    return {key: len(value) for key, value in contract.items() if isinstance(value, list)}


def _last_json_line(text: str) -> dict[str, Any] | None:
    for line in reversed((text or "").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _elapsed(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
