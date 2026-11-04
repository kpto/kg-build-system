"""Declarations, linked symbols and typed references.

A language offers declarations; the linker keys them and transcribes them into
symbols. A symbol carries its key, kind, value and the references the linker
must resolve. A ``SymbolRef`` names a symbol by language and key.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from .key import Key


@dataclass(frozen=True, slots=True)
class SymbolRef:
    """A typed reference to one symbol.

    ``language`` names the language that owns the symbol and ``key`` is the
    symbol's key within that language.

    Example:
    ```python
    from kg_build_system.kernel import Key, SymbolRef

    reference = SymbolRef("data", Key(("site",)))
    assert reference.language == "data"
    ```
    """

    language: str
    key: Key

    def __str__(self) -> str:
        return f"{self.language}:{self.key}"


@dataclass(frozen=True, slots=True)
class Declaration:
    """One authoring object a language offers the linker.

    A declaration carries only the value the language recognised. It has no key
    yet: the language computes the key with ``compute_key``.

    Example:
    ```python
    from kg_build_system.kernel import Declaration

    declaration = Declaration({"name": "site"})
    assert declaration.value == {"name": "site"}
    ```
    """

    value: Any


@dataclass(frozen=True, slots=True)
class Symbol:
    """One linked unit of a language.

    ``key`` is unique within the language that produced it, ``value`` is the
    language's own frozen representation (a DTO fragment in the distribution) and
    ``references`` names the symbols this symbol depends on.

    Example:
    ```python
    from kg_build_system.kernel import Key, Symbol

    symbol = Symbol(Key(("site",)), "node", {"name": "site"})
    assert symbol.references == ()
    ```
    """

    key: Key
    kind: str
    value: Any
    references: tuple[SymbolRef, ...] = ()


@dataclass(frozen=True, slots=True)
class SymbolContext:
    """The symbols transcribed before the current language.

    ``symbols`` is copied and wrapped in a read-only proxy. ``get_symbol``
    raises ``KeyError`` for a reference that has not been transcribed yet.

    Example:
    ```python
    from kg_build_system.kernel import Key, Symbol, SymbolContext, SymbolRef

    reference = SymbolRef("data", Key(("site",)))
    context = SymbolContext({
        reference: Symbol(Key(("site",)), "relation", {"name": "site"}),
    })
    assert context.get_value(reference) == {"name": "site"}
    ```
    """

    symbols: Mapping[SymbolRef, Symbol] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "symbols", MappingProxyType(dict(self.symbols)),
        )

    def get_symbol(self, reference: SymbolRef) -> Symbol:
        """Return one transcribed symbol.

        Example:
        ```python
        symbol = context.get_symbol(reference)
        assert symbol.key == reference.key
        ```
        """
        try:
            return self.symbols[reference]
        except KeyError:
            raise KeyError(f"unknown symbol {reference}") from None

    def get_value(self, reference: SymbolRef) -> Any:
        """Return one transcribed symbol's value.

        Example:
        ```python
        value = context.get_value(reference)
        ```
        """
        return self.get_symbol(reference).value


__all__ = ["Declaration", "Symbol", "SymbolContext", "SymbolRef"]
