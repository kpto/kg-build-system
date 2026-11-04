"""Static discovery of asset contracts without importing authored modules."""
from __future__ import annotations

from hashlib import sha256
import re
from pathlib import Path
from typing import Any, cast

import libcst as cst
from libcst.metadata import MetadataWrapper, ParentNodeProvider, PositionProvider

from ...model.internal.models import (
    DiscoveredGeneration, GenerationLocation,
)
from ...model.public.errors import GenerationError
from ...model.public.requests import GenerationRequest
from ...model.public.values import StaticValue

_ASSET_CONTRACT = {
    "kg_build_system.generation.asset_contract",
    "kg_build_system.generation.code_generation.asset_contract",
}
_ASSET_CONTRACT_OPTIONS = {
    "kg_build_system.generation.AssetContractOptions",
    "kg_build_system.generation.code_generation.AssetContractOptions",
}
_ASSET = {
    "kg_build_system.Asset",
    "kg_build_system.distribution.languages.asset.Asset",
}
_ASSET_OPTIONS = {
    "kg_build_system.AssetOptions",
    "kg_build_system.distribution.languages.asset.AssetOptions",
}
_OPTIONS_FIELDS = {"provider", "configuration", "package"}


def _dotted(node: cst.BaseExpression | None) -> str | None:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        parent = _dotted(node.value)
        return f"{parent}.{node.attr.value}" if parent else None
    return None


def _snake_case(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_]", "_", value)
    result = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", result).lower().strip("_")
    return result or "asset"


def _static(node: cst.BaseExpression) -> StaticValue:
    if isinstance(node, cst.SimpleString):
        value = node.evaluated_value
        if isinstance(value, str):
            return value
    if isinstance(node, cst.Integer):
        return int(node.value.replace("_", ""), 0)
    if isinstance(node, cst.Float):
        return float(node.value.replace("_", ""))
    if isinstance(node, cst.Name) and node.value in {"True", "False", "None"}:
        return {"True": True, "False": False, "None": None}[node.value]
    if isinstance(node, (cst.List, cst.Tuple)):
        if any(element is None or isinstance(element, cst.StarredElement) for element in node.elements):
            raise GenerationError("asset contract configuration does not support unpacking")
        values = [_static(cast(cst.Element, element).value) for element in node.elements]
        return tuple(values) if isinstance(node, cst.Tuple) else values
    if isinstance(node, cst.Dict):
        result: dict[str, StaticValue] = {}
        for element in node.elements:
            if not isinstance(element, cst.DictElement):
                raise GenerationError("asset contract configuration does not support dictionary unpacking")
            key = _static(element.key)
            if not isinstance(key, str):
                raise GenerationError("asset contract configuration dictionary keys must be strings")
            result[key] = _static(element.value)
        return result
    raise GenerationError("asset contract configuration values must be static literals")


