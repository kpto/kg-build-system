"""The single authoring selection type and its gated row-effect handles.

``Selection[T]`` is the only authoring class. Presence is a type argument:
``NullableSelection[T]`` is the alias ``Selection[Nullable[T]]``. Overloads on
``self`` narrow the result and hide operations that are not valid for the
current value shape. The compiler expression tree stays private.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast, overload

from kg_build_system.distribution.model.public.refs import RelationRef
from kg_build_system.kernel.model.public.types import (
    Array,
    ArrayType,
    LogicalType,
    Nullable,
    NullableType,
    Shape,
    Struct,
)

from .pair import Pair

if TYPE_CHECKING:
    from ..internal.model import ExpressionNode, SelectedMember
    from .selections.effects import (
        ArrayRowEffects, NullableArrayRowEffects, NullableRowEffects,
        RowEffects,
    )


class Selection[T]:
    """The single authoring type: value algebra and expression algebra."""

    __slots__ = ("_member", "_node")

    def __init__(
        self,
        node: "ExpressionNode | None" = None,
        *,
        member: "SelectedMember | None" = None,
    ) -> None:
        if (node is None) == (member is None):
            raise TypeError(
                "a selection requires exactly one expression or selected member"
            )
        self._node = node
        self._member = member

    @property
    def logical_type(self) -> LogicalType:
        """The canonical logical type of the selected position.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            assert Row.name.logical_type.name == "str"
            ```
        """
        node = self._node
        if node is not None:
            return node.logical_type
        member = cast("SelectedMember", self._member)
        return member.logical_type

    # ------------------------------------------------------------ row effects

    @overload
    def alter_rows[N](self: Selection[Nullable[Array[N]]]) -> "NullableArrayRowEffects[N]": ...
    @overload
    def alter_rows[N](self: Selection[Nullable[N]]) -> "NullableRowEffects[N]": ...
    @overload
    def alter_rows[N](self: Selection[Array[N]]) -> "ArrayRowEffects[N]": ...
    @overload
    def alter_rows(self) -> "RowEffects[Selection[T]]": ...
    def alter_rows(self) -> Any:
        """Return the one-shot handle for a row effect.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            selected = Row.name.alter_rows().drop_null()
            assert selected.logical_type.name == "str"
            ```
        """
        from .selections.effects import (
            ArrayRowEffects,
            NullableArrayRowEffects,
            NullableRowEffects,
            RowEffects,
        )

        logical_type = self.logical_type
        if isinstance(logical_type, NullableType):
            if isinstance(logical_type.value, ArrayType):
                return NullableArrayRowEffects[Any](self)
            return NullableRowEffects[Any](self)
        if isinstance(logical_type, ArrayType):
            return ArrayRowEffects[Any](self)
        return RowEffects[Any](self)

    # -------------------------------------------------------- struct navigation

    @overload
    def extract[S: Struct, U](
        self: Selection[S], selector: Callable[[S], Selection[U]],
    ) -> Selection[U]: ...
    @overload
    def extract[S: Struct, D](
        self: Selection[Nullable[S]],
        selector: Callable[[S], Selection[Nullable[D]]],
    ) -> Selection[Nullable[D]]: ...
    @overload
    def extract[S: Struct, U](
        self: Selection[Nullable[S]], selector: Callable[[S], Selection[U]],
    ) -> Selection[Nullable[U]]: ...
    def extract(self, selector: Callable[[Any], Selection[Any]]) -> Any:
        """Select one declared member, composing presence and owner kind.

        Example:
            ```python
            from kg_build_system import Field, Struct, Table, field

            class Detail(Struct):
                label: Field[str] = field(name="label")

            class Row(Table):
                detail: Field[Detail] = field(name="detail")

            assert Row.detail.extract(lambda value: value.label).logical_type.name == "str"
            ```
        """
        from ...service._private.selections import extract_member

        return extract_member(self, selector)

    # ------------------------------------------------- ungated array operations

    @overload
    def at[U](
        self: Selection[Array[Nullable[U]]], index: int | Selection[int],
    ) -> Selection[Nullable[U]]: ...
    @overload
    def at[U](
        self: Selection[Array[U]], index: int | Selection[int],
    ) -> Selection[Nullable[U]]: ...
    def at(self, index: int | Selection[int]) -> Any:
        """Index an array; an out-of-bounds index is a nullable result.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                tags: Field[Array[str]] = field(name="tags")

            assert Row.tags.at(0).logical_type.value.name == "str"
            ```
        """
        from ...service._private.selections import array_at

        return array_at(self, index)

    def slice[I](
        self: Selection[Array[I]],
        start: int | Selection[int],
        end: int | Selection[int],
    ) -> Selection[Array[I]]:
        """Keep an array range; item presence is unchanged.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                tags: Field[Array[str]] = field(name="tags")

            assert Row.tags.slice(0, 1).logical_type.name == "array"
            ```
        """
        from ...service._private.selections import array_slice

        return cast("Selection[Array[I]]", array_slice(self, start, end))

    def lookup[S: Shape](
        self,
        relation: type[S] | RelationRef,
        key: Selection[Any] | None = None,
        *,
        target_key: str | Selection[Any] | None = None,
    ) -> Selection[Nullable[Array[S]]]:
        """Read every target record whose key equals this row's key.

        The result is a value: an array of target records, or null when no
        target matches. A null key never matches. Row behaviour is composed
        from the result:

        - left: use the lookup value as it is;
        - inner: ``lookup(...).alter_rows().drop_null()``;
        - one row per match: ``lookup(...).alter_rows().expand()``.

        ``target_key`` defaults to the column name of a direct field key. Pass
        it explicitly when the target column has a different name.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Region(Table):
                region_id: Field[str] = field(name="region_id")

            class Site(Table):
                region_id: Field[str] = field(name="region_id")

            regions = Site.region_id.lookup(Region, Site.region_id)
            assert regions.logical_type.value.name == "array"
            ```
        """
        from ...service._private.lookup import lookup_value

        return cast(
            "Selection[Nullable[Array[S]]]",
            lookup_value(relation, self if key is None else key, target_key=target_key),
        )

    @overload
    def zip[L, R](
        self: Selection[Array[L]], other: Selection[Array[R]],
    ) -> Selection[Array[Pair[L, R]]]: ...
    @overload
    def zip[L, R](
        self: Selection[Nullable[Array[L]]], other: Selection[Array[R]],
    ) -> Selection[Nullable[Array[Pair[L, R]]]]: ...
    @overload
    def zip[L, R](
        self: Selection[Array[L]], other: Selection[Nullable[Array[R]]],
    ) -> Selection[Nullable[Array[Pair[L, R]]]]: ...
    @overload
    def zip[L, R](
        self: Selection[Nullable[Array[L]]],
        other: Selection[Nullable[Array[R]]],
    ) -> Selection[Nullable[Array[Pair[L, R]]]]: ...
    def zip(self, other: Any) -> Any:
        """Pair two arrays by position into an array of paired records.

        The arrays must have the same length; a mismatch raises at execution.
        An absent input makes the result absent. This is a value operation, not
        a row-level cross or zip.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                tags: Field[Array[str]] = field(name="tags")
                labels: Field[Array[str]] = field(name="labels")

            paired = (
                Row.tags.alter_rows().drop_null()
                .zip(Row.labels.alter_rows().drop_null())
            )
            assert paired.logical_type.value.name == "array"
            ```
        """
        from ...service._private.selections import zip_arrays

        return zip_arrays(self, other)

    def unique[I](self: Selection[Array[I]]) -> Selection[Array[I]]:
        """Deduplicate array items.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                tags: Field[Array[str]] = field(name="tags")

            assert Row.tags.unique().logical_type.name == "array"
            ```
        """
        from ...service._private.selections import array_operation

        return cast("Selection[Array[I]]", array_operation(self, "distinct"))

    def sort[I](self: Selection[Array[I]]) -> Selection[Array[I]]:
        """Sort array items ascending.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                tags: Field[Array[str]] = field(name="tags")

            assert Row.tags.sort().logical_type.name == "array"
            ```
        """
        from ...service._private.selections import array_operation

        return cast("Selection[Array[I]]", array_operation(self, "sort"))

    def concat(self: Selection[Array[str]], separator: str) -> Selection[str]:
        """Join an array of non-null strings into one string.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                tags: Field[Array[str]] = field(name="tags")

            assert Row.tags.concat(",").logical_type.name == "str"
            ```
        """
        from ...service._private.selections import array_concat

        return cast("Selection[str]", array_concat(self, separator))

    def transform_items[I, U](
        self: Selection[Array[I]],
        selector: Callable[[Selection[I]], Selection[U]],
    ) -> Selection[Array[U]]:
        """Map every item; the selector receives the item selection.

        Example:
            ```python
            from kg_build_system import Array, Field, Table, field

            class Row(Table):
                tags: Field[Array[str]] = field(name="tags")

            mapped = Row.tags.transform_items(lambda item: item.prepend("kg:"))
            assert mapped.logical_type.name == "array"
            ```
        """
        from ...service._private.selections import transform_items

        return cast("Selection[Array[U]]", transform_items(self, selector))

    def drop_null_items[I](
        self: Selection[Array[Nullable[I]]],
    ) -> Selection[Array[I]]:
        """Remove null items from an array.

        Example:
            ```python
            from kg_build_system import Array, Field, Nullable, Table, field

            class Row(Table):
                tags: Field[Array[Nullable[str]]] = field(name="tags")

            assert Row.tags.drop_null_items().logical_type.name == "array"
            ```
        """
        from ...service._private.selections import null_items_removed

        return cast("Selection[Array[I]]", null_items_removed(self))

    # -------------------------------------------------- present scalar algebra

    def prepend(self: Selection[str], value: str | Selection[str]) -> Selection[str]:
        """Prefix a present string.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            assert Row.name.prepend("kg:").logical_type.name == "str"
            ```
        """
        from ...service._private.selections import text_concat

        return cast("Selection[str]", text_concat(self, value, prepend=True))

    def append(self: Selection[str], value: str | Selection[str]) -> Selection[str]:
        """Suffix a present string.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            assert Row.name.append("!").logical_type.name == "str"
            ```
        """
        from ...service._private.selections import text_concat

        return cast("Selection[str]", text_concat(self, value, prepend=False))

    def replace(self: Selection[str], search: str, replacement: str) -> Selection[str]:
        """Replace every occurrence of ``search`` with ``replacement``.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            assert Row.name.replace("-", "_").logical_type.name == "str"
            ```
        """
        from ...service._private.selections import text_replace

        return cast("Selection[str]", text_replace(self, search, replacement))

    def equals(self: Selection[str], value: str | Selection[str]) -> Selection[bool]:
        """Compare a present string for equality.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            assert Row.name.equals("Depot").logical_type.name == "bool"
            ```
        """
        from ...service._private.selections import text_equals

        return cast("Selection[bool]", text_equals(self, value))

    def before_separator(
        self: Selection[str], separator: str, occurrence: int = 1,
        *, include_separator: bool = False,
    ) -> Selection[str]:
        """The text before the nth appearance of ``separator``.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            assert Row.name.before_separator("::").logical_type.name == "str"
            ```
        """
        from ...service._private.selections import separator_text

        return cast(
            "Selection[str]",
            separator_text(
                self, separator, occurrence, "before", include_separator,
            ),
        )

    def after_separator(
        self: Selection[str], separator: str, occurrence: int = 1,
        *, include_separator: bool = False,
    ) -> Selection[str]:
        """The text after the nth appearance of ``separator``.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            assert Row.name.after_separator("::").logical_type.name == "str"
            ```
        """
        from ...service._private.selections import separator_text

        return cast(
            "Selection[str]",
            separator_text(
                self, separator, occurrence, "after", include_separator,
            ),
        )

    @overload
    def add(self: Selection[int], other: int | Selection[int]) -> Selection[int]: ...
    @overload
    def add(self: Selection[float], other: float | Selection[float]) -> Selection[float]: ...
    def add(self, other: Any) -> Any:
        """Add another number of the same logical type.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                count: Field[int] = field(name="count")

            assert Row.count.add(1).logical_type.name == "int"
            ```
        """
        from ...service._private.selections import numeric_binary

        return numeric_binary(self, "add", other)

    @overload
    def sub(self: Selection[int], other: int | Selection[int]) -> Selection[int]: ...
    @overload
    def sub(self: Selection[float], other: float | Selection[float]) -> Selection[float]: ...
    def sub(self, other: Any) -> Any:
        """Subtract another number of the same logical type.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                count: Field[int] = field(name="count")

            assert Row.count.sub(1).logical_type.name == "int"
            ```
        """
        from ...service._private.selections import numeric_binary

        return numeric_binary(self, "subtract", other)

    def not_(self: Selection[bool]) -> Selection[bool]:
        """Negate a present Boolean.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                active: Field[bool] = field(name="active")

            assert Row.active.not_().logical_type.name == "bool"
            ```
        """
        from ...service._private.selections import boolean_unary

        return cast("Selection[bool]", boolean_unary(self, "not"))

    def and_(
        self: Selection[bool], other: bool | Selection[bool],
    ) -> Selection[bool]:
        """Combine two present Booleans with logical and.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                active: Field[bool] = field(name="active")

            assert Row.active.and_(True).logical_type.name == "bool"
            ```
        """
        from ...service._private.selections import boolean_binary

        return cast("Selection[bool]", boolean_binary(self, "and", other))

    def or_(
        self: Selection[bool], other: bool | Selection[bool],
    ) -> Selection[bool]:
        """Combine two present Booleans with logical or.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                active: Field[bool] = field(name="active")

            assert Row.active.or_(False).logical_type.name == "bool"
            ```
        """
        from ...service._private.selections import boolean_binary

        return cast("Selection[bool]", boolean_binary(self, "or", other))

    def to_string(self: Selection[T]) -> Selection[str]:
        """Render a present scalar as canonical text.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                count: Field[int] = field(name="count")

            assert Row.count.to_string().logical_type.name == "str"
            ```
        """
        from ...service._private.selections import scalar_to_string

        return cast("Selection[str]", scalar_to_string(self))

    def default_to[U](
        self: Selection[Nullable[U]], value: U | Selection[U],
    ) -> Selection[U]:
        """Replace an absent value with a fallback.

        Example:
            ```python
            from kg_build_system import Field, Table, field

            class Row(Table):
                name: Field[str] = field(name="name")

            assert Row.name.default_to("unknown").logical_type.name == "str"
            ```
        """
        from ...service._private.selections import default_to

        return cast("Selection[U]", default_to(self, value))


type NullableSelection[T] = Selection[Nullable[T]]
"""The nullable spelling of the single authoring type."""


__all__ = ["NullableSelection", "Selection"]
