"""The semantics units an author writes.

One meaning value, ``Semantics``, is attached to every declaration.

A ``Purpose`` states one expected use of the subject and owns the limitations
that bound that use. A ``Claim`` is a contextless assertion about the subject and
never owns a limitation. The graph declaration's ``Semantics`` must carry a
purpose; every other declaration's purpose is optional and narrows the root.

Example:
    ```python
    from kg_build_system.distribution.languages.semantics import (
        Claim, Limitation, Purpose, Semantics,
    )

    root = Semantics(
        purpose=Purpose(
            text="Target prioritisation.",
            limitations=(Limitation("No literature mining."),),
        ),
        claims=(Claim("The graph describes gene-disease associations."),),
    )
    declaration = Semantics(
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
        from kg_build_system.distribution.languages.semantics import Claim

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
        from kg_build_system.distribution.languages.semantics import Limitation

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
        from kg_build_system.distribution.languages.semantics import (
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


@dataclass(frozen=True, slots=True)
class Semantics:
    """The one meaning value attached to a declaration.

    A semantics value carries at most one purpose and any number of contextless
    claims. It must carry at least one of the two.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics import (
            Claim, Limitation, Purpose, Semantics,
        )

        semantics = Semantics(
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
            raise TypeError("semantics purpose must be a Purpose")
        object.__setattr__(
            self, "claims", unit_tuple(self.claims, Claim, "semantics claims"),
        )
        if self.purpose is None and not self.claims:
            raise ValueError(
                "semantics requires at least one claim or purpose"
            )


def require_declaration_semantics(value: object, *, context: str = "semantics") -> None:
    """Reject a value that is not a ``Semantics`` attachment.

    This helper is public so every language's authoring model applies the same
    rule without a local private helper.
    """
    if value is None:
        return
    if not isinstance(value, Semantics):
        raise TypeError(f"{context} must be a Semantics value")


__all__ = [
    "Claim", "Limitation", "Purpose", "Semantics",
    "require_declaration_semantics",
]
