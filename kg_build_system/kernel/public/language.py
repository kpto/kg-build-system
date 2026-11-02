"""The language protocol: authoring declarations to one named build part.

A language owns one part of a build. It collects the declarations it recognises
from a namespace, lowers them into its own IR, then validates and encodes that
IR. Languages declare the names of the parts they read, so a registry can lower
them in dependency order.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


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
    """The already-lowered parts a language may read while lowering.

    ``part`` returns the IR of a language named in ``requires``. It raises
    ``KeyError`` for a part that has not been lowered yet, which the registry's
    dependency order is responsible for preventing.

    Example:
    ```python
    class Context:
        def part(self, name):
            return {"data": ("table",)}[name]

    assert Context().part("data") == ("table",)
    ```
    """

    def part(self, name: str) -> Any:
        """Return the lowered part named ``name``.

        Example:
            ```python
            class Context:
                def part(self, name):
                    return {"data": ("table",)}[name]

            assert Context().part("data") == ("table",)
            ```
        """
        ...


class Language(Protocol):
    """One named build part: collect, lower, validate, encode and decode.

    ``name`` is the part name written into ``BuildIR.parts``. ``requires`` names
    the parts this language reads; the registry rejects unknown dependencies and
    dependency cycles, then lowers languages in a consistent order.

    Example:
    ```python
    class EchoLanguage:
        name = "echo"
        requires = ()

        def collect(self, namespace):
            return namespace.values()

        def lower(self, declarations, context):
            return tuple(declarations)

        def validate(self, ir):
            assert isinstance(ir, tuple)

        def encode(self, ir):
            return list(ir)

        def decode(self, value):
            return tuple(value)
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

    def lower(
        self, declarations: Sequence[object], context: LanguageContext,
    ) -> Any:
        """Turn collected declarations into this language's frozen IR.

        Example:
            ```python
            ir = EchoLanguage().lower(declarations, context)
            ```
        """
        ...

    def validate(self, ir: Any) -> None:
        """Reject an IR value that violates this language's invariants.

        Example:
            ```python
            EchoLanguage().validate(("value",))
            ```
        """
        ...

    def encode(self, ir: Any) -> Any:
        """Return the JSON-compatible form of this language's IR.

        Example:
            ```python
            assert EchoLanguage().encode(("value",)) == ["value"]
            ```
        """
        ...

    def decode(self, value: Any) -> Any:
        """Rebuild this language's IR from its encoded form.

        Example:
            ```python
            assert EchoLanguage().decode(["value"]) == ("value",)
            ```
        """
        ...


__all__ = ["Language", "LanguageContext", "Namespace"]
