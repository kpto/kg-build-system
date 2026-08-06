"""Canonical value types and validation for build-system declarations."""
from __future__ import annotations

from types import UnionType
from typing import Any, get_args, get_origin

type Scalar = str | int | float | bool


_SCALARS = frozenset({str, int, float, bool})


def _optional(annotation: Any) -> tuple[Any, bool]:
    origin, arguments = get_origin(annotation), get_args(annotation)
    if origin in (UnionType,) or str(origin) == "typing.Union":
        non_null = tuple(argument for argument in arguments if argument is not type(None))
        if len(non_null) == 1 and len(non_null) != len(arguments):
            return non_null[0], True
    return annotation, False


def validate_value_type(annotation: Any, *, context: str, allow_collection: bool) -> None:
    """Reject annotations outside the portable scalar vocabulary."""
    if annotation is Any:
        raise TypeError(f"{context} must declare a supported type, not Any")
    base, _ = _optional(annotation)
    origin, arguments = get_origin(base), get_args(base)
    if origin is list:
        if not allow_collection:
            raise TypeError(f"{context} may not be a collection")
        if len(arguments) != 1:
            raise TypeError(f"{context} collection must declare one item type")
        item, _ = _optional(arguments[0])
        if item not in _SCALARS:
            raise TypeError(f"{context} collection items must be Scalar, not {item!r}")
        return
    if base not in _SCALARS:
        raise TypeError(f"{context} must be Scalar, Scalar | None, or list[Scalar | None], not {annotation!r}")


def validate_literal(value: Any) -> None:
    """Reject literal values that cannot be represented by the portable IR."""
    if value is None or type(value) in _SCALARS:
        return
    if isinstance(value, list) and all(item is None or type(item) in _SCALARS for item in value):
        return
    raise TypeError(f"literals must be Scalar, Scalar | None, or list[Scalar | None], not {value!r}")


__all__ = ["Scalar", "validate_literal", "validate_value_type"]
