"""Persisting the IR document: atomic writes, revisions and fingerprints.

The document at ``<project_root>/.kg-studio/project.ir.json`` is the project's
source of truth and is meant to be committed to version control, so writes are
atomic and every accepted change bumps a monotonic revision. Derived state
(``manifest.json``, ``anchors.json``) lives beside it but is regenerable and is
never read as authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .document import DOCUMENT_FILENAME, ProjectDocument
from .validate import Issue, blocking, validate_document

STATE_DIRECTORY = ".kg-studio"
MANIFEST_FILENAME = "manifest.json"
ANCHORS_FILENAME = "anchors.json"


class RevisionConflict(Exception):
    """A commit was attempted against a revision that is no longer current."""

    def __init__(self, expected: int, actual: int, document: ProjectDocument) -> None:
        super().__init__(f"expected revision {expected}, document is at {actual}")
        self.expected = expected
        self.actual = actual
        self.document = document


class DocumentInvalid(Exception):
    """A document failed structural validation and was not written."""

    def __init__(self, issues: list[Issue]) -> None:
        super().__init__("; ".join(issue.message for issue in issues) or "invalid document")
        self.issues = issues


@dataclass(frozen=True, slots=True)
class StagedDocument:
    document: ProjectDocument
    issues: tuple[Issue, ...]
    changed: bool


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_fingerprint(document: ProjectDocument) -> str:
    """Identity of the document's meaning, ignoring its revision.

    Two saves of the same content must produce the same fingerprint, otherwise
    every keystroke would look like a generation input change.
    """
    payload = document.model_dump(mode="json", exclude={"revision"})
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DocumentStore:
    """Single-writer access to one workspace's IR document."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()
        self.state_directory = self.project_root / STATE_DIRECTORY
        self.document_path = self.state_directory / DOCUMENT_FILENAME
        self.manifest_path = self.state_directory / MANIFEST_FILENAME
        self.anchors_path = self.state_directory / ANCHORS_FILENAME
        self._lock = threading.RLock()
        self._document: ProjectDocument | None = None
        self._fingerprint: str | None = None
        #: Digest of the file bytes the cached document came from. It has to be
        #: remembered, not recomputed on demand, or comparing it to the file would
        #: always report "unchanged".
        self._disk_digest: str = ""

    # -- paths ---------------------------------------------------------------

    @property
    def package_directory(self) -> Path:
        document = self.document
        return self.project_root / document.project.package

    # -- reading -------------------------------------------------------------

    @property
    def exists(self) -> bool:
        return self.document_path.is_file()

    def load(self) -> ProjectDocument:
        """The current document, read from disk once and then cached."""
        with self._lock:
            if self._document is None:
                text = self._read_text()
                self._document = self._parse(text)
                self._disk_digest = _digest(text)
                self._fingerprint = content_fingerprint(self._document)
            return self._document

    def _read_text(self) -> str | None:
        if not self.document_path.is_file():
            return None
        return self.document_path.read_text(encoding="utf-8")

    def _parse(self, text: str | None) -> ProjectDocument:
        if text is None:
            return ProjectDocument()
        return ProjectDocument.model_validate(json.loads(text))

    def reload_if_changed(self) -> ProjectDocument | None:
        """Adopt an out-of-band edit, returning the document when one appeared.

        Hand-editing the document is a supported workflow, so an external change
        must not be overwritten blindly by the next commit.
        """
        with self._lock:
            self.load()
            text = self._read_text()
            if text is None:
                return None
            digest = _digest(text)
            if digest == self._disk_digest:
                return None
            document = self._parse(text)
            self._document = document
            self._fingerprint = content_fingerprint(document)
            self._disk_digest = digest
            return document

    # -- writing -------------------------------------------------------------

    def stage(
        self,
        candidate: ProjectDocument,
        *,
        expected_revision: int | None = None,
        known_modules: set[str] | None = None,
        normalize: Any = None,
    ) -> StagedDocument:
        """Validate a candidate change without writing it.

        ``normalize`` is the backend's pass over a document that fills derived
        fields the client is not allowed to own (expression ``logical_type`` values
        and struct reference modules). It is injected rather than imported so this
        module stays free of the inference layer.
        """
        with self._lock:
            current = self.load()
            if expected_revision is not None and expected_revision != current.revision:
                raise RevisionConflict(expected_revision, current.revision, current)
            document = candidate.updated(revision=current.revision)
            if normalize is not None:
                document = normalize(document)
            issues = validate_document(document, known_modules=known_modules)
            return StagedDocument(document=document, issues=blocking(list(issues)), changed=self._fingerprint != content_fingerprint(document))

    def commit(self, staged: StagedDocument) -> ProjectDocument:
        """Persist a staged document as the next revision."""
        with self._lock:
            if staged.issues:
                raise DocumentInvalid(list(staged.issues))
            current = self.load()
            if not staged.changed:
                return current
            document = staged.document.updated(revision=current.revision + 1)
            self._write(document)
            self._document = document
            self._fingerprint = content_fingerprint(document)
            return document

    def initialize(self, document: ProjectDocument) -> ProjectDocument:
        """Create the document for a workspace that has none yet."""
        with self._lock:
            if self.exists:
                raise FileExistsError(f"a project document already exists at {self.document_path}")
            payload = document.updated(revision=1)
            issues = blocking(validate_document(payload))
            if issues:
                raise DocumentInvalid(issues)
            self._write(payload)
            self._document = payload
            self._fingerprint = content_fingerprint(payload)
            return payload

    def _write(self, document: ProjectDocument) -> None:
        text = document.model_dump_json(indent=2) + "\n"
        self.state_directory.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{self.document_path.name}.", dir=self.state_directory
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.document_path)
            self._disk_digest = _digest(text)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    # -- derived state -------------------------------------------------------

    def write_json(self, path: Path, payload: Any) -> None:
        self.state_directory.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def read_json(self, path: Path) -> Any | None:
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    @property
    def revision(self) -> int:
        return self.load().revision

    @property
    def document(self) -> ProjectDocument:
        return self.load()

    @property
    def fingerprint(self) -> str:
        self.load()
        assert self._fingerprint is not None
        return self._fingerprint
