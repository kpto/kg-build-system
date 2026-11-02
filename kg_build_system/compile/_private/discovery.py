"""Private namespace discovery for blueprint lowering."""
from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType


class _Namespace:
    """Explicit declarations presented as a namespace."""

    def __init__(self, values: Sequence[object]) -> None:
        self._values = tuple(values)

    def values(self) -> Sequence[object]:
        """Return the explicit declarations."""
        return self._values


class _ModuleNamespace:
    """Every public module-level value under a package path."""

    def __init__(self, modules: Sequence[ModuleType]) -> None:
        self._modules = tuple(modules)

    def values(self) -> Sequence[object]:
        """Return every public value of the discovered modules."""
        result: list[object] = []
        for module in self._modules:
            result.extend(
                value for name, value in vars(module).items()
                if not name.startswith("_")
            )
        return tuple(result)


def namespace_modules(path: str | Path) -> tuple[ModuleType, ...]:
    """Import every module under ``path`` in a stable order."""
    root = Path(path).resolve()
    parent = root.parent
    package = root.name
    names: set[str] = {package}
    for directory, children, files in os.walk(root):
        current = Path(directory)
        children[:] = [
            child for child in children
            if child.isidentifier()
            and child not in {"build", "node_modules", "__pycache__"}
        ]
        relative = current.relative_to(root)
        parts = (package, *relative.parts) if relative.parts else (package,)
        if current != root:
            names.add(".".join(parts))
        for file in files:
            if not file.endswith(".py") or file == "__init__.py":
                continue
            stem = file[:-3]
            if stem.isidentifier():
                names.add(".".join((*parts, stem)))
    sys.path.insert(0, str(parent))
    try:
        return tuple(importlib.import_module(name) for name in sorted(names))
    finally:
        sys.path.remove(str(parent))


__all__ = ["namespace_modules"]
