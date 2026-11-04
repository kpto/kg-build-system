"""Private namespace discovery for blueprint creation."""
from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import ModuleType


class _Values:
    """A namespace over explicit values, without asset expansion."""

    def __init__(self, values: Sequence[object]) -> None:
        self._values = values

    def values(self) -> Sequence[object]:
        return self._values


def _expression_reads(value: object) -> set[tuple[str, str]]:
    """The relation and first field path one authoring expression reads."""
    from kg_build_system.distribution.languages.expressions.model.internal import (
        ExpressionNode,
        FieldReferenceExpression,
        OperationExpression,
    )

    if not isinstance(value, ExpressionNode):
        return set()
    if isinstance(value, FieldReferenceExpression):
        return {(value.source, value.path[0])}
    if isinstance(value, OperationExpression):
        return {
            read
            for argument in value.arguments
            for read in _expression_reads(argument)
        }
    return set()


def _binding_expressions(binding: object) -> tuple[object, ...]:
    names = ("build_key", "source_build_key", "target_build_key")
    expressions = [
        getattr(binding, name, None) for name in names
    ]
    expressions.extend(
        expression for _, expression in getattr(binding, "properties", ()) or ()
    )
    return tuple(
        getattr(expression, "model", expression)
        for expression in expressions
        if expression is not None
    )


def _table_declarations(
    bindings: Sequence[object], *, found: Iterable[str] = (),
) -> tuple[type, ...]:
    """Resolve the tables explicit declarative bindings read by graph name."""
    from kg_build_system.distribution.languages.data.model.public import (
        Table,
        is_concrete_table,
    )

    reads = {
        read
        for binding in bindings
        for expression in _binding_expressions(binding)
        for read in _expression_reads(expression)
    }
    names = {source for source, _ in reads} - set(found)
    if not names:
        return ()
    modules = {
        getattr(getattr(binding, "target", None), "__module__", None)
        for binding in bindings
    }

    def subclasses(value: type) -> Iterable[type]:
        for child in value.__subclasses__():
            yield child
            yield from subclasses(child)

    def matches(table: type) -> bool:
        spec = vars(table).get("_kg_declaration_spec")
        name = getattr(spec, "name", None)
        if name not in names:
            return False
        fields = {field.name for field in getattr(spec, "fields", ())}
        return any(
            source == name and field in fields for source, field in reads
        )

    candidates = tuple(
        table for table in subclasses(Table)
        if is_concrete_table(table) and matches(table)
    )
    scoped = tuple(
        table for table in candidates if table.__module__ in modules
    )
    return scoped or candidates


def _with_assets(values: Sequence[object]) -> tuple[object, ...]:
    """Add the table declarations and assets explicit bindings imply."""
    from kg_build_system.distribution.languages.data.service.internal import (
        collect_values,
    )

    initial = collect_values(_Values(values))
    known = {
        spec.name
        for value in initial
        if (spec := vars(value).get("_kg_declaration_spec")) is not None
        and spec.kind == "table"
    }
    tables = _table_declarations(values, found=known)
    found = collect_values(_Values((*values, *tables)))
    assets: list[object] = []
    for value in (*tables, *found):
        spec = vars(value).get("_kg_declaration_spec")
        asset = getattr(spec, "asset", None)
        if asset is not None:
            assets.append(asset)
    return (*values, *tables, *dict.fromkeys(assets))


class _Namespace:
    """Explicit declarations presented as a namespace."""

    def __init__(self, values: Sequence[object]) -> None:
        self._values = tuple(values)

    def values(self) -> Sequence[object]:
        """Return the explicit declarations and the assets their tables name."""
        return _with_assets(self._values)


class _ModuleNamespace:
    """Every public module-level value under a package path."""

    def __init__(self, modules: Sequence[ModuleType]) -> None:
        self._modules = tuple(modules)

    def values(self) -> Sequence[object]:
        """Return every public value of the discovered modules, once."""
        result: list[object] = []
        seen: set[int] = set()
        for module in self._modules:
            for name, value in vars(module).items():
                if name.startswith("_") or id(value) in seen:
                    continue
                seen.add(id(value))
                result.append(value)
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
