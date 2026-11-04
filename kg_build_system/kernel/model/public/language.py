"""The language frontend: declarations, symbols and source rendering.

A language owns one part of a build. It discovers the authoring objects it
recognises, computes a key and kind for each declaration, transcribes a batch of
declarations into symbols and renders a symbol value back to authoring source.
The linker orders languages, resolves references and assembles the model.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
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
    """Resolve a value to its symbol reference and that reference's edges.

    The linker supplies the resolver after transcription. ``get_identity``
    returns ``None`` for a value the framework does not publish as a symbol.

    Example:
    ```python
    class Resolver:
        def get_identity(self, value):
            return None

        def get_references(self, value):
            return ()
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

    def get_references(self, value: Any) -> tuple[SymbolRef, ...]:
        """Return the references one value declares.

        Example:
            ```python
            references = resolver.get_references(value)
            ```
        """
        ...


class Language(Protocol):
    """One named frontend: discover, key, transcribe and render.

    ``name`` is the language name written into every ``SymbolRef`` it
    produces. ``transcribe_many`` is the required transcription path in this
    wave; it may delegate to a batch implementation and split the resulting
    DTOs into one symbol per declaration.

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

        def owns(self, value):
            return isinstance(value, str)

        def get_identity(self, value):
            return SymbolRef("echo", Key((value,))) if isinstance(value, str) else None

        def get_references(self, value, resolver):
            return ()

        def transcribe_many(self, declarations, context):
            return {
                SymbolRef("echo", self.compute_key(item)): Symbol(
                    self.compute_key(item), "echo", item.value,
                )
                for item in declarations
            }

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

    def owns(self, value: Any) -> bool:
        """Whether this language owns ``value``.

        The resolver uses ownership to choose the language that answers
        ``get_identity`` and ``get_references``. A language may also own its
        transcribed values (DTO fragments), because the linker resolves
        references after transcription.

        Example:
            ```python
            assert EchoLanguage().owns("hello")
            ```
        """
        ...

    def get_identity(self, value: Any) -> SymbolRef | None:
        """Return the reference of one authoring or transcribed value.

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
        """Return the references one transcribed symbol value declares.

        This wave passes the transcribed symbol value (a DTO fragment) and the
        linker calls the method after transcription. A later wave may pass the
        authoring value instead.

        Example:
            ```python
            references = EchoLanguage().get_references("hello", resolver)
            ```
        """
        ...

    def transcribe_many(
        self, declarations: Sequence[Declaration], context: SymbolContext,
    ) -> Mapping[SymbolRef, Symbol]:
        """Transcribe a batch of declarations into symbols.

        ``context`` holds the symbols of languages transcribed earlier.
        ``transcribe_many`` is the required transcription path in this wave; a
        per-symbol ``transcribe`` is an optimisation added later.

        Example:
            ```python
            symbols = EchoLanguage().transcribe_many(declarations, context)
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
