"""The language protocol: authoring declarations to one named build part.

A language owns one part of a build. It collects the declarations it recognises
from a namespace, transcribes them into its own DTO, validates that DTO and
renders it back to authoring source. Languages declare the names of the parts
they read, so a registry can transcribe them in dependency order.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol


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
    """The already-transcribed parts a language may read while transcribing.

    ``part`` returns the DTO of a language named in ``requires``. It raises
    ``KeyError`` for a part that has not been transcribed yet, which the
    registry's dependency order is responsible for preventing.

    Example:
    ```python
    class Context:
        def part(self, name):
            return {"data": ("table",)}[name]

    assert Context().part("data") == ("table",)
    ```
    """

    def part(self, name: str) -> Any:
        """Return the transcribed part named ``name``.

        Example:
            ```python
            class Context:
                def part(self, name):
                    return {"data": ("table",)}[name]

            assert Context().part("data") == ("table",)
            ```
        """
        ...


class RenderContext(Protocol):
    """The opaque context a language receives when rendering its DTO.

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
    """One named build part: collect, transcribe, validate and render.

    ``name`` is the part name written into ``Build.parts``. ``requires`` names
    the parts this language reads; the registry rejects unknown dependencies and
    dependency cycles, then transcribes languages in a consistent order.

    Example:
    ```python
    from kg_build_system.kernel import SourceFragment

    class EchoLanguage:
        name = "echo"
        requires = ()

        def collect(self, namespace):
            return namespace.values()

        def transcribe(self, declarations, context):
            return tuple(declarations)

        def validate(self, dto):
            assert isinstance(dto, tuple)

        def render(self, dto, context):
            return SourceFragment("inline", repr(dto))
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
    ) -> Any:
        """Turn collected declarations into this language's frozen DTO.

        Example:
            ```python
            dto = EchoLanguage().transcribe(declarations, context)
            ```
        """
        ...

    def validate(self, dto: Any) -> None:
        """Reject a DTO that violates this language's invariants.

        Example:
            ```python
            EchoLanguage().validate(("value",))
            ```
        """
        ...

    def render(self, dto: Any, context: RenderContext) -> SourceFragment:
        """Render this language's DTO back to authoring source.

        Example:
            ```python
            fragment = EchoLanguage().render(("value",), context)
            assert fragment.kind == "inline"
            ```
        """
        ...


__all__ = [
    "Language", "LanguageContext", "Namespace", "RenderContext",
    "SourceFragment",
]
