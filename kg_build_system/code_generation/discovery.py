"""Static discovery of ``@generated`` declarations without project imports."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider

from .models import (
    DiscoveredGeneration,
    GenerationError,
    GenerationLocation,
    GenerationRequest,
    StaticValue,
)


_CANONICAL_MODULES = {
    "kg_build_system",
    "kg_build_system.code_generation",
    "kg_build_system.code_generation.decorator",
}
_CANONICAL_DECORATORS = {f"{module}.generated" for module in _CANONICAL_MODULES}


def _dotted(node: cst.BaseExpression) -> str | None:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        parent = _dotted(node.value)
        return f"{parent}.{node.attr.value}" if parent else None
    return None


def _static(node: cst.BaseExpression) -> StaticValue:
    if isinstance(node, cst.SimpleString):
        value = node.evaluated_value
        if not isinstance(value, str):
            raise GenerationError("generated arguments do not support bytes literals")
        return value
    if isinstance(node, cst.Integer):
        return int(node.value.replace("_", ""), 0)
    if isinstance(node, cst.Float):
        return float(node.value.replace("_", ""))
    if isinstance(node, cst.Name) and node.value in {"True", "False", "None"}:
        return {"True": True, "False": False, "None": None}[node.value]
    if isinstance(node, (cst.List, cst.Tuple)):
        values = [_static(element.value) for element in node.elements if element is not None]
        return tuple(values) if isinstance(node, cst.Tuple) else values
    if isinstance(node, cst.Dict):
        result: dict[str, StaticValue] = {}
        for element in node.elements:
            if element is None or not isinstance(element, cst.DictElement):
                raise GenerationError("generated configuration does not support dictionary unpacking")
            key = _static(element.key)
            if not isinstance(key, str):
                raise GenerationError("generated configuration dictionary keys must be strings")
            result[key] = _static(element.value)
        return result
    raise GenerationError("generated arguments must be static literals")


class _DiscoveryVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, project_root: Path, source_path: Path) -> None:
        self.project_root = project_root
        self.source_path = source_path
        self.direct_imports: dict[str, str] = {}
        self.module_aliases: dict[str, str] = {}
        self.results: list[DiscoveredGeneration] = []
        self.scope_depth = 0

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        module = _dotted(node.module) if node.module is not None else None
        if module is None or isinstance(node.names, cst.ImportStar):
            return
        for alias in node.names:
            if not isinstance(alias, cst.ImportAlias):
                continue
            name = _dotted(alias.name)
            if name:
                imported_name = _dotted(alias.asname.name) if alias.asname else name
                if imported_name:
                    self.direct_imports[imported_name] = f"{module}.{name}"

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            if not isinstance(alias, cst.ImportAlias):
                continue
            module = _dotted(alias.name)
            if module:
                imported_name = _dotted(alias.asname.name) if alias.asname else module.split(".")[0]
                if imported_name:
                    self.module_aliases[imported_name] = module if alias.asname else module.split(".")[0]

    def visit_FunctionDef(self, _node: cst.FunctionDef) -> None:
        self.scope_depth += 1

    def leave_FunctionDef(self, _node: cst.FunctionDef) -> None:
        self.scope_depth -= 1

    def _resolve(self, expression: cst.BaseExpression) -> str | None:
        dotted = _dotted(expression)
        if not dotted:
            return None
        parts = dotted.split(".")
        if parts[0] in self.direct_imports:
            return ".".join((self.direct_imports[parts[0]], *parts[1:]))
        if parts[0] in self.module_aliases:
            return ".".join((self.module_aliases[parts[0]], *parts[1:]))
        return None

    def _matches(self, expression: cst.BaseExpression) -> bool:
        target = expression.func if isinstance(expression, cst.Call) else expression
        return self._resolve(target) in _CANONICAL_DECORATORS

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        matches = [index for index, decorator in enumerate(node.decorators) if self._matches(decorator.decorator)]
        if not matches:
            self.scope_depth += 1
            return True
        position = cast(Any, self.get_metadata(PositionProvider, node))
        prefix = f"{self.source_path.as_posix()}:{position.start.line}: {node.name.value}"
        if self.scope_depth:
            raise GenerationError(f"{prefix} generated declarations must be module-level")
        if len(matches) > 1:
            raise GenerationError(f"{prefix} has multiple @generated decorators")
        if matches[0] != 0:
            raise GenerationError(f"{prefix} @generated must be the topmost decorator")
        decorator = node.decorators[0].decorator
        if not isinstance(decorator, cst.Call):
            raise GenerationError(f"{prefix} @generated requires a provider type and config instance")
        if len(decorator.args) != 2 or any(argument.keyword is not None or argument.star for argument in decorator.args):
            raise GenerationError(f"{prefix} @generated requires a provider type and config instance")
        provider_name = self._resolve(decorator.args[0].value)
        config_call = decorator.args[1].value
        if provider_name is None:
            raise GenerationError(f"{prefix} provider type must be imported from a provider module")
        if not isinstance(config_call, cst.Call):
            raise GenerationError(f"{prefix} config must be constructed inline")
        config_name = self._resolve(config_call.func)
        if config_name is None:
            raise GenerationError(f"{prefix} config type must be imported from a provider module")
        values: dict[str, StaticValue] = {}
        for argument in config_call.args:
            if argument.keyword is None or argument.star:
                raise GenerationError(f"{prefix} provider config accepts keyword arguments only")
            if argument.keyword.value in values:
                raise GenerationError(f"{prefix} duplicate provider config argument {argument.keyword.value!r}")
            values[argument.keyword.value] = _static(argument.value)
        provider_module, provider_qualname = provider_name.rsplit(".", 1)
        config_module, config_qualname = config_name.rsplit(".", 1)
        generated_name = f"G_{node.name.value}"
        relative = self.source_path.relative_to(self.project_root)
        sidecar = relative.parent / "_generated" / relative.name
        self.results.append(
            DiscoveredGeneration(
                GenerationRequest(
                    provider_module,
                    provider_qualname,
                    config_module,
                    config_qualname,
                    values,
                ),
                GenerationLocation(
                    self.project_root,
                    self.source_path,
                    position.start.line,
                    position.start.column,
                    node.name.value,
                ),
                sidecar,
                generated_name,
            )
        )
        self.scope_depth += 1
        return True

    def leave_ClassDef(self, _node: cst.ClassDef) -> None:
        self.scope_depth -= 1


def discover_file(project_root: str | Path, source_path: str | Path) -> tuple[DiscoveredGeneration, ...]:
    root = Path(project_root).resolve()
    path = Path(source_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"source file is outside the project: {path}") from error
    try:
        module = cst.parse_module(path.read_text(encoding="utf-8"))
    except (OSError, cst.ParserSyntaxError) as error:
        raise GenerationError(f"{path}: cannot parse Python source: {error}") from error
    visitor = _DiscoveryVisitor(root, path)
    MetadataWrapper(module).visit(visitor)
    return tuple(visitor.results)


def discover(project_root: str | Path) -> tuple[DiscoveredGeneration, ...]:
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise ValueError(f"generation project is not a directory: {root}")
    source_paths: list[Path] = []
    for directory, directory_names, file_names in root.walk(top_down=True):
        directory_names[:] = sorted(name for name in directory_names if not name.startswith("."))
        source_paths.extend(
            directory / name
            for name in sorted(file_names)
            if name.endswith(".py") and not name.startswith(".")
        )
    candidate_paths = [
        path for path in source_paths if "generated" in path.read_text(encoding="utf-8")
    ]
    results = [request for path in candidate_paths for request in discover_file(root, path)]
    identities: set[tuple[Path, str]] = set()
    for request in results:
        identity = (request.sidecar_path, request.generated_name)
        if identity in identities:
            raise GenerationError(f"generated output collision for {request.generated_name} in {request.sidecar_path}")
        identities.add(identity)
    return tuple(results)
