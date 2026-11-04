"""Create a graph blueprint from declarations.

The service collects and transcribes through the kernel toolchain, links the
layer DTOs with :class:`BlueprintLinker` and validates the result. It does not
take modules and it does not compile.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from kg_build_system.distribution.languages.binding.service.internal import BindingLanguage
from kg_build_system.distribution.languages.data.service.internal import DataLanguage
from kg_build_system.distribution.languages.topology.service.internal import TopologyLanguage
from kg_build_system.kernel import Toolchain

from ...model.public import GraphBlueprint
from ..internal.adapters.kernel_linker import BlueprintLinker
from .discovery import _ModuleNamespace, _Namespace, namespace_modules


def _default_languages() -> tuple[Any, ...]:
    """Return the default data, topology and binding languages."""
    return (DataLanguage(), TopologyLanguage(), BindingLanguage())


def create_blueprint(
    *,
    namespace_path: str | Path | None = None,
    bindings: Iterable[Any] = (),
    sources: Sequence[Any] = (),
    languages: Sequence[Any] | None = None,
) -> GraphBlueprint:
    """Collect declarations into a validated, frozen graph blueprint.

    Supply either ``namespace_path`` or explicit ``bindings`` and ``sources``.
    The declared languages are run through the kernel toolchain; each language
    collects and transcribes its own DTO, and :class:`BlueprintLinker` assembles
    the DTOs into one blueprint.
    """
    explicit_bindings = tuple(bindings)
    explicit_sources = tuple(sources)
    if namespace_path is not None:
        if explicit_bindings or explicit_sources:
            raise ValueError(
                "namespace_path cannot be combined with bindings or sources"
            )
        namespace: Any = _ModuleNamespace(namespace_modules(namespace_path))
    else:
        namespace = _Namespace((*explicit_bindings, *explicit_sources))
    toolchain = Toolchain(
        languages=tuple(languages or _default_languages()),
        linker=BlueprintLinker(),
    )
    return toolchain.build(namespace)


__all__ = ["create_blueprint"]
