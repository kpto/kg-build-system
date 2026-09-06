"""The whole-project writer: render, verify ownership, replace atomically.

``write_project`` is the only place that touches disk. It owns exactly the files it
has written, recorded in ``<state_dir>/manifest.json`` with a hash each, and:

* never writes a path it does not own, unless the bytes already equal what it would
  write — a file studio did not create is left alone rather than overwritten;
* prunes owned files the document no longer wants, and the ``__pycache__`` under the
  directories it owns, so a rename leaves nothing behind that could still be imported;
* writes every file through a temporary file and ``os.replace``, so a crash mid-write
  cannot leave a half-written module;
* never writes inside ``<project_root>/<data_directory>``, which holds the inputs the
  project reads and studio does not own.

A second write of the same document changes nothing: identical bytes are not rewritten
and the manifest keeps the timestamp of the run that actually changed something.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from ..ir.document import ProjectDocument
from . import (
    annotations,
    bindings,
    entry,
    projections,
    sources,
    tables,
    topology,
)
from .anchors import ANCHOR_FILENAME, build_anchor_index
from .layout import Layout
from .render import GenerationError, RenderedFile, document_fingerprint

STATE_DIRECTORY: Final = ".kg-studio"
MANIFEST_FILENAME: Final = "manifest.json"
MANIFEST_FORMAT_VERSION: Final = 1


class OwnershipError(GenerationError):
    """A path the manifest does not own, which studio therefore will not touch."""


@dataclass(frozen=True)
class GenerationOutcome:
    """What one write did, so the caller can report and the watcher can react."""

    project_root: Path
    state_dir: Path
    package: str
    document_fingerprint: str
    revision: int
    owned_files: tuple[str, ...]
    written: tuple[str, ...]
    unchanged: tuple[str, ...]
    removed: tuple[str, ...]
    adopted: tuple[str, ...]
    discarded_edits: tuple[str, ...]
    anchors_path: Path
    manifest_path: Path
    #: Declared slots the document's own bindings do not honour. The generator renders
    #: the declaration faithfully, so these reach the UI instead of the source code.
    gaps: tuple[Any, ...] = ()
    anchors: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def changed(self) -> tuple[str, ...]:
        return tuple(sorted({*self.written, *self.removed}))


def render_project(document: ProjectDocument) -> list[RenderedFile]:
    """Every owned file of one document, in a stable order, each one validated."""
    layout = Layout(document)
    data_prefix = f"{layout.package}/{document.project.data_directory}/"
    files: list[RenderedFile] = []
    layers = (
        annotations.render_annotations(document, layout),
        tables.render_tables(document, layout),
        projections.render_projections(document, layout),
        topology.render_topology(document, layout),
        bindings.render_bindings(document, layout),
        sources.render_sources(document, layout),
    )
    for layer in layers:
        files.extend(layer)
    files.extend(entry.render_entry(document, layout, files))

    seen: dict[str, str] = {}
    for rendered in files:
        folded = rendered.path.casefold()
        if folded in seen and seen[folded] != rendered.path:
            raise GenerationError(
                f"{rendered.path} and {seen[folded]} collide once case-folded, "
                "which one filesystem would treat as one file"
            )
        seen[folded] = rendered.path
        if rendered.path.startswith(data_prefix) or f"/{data_prefix}" in f"/{rendered.path}":
            raise GenerationError(
                f"{rendered.path} is inside {document.project.data_directory}/, "
                "which holds the data the project reads and studio never owns"
            )
    return files


def write_project(
    document: ProjectDocument,
    project_root: Path,
    *,
    state_dir: Path | None = None,
    revision: int | None = None,
) -> GenerationOutcome:
    """Render and write the whole project, then its manifest and anchor index."""
    root = Path(project_root).expanduser()
    state = Path(state_dir) if state_dir is not None else root / STATE_DIRECTORY
    files = render_project(document)
    gaps = topology.slot_gaps(document)
    fingerprint = document_fingerprint(document)
    layout = Layout(document)

    manifest = _read_manifest(state / MANIFEST_FILENAME)
    owned = set(manifest.get("owned_files", ()))
    hashes = dict(manifest.get("owned_file_hashes", {}))

    wanted = {item.path: item for item in files}
    _verify_ownership(root, wanted, owned, hashes)
    adopted = tuple(
        sorted(
            path
            for path in wanted
            if path not in owned and (root / path).exists()
        )
    )
    discarded = tuple(
        sorted(
            path
            for path, recorded in hashes.items()
            if path in wanted and _digest(root / path) != recorded and (root / path).exists()
        )
    )

    written: list[str] = []
    unchanged: list[str] = []
    for path in sorted(wanted):
        if _write(root / path, wanted[path].content):
            written.append(path)
        else:
            unchanged.append(path)

    removed = _prune(root, owned - set(wanted), manifest)

    directories = {str(Path(path).parent) for path in wanted}
    removed = tuple(sorted({*removed, *_prune_directories(root, manifest, directories)}))
    _clean_caches(root, sorted({*directories, layout.package, "."}))

    anchors = build_anchor_index(
        document, files, fingerprint=fingerprint, revision=revision
    )
    previous_generated = str(manifest.get("generated_at", ""))
    same_bytes = (
        owned == set(wanted)
        and hashes == {path: _text_digest(item.content) for path, item in wanted.items()}
        and manifest.get("anchors_hash") == _value_digest(anchors)
    )
    generated_at = previous_generated or _timestamp() if same_bytes else _timestamp()

    payload = {
        "format_version": MANIFEST_FORMAT_VERSION,
        "document_fingerprint": fingerprint,
        "owned_files": sorted(wanted),
        "owned_file_hashes": {path: _text_digest(item.content) for path, item in sorted(wanted.items())},
        "owned_directories": sorted({*directories, layout.package}),
        "generated_at": generated_at,
        "anchors_hash": _value_digest(anchors),
    }
    _write(state / MANIFEST_FILENAME, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _write(
        state / ANCHOR_FILENAME,
        json.dumps(anchors, indent=2, sort_keys=True) + "\n",
    )

    return GenerationOutcome(
        project_root=root,
        state_dir=state,
        package=layout.package,
        document_fingerprint=fingerprint,
        revision=document.revision if revision is None else revision,
        owned_files=tuple(sorted(wanted)),
        written=tuple(written),
        unchanged=tuple(unchanged),
        removed=removed,
        adopted=adopted,
        discarded_edits=discarded,
        anchors_path=state / ANCHOR_FILENAME,
        manifest_path=state / MANIFEST_FILENAME,
        gaps=gaps,
        anchors=anchors,
    )


# ------------------------------------------------------------------- ownership


def _verify_ownership(
    root: Path, wanted: dict[str, RenderedFile], owned: set[str], hashes: dict[str, str]
) -> None:
    for path, rendered in sorted(wanted.items()):
        target = _resolve_in(root, path)
        if not target.exists() or path in owned:
            continue
        if _digest(target) == _text_digest(rendered.content):
            continue  # already exactly the bytes studio would write
        raise OwnershipError(
            f"{path} exists and studio did not generate it; refusing to overwrite it"
        )
    for path in sorted(hashes):
        if path in wanted:
            continue
        target = _resolve_in(root, path)
        if not target.exists():
            continue
        if path not in owned:
            raise OwnershipError(
                f"{path} is recorded in the manifest but is no longer owned; refusing to prune it"
            )


def _resolve_in(root: Path, relative: str) -> Path:
    parts = Path(relative).parts
    if not relative or Path(relative).is_absolute() or ".." in parts:
        raise GenerationError(f"{relative!r} is not a path inside the project")
    target = root.joinpath(*parts)
    resolved = target.resolve() if target.exists() else target
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise GenerationError(f"{relative} resolves outside {root}") from error
    return target


# ------------------------------------------------------------------------ writes


def _write(path: Path, content: str) -> bool:
    """Write through a temporary file; report whether the bytes actually changed."""
    target = _resolve_in(path.parent, path.name)
    if target.exists() and target.read_text(encoding="utf-8") == content:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, _file_mode(target))
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return True


def _file_mode(target: Path) -> int:
    if target.exists():
        return target.stat().st_mode & 0o777
    mode = 0o644
    mask = os.umask(0)
    os.umask(mask)
    return mode & ~mask


# ----------------------------------------------------------------------- pruning


def _prune(root: Path, paths: set[str], manifest: dict[str, Any]) -> tuple[str, ...]:
    """Delete owned files the document no longer wants, hash-verified.

    A file whose bytes are no longer the ones studio wrote is no longer ours to
    remove, whatever the manifest once said, so the run stops rather than deleting
    something somebody else has put there.
    """
    hashes = dict(manifest.get("owned_file_hashes", {}))
    removed: list[str] = []
    for relative in sorted(paths):
        if not relative.endswith(".py"):
            continue  # the manifest only ever records Python files, but be explicit
        if relative not in hashes:
            raise OwnershipError(
                f"{relative} is no longer wanted but studio does not own it"
            )
        target = _resolve_in(root, relative)
        if not target.exists():
            removed.append(relative)
            continue
        if _digest(target) != hashes[relative]:
            raise OwnershipError(
                f"{relative} is no longer wanted but no longer holds the bytes studio "
                "wrote; refusing to delete it"
            )
        target.unlink()
        removed.append(relative)
    return tuple(removed)


def _prune_directories(root: Path, manifest: dict[str, Any], keep: set[str]) -> tuple[str, ...]:
    """Package directories a rename or a deletion left behind.

    Only directories studio recorded as owned are visited, deepest first, and one is
    removed only once nothing of anyone else's remains in it — which after the cache
    sweep means nothing at all.
    """
    for relative in sorted(keep):
        _empty_cache_dirs(root / relative)
    removed: list[str] = []
    candidates = sorted(set(manifest.get("owned_directories", ())) - keep, key=lambda item: -len(item))
    for relative in candidates:
        if relative in (".", ""):
            continue
        target = _resolve_in(root, relative)
        if not target.is_dir():
            continue
        _empty_cache_dirs(target)
        try:
            target.rmdir()
        except OSError:
            continue  # someone else has files here; leave the directory alone
        removed.append(relative)
    return tuple(removed)


def _empty_cache_dirs(target: Path) -> None:
    for cache in target.glob("**/__pycache__"):
        if cache.is_dir():
            shutil.rmtree(cache, ignore_errors=True)


def _clean_caches(root: Path, directories: list[str]) -> None:
    """Drop stale byte-code under owned directories so an old module cannot import."""
    for relative in directories:
        directory = root if relative in (".", "") else _resolve_in(root, relative)
        if not directory.is_dir():
            continue
        for cache in sorted(directory.glob("**/__pycache__")):
            if cache.is_dir():
                shutil.rmtree(cache, ignore_errors=True)


# ---------------------------------------------------------------------- manifest


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise GenerationError(f"{path} is not readable as a manifest: {error}") from error
    if not isinstance(payload, dict):
        raise GenerationError(f"{path} is not a manifest")
    version = payload.get("format_version")
    if version not in (None, MANIFEST_FORMAT_VERSION):
        raise GenerationError(
            f"{path} was written by format version {version!r}, not "
            f"{MANIFEST_FORMAT_VERSION}; regenerate the project from the document"
        )
    return payload


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _digest(path: Path) -> str:
    if not path.exists():
        return ""
    return _text_digest(path.read_text(encoding="utf-8"))


def _text_digest(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


def _value_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
