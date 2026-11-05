"""The public paired-record value produced by ``Selection.zip``.

A pair is a canonical value record with two present members, ``left`` and
``right``. It is a value shape, not a row source and not an anonymous tuple.

Example:
    ```python
    from kg_build_system import Field, Pair, Table, field

    class Row(Table):
        labels: Field[str] = field(name="label")

    pair: Pair[str, int]
    ```
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from kg_build_system.kernel.model.public.types import Struct

if TYPE_CHECKING:
    from .selection import Selection


class Pair[L, R](Struct):
    """Two values paired by position, in ``left`` and ``right`` order."""

    __slots__ = ()

    if TYPE_CHECKING:
        left: "Selection[L]"
        right: "Selection[R]"


__all__ = ["Pair"]
