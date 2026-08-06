"""Canonical value types supported by build-system declarations.

These aliases define the portable scalar vocabulary. Declaration and expression
validation will consume them in subsequent changes.
"""

type Scalar = str | int | float | bool
type NullableScalar = Scalar | None
type Collection[T: Scalar | NullableScalar] = list[T]


__all__ = ["Collection", "NullableScalar", "Scalar"]
