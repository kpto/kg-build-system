"""Create a graph blueprint from declarations.

The service collects and transcribes through the kernel toolchain, links the
layer DTOs with :class:`BlueprintLinker` and validates the result. It does not
take modules and it does not compile.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from kg_build_system.distribution.languages.asset.service.internal import AssetLanguage
from kg_build_system.distribution.languages.binding.service.internal import BindingLanguage
from kg_build_system.distribution.languages.data.service.internal import DataLanguage
from kg_build_system.distribution.languages.expressions.service.internal import ExpressionsLanguage
from kg_build_system.distribution.languages.topology.service.internal import TopologyLanguage
from kg_build_system.kernel import Toolchain

from ...model.public import GraphBlueprint
from ..internal.adapters.kernel_linker import BlueprintLinker
from .discovery import _ModuleNamespace, _Namespace, namespace_modules


def _default_languages() -> tuple[Any, ...]:
    """Return the default expression, asset, data, topology and binding languages."""
    return (
        ExpressionsLanguage(), AssetLanguage(), DataLanguage(),
        TopologyLanguage(), BindingLanguage(),
    )


def create_blueprint(
    *,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Any] = (),
    languages: Sequence[Any] | None = None,
) -> GraphBlueprint:
    """Collect declarations into a validated, frozen graph blueprint.

    Supply either ``namespace_path`` or explicit ``bindings``. The declared
    languages are run through the kernel toolchain; each language collects and
    transcribes its own DTO, and :class:`BlueprintLinker` assembles the DTOs
    into one blueprint.
    """
    explicit_bindings = tuple(bindings)
    if namespace_path is not None:
        if explicit_bindings:
            raise ValueError(
                "namespace_path cannot be combined with bindings"
            )
        namespace: Any = _ModuleNamespace(namespace_modules(namespace_path))
    else:
        namespace = _Namespace(explicit_bindings)
    toolchain = Toolchain(
        languages=tuple(languages or _default_languages()),
        linker=BlueprintLinker(),
    )
    return toolchain.build(namespace)


__all__ = ["create_blueprint"]
