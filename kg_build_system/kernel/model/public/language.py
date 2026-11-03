"""The language frontend: declarations to one named layer.

A language owns one layer of a build. It collects the declarations it recognises
from a namespace, transcribes them into its own value and a symbol index,
validates that value and renders it back to authoring source. Languages declare
the names of the layers they read, so the toolchain can transcribe them in
dependency order.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, Protocol


@dataclass(frozen=True, slots=True)
class Definition:
    """One named unit another language may reference.

    ``kind`` names the sort of symbol (for example ``"table"`` or ``"node"``)
    and ``value`` is the language's own frozen representation. The kernel treats
    both strings and the value as opaque.

    Example:
    ```python
    from kg_build_system.kernel import Definition

    definition = Definition("Site", "node", {"name": "Site"})
    assert definition.id == "Site"
    ```
    """

    id: str
    kind: str
    value: Any


@dataclass(frozen=True, slots=True)
class Layer:
    """One language's transcribed value and the definitions it publishes.

    ``value`` is the language's own DTO. ``definitions`` is the symbol index
    other languages read; it is copied and wrapped in a read-only proxy.

    Example:
    ```python
    from kg_build_system.kernel import Definition, Layer

    layer = Layer(
        "topology",
        {"nodes": ("Site",)},
        {"Site": Definition("Site", "node", {"name": "Site"})},
    )
    assert layer.definitions["Site"].kind == "node"
    ```
    """

    language: str
    value: Any
    definitions: Mapping[str, Definition] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "definitions", MappingProxyType(dict(self.definitions)),
        )


class Namespace(Protocol):
    """The authoring objects one build may collect declarations from.

    A namespace is supplied by the caller. The kernel does not inspect it: a
    language decides which values it recognises and ignores the rest.

    Example:
    ```python
    class Namespace:
        def values(self):
            return (1, 2)

    values = Namespace().values()
    ```
    """

    def values(self) -> Sequence[object]:
        """Return every declaration value the caller made available.

        Example:
            ```python
            class Namespace:
                def values(self):
                    return (1, 2)

            assert Namespace().values() == (1, 2)
            ```
        """
        ...


class LanguageContext(Protocol):
    """The already-transcribed layers a language may read while transcribing.

    ``layer`` returns the layer of a language named in ``requires``. It raises
    ``KeyError`` for a layer that has not been transcribed yet, which the
    toolchain's dependency order is responsible for preventing.

    Example:
    ```python
    class Context:
        def layer(self, name):
            return {"data": "layer"}[name]

    assert Context().layer("data") == "layer"
    ```
    """

    def layer(self, name: str) -> Layer:
        """Return the transcribed layer named ``name``.

        Example:
            ```python
            class Context:
                def layer(self, name):
                    return {"data": "layer"}[name]

            assert Context().layer("data") == "layer"
            ```
        """
        ...


class RenderContext(Protocol):
    """The opaque context a language receives when rendering its value.

    The framework owns the context. A language passes it to the renderers of
    the layers it depends on; it does not inspect it.

    Example:
    ```python
    class Context:
        pass

    Context()
    ```
    """


@dataclass(frozen=True, slots=True)
class SourceFragment:
    """One rendered piece of authoring source.

    ``kind`` is ``"inline"`` for an expression fragment or ``"declaration"``
    for a top-level declaration. ``body`` is the source text and ``imports``
    names the modules the fragment needs.

    Example:
    ```python
    from kg_build_system.kernel import SourceFragment

    fragment = SourceFragment("declaration", "value = 1", ("example",))
    assert fragment.body == "value = 1"
    ```
    """

    kind: Literal["inline", "declaration"]
    body: str
    imports: tuple[str, ...] = ()


class Language(Protocol):
    """One named layer: collect, transcribe, validate and render.

    ``name`` is the layer name written into the toolchain's layer map.
    ``requires`` names the layers this language reads; the toolchain rejects
    unknown dependencies and dependency cycles, then transcribes languages in a
    consistent order. ``transcribe`` returns a ``Layer`` whose ``language`` is
    ``name``.

    Example:
    ```python
    from kg_build_system.kernel import Layer, SourceFragment

    class EchoLanguage:
        name = "echo"
        requires = ()

        def collect(self, namespace):
            return namespace.values()

        def transcribe(self, declarations, context):
            return Layer("echo", tuple(declarations))

        def validate(self, layer):
            assert layer.language == "echo"

        def render(self, layer, context):
            return SourceFragment("inline", repr(layer.value))
    ```
    """

    name: str
    requires: tuple[str, ...]

    def collect(self, namespace: Namespace) -> Sequence[object]:
        """Select the declarations this language recognises.

        Example:
            ```python
            declarations = EchoLanguage().collect(namespace)
            ```
        """
        ...

    def transcribe(
        self, declarations: Sequence[object], context: LanguageContext,
    ) -> Layer:
        """Turn collected declarations into this language's layer.

        Example:
            ```python
            layer = EchoLanguage().transcribe(declarations, context)
            assert layer.language == "echo"
            ```
        """
        ...

    def validate(self, layer: Layer) -> None:
        """Reject a layer that violates this language's invariants.

        Example:
            ```python
            EchoLanguage().validate(EchoLanguage().transcribe((), context))
            ```
        """
        ...

    def render(self, layer: Layer, context: RenderContext) -> SourceFragment:
        """Render this language's layer back to authoring source.

        Example:
            ```python
            fragment = EchoLanguage().render(layer, context)
            assert fragment.kind == "inline"
            ```
        """
        ...


__all__ = [
    "Definition", "Language", "LanguageContext", "Layer", "Namespace",
    "RenderContext", "SourceFragment",
]
