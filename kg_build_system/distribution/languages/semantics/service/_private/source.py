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
    FrameDTO,
    GraphSemanticsDTO,
    LimitationDTO,
    PurposeDTO,
    SemanticsDTO,
)
from ...model.public.units import (
    Claim,
    Frame,
    GraphSemantics,
    Limitation,
    Purpose,
    Semantics,
)

_IMPORT_ORDER = (
    "Claim", "Frame", "Limitation", "Purpose", "Semantics", "GraphSemantics",
)


def _indent(level: int) -> str:
    return " " * (4 * level)


def _unit_line(
    value: Claim | Limitation | ClaimDTO | LimitationDTO,
    level: int,
    names: set[str],
) -> list[str]:
    if isinstance(value, (Claim, ClaimDTO)):
        names.add("Claim")
        return [f"{_indent(level)}Claim({value.text!r}),"]
    names.add("Limitation")
    return [f"{_indent(level)}Limitation({value.text!r}),"]


def _claims_field(
    claims: Iterable[Claim | ClaimDTO],
    level: int,
    names: set[str],
) -> list[str]:
    lines = [f"{_indent(level)}claims=("]
    for claim in claims:
        lines.extend(_unit_line(claim, level + 1, names))
    lines.append(f"{_indent(level)}),")
    return lines


def _frames_field(
    frames: Iterable[Frame | FrameDTO],
    level: int,
    names: set[str],
) -> list[str]:
    lines = [f"{_indent(level)}frames=("]
    for frame in frames:
        frame_lines = _frame_lines(frame, level + 1, names)
        frame_lines[-1] = f"{frame_lines[-1]},"
        lines.extend(frame_lines)
    lines.append(f"{_indent(level)}),")
    return lines


def _frame_lines(
    value: Frame | FrameDTO,
    level: int,
    names: set[str],
) -> list[str]:
    names.add("Frame")
    pad = _indent(level)
    if not value.limitations:
        return [f"{pad}Frame({value.text!r})"]
    child = _indent(level + 1)
    lines = [
        f"{pad}Frame(",
        f"{child}{value.text!r},",
        f"{child}limitations=(",
    ]
    for limitation in value.limitations:
        lines.extend(_unit_line(limitation, level + 2, names))
    lines.append(f"{child}),")
    lines.append(f"{pad})")
    return lines


def _purpose_lines(
    value: Purpose | PurposeDTO,
    level: int,
    names: set[str],
) -> list[str]:
    names.add("Purpose")
    pad = _indent(level)
    if not value.frames:
        return [f"{pad}Purpose({value.text!r})"]
    child = _indent(level + 1)
    lines = [
        f"{pad}Purpose(",
        f"{child}{value.text!r},",
        f"{child}frames=(",
    ]
    for frame in value.frames:
        frame_lines = _frame_lines(frame, level + 2, names)
        frame_lines[-1] = f"{frame_lines[-1]},"
        lines.extend(frame_lines)
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
    lines = [f"{pad}Semantics("]
    if value.claims:
        lines.extend(_claims_field(value.claims, level + 1, names))
    if value.frames:
        lines.extend(_frames_field(value.frames, level + 1, names))
    lines.append(f"{pad})")
    return lines


def _graph_semantics_lines(
    value: GraphSemantics | GraphSemanticsDTO,
    level: int,
    names: set[str],
) -> list[str]:
    names.add("GraphSemantics")
    pad = _indent(level)
    lines = [f"{pad}GraphSemantics("]
    if value.claims:
        lines.extend(_claims_field(value.claims, level + 1, names))
    purpose = _purpose_lines(value.purpose, 0, names)
    purpose_pad = _indent(level + 1)
    lines.append(f"{purpose_pad}purpose={purpose[0]}")
    lines.extend(f"{purpose_pad}{line}" for line in purpose[1:])
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


def render_graph_semantics(
    value: GraphSemantics | GraphSemanticsDTO,
) -> SourceFragment:
    """Render a graph semantics value as an embeddable fragment.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics.model.public import (
            GraphSemantics, Purpose,
        )
        from kg_build_system.distribution.languages.semantics.service.internal import (
            render_graph_semantics,
        )

        fragment = render_graph_semantics(
            GraphSemantics(purpose=Purpose("A purpose.")),
        )
        assert fragment.body.startswith("semantics=GraphSemantics(")
        ```
    """
    names: set[str] = set()
    expression = "\n".join(_graph_semantics_lines(value, 0, names))
    return SourceFragment("inline", f"semantics={expression}", _imports(names))


__all__ = [
    "render_graph_semantics", "render_semantics",
    "render_semantics_expression",
]