def _module_name(root: Path, path: Path) -> str:
    prefix = (root.name,) if (root / "__init__.py").is_file() else ()
    parts = (*prefix, *path.relative_to(root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _product_path(root: Path, package: str, asset_name: str) -> Path:
    """``<package>/<asset name>`` below the project root.

    The package is an import path. When the project root is itself a package,
    its leading package segment names the root and is not repeated on disk.
    """
    parts = package.split(".")
    if (root / "__init__.py").is_file() and parts and parts[0] == root.name:
        parts = parts[1:]
    return Path(*parts, asset_name)


class _Visitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider, ParentNodeProvider)

    def __init__(self, root: Path, path: Path, source_digest: str) -> None:
        self.root, self.path = root, path
        self.source_digest = source_digest
        self.direct: dict[str, str] = {}
        self.modules: dict[str, str] = {}
        self.depth = 0
        self.results: list[DiscoveredGeneration] = []

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        module = _dotted(node.module)
        if module is None or node.relative or isinstance(node.names, cst.ImportStar):
            return
        for alias in node.names:
            name = _dotted(alias.name)
            local = _dotted(alias.asname.name) if alias.asname else name
            if name and local:
                self.direct[local] = f"{module}.{name}"

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            module = _dotted(alias.name)
            if not module:
                continue
            local = _dotted(alias.asname.name) if alias.asname else module.split(".")[0]
            if local:
                self.modules[local] = module if alias.asname else module.split(".")[0]

    def _resolve(self, expression: cst.BaseExpression) -> str | None:
        dotted = _dotted(expression)
        if not dotted:
            return None
        parts = dotted.split(".")
        if parts[0] in self.direct:
            return ".".join((self.direct[parts[0]], *parts[1:]))
        if parts[0] in self.modules:
            return ".".join((self.modules[parts[0]], *parts[1:]))
        return None

    def visit_FunctionDef(self, _node: cst.FunctionDef) -> None:
        self.depth += 1

    def leave_FunctionDef(self, _node: cst.FunctionDef) -> None:
        self.depth -= 1

    def _contract_decorator(
        self, node: cst.ClassDef,
    ) -> tuple[cst.Call, cst.Decorator] | None:
        found: tuple[cst.Call, cst.Decorator] | None = None
        for decorator in node.decorators:
            expression = decorator.decorator
            if not isinstance(expression, cst.Call) or self._resolve(expression.func) not in _ASSET_CONTRACT:
                continue
            if found is not None:
                raise GenerationError(
                    f"{self.path.as_posix()}: a class declares one asset contract"
                )
            found = (expression, decorator)
        return found

    def _asset_name(self, node: cst.ClassDef, class_name: str) -> str:
        for statement in node.body.body:
            if not isinstance(statement, cst.SimpleStatementLine):
                continue
            for small in statement.body:
                target = None
                value = None
                if isinstance(small, cst.Assign) and len(small.targets) == 1:
                    target, value = small.targets[0].target, small.value
                elif isinstance(small, cst.AnnAssign):
                    target, value = small.target, small.value
                if (
                    isinstance(target, cst.Name)
                    and target.value == "options"
                    and isinstance(value, cst.Call)
                    and self._resolve(value.func) in _ASSET_OPTIONS
                ):
                    for argument in value.args:
                        if argument.keyword is not None and argument.keyword.value == "name":
                            name = _static(argument.value)
                            if not isinstance(name, str) or not name:
                                raise GenerationError(
                                    f"{self.path.as_posix()}: AssetOptions.name must be a non-empty string"
                                )
                            return name
        return _snake_case(class_name)

    def _request(
        self, node: cst.ClassDef, call: cst.Call, position: Any,
    ) -> DiscoveredGeneration:
        prefix = f"{self.path.as_posix()}:{position.line}"
        parent = self.get_metadata(ParentNodeProvider, node)
        if not isinstance(parent, cst.Module):
            raise GenerationError(f"{prefix}: asset contracts must be declared at module level")
        if len(node.bases) != 1 or node.bases[0].keyword is not None or node.bases[0].star:
            raise GenerationError(f"{prefix}: an asset contract requires one Asset base class")
        if self._resolve(node.bases[0].value) not in _ASSET:
            raise GenerationError(f"{prefix}: @asset_contract can only decorate an Asset subclass")
        if len(call.args) != 1 or call.args[0].keyword is not None or call.args[0].star:
            raise GenerationError(
                f"{prefix}: @asset_contract requires one inline AssetContractOptions(...)"
            )
        options_call = call.args[0].value
        if not isinstance(options_call, cst.Call):
            raise GenerationError(
                f"{prefix}: @asset_contract requires one inline AssetContractOptions(...)"
            )
        if self._resolve(options_call.func) not in _ASSET_CONTRACT_OPTIONS:
            raise GenerationError(
                f"{prefix}: @asset_contract requires AssetContractOptions"
            )
        fields: dict[str, cst.BaseExpression] = {}
        for argument in options_call.args:
            if argument.keyword is None or argument.star:
                raise GenerationError(
                    f"{prefix}: AssetContractOptions accepts keyword arguments only"
                )
            key = argument.keyword.value
            if key not in _OPTIONS_FIELDS:
                raise GenerationError(f"{prefix}: unknown AssetContractOptions field {key!r}")
            if key in fields:
                raise GenerationError(f"{prefix}: duplicate AssetContractOptions field {key!r}")
            fields[key] = argument.value
        missing = _OPTIONS_FIELDS - set(fields)
        if missing:
            raise GenerationError(
                f"{prefix}: AssetContractOptions is missing {', '.join(sorted(missing))}"
            )
        package = _static(fields["package"])
        if not isinstance(package, str) or any(
            not part.isidentifier() for part in package.split(".")
        ):
            raise GenerationError(f"{prefix}: package must be a dotted identifier")
        provider = self._resolve(fields["provider"])
        if provider is None:
            raise GenerationError(f"{prefix}: provider type must be statically imported")
        config_call = fields["configuration"]
        if not isinstance(config_call, cst.Call):
            raise GenerationError(f"{prefix}: configuration must be constructed inline")
        config = self._resolve(config_call.func)
        if config is None:
            raise GenerationError(f"{prefix}: configuration type must be statically imported")
        values: dict[str, StaticValue] = {}
        for argument in config_call.args:
            if argument.keyword is None or argument.star:
                raise GenerationError(
                    f"{prefix}: provider configuration accepts keyword arguments only"
                )
            key = argument.keyword.value
            if key in values:
                raise GenerationError(f"{prefix}: duplicate configuration argument {key!r}")
            values[key] = _static(argument.value)
        provider_module, provider_qualname = provider.rsplit(".", 1)
        config_module, config_qualname = config.rsplit(".", 1)
        asset_name = self._asset_name(node, node.name.value)
        asset_module = _module_name(self.root, self.path)
        asset_qualname = node.name.value
        source_package = asset_module.rsplit(".", 1)[0] if "." in asset_module else asset_module
        product_path = _product_path(self.root, package, asset_name)
        package_import = f"{package}.{asset_name}"
        return DiscoveredGeneration(
            GenerationRequest(
                provider_module, provider_qualname, config_module, config_qualname,
                values, package, asset_module, asset_qualname, self.source_digest,
            ),
            GenerationLocation(
                self.root, self.path, position.line, position.column,
                asset_name, source_package,
            ),
            product_path,
            package_import,
        )

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        declared = self._contract_decorator(node)
        # An asset contract is an importable module-level declaration. A
        # decorated class inside a function or another class has no module
        # qualname a generated file could import, so it is not a request.
        if declared is not None and not self.depth:
            call, decorator = declared
            position = cast(Any, self.get_metadata(PositionProvider, decorator)).start
            self.results.append(self._request(node, call, position))
        self.depth += 1

    def leave_ClassDef(self, _node: cst.ClassDef) -> None:
        self.depth -= 1


def discover_file(project_root: str | Path, source_path: str | Path) -> tuple[DiscoveredGeneration, ...]:
    """Discover the asset contracts declared by one source file."""
    root, path = Path(project_root).resolve(), Path(source_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"source file is outside the project: {path}") from error
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise GenerationError(f"{path}: cannot read Python source: {error}") from error
    if "asset_contract" not in text:
        return ()
    try:
        module = cst.parse_module(text)
    except cst.ParserSyntaxError as error:
        raise GenerationError(f"{path}: cannot parse Python source: {error}") from error
    visitor = _Visitor(root, path, sha256(text.encode("utf-8")).hexdigest())
    MetadataWrapper(module).visit(visitor)
    return tuple(visitor.results)


def discover(project_root: str | Path) -> tuple[DiscoveredGeneration, ...]:
    """Discover every asset contract beneath a project root."""
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise ValueError(f"generation project is not a directory: {root}")
    paths: list[Path] = []
    for directory, directory_names, file_names in root.walk(top_down=True):
        directory_names[:] = sorted(
            name for name in directory_names
            if not name.startswith(".") and name != "__pycache__"
        )
        for name in sorted(file_names):
            if not name.endswith(".py"):
                continue
            path = directory / name
            if "asset_contract" in path.read_text(encoding="utf-8", errors="ignore"):
                paths.append(path)
    results = tuple(request for path in paths for request in discover_file(root, path))
    products: set[Path] = set()
    identities: set[str] = set()
    for request in results:
        normalized = Path(str(request.product_path).casefold())
        if normalized in products:
            raise GenerationError(f"generated product collision for {request.product_path}")
        products.add(normalized)
        identity = request.location.request_id.casefold()
        if identity in identities:
            raise GenerationError(
                f"asset contract identity collision for {request.location.request_id!r}"
            )
        identities.add(identity)
    return results


__all__ = ["discover", "discover_file"]
