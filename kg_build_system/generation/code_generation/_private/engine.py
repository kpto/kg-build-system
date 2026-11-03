"""Desired-state generation, manifest ownership, safe installation and pruning.

``generate`` is one pass with explicit stages: discover, prepare, classify,
observe, diff, install, verify and result. Each stage is a function below so a
failure names the stage it belongs to.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import tempfile

from .discovery import discover, discover_file
from .manifest import MANIFEST, load_manifest, manifest_text
from ..internal.models import (
    DiscoveredGeneration, GenerationAction, GenerationActionKind, GenerationError,
    GenerationManifest, GenerationResult, GenerationStatus,
)
from ..internal.providers import ProviderContext
from .adapters import load_provider
from .rendering import FORMAT_VERSION, HEADER, generation_fingerprint, render_package


@dataclass(frozen=True, slots=True)
class _PreparedRequest:
    request: DiscoveredGeneration
    product: Path


@dataclass(frozen=True, slots=True)
class _ObservedProduct:
    request: DiscoveredGeneration
    product: Path
    desired: dict[Path, str]
    manifest: GenerationManifest


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


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
        if (
            not path.is_file()
            or not content.startswith(_ownership_header(manifest.request_id, manifest.request_fingerprint))
            or (expected_hash is not None and sha256(content.encode()).hexdigest() != expected_hash)
        ):
            raise GenerationError(f"owned generated file was unexpectedly modified: {path}")
    return path


def _bytecode_files(source: Path) -> tuple[Path, ...]:
    """Return cache files derived unambiguously from one generated Python source."""
    if source.suffix != ".py":
        return ()
    cache = source.parent / "__pycache__"
    if not cache.is_dir():
        return ()
    return tuple(sorted(cache.glob(f"{source.stem}.*.pyc"), key=lambda path: path.name))


def _prune_bytecode(sources: Iterable[Path]) -> list[Path]:
    removed: list[Path] = []
    cache_directories: set[Path] = set()
    for source in sources:
        cache_directories.add(source.parent / "__pycache__")
        for bytecode in _bytecode_files(source):
            bytecode.unlink()
            removed.append(bytecode)
    for cache in sorted(cache_directories, key=lambda path: (-len(path.parts), path.as_posix())):
        if cache.is_dir() and not any(cache.iterdir()):
            cache.rmdir()
    return removed


def _owned_directories(files: Iterable[PurePosixPath]) -> tuple[str, ...]:
    values: set[PurePosixPath] = set()
    for file in files:
        parent = file.parent
        while parent != PurePosixPath("."):
            values.add(parent)
            parent = parent.parent
    return tuple(path.as_posix() for path in sorted(values, key=lambda p: (len(p.parts), p.as_posix())))


def _discover(root: Path) -> tuple[DiscoveredGeneration, ...]:
    return discover(root)


def _prepare(root: Path, requests: tuple[DiscoveredGeneration, ...]) -> tuple[tuple[_PreparedRequest, ...], set[Path]]:
    """Resolve product paths and refuse collisions before any observation."""
    prepared: list[_PreparedRequest] = []
    desired_product_paths: set[Path] = set()
    for request in requests:
        declared_product = root / request.product_path
        resolved = declared_product.resolve()
        if resolved in desired_product_paths:
            raise GenerationError(f"generated product collision at {declared_product}")
        desired_product_paths.add(resolved)
        prepared.append(_PreparedRequest(request, resolved))
    return tuple(prepared), desired_product_paths


def _product_is_current(product: Path, manifest: GenerationManifest, fingerprint: str) -> bool:
    """Whether a committed product still matches its manifest exactly.

    The manifest records the request fingerprint and the hash of every owned
    file, so a current product needs no provider observation at all: the
    request has not changed, and the tracked reference is what the manifest
    vouches for.
    """
    if manifest.format_version != FORMAT_VERSION:
        return False
    if manifest.request_fingerprint != fingerprint:
        return False
    if set(manifest.owned_file_hashes) != set(manifest.owned_files):
        return False
    for relative, expected in manifest.owned_file_hashes.items():
        path = product.joinpath(*_safe_owned(relative).parts)
        if not path.is_file():
            return False
        if sha256(path.read_text(encoding="utf-8").encode()).hexdigest() != expected:
            return False
    return True


def _classify(prepared: tuple[_PreparedRequest, ...], *, regenerate: bool) -> tuple[_PreparedRequest, ...]:
    """Split prepared requests into current products and products to observe."""
    pending: list[_PreparedRequest] = []
    for item in prepared:
        manifest_path = item.product / MANIFEST
        if not regenerate and manifest_path.is_file():
            existing = load_manifest(manifest_path)
            provider, _config = load_provider(item.request.request)
            if _product_is_current(
                item.product, existing,
                generation_fingerprint(item.request, provider.VERSION),
            ):
                continue
        pending.append(item)
    return tuple(pending)


async def _desired(root: Path, request: DiscoveredGeneration) -> _ObservedProduct:
    """Observe one request's sources once and render its complete desired product.

    The provider reads what it needs at this point only; the engine tracks the
    request, never the observed data, so no dependency exists to hash or watch.
    """
    provider, config = load_provider(request.request)
    context = ProviderContext(root, request.location.source_path, request.location.request_id, config)
    fingerprint = generation_fingerprint(request, provider.VERSION)
    package = await provider.generate(context)
    first = render_package(request, package, fingerprint)
    second = render_package(request, package, fingerprint)
    if first != second:
        raise GenerationError(
            f"provider {provider.__module__}.{provider.__qualname__} did not render deterministically"
        )
    rendered = first
    product = (root / request.product_path).resolve()
    desired = {product.joinpath(*relative.parts): content for relative, content in rendered.items()}
    relative_files = tuple(sorted(rendered, key=lambda value: value.as_posix()))
    manifest = GenerationManifest(
        FORMAT_VERSION, request.location.request_id, request.location.source_package,
        provider.__module__, provider.__qualname__, provider.VERSION, fingerprint,
        package.source_digest,
        tuple(path.as_posix() for path in relative_files), _owned_directories(relative_files),
        {path.as_posix(): sha256(rendered[path].encode()).hexdigest() for path in relative_files},
    )
    desired[product / MANIFEST] = manifest_text(manifest)
    return _ObservedProduct(request, product, desired, manifest)


async def _observe(root: Path, pending: tuple[_PreparedRequest, ...]) -> tuple[_ObservedProduct, ...]:
    return tuple([await _desired(root, item.request) for item in pending])


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


def _compare_product(
    product: Path, desired: dict[Path, str], manifest: GenerationManifest,
) -> tuple[list[Path], list[Path]]:
    manifest_path = product / MANIFEST
    stale: list[Path] = []
    obsolete: list[Path] = []
    if product.exists() and not product.is_dir():
        raise GenerationError(f"generated product path collides with a file: {product}")
    if not manifest_path.exists():
        for path in desired:
            if path.exists():
                raise GenerationError(f"refusing to overwrite unrecognized content at {path}")
        return list(desired), obsolete
    old = load_manifest(manifest_path)
    if old.request_id != manifest.request_id or old.request_source_package != manifest.request_source_package:
        raise GenerationError(f"generation manifest identity does not match request at {manifest_path}")
    for relative in old.owned_files:
        _verify_owned(product, relative, old)
    desired_relatives = set(manifest.owned_files)
    obsolete.extend(
        _verify_owned(product, relative, old)
        for relative in old.owned_files
        if relative not in desired_relatives
    )
    old_owned = set(old.owned_files)
    for path, content in desired.items():
        relative = path.relative_to(product).as_posix()
        if path.exists() and relative not in old_owned and path != manifest_path:
            raise GenerationError(f"refusing to overwrite unrecognized content at {path}")
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            stale.append(path)
    return stale, obsolete


def _diff(
    products: tuple[_ObservedProduct, ...],
    desired_product_paths: set[Path],
    root: Path,
) -> tuple[list[Path], list[tuple[Path, GenerationManifest, list[Path]]], tuple[Path, ...]]:
    """Compare every desired product with what is installed, without mutating."""
    orphan_manifests = tuple(
        path for path in _existing_manifests(root)
        if path.parent.resolve() not in desired_product_paths
    )
    stale: list[Path] = []
    obsolete_by_product: list[tuple[Path, GenerationManifest, list[Path]]] = []
    for product in products:
        changed, obsolete = _compare_product(product.product, product.desired, product.manifest)
        stale.extend(changed)
        stale.extend(obsolete)
        old_manifest = load_manifest(product.product / MANIFEST) if (product.product / MANIFEST).exists() else None
        if old_manifest is not None:
            obsolete_by_product.append((product.product, old_manifest, obsolete))
    for path in orphan_manifests:
        manifest = load_manifest(path)
        for relative in manifest.owned_files:
            _verify_owned(path.parent, relative, manifest)
        stale.extend(path.parent.joinpath(*_safe_owned(relative).parts) for relative in manifest.owned_files)
        stale.append(path)
    return stale, obsolete_by_product, orphan_manifests


def _prune(
    product: Path, manifest: GenerationManifest, files: Iterable[Path] | None = None,
    *, remove_manifest: bool = False,
) -> list[Path]:
    removed: list[Path] = []
    candidates = (
        tuple(files) if files is not None
        else tuple(_verify_owned(product, relative, manifest) for relative in manifest.owned_files)
    )
    removed.extend(_prune_bytecode(candidates))
    for path in candidates:
        if path.exists():
            path.unlink()
            removed.append(path)
    for relative in sorted(
        (_safe_owned(value) for value in manifest.owned_directories),
        key=lambda p: (-len(p.parts), p.as_posix()),
    ):
        directory = product.joinpath(*relative.parts)
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    if remove_manifest:
        path = product / MANIFEST
        if path.exists():
            path.unlink()
            removed.append(path)
        if product.is_dir() and not any(product.iterdir()):
            product.rmdir()
    return removed


def _install(
    products: tuple[_ObservedProduct, ...],
    obsolete_by_product: list[tuple[Path, GenerationManifest, list[Path]]],
    orphan_manifests: tuple[Path, ...],
) -> None:
    """Mutate the filesystem after every validation has succeeded."""
    for product, old, obsolete in obsolete_by_product:
        _prune(product, old, obsolete)
    for path in orphan_manifests:
        _prune(path.parent, load_manifest(path), remove_manifest=True)
    for product in products:
        _prune_bytecode(
            path for path, content in product.desired.items()
            if path.suffix == ".py" and path.exists() and path.read_text(encoding="utf-8") != content
        )
        for path, content in sorted(
            product.desired.items(),
            key=lambda item: (item[0].name == MANIFEST, item[0].as_posix()),
        ):
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                _atomic_write(path, content)


async def _verify(root: Path) -> None:
    if (await generate(root, check=True)).status is not GenerationStatus.CURRENT:
        raise GenerationError("generation did not produce an idempotent desired state")


def _result(
    root: Path,
    stale: Iterable[Path],
    products: tuple[_ObservedProduct, ...],
    obsolete_by_product: list[tuple[Path, GenerationManifest, list[Path]]],
    orphan_manifests: tuple[Path, ...],
) -> GenerationResult:
    changed_relative = tuple(sorted(
        {path.relative_to(root) for path in stale}, key=lambda path: path.as_posix(),
    ))
    if not changed_relative:
        return GenerationResult(GenerationStatus.CURRENT)
    deleted_absolute = {
        path for _product, _old, obsolete in obsolete_by_product
        for path in obsolete if path.exists()
    }
    for manifest_path in orphan_manifests:
        manifest = load_manifest(manifest_path)
        deleted_absolute.update(
            manifest_path.parent.joinpath(*_safe_owned(relative).parts)
            for relative in manifest.owned_files
            if manifest_path.parent.joinpath(*_safe_owned(relative).parts).exists()
        )
        deleted_absolute.add(manifest_path)
    desired_absolute = {path for product in products for path in product.desired}
    created_absolute = {path for path in desired_absolute if path in stale and not path.exists()}
    updated_absolute = {path for path in desired_absolute if path in stale and path.exists()}
    relative = lambda values: tuple(
        sorted((path.relative_to(root) for path in values), key=lambda path: path.as_posix())
    )
    return GenerationResult(
        GenerationStatus.CHANGED,
        changed_paths=changed_relative,
        created_paths=relative(created_absolute),
        updated_paths=relative(updated_absolute),
        deleted_paths=relative(deleted_absolute),
    )


async def generate(
    project_root: str | Path, *, check: bool = False, regenerate: bool = False,
) -> GenerationResult:
    """Generate or validate all requests as one desired-state pass.

    A product whose manifest still matches its request fingerprint and file
    hashes is taken as current without observing its sources: data is a
    reference, not a tracked input, so nothing outside the declarations can
    make a product stale. ``regenerate`` forces every provider to re-observe,
    which is how a source schema change is deliberately pulled into the
    project; combined with ``check`` it reports that drift without writing.
    """
    root = Path(project_root).resolve()
    requests = _discover(root)
    prepared, desired_product_paths = _prepare(root, requests)
    pending = _classify(prepared, regenerate=regenerate)
    products = await _observe(root, pending)
    try:
        stale, obsolete_by_product, orphan_manifests = _diff(
            products, desired_product_paths, root,
        )
    except GenerationError as error:
        if check:
            return GenerationResult(GenerationStatus.STALE, diagnostics=(str(error),))
        raise
    if check:
        changed = tuple(sorted(
            {path.relative_to(root) for path in stale}, key=lambda path: path.as_posix(),
        ))
        if not changed:
            return GenerationResult(GenerationStatus.CURRENT)
        return GenerationResult(
            GenerationStatus.STALE,
            diagnostics=tuple(
                f"{path.as_posix()} is missing, stale, altered, or orphaned" for path in changed
            ),
        )
    result = _result(root, stale, products, obsolete_by_product, orphan_manifests)
    if result.status is GenerationStatus.CURRENT:
        return result
    _install(products, obsolete_by_product, orphan_manifests)
    await _verify(root)
    return result


class GenerationSession:
    """Complete baseline and declaration index for incremental watch mode.

    A session runs an initial desired-state pass, then compares each watched
    declaration edit with the indexed request set. Only a changed request causes
    a generation pass; product files are ignored.

    Example:
        ```python
        from kg_build_system.generation.code_generation import GenerationSession

        session = GenerationSession(".")
        ```
    """

    def __init__(self, project_root: str | Path) -> None:
        """Index the project root, without generating or observing anything yet.

        Call :meth:`start` for the baseline pass and :meth:`handle` for each
        watched change batch.

        Example:
            ```python
            from kg_build_system.generation.code_generation import GenerationSession

            session = GenerationSession(".")
            ```
        """
        self.root = Path(project_root).resolve()
        self._by_source: dict[Path, tuple[DiscoveredGeneration, ...]] = {}
        self._products: tuple[Path, ...] = ()

    async def _index(self) -> None:
        requests = discover(self.root)
        by_source: dict[Path, list[DiscoveredGeneration]] = defaultdict(list)
        products: list[Path] = []
        for request in requests:
            by_source[request.location.source_path].append(request)
            products.append((self.root / request.product_path).resolve())
        self._by_source = {path: tuple(values) for path, values in by_source.items()}
        self._products = tuple(sorted(set(self._products).union(products), key=lambda path: path.as_posix()))

    async def start(self) -> GenerationResult:
        """Run the baseline generation pass and index the resulting requests.

        The returned result describes what the initial pass wrote; subsequent
        changes are handled by :meth:`handle`.

        Example:
            ```python
            import asyncio

            from kg_build_system.generation.code_generation import GenerationSession

            async def run() -> None:
                session = GenerationSession(".")
                result = await session.start()
                print(result.status)

            asyncio.run(run())
            ```
        """
        result = await generate(self.root)
        await self._index()
        return result

    async def handle(
        self,
        changed_paths: Iterable[str | Path],
        *,
        on_action: Callable[[GenerationAction], None] | None = None,
    ) -> GenerationResult:
        """Regenerate after a batch of watched declaration changes.

        Paths may be absolute or relative to the project root. Only changed
        ``__init__.py`` request declarations schedule a pass; paths beneath an
        owned product are ignored. ``on_action`` receives each added, changed
        or deleted declaration before generation runs.

        Example:
            ```python
            import asyncio
            from pathlib import Path

            from kg_build_system.generation.code_generation import GenerationSession

            async def run() -> None:
                session = GenerationSession(".")
                await session.start()
                result = await session.handle(
                    [Path("contracts/__init__.py")],
                    on_action=lambda action: print(action.kind),
                )
                print(result.actions)

            asyncio.run(run())
            ```
        """
        actions: list[GenerationAction] = []
        for changed in changed_paths:
            path = Path(changed)
            absolute = path.resolve() if path.is_absolute() else (self.root / path).resolve()
            if any(absolute == product or product in absolute.parents for product in self._products):
                continue
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
                        actions.append(GenerationAction(
                            GenerationActionKind.DECLARATION_ADDED, source, (source,), new.package_import,
                        ))
                    elif new is None and old is not None:
                        actions.append(GenerationAction(
                            GenerationActionKind.DECLARATION_DELETED, source, (source,), old.package_import,
                        ))
                    elif old != new and new is not None:
                        actions.append(GenerationAction(
                            GenerationActionKind.DECLARATION_CHANGED, source, (source,), new.package_import,
                        ))
        if not actions:
            return GenerationResult(GenerationStatus.CURRENT)
        if on_action is not None:
            for action in actions:
                on_action(action)
        result = await generate(self.root)
        await self._index()
        return replace(result, actions=tuple(actions))


__all__ = ["GenerationSession", "generate"]
