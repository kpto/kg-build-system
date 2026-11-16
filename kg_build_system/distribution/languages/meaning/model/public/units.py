"""The meaning units an author writes.

One meaning value, ``Meaning``, is attached to every declaration. An author who
states no meaning passes ``Omitted`` explicitly; there is no implicit absence.

A ``Purpose`` states one expected use of the subject and owns the limitations
that bound that use. A ``Claim`` is a contextless assertion about the subject and
never owns a limitation. The graph declaration's ``Meaning`` must carry a
purpose; every other declaration's purpose is optional and narrows the root.

Example:
    ```python
    from kg_build_system.distribution.languages.meaning import (
        Claim, Limitation, Purpose, Meaning,
    )

    root = Meaning(
        purpose=Purpose(
            text="Target prioritisation.",
            limitations=(Limitation("No literature mining."),),
        ),
        claims=(Claim("The graph describes gene-disease associations."),),
    )
    declaration = Meaning(
        purpose=Purpose(text="Use this node as the released target record."),
        claims=(Claim("Scores are per datatype."),),
    )
    ```
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Claim:
    """An authored, contextless assertion about the subject.

    A claim holds regardless of purpose and never owns a limitation.

    Example:
        ```python
        from kg_build_system.distribution.languages.meaning import Claim

        claim = Claim("The graph describes gene-disease associations.")
        ```
    """

    text: str

    def __post_init__(self) -> None:
        from ...service._private.validation import required_text

        required_text(self.text, "a claim text")


@dataclass(frozen=True, slots=True)
class Limitation:
    """What a purpose does not authorize.

    A limitation belongs inside a purpose; it is never attached to a declaration
    or a claim on its own.

    Example:
        ```python
        from kg_build_system.distribution.languages.meaning import Limitation

        limitation = Limitation("No literature mining.")
        ```
    """

    text: str

    def __post_init__(self) -> None:
        from ...service._private.validation import required_text

        required_text(self.text, "a limitation text")


@dataclass(frozen=True, slots=True)
class Purpose:
    """One expected use of the subject, owning the limitations of that use.

    A declaration carries at most one purpose. A local purpose is read under the
    graph purpose and must narrow it.

    Example:
        ```python
        from kg_build_system.distribution.languages.meaning import (
            Limitation, Purpose,
        )

        purpose = Purpose(
            text="Target prioritisation.",
            limitations=(Limitation("No literature mining."),),
        )
        ```
    """

    text: str
    limitations: Sequence[Limitation] = ()

    def __post_init__(self) -> None:
        from ...service._private.validation import required_text, unit_tuple

        required_text(self.text, "a purpose text")
        object.__setattr__(
            self,
            "limitations",
            unit_tuple(
                self.limitations, Limitation, "purpose limitations",
            ),
        )


class Omitted:
    """The author states no meaning for this declaration.

    ``Omitted`` is a marker, not a meaning: pass the class itself
    (``meaning=Omitted``). It is refused where a declaration cannot opt out: the
    graph declaration, a published contract and a binding.

    Example:
        ```python
        
        marker = Omitted
        assert marker is Omitted
        ```
    """


def is_omitted(value: object) -> bool:
    """Return whether ``value`` is the explicit no-meaning marker.

    Example:
        ```python
        from kg_build_system import Omitted, is_omitted

        assert is_omitted(Omitted)
        assert not is_omitted(None)
        ```
    """
    return value is Omitted


@dataclass(frozen=True, slots=True)
class Meaning:
    """The one meaning value attached to a declaration.

    A meaning value carries at most one purpose and any number of contextless
    claims. It must carry at least one of the two.

    Example:
        ```python
        from kg_build_system.distribution.languages.meaning import (
            Claim, Limitation, Purpose, Meaning,
        )

        meaning = Meaning(
            purpose=Purpose(
                text="Scored associations.",
                limitations=(Limitation("Unscored evidence is absent."),),
            ),
            claims=(Claim("Scores are per datatype."),),
        )
        ```
    """

    purpose: Purpose | None = None
    claims: Sequence[Claim] = ()

    def __post_init__(self) -> None:
        from ...service._private.validation import unit_tuple

        if self.purpose is not None and not isinstance(self.purpose, Purpose):
            raise TypeError("meaning purpose must be a Purpose")
        object.__setattr__(
            self, "claims", unit_tuple(self.claims, Claim, "meaning claims"),
        )
        if self.purpose is None and not self.claims:
            raise ValueError(
                "meaning requires at least one claim or purpose"
            )


def require_declaration_meaning(
    value: object, *, context: str = "meaning",
) -> Meaning | None:
    """Return the attached meaning, or ``None`` for the ``Omitted`` marker.

    This helper is public so every language's authoring model applies the same
    rule without a local private helper. A declaration must state either a
    ``Meaning`` or ``Omitted``; ``None`` is not an authoring value.

    Example:
        ```python
        from kg_build_system import Omitted, require_declaration_meaning

        assert require_declaration_meaning(Omitted) is None
        ```
    """
    if is_omitted(value):
        return None
    if not isinstance(value, Meaning):
        raise TypeError(
            f"{context} must be a Meaning value or the Omitted marker"
        )
    return value


__all__ = [
    "Claim", "Limitation", "Meaning", "Omitted", "Purpose", "is_omitted",
    "require_declaration_meaning",
]
