"""Static discovery of generation assignments without importing authored modules."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
import keyword

import libcst as cst
from libcst.metadata import MetadataWrapper, ParentNodeProvider, PositionProvider

from .models import DiscoveredGeneration, GenerationError, GenerationLocation, GenerationRequest, StaticValue

_CANONICAL = {
    "kg_build_system.generation",
    "kg_build_system.code_generation.generation",
    "kg_build_system.code_generation.requests.generation",
}


def _dotted(node: cst.BaseExpression | None) -> str | None:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        parent = _dotted(node.value)
        return f"{parent}.{node.attr.value}" if parent else None
    return None


def _static(node: cst.BaseExpression) -> StaticValue:
    if isinstance(node, cst.SimpleString):
        value = node.evaluated_value
        if isinstance(value, str):
            return value
    if isinstance(node, cst.Integer): return int(node.value.replace("_", ""), 0)
    if isinstance(node, cst.Float): return float(node.value.replace("_", ""))
    if isinstance(node, cst.Name) and node.value in {"True", "False", "None"}:
        return {"True": True, "False": False, "None": None}[node.value]
    if isinstance(node, (cst.List, cst.Tuple)):
        if any(element is None or isinstance(element, cst.StarredElement) for element in node.elements):
            raise GenerationError("generation configuration does not support unpacking")
        values = [_static(cast(cst.Element, element).value) for element in node.elements]
        return tuple(values) if isinstance(node, cst.Tuple) else values
    if isinstance(node, cst.Dict):
        result: dict[str, StaticValue] = {}
        for element in node.elements:
            if not isinstance(element, cst.DictElement):
                raise GenerationError("generation configuration does not support dictionary unpacking")
            key = _static(element.key)
            if not isinstance(key, str):
                raise GenerationError("generation configuration dictionary keys must be strings")
            result[key] = _static(element.value)
        return result
    raise GenerationError("generation configuration values must be static literals")


class _Visitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider, ParentNodeProvider)

    def __init__(self, root: Path, path: Path) -> None:
        self.root, self.path = root, path
        self.direct: dict[str, str] = {}
        self.modules: dict[str, str] = {}
        self.depth = 0
        self.results: list[DiscoveredGeneration] = []

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        module = _dotted(node.module)
        if module is None or node.relative or isinstance(node.names, cst.ImportStar): return
        for alias in node.names:
            name = _dotted(alias.name)
            local = _dotted(alias.asname.name) if alias.asname else name
            if name and local: self.direct[local] = f"{module}.{name}"

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            module = _dotted(alias.name)
            if not module: continue
            local = _dotted(alias.asname.name) if alias.asname else module.split(".")[0]
            if local: self.modules[local] = module if alias.asname else module.split(".")[0]

    def _resolve(self, expression: cst.BaseExpression) -> str | None:
        dotted = _dotted(expression)
        if not dotted: return None
        parts = dotted.split(".")
        if parts[0] in self.direct: return ".".join((self.direct[parts[0]], *parts[1:]))
        if parts[0] in self.modules: return ".".join((self.modules[parts[0]], *parts[1:]))
        return None

    def visit_FunctionDef(self, _node: cst.FunctionDef) -> None: self.depth += 1
    def leave_FunctionDef(self, _node: cst.FunctionDef) -> None: self.depth -= 1
    def visit_ClassDef(self, _node: cst.ClassDef) -> None: self.depth += 1
    def leave_ClassDef(self, _node: cst.ClassDef) -> None: self.depth -= 1

    def visit_Expr(self, node: cst.Expr) -> None:
        if not isinstance(node.value, cst.Call) or self._resolve(node.value.func) not in _CANONICAL:
            return
        position = cast(Any, self.get_metadata(PositionProvider, node)).start
        raise GenerationError(
            f"{self.path.as_posix()}:{position.line}: generation(...) must be assigned to a name, "
            "for example release = generation(...); the assignment name defines the generated package identity"
        )

    def visit_Assign(self, node: cst.Assign) -> None:
        if not isinstance(node.value, cst.Call) or self._resolve(node.value.func) not in _CANONICAL:
            return
        position = cast(Any, self.get_metadata(PositionProvider, node)).start
        prefix = f"{self.path.as_posix()}:{position.line}"
        if self.path.name != "__init__.py": raise GenerationError(f"{prefix}: generation requests must be in __init__.py")
        parent = self.get_metadata(ParentNodeProvider, node)
        grandparent = self.get_metadata(ParentNodeProvider, cast(cst.CSTNode, parent))
        if self.depth or not isinstance(parent, cst.SimpleStatementLine) or not isinstance(grandparent, cst.Module):
            raise GenerationError(f"{prefix}: generation requests must be module-level")
        if len(node.targets) != 1 or not isinstance(node.targets[0].target, cst.Name):
            raise GenerationError(f"{prefix}: generation requests require one plain assignment target")
        request_id = node.targets[0].target.value
        if request_id.startswith("_") or not request_id.isidentifier() or keyword.iskeyword(request_id):
            raise GenerationError(f"{prefix}: invalid generation request identity {request_id!r}")
        args = node.value.args
        if len(args) != 2 or any(arg.keyword is not None or arg.star for arg in args):
            raise GenerationError(f"{prefix}: generation requires a provider type and inline configuration")
        provider = self._resolve(args[0].value)
        config_call = args[1].value
        if provider is None: raise GenerationError(f"{prefix}: provider type must be statically imported")
        if not isinstance(config_call, cst.Call): raise GenerationError(f"{prefix}: configuration must be constructed inline")
        config = self._resolve(config_call.func)
        if config is None: raise GenerationError(f"{prefix}: configuration type must be statically imported")
        values: dict[str, StaticValue] = {}
        for arg in config_call.args:
            if arg.keyword is None or arg.star: raise GenerationError(f"{prefix}: provider configuration accepts keyword arguments only")
            key = arg.keyword.value
            if key in values: raise GenerationError(f"{prefix}: duplicate configuration argument {key!r}")
            values[key] = _static(arg.value)
        provider_module, provider_qualname = provider.rsplit(".", 1)
        config_module, config_qualname = config.rsplit(".", 1)
        relative_parent = self.path.relative_to(self.root).parent
        package_parts = relative_parent.parts
        source_package = ".".join(package_parts)
        package_import = ".".join((*package_parts, request_id))
        self.results.append(DiscoveredGeneration(
            GenerationRequest(provider_module, provider_qualname, config_module, config_qualname, values),
            GenerationLocation(self.root, self.path, position.line, position.column, request_id, source_package),
            relative_parent / request_id,
            package_import,
        ))

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if isinstance(node.value, cst.Call) and self._resolve(node.value.func) in _CANONICAL:
            position = cast(Any, self.get_metadata(PositionProvider, node)).start
            raise GenerationError(f"{self.path.as_posix()}:{position.line}: generation requests must use a simple assignment")


def discover_file(project_root: str | Path, source_path: str | Path) -> tuple[DiscoveredGeneration, ...]:
    root, path = Path(project_root).resolve(), Path(source_path).resolve()
    try: path.relative_to(root)
    except ValueError as error: raise ValueError(f"source file is outside the project: {path}") from error
    if path.name != "__init__.py":
        text = path.read_text(encoding="utf-8")
        if "generation" not in text: return ()
    try: module = cst.parse_module(path.read_text(encoding="utf-8"))
    except (OSError, cst.ParserSyntaxError) as error: raise GenerationError(f"{path}: cannot parse Python source: {error}") from error
    visitor = _Visitor(root, path)
    MetadataWrapper(module).visit(visitor)
    return tuple(visitor.results)


def discover(project_root: str | Path) -> tuple[DiscoveredGeneration, ...]:
    root = Path(project_root).resolve()
    if not root.is_dir(): raise ValueError(f"generation project is not a directory: {root}")
    paths: list[Path] = []
    for directory, directory_names, file_names in root.walk(top_down=True):
        directory_names[:] = sorted(n for n in directory_names if not n.startswith(".") and n not in {"__pycache__"})
        if "__init__.py" in file_names:
            path = directory / "__init__.py"
            if "generation" in path.read_text(encoding="utf-8"): paths.append(path)
    results = tuple(request for path in paths for request in discover_file(root, path))
    identities: set[Path] = set()
    for request in results:
        normalized = Path(str(request.product_path).casefold())
        if normalized in identities: raise GenerationError(f"generated product collision for {request.product_path}")
        identities.add(normalized)
    return results
