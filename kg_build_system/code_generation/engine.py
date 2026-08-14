"""Desired-state generation, manifest ownership, safe installation, and pruning."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import asdict, replace
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import tempfile

from .discovery import discover, discover_file
from .models import (
    DiscoveredGeneration, GenerationAction, GenerationActionKind, GenerationError,
    GenerationManifest, GenerationResult, GenerationStatus,
)
from .providers import ProviderContext, load_provider
from .rendering import FORMAT_VERSION, HEADER, generation_fingerprint, render_package

MANIFEST = ".kbs-generation.json"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def _manifest_text(manifest: GenerationManifest) -> str:
    return json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n"


def _load_manifest(path: Path) -> GenerationManifest:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return GenerationManifest(
            format_version=str(value["format_version"]), request_id=str(value["request_id"]),
            request_source_package=str(value["request_source_package"]), provider_import=str(value["provider_import"]),
            provider_qualname=str(value["provider_qualname"]), provider_version=str(value["provider_version"]),
            request_fingerprint=str(value["request_fingerprint"]),
            owned_files=tuple(str(item) for item in value["owned_files"]),
            owned_directories=tuple(str(item) for item in value["owned_directories"]),
            owned_file_hashes={str(key): str(item) for key, item in value.get("owned_file_hashes", {}).items()},
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise GenerationError(f"invalid generation manifest {path}: {error}") from error


def _safe_owned(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise GenerationError(f"unsafe owned manifest path {value!r}")
    return path


def _ownership_header(request_id: str, fingerprint: str) -> str:
    return f"{HEADER}\n# request: {request_id}\n# fingerprint: {fingerprint}\n"


def _verify_owned(root: Path, relative: str, manifest: GenerationManifest) -> Path:
    path = root.joinpath(*_safe_owned(relative).parts)
    if path.exists():
        content = path.read_text(encoding="utf-8") if path.is_file() else ""
        expected_hash = manifest.owned_file_hashes.get(relative)
        if not path.is_file() or not content.startswith(_ownership_header(manifest.request_id, manifest.request_fingerprint)) or (
            expected_hash is not None and sha256(content.encode()).hexdigest() != expected_hash
        ):
            raise GenerationError(f"owned generated file was unexpectedly modified: {path}")
    return path


def _bytecode_files(source: Path) -> tuple[Path, ...]:
    """Return cache files derived unambiguously from one generated Python source."""
    if source.suffix != ".py": return ()
    cache = source.parent / "__pycache__"
    if not cache.is_dir(): return ()
    return tuple(sorted(cache.glob(f"{source.stem}.*.pyc"), key=lambda path: path.name))


def _prune_bytecode(sources: Iterable[Path]) -> list[Path]:
    removed: list[Path] = []
    cache_directories: set[Path] = set()
    for source in sources:
        cache_directories.add(source.parent / "__pycache__")
        for bytecode in _bytecode_files(source):
            bytecode.unlink(); removed.append(bytecode)
    for cache in sorted(cache_directories, key=lambda path: (-len(path.parts), path.as_posix())):
        if cache.is_dir() and not any(cache.iterdir()): cache.rmdir()
    return removed


def _owned_directories(files: Iterable[PurePosixPath]) -> tuple[str, ...]:
    values: set[PurePosixPath] = set()
    for file in files:
        parent = file.parent
        while parent != PurePosixPath("."):
            values.add(parent); parent = parent.parent
    return tuple(path.as_posix() for path in sorted(values, key=lambda p: (len(p.parts), p.as_posix())))


async def _desired(root: Path, request: DiscoveredGeneration) -> tuple[Path, dict[Path, str], GenerationManifest, tuple[Path, ...]]:
    provider, config = load_provider(request.request)
    context = ProviderContext(root, request.location.source_path, request.location.request_id, config)
    dependencies = tuple(await provider.dependencies(context))
    for dependency in dependencies:
        try: dependency.resolve().relative_to(root)
        except ValueError as error: raise GenerationError(f"provider dependency is outside the project: {dependency}") from error
        if not dependency.is_file(): raise GenerationError(f"provider dependency does not exist: {dependency}")
    fingerprint = generation_fingerprint(request, provider.VERSION, tuple(path.read_bytes() for path in dependencies))
    first = render_package(request, await provider.generate(context), fingerprint)
    second = render_package(request, await provider.generate(context), fingerprint)
    if first != second: raise GenerationError(f"provider {provider.__module__}.{provider.__qualname__} is not deterministic")
    rendered = first
    product = root / request.product_path
    desired = {product.joinpath(*relative.parts): content for relative, content in rendered.items()}
    relative_files = tuple(sorted(rendered, key=lambda value: value.as_posix()))
    manifest = GenerationManifest(
        FORMAT_VERSION, request.location.request_id, request.location.source_package,
        provider.__module__, provider.__qualname__, provider.VERSION, fingerprint,
        tuple(path.as_posix() for path in relative_files), _owned_directories(relative_files),
        {path.as_posix(): sha256(rendered[path].encode()).hexdigest() for path in relative_files},
    )
    desired[product / MANIFEST] = _manifest_text(manifest)
    return product, desired, manifest, dependencies


def _existing_manifests(root: Path) -> tuple[Path, ...]:
    manifests: list[Path] = []
    for directory, directory_names, file_names in root.walk(top_down=True):
        directory_names[:] = sorted(
            name for name in directory_names
            if not name.startswith(".") and name != "__pycache__"
        )
        if MANIFEST in file_names:
            manifests.append(directory / MANIFEST)
    return tuple(sorted(manifests, key=lambda path: path.as_posix()))


def _compare_product(product: Path, desired: dict[Path, str], manifest: GenerationManifest) -> tuple[list[Path], list[Path]]:
    manifest_path = product / MANIFEST
    stale: list[Path] = []
    obsolete: list[Path] = []
    if product.exists() and not product.is_dir():
        raise GenerationError(f"generated product path collides with a file: {product}")
    if not manifest_path.exists():
        for path in desired:
            if path.exists(): raise GenerationError(f"refusing to overwrite unrecognized content at {path}")
        return list(desired), obsolete
    old = _load_manifest(manifest_path)
    if old.request_id != manifest.request_id or old.request_source_package != manifest.request_source_package:
        raise GenerationError(f"generation manifest identity does not match request at {manifest_path}")
    for relative in old.owned_files: _verify_owned(product, relative, old)
    desired_relatives = set(manifest.owned_files)
    obsolete.extend(_verify_owned(product, relative, old) for relative in old.owned_files if relative not in desired_relatives)
    old_owned = set(old.owned_files)
    for path, content in desired.items():
        relative = path.relative_to(product).as_posix()
        if path.exists() and relative not in old_owned and path != manifest_path:
            raise GenerationError(f"refusing to overwrite unrecognized content at {path}")
        if not path.exists() or path.read_text(encoding="utf-8") != content: stale.append(path)
    return stale, obsolete


def _prune(product: Path, manifest: GenerationManifest, files: Iterable[Path] | None = None, *, remove_manifest: bool = False) -> list[Path]:
    removed: list[Path] = []
    candidates = tuple(files) if files is not None else tuple(_verify_owned(product, relative, manifest) for relative in manifest.owned_files)
    removed.extend(_prune_bytecode(candidates))
    for path in candidates:
        if path.exists(): path.unlink(); removed.append(path)
    for relative in sorted((_safe_owned(value) for value in manifest.owned_directories), key=lambda p: (-len(p.parts), p.as_posix())):
        directory = product.joinpath(*relative.parts)
        if directory.is_dir() and not any(directory.iterdir()): directory.rmdir()
    if remove_manifest:
        path = product / MANIFEST
        if path.exists(): path.unlink(); removed.append(path)
        if product.is_dir() and not any(product.iterdir()): product.rmdir()
    return removed


async def generate(project_root: str | Path, *, check: bool = False) -> GenerationResult:
    """Generate or validate all requests as one desired-state pass."""
    root = Path(project_root).resolve()
    requests = discover(root)
    products: list[tuple[DiscoveredGeneration, Path, dict[Path, str], GenerationManifest, tuple[Path, ...]]] = []
    desired_product_paths: set[Path] = set()
    for request in requests:
        product, desired, manifest, dependencies = await _desired(root, request)
        resolved = product.resolve()
        if resolved in desired_product_paths: raise GenerationError(f"generated product collision at {product}")
        desired_product_paths.add(resolved)
        products.append((request, product, desired, manifest, dependencies))

    orphan_manifests = tuple(path for path in _existing_manifests(root) if path.parent.resolve() not in desired_product_paths)
    stale: list[Path] = []
    obsolete_by_product: list[tuple[Path, GenerationManifest, list[Path]]] = []
    try:
        for _request, product, desired, manifest, _dependencies in products:
            changed, obsolete = _compare_product(product, desired, manifest)
            stale.extend(changed); stale.extend(obsolete)
            old_manifest = _load_manifest(product / MANIFEST) if (product / MANIFEST).exists() else None
            if old_manifest is not None: obsolete_by_product.append((product, old_manifest, obsolete))
        for path in orphan_manifests:
            manifest = _load_manifest(path)
            for relative in manifest.owned_files: _verify_owned(path.parent, relative, manifest)
            stale.extend(path.parent.joinpath(*_safe_owned(relative).parts) for relative in manifest.owned_files)
            stale.append(path)
    except GenerationError as error:
        if check: return GenerationResult(GenerationStatus.STALE, diagnostics=(str(error),))
        raise
    changed_relative = tuple(sorted({path.relative_to(root) for path in stale}, key=lambda path: path.as_posix()))
    if check:
        if not changed_relative: return GenerationResult(GenerationStatus.CURRENT)
        return GenerationResult(GenerationStatus.STALE, diagnostics=tuple(f"{path.as_posix()} is missing, stale, altered, or orphaned" for path in changed_relative))
    if not changed_relative: return GenerationResult(GenerationStatus.CURRENT)

    deleted_absolute = {
        path for _product, _old, obsolete in obsolete_by_product for path in obsolete if path.exists()
    }
    for manifest_path in orphan_manifests:
        manifest = _load_manifest(manifest_path)
        deleted_absolute.update(
            manifest_path.parent.joinpath(*_safe_owned(relative).parts)
            for relative in manifest.owned_files
            if manifest_path.parent.joinpath(*_safe_owned(relative).parts).exists()
        )
        deleted_absolute.add(manifest_path)
    desired_absolute = {path for _request, _product, desired, _manifest, _dependencies in products for path in desired}
    created_absolute = {path for path in desired_absolute if path in stale and not path.exists()}
    updated_absolute = {path for path in desired_absolute if path in stale and path.exists()}

    # All providers, paths, ownership, and collisions have been validated before mutation.
    for product, old, obsolete in obsolete_by_product: _prune(product, old, obsolete)
    for path in orphan_manifests: _prune(path.parent, _load_manifest(path), remove_manifest=True)
    for _request, _product, desired, _manifest, _dependencies in products:
        _prune_bytecode(path for path, content in desired.items() if path.suffix == ".py" and path.exists() and path.read_text(encoding="utf-8") != content)
        for path, content in sorted(desired.items(), key=lambda item: (item[0].name == MANIFEST, item[0].as_posix())):
            if not path.exists() or path.read_text(encoding="utf-8") != content: _atomic_write(path, content)
    if (await generate(root, check=True)).status is not GenerationStatus.CURRENT:
        raise GenerationError("generation did not produce an idempotent desired state")
    relative = lambda values: tuple(sorted((path.relative_to(root) for path in values), key=lambda path: path.as_posix()))
    return GenerationResult(
        GenerationStatus.CHANGED,
        changed_paths=changed_relative,
        created_paths=relative(created_absolute),
        updated_paths=relative(updated_absolute),
        deleted_paths=relative(deleted_absolute),
    )


class GenerationSession:
    """Complete baseline and dependency index for incremental watch mode."""
    def __init__(self, project_root: str | Path) -> None:
        self.root = Path(project_root).resolve()
        self._by_source: dict[Path, tuple[DiscoveredGeneration, ...]] = {}
        self._by_dependency: dict[Path, set[Path]] = defaultdict(set)
        self._dependency_fingerprints: dict[Path, str | None] = {}
        self._products: tuple[Path, ...] = ()

    async def _index(self) -> None:
        requests = discover(self.root)
        by_source: dict[Path, list[DiscoveredGeneration]] = defaultdict(list)
        dependencies: dict[Path, set[Path]] = defaultdict(set)
        products: list[Path] = []
        for request in requests:
            by_source[request.location.source_path].append(request)
            products.append((self.root / request.product_path).resolve())
            provider, config = load_provider(request.request)
            context = ProviderContext(self.root, request.location.source_path, request.location.request_id, config)
            for dependency in await provider.dependencies(context): dependencies[dependency.resolve()].add(request.location.source_path)
        self._by_source = {path: tuple(values) for path, values in by_source.items()}
        self._by_dependency = dependencies
        self._dependency_fingerprints = {
            path: sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            for path in dependencies
        }
        self._products = tuple(sorted(set(self._products).union(products), key=lambda path: path.as_posix()))

    async def start(self) -> GenerationResult:
        result = await generate(self.root); await self._index(); return result

    async def handle(
        self,
        changed_paths: Iterable[str | Path],
        *,
        on_action: Callable[[GenerationAction], None] | None = None,
    ) -> GenerationResult:
        actions: list[GenerationAction] = []
        for changed in changed_paths:
            path = Path(changed); absolute = path.resolve() if path.is_absolute() else (self.root / path).resolve()
            if any(absolute == product or product in absolute.parents for product in self._products): continue
            if absolute.name == "__init__.py":
                previous = self._by_source.get(absolute, ())
                current = discover_file(self.root, absolute) if absolute.is_file() else ()
                if current == previous:
                    continue
                previous_by_id = {item.location.request_id: item for item in previous}
                current_by_id = {item.location.request_id: item for item in current}
                source = absolute.relative_to(self.root)
                for request_id in sorted(previous_by_id.keys() | current_by_id.keys()):
                    old, new = previous_by_id.get(request_id), current_by_id.get(request_id)
                    if old is None and new is not None:
                        actions.append(GenerationAction(GenerationActionKind.DECLARATION_ADDED, source, (source,), new.package_import))
                    elif new is None and old is not None:
                        actions.append(GenerationAction(GenerationActionKind.DECLARATION_DELETED, source, (source,), old.package_import))
                    elif old != new and new is not None:
                        actions.append(GenerationAction(GenerationActionKind.DECLARATION_CHANGED, source, (source,), new.package_import))
            elif absolute in self._by_dependency:
                fingerprint = sha256(absolute.read_bytes()).hexdigest() if absolute.is_file() else None
                if fingerprint != self._dependency_fingerprints.get(absolute):
                    for source_path in sorted(self._by_dependency[absolute]):
                        for request in self._by_source.get(source_path, ()):
                            actions.append(GenerationAction(
                                GenerationActionKind.DEPENDENCY,
                                absolute.relative_to(self.root),
                                (source_path.relative_to(self.root),),
                                request.package_import,
                            ))
        if not actions: return GenerationResult(GenerationStatus.CURRENT)
        if on_action is not None:
            for action in actions:
                on_action(action)
        result = await generate(self.root); await self._index()
        return replace(result, actions=tuple(actions))
