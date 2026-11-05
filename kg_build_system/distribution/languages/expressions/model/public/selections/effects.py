"""One-shot row-effect handles for selections.

Example:
    ```python
    from kg_build_system import Array, Field, Table, field

    class Row(Table):
        tags: Field[Array[str]] = field(name="tags")

    assert Row.tags.alter_rows().expand() is not None
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from kg_build_system.kernel.model.public.types import Array, Nullable

from ..selection import NullableSelection, Selection
from ...internal.model.selection import RowEffectHandle



class RowEffects[S](RowEffectHandle):
    """Effects valid on every present selection: ``drop_if`` only."""

    def drop_if(self, predicate: Callable[[S], "Selection[bool]"]) -> S:
        """Drop rows whose predicate is not true; the type does not refine.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            selected = Row.name.alter_rows().drop_if(
                lambda value: value.equals("a")
            )
            assert selected.logical_type.name == "str"
            ```
        """
        from ....service._private.selections import drop_if_rows

        return cast(S, drop_if_rows(self.consume(), predicate))


class NullableRowEffects[N](RowEffects["Selection[Nullable[N]]"]):
    """Effects valid on a present-or-absent scalar: ``drop_null`` and ``drop_if``."""

    def drop_null(self) -> "Selection[N]":
        """Drop rows whose value is null and return the present selection.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            selected = Row.name.alter_rows().drop_null()
            assert selected.logical_type.name == "str"
            ```
        """
        from ....service._private.selections import drop_null_rows

        return cast("Selection[N]", drop_null_rows(self.consume()))

    def drop_if(
        self, predicate: Callable[[Selection[Nullable[N]]], Selection[bool]],
    ) -> "Selection[Nullable[N]]":
        """Drop rows whose predicate is not true; presence is preserved.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            selected = Row.name.alter_rows().drop_if(
                lambda value: value.equals("a")
            )
            assert selected.logical_type.value.name == "str"
            ```
        """
        from ....service._private.selections import drop_if_rows

        return cast(
            "Selection[Nullable[N]]",
            drop_if_rows(self.consume(), predicate),
        )


class ArrayRowEffects[I](RowEffects["Selection[Array[I]]"]):
    """Effects valid on a present array: ``expand`` and ``drop_if``."""

    def expand(self) -> "Selection[I]":
        """Explode the array into one row per item.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                tags: Field[Array[str]] = field(name="tags")

            expanded = Row.tags.alter_rows().expand()
            assert expanded.logical_type.name == "str"
            ```
        """
        from ....service._private.selections import expand_rows

        return cast("Selection[I]", expand_rows(self.consume()))

    def drop_if(
        self, predicate: Callable[[Selection[Array[I]]], Selection[bool]],
    ) -> "Selection[Array[I]]":
        """Drop rows whose predicate is not true; the array type is preserved.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                tags: Field[Array[str]] = field(name="tags")

            selected = Row.tags.alter_rows().drop_if(
                lambda value: value.unique().at(0).equals("a")
            )
            assert selected.logical_type.name == "array"
            ```
        """
        from ....service._private.selections import drop_if_rows

        return cast(
            "Selection[Array[I]]", drop_if_rows(self.consume(), predicate),
        )


class NullableArrayRowEffects[I](NullableRowEffects[Array[I]]):
    """Effects valid on a present-or-absent array: ``drop_null``, ``expand``, ``drop_if``."""

    def expand(self) -> "Selection[I]":
        """Explode the array; an absent or empty array produces no rows.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                tags: Field[Array[str]] = field(name="tags")

            expanded = Row.tags.alter_rows().expand()
            assert expanded.logical_type.name == "str"
            ```
        """
        from ....service._private.selections import expand_rows

        return cast("Selection[I]", expand_rows(self.consume()))

    def drop_if(
        self,
        predicate: Callable[[Selection[Nullable[Array[I]]]], Selection[bool]],
    ) -> "Selection[Nullable[Array[I]]]":
        """Drop rows whose predicate is not true; presence is preserved.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                tags: Field[Array[str]] = field(name="tags")

            selected = Row.tags.alter_rows().drop_if(
                lambda value: value.unique().at(0).equals("a")
            )
            assert selected.logical_type.value.name == "array"
            ```
        """
        from ....service._private.selections import drop_if_rows

        return cast(
            "Selection[Nullable[Array[I]]]",
            drop_if_rows(self.consume(), predicate),
        )


__all__ = [
    "ArrayRowEffects", "NullableArrayRowEffects", "NullableRowEffects",
    "RowEffects",
]
