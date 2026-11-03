"""Render the binding blueprint DTO as authoring source."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from kg_build_system.kernel import SourceFragment

from ...model.internal.dto.blueprint_dto import BindingDTO


def bind_reference(
    function: Any, *, module: str, qualname: str, signature: str,
) -> Any:
    """Attach the original Python reference to a generated ``bind`` callable.

    The generated lambda evaluates the already-transcribed values, but the
    blueprint needs the original module, qualified name and signature to stay
    stable across the source round trip. The helper returns the same callable.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.service.internal.source import (
            bind_reference,
        )

        function = bind_reference(
            lambda row: row,
            module="example.bindings",
            qualname="build_unit",
            signature="(row)",
        )
        assert function.__module__ == "example.bindings"
        ```
    """
    from .._private.source import bind_reference as bind

    return bind(function, module=module, qualname=qualname, signature=signature)


def render_binding_source(
    bindings: Sequence[BindingDTO], context: Any = None,
) -> SourceFragment:
    """Render binding DTOs as authoring source.

    Direct bindings render as ``node_binding(build_key=..., properties=...)``;
    Python bindings render with their row plan and a ``bind`` lambda that
    returns ``NodeValues`` or ``EdgeValues``. The target is always named by its
    logical graph name, never by a Python symbol.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.service.internal import (
            render_binding_source,
        )

        fragment = render_binding_source(())
        assert fragment.body == ""
        ```
    """
    from .._private.source import render_binding_source as render

    return render(bindings, context)


__all__ = ["bind_reference", "render_binding_source"]
