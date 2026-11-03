"""Deterministic rendering and validation of normalized generated packages."""
from __future__ import annotations

from pathlib import Path, PurePosixPath

import libcst as cst

from ....model._private.generated import (
    GeneratedClass, GeneratedFile, GeneratedPackage, GeneratedStructType,
    GeneratedType, NullabilityNote,
)
from ....model.internal.models import DiscoveredGeneration
from ....model.public.errors import GenerationError
from .constants import FILE_DIRECTIVES, HEADER, REPRESENTATIVE_IMPORT
from .declarations import declaration_imports, render_declaration
from .types import struct_references


def _safe_path(value: Path) -> PurePosixPath:
    path = PurePosixPath(value.as_posix())
    if path.is_absolute() or not path.parts or ".." in path.parts or path.suffix != ".py":
        raise GenerationError(f"invalid generated Python path {value}")
    return path


def _module_name(package_import: str, path: PurePosixPath) -> str:
    parts = path.with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join((package_import, *parts))


def _note_belongs_to_file(note: NullabilityNote, classes: tuple[GeneratedClass, ...]) -> bool:
    """Whether one provenance line describes what this file declares.

    A catalogue rendered one file per table should carry only the line about that
    table's own source; a line naming no declaration is shared by the package.
    """
    if not note.declarations:
        return True
    declared = {declaration.name for declaration in classes}
    return bool(declared & set(note.declarations))


def _declaration_references(declaration: GeneratedClass) -> tuple[GeneratedStructType, ...]:
    references = [
        reference
        for field in declaration.fields
        for reference in struct_references(field.value_type)
    ]
    return tuple((
        *references,
        *(GeneratedStructType(member.declaration_name) for member in declaration.members),
    ))


def render_package(
    request: DiscoveredGeneration, package: GeneratedPackage, fingerprint: str,
) -> dict[PurePosixPath, str]:
    """Validate and render a complete desired package as relative paths to text."""
    paths: dict[str, PurePosixPath] = {}
    declared_here_by_file: dict[PurePosixPath, frozenset[str]] = {}
    declared_in: dict[str, list[PurePosixPath]] = {}
    normalized_files: list[tuple[PurePosixPath, GeneratedFile | None]] = []
    for file in package.files:
        path = _safe_path(file.relative_path)
        folded = path.as_posix().casefold()
        if folded in paths:
            raise GenerationError(f"case-normalized generated path collision: {path}")
        paths[folded] = path
        normalized_files.append((path, file))
        declared_here: set[str] = set()
        for declaration in file.declarations:
            if declaration.name in declared_here:
                raise GenerationError(f"duplicate generated declaration identity {declaration.name} in {path}")
            declared_here.add(declaration.name)
            declared_in.setdefault(declaration.name, []).append(path)
        declared_here_by_file[path] = frozenset(declared_here)

    def path_text(value: PurePosixPath) -> str:
        return f"'{value.as_posix()}'"

    def resolve(name: str, in_path: PurePosixPath, bound_in: PurePosixPath | None = None) -> PurePosixPath | None:
        """The file one generated reference resolves to, or None when it is local.

        A reference bound to a declaring file is exact: its target is that
        file's declaration of the name, and several files sharing a name is
        ordinary. An unbound reference resolves the way Python resolves names
        for a handwritten author: the declaring file wins, and any other
        reference needs the name to be unique across the package to be
        imported. A name no file declares dangles, and an unbound name two
        files declare is ambiguous for an import; both are refused rather
        than guessed, so an import is never bound to the wrong declaration.
        """
        if bound_in is not None:
            if name not in declared_here_by_file.get(bound_in, frozenset()):
                raise GenerationError(
                    f"generated reference {name!r} is bound to {path_text(bound_in)}, which declares no such declaration"
                )
            return None if bound_in == in_path else bound_in
        if name in declared_here_by_file.get(in_path, frozenset()):
            return None
        candidates = declared_in.get(name, [])
        if not candidates:
            raise GenerationError(
                f"generated reference {name!r} in {path_text(in_path)} names no declaration in the package"
            )
        if len(candidates) > 1:
            located = ", ".join(sorted(path_text(candidate) for candidate in candidates))
            raise GenerationError(
                f"generated reference {name!r} in {path_text(in_path)} is ambiguous across {located}; "
                "an unbound name shared by several files resolves only inside its own file"
            )
        return candidates[0]

    # Every directory in a Python package is explicit and owned.
    required_initializers = {PurePosixPath("__init__.py")}
    for path, _file in normalized_files:
        parent = path.parent
        while parent != PurePosixPath("."):
            required_initializers.add(parent / "__init__.py")
            parent = parent.parent
    existing = {path for path, _ in normalized_files}
    normalized_files.extend((path, None) for path in sorted(required_initializers - existing, key=str))

    rendered: dict[PurePosixPath, str] = {}
    for path, file in sorted(normalized_files, key=lambda item: item[0].as_posix()):
        classes: tuple[GeneratedClass, ...] = () if file is None else file.declarations
        exports = () if file is None else file.exports
        imports = declaration_imports(classes)
        fields = tuple(field for declaration in classes for field in declaration.fields)
        if fields:
            imports.update(("Field", "field"))
        cross: dict[str, set[str]] = {}
        for declaration in classes:
            for reference in _declaration_references(declaration):
                target = resolve(reference.declaration_name, path, reference.in_file)
                if target is not None:
                    cross.setdefault(_module_name(request.package_import, target), set()).add(reference.declaration_name)
        for name in exports:
            target = resolve(name, path)
            if target is not None:
                cross.setdefault(_module_name(request.package_import, target), set()).add(name)
        # Same-named declarations are legal across files; a file that would
        # import two of them needs an alias the model does not yet carry, so
        # the collision is refused rather than rendered as silent shadowing.
        imported_from: dict[str, str] = {}
        for module, names in cross.items():
            for name in names:
                if imported_from.setdefault(name, module) != module:
                    raise GenerationError(
                        f"generated file {path_text(path)} would import {name!r} from both "
                        f"{imported_from[name]} and {module}; a file cannot bind two same-named declarations"
                    )
        annotation_imports: dict[str, set[str]] = {}
        for declaration in classes:
            for field in declaration.fields:
                for annotation in field.annotations:
                    annotation_imports.setdefault(annotation.import_module, set()).add(annotation.class_name)
        lines = [
            HEADER,
            f"# request: {request.location.request_id}",
            f"# fingerprint: {fingerprint}",
        ]
        lines.extend(
            f"# {note.line}"
            for note in package.nullability_notes
            if _note_belongs_to_file(note, classes)
        )
        lines.extend([*FILE_DIRECTIVES, ""])
        if classes:
            lines.append(f"from kg_build_system import {', '.join(sorted(imports))}")
            lines.append(REPRESENTATIVE_IMPORT)
        all_external = {module: set(names) for module, names in annotation_imports.items()}
        for module, names in cross.items():
            all_external.setdefault(module, set()).update(names)
        lines.extend(f"from {module} import {', '.join(sorted(names))}" for module, names in sorted(all_external.items()))
        if classes or cross:
            lines.extend(("", ""))
        for index, declaration in enumerate(classes):
            lines.extend(render_declaration(declaration))
            if index != len(classes) - 1:
                lines.extend(("", ""))
        if exports:
            lines.extend(("", f"__all__ = {list(exports)!r}"))
        content = "\n".join(lines).rstrip() + "\n"
        cst.parse_module(content)
        rendered[path] = content
    return rendered


__all__ = ["render_package"]
