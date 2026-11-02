"""Nullability claims and value-shape wrapping."""
from __future__ import annotations

from ..ir import GeneratedNullableType, GeneratedType, Nullability
from .formats import SchemaTier


def describe_nullability(tier: SchemaTier, describe_reports_nullable: bool) -> Nullability:
    """Map ``DESCRIBE``'s ``null`` column according to the source tier.

    That column reports only *enforced* ``NOT NULL`` catalog constraints, so it
    is silent about what a file declares: a table-function scan answers ``YES``
    for every column whether or not the file marks it ``required``. Only an
    enforced store may therefore yield non-nullability here, and Parquet is
    overridden from ``parquet_schema()`` afterwards.
    """
    if tier != "enforced":
        return Nullability.DEFAULTED
    return Nullability.DEFAULTED if describe_reports_nullable else Nullability.ENFORCED


def level_nullability(repetition: str) -> Nullability:
    """The file's own word for one node: ``required`` is a claim, ``optional`` is not."""
    return Nullability.DECLARED if repetition.upper() == "REQUIRED" else Nullability.DEFAULTED


def wrap(value: GeneratedType, nullability: Nullability) -> GeneratedType:
    """Wrap a value in ``GeneratedNullableType`` when the claim is defaulted."""
    if nullability is Nullability.DEFAULTED and not isinstance(value, GeneratedNullableType):
        return GeneratedNullableType(value)
    return value


__all__ = ["describe_nullability", "level_nullability", "wrap"]
