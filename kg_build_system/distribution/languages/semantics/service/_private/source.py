"""Render semantics values back to authoring source.

Text is written with ``repr`` so the generated source carries no interpreter and
no hand-escaped quoting. A fragment's body is the ``semantics=...`` keyword
argument another renderer embeds inside an options block; the expression helper
returns only the ``Semantics(...)`` value.
"""
from __future__ import annotations

from collections.abc import Iterable

from kg_build_system.kernel import SourceFragment

from ...model.internal.dto.semantics_dto import (
    ClaimDTO,
    LimitationDTO,
    PurposeDTO,
    SemanticsDTO,
)
from ...model.public.units import Claim, Purpose, Semantics

_IMPORT_ORDER = ("Claim", "Limitation", "Purpose", "Semantics")


def _indent(level: int) -> str:
    return " " * (4 * level)


def _claim_lines(
    claims: Iterable[Claim | ClaimDTO],
    level: int,
    names: set[str],
) -> list[str]:
    names.add("Claim")
    return [
        f"{_indent(level)}Claim({claim.text!r})," for claim in claims
    ]


def _purpose_lines(
    value: Purpose | PurposeDTO,
    level: int,
    names: set[str],
) -> list[str]:
    """Render ``Purpose(...)`` starting at ``level`` with no trailing comma."""
    names.add("Purpose")
    pad = _indent(level)
    if not value.limitations:
        return [f"{pad}Purpose({value.text!r})"]
    child = _indent(level + 1)
    names.add("Limitation")
    lines = [
        f"{pad}Purpose(",
        f"{child}{value.text!r},",
        f"{child}limitations=(",
    ]
    for limitation in value.limitations:
        lines.append(f"{_indent(level + 2)}Limitation({limitation.text!r}),")
    lines.append(f"{child}),")
    lines.append(f"{pad})")
    return lines


def _semantics_lines(
    value: Semantics | SemanticsDTO,
    level: int,
    names: set[str],
) -> list[str]:
    names.add("Semantics")
    pad = _indent(level)
    child_level = level + 1
    child = _indent(child_level)
    lines = [f"{pad}Semantics("]
    if value.purpose is not None:
        purpose = _purpose_lines(value.purpose, child_level, names)
        assert purpose[0].startswith(child)
        purpose[0] = f"{child}purpose={purpose[0][len(child):]}"
        purpose[-1] = f"{purpose[-1]},"
        lines.extend(purpose)
    if value.claims:
        lines.append(f"{child}claims=(")
        lines.extend(_claim_lines(value.claims, child_level + 1, names))
        lines.append(f"{child}),")
    lines.append(f"{pad})")
    return lines


def _imports(names: set[str]) -> tuple[str, ...]:
    if not names:
        return ()
    ordered = ", ".join(name for name in _IMPORT_ORDER if name in names)
    return (f"from kg_build_system import {ordered}",)


def render_semantics_expression(value: Semantics | SemanticsDTO) -> str:
    """Render only the ``Semantics(...)`` authoring expression."""
    names: set[str] = set()
    return "\n".join(_semantics_lines(value, 0, names))


def render_semantics(value: Semantics | SemanticsDTO) -> SourceFragment:
    """Render a declaration semantics value as an embeddable fragment.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics.model.public import (
            Claim, Semantics,
        )
        from kg_build_system.distribution.languages.semantics.service.internal import (
            render_semantics,
        )

        fragment = render_semantics(Semantics(claims=(Claim("A claim."),)))
        assert fragment.body.startswith("semantics=Semantics(")
        ```
    """
    names: set[str] = set()
    expression = "\n".join(_semantics_lines(value, 0, names))
    return SourceFragment("inline", f"semantics={expression}", _imports(names))


__all__ = ["render_semantics", "render_semantics_expression"]
