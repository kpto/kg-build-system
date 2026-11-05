"""The language frontend: declarations, symbols and source rendering.

A language owns one part of a build. It discovers the authoring objects it
recognises, computes a key and kind for each declaration, reports the
references one authoring value declares, transcribes one declaration into a
symbol and renders a symbol value back to authoring source. The linker indexes
declarations, selects roots, walks the reference closure, orders declarations,
transcribes only the reachable ones and assembles the model.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from .key import Key
from .symbol import Declaration, Symbol, SymbolContext, SymbolRef


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


class RenderContext(Protocol):
    """The opaque context a language receives when rendering a symbol.

    The framework owns the context. A language passes it to the renderers of
    the languages it depends on; it does not inspect it.

    Example:
    ```python
    class Context:
        pass

    Context()
    ```
    """


class ReferenceResolver(Protocol):
    """Resolve an authoring value to the symbol reference it denotes.

    The linker supplies the resolver before transcription. It answers from the
    declarations it has indexed across every language, so a language can resolve
    a typed reference without knowing which language owns the value.

    Example:
    ```python
    class Resolver:
        def get_identity(self, value):
            return None
    ```
    """

    def get_identity(self, value: Any) -> SymbolRef | None:
        """Return the reference of ``value``, or ``None`` when it has none.

        Example:
            ```python
            reference = resolver.get_identity(value)
            ```
        """
        ...


class Language(Protocol):
    """One named frontend: discover, key, transcribe and render.

    ``name`` is the language name written into every ``SymbolRef`` it
    produces. ``transcribe`` is the required per-declaration path; a language
    may use a batch implementation internally, but the linker calls
    ``transcribe`` once per reachable declaration.

    Example:
    ```python
    from kg_build_system.kernel import (
        Declaration, Key, SourceFragment, Symbol, SymbolRef,
    )

    class EchoLanguage:
        name = "echo"

        def discover_declarations(self, namespace):
            return (Declaration(value) for value in namespace.values())

        def compute_key(self, declaration):
            return Key((str(declaration.value),))

        def get_kind(self, declaration):
            return "echo"

        def get_identity(self, value):
            return SymbolRef("echo", Key((value,))) if isinstance(value, str) else None

        def get_references(self, value, resolver):
            return ()

        def transcribe(self, declaration, context):
            key = self.compute_key(declaration)
            return Symbol(key, "echo", declaration.value)

        def render(self, symbol, context):
            return SourceFragment("inline", repr(symbol.value))
    ```
    """

    name: str

    def discover_declarations(
        self, namespace: Namespace,
    ) -> Iterable[Declaration]:
        """Select the declarations this language recognises.

        Example:
            ```python
            declarations = EchoLanguage().discover_declarations(namespace)
            ```
        """
        ...

    def compute_key(self, declaration: Declaration) -> Key:
        """Return the key of one declaration within this language.

        Example:
            ```python
            key = EchoLanguage().compute_key(Declaration("hello"))
            assert key == Key(("hello",))
            ```
        """
        ...

    def get_kind(self, declaration: Declaration) -> str:
        """Return the symbol kind of one declaration.

        Example:
            ```python
            assert EchoLanguage().get_kind(Declaration("hello")) == "echo"
            ```
        """
        ...

    def get_identity(self, value: Any) -> SymbolRef | None:
        """Return the reference one authoring value denotes.

        The value is an authoring value, not a transcribed symbol or DTO. A
        value the language does not publish as a symbol returns ``None``.

        Example:
            ```python
            reference = EchoLanguage().get_identity("hello")
            assert reference == SymbolRef("echo", Key(("hello",)))
            ```
        """
        ...

    def get_references(
        self, value: Any, resolver: ReferenceResolver,
    ) -> tuple[SymbolRef, ...]:
        """Return the direct dependencies one authoring declaration value declares.

        The linker calls this before transcription, using the declaration value.
        The result names only direct edges: the closure walk follows them to
        reach the rest. An expression is an inline fragment, so its leaves are
        typed references rather than separately keyed expressions.

        Example:
            ```python
            references = EchoLanguage().get_references("hello", resolver)
            ```
        """
        ...

    def transcribe(
        self, declaration: Declaration, context: SymbolContext,
    ) -> Symbol:
        """Transcribe one declaration into one symbol.

        ``context`` holds the symbols already transcribed, dependencies first.
        This is the required per-declaration path; the linker selects the
        reference closure before calling it and never transcribes an
        unreachable declaration.

        Example:
            ```python
            symbol = EchoLanguage().transcribe(
                Declaration("hello"), SymbolContext(),
            )
            assert symbol.key == Key(("hello",))
            ```
        """
        ...

    def render(self, symbol: Symbol, context: RenderContext) -> SourceFragment:
        """Render one symbol value back to authoring source.

        A renderer accepts either a ``Symbol`` or its value so the interpreter
        can render a whole layer DTO as well as one symbol.

        Example:
            ```python
            fragment = EchoLanguage().render(symbol, context)
            assert fragment.kind == "inline"
            ```
        """
        ...


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


__all__ = [
    "Declaration", "Key", "Language", "Namespace", "ReferenceResolver",
    "RenderContext", "SourceFragment", "Symbol", "SymbolContext", "SymbolRef",
]
