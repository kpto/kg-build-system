"""The semantics units an author writes.

A semantics value is either the project's meaning root, ``GraphSemantics``, or a
declaration fragment, ``Semantics``. Claims are contextless statements. A
purpose is the expected use of the graph; frames scope the limitation space
within it, and limitations belong to a frame.

Example:
    ```python
    from kg_build_system.distribution.languages.semantics import (
        Claim, Frame, GraphSemantics, Limitation, Purpose, Semantics,
    )

    graph_semantics = GraphSemantics(
        claims=(Claim("The graph describes gene-disease associations."),),
        purpose=Purpose(
            text="Target prioritisation.",
            frames=(
                Frame(
                    text="Curated evidence only.",
                    limitations=(Limitation("No literature mining."),),
                ),
            ),
        ),
    )
    declaration_semantics = Semantics(
        claims=(Claim("Scores are per datatype."),),
    )
    ```
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Claim:
    """A contextless statement that holds regardless of purpose or frame.

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
    """What a reader must know given the purpose and frame.

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
class Frame:
    """The scope and boundary of the limitation space within the purpose.

    A frame owns its limitations. A declaration frame is read under the one
    graph purpose.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics import (
            Frame, Limitation,
        )

        frame = Frame(
            text="Curated evidence only.",
            limitations=(Limitation("No literature mining."),),
        )
        ```
    """

    text: str
    limitations: Sequence[Limitation] = ()

    def __post_init__(self) -> None:
        from ...service._private.validation import required_text, unit_tuple

        required_text(self.text, "a frame text")
        object.__setattr__(
            self,
            "limitations",
            unit_tuple(
                self.limitations, Limitation, "frame limitations",
            ),
        )


@dataclass(frozen=True, slots=True)
class Purpose:
    """The expected use of the graph. Exactly one exists per project.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics import (
            Frame, Limitation, Purpose,
        )

        purpose = Purpose(
            text="Target prioritisation.",
            frames=(
                Frame(
                    text="Curated evidence only.",
                    limitations=(Limitation("No literature mining."),),
                ),
            ),
        )
        ```
    """

    text: str
    frames: Sequence[Frame] = ()

    def __post_init__(self) -> None:
        from ...service._private.validation import required_text, unit_tuple

        required_text(self.text, "a purpose text")
        object.__setattr__(
            self,
            "frames",
            unit_tuple(self.frames, Frame, "purpose frames"),
        )


@dataclass(frozen=True, slots=True)
class Semantics:
    """A declaration semantics fragment under the graph purpose.

    A declaration fragment has no purpose of its own and must carry at least one
    claim or frame.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics import (
            Claim, Frame, Limitation, Semantics,
        )

        semantics = Semantics(
            claims=(Claim("Scores are per datatype."),),
            frames=(
                Frame(
                    text="Scored associations.",
                    limitations=(Limitation("Unscored evidence is absent."),),
                ),
            ),
        )
        ```
    """

    claims: Sequence[Claim] = ()
    frames: Sequence[Frame] = ()

    def __post_init__(self) -> None:
        from ...service._private.validation import unit_tuple

        object.__setattr__(
            self, "claims", unit_tuple(self.claims, Claim, "semantics claims"),
        )
        object.__setattr__(
            self, "frames", unit_tuple(self.frames, Frame, "semantics frames"),
        )
        if not self.claims and not self.frames:
            raise ValueError(
                "semantics requires at least one claim or frame"
            )


@dataclass(frozen=True, slots=True)
class GraphSemantics:
    """The project's meaning root: claims and exactly one purpose.

    ``purpose`` is required and keyword-only so it cannot be omitted while a
    declaration fragment's optional claims still default to an empty tuple.

    Example:
        ```python
        from kg_build_system.distribution.languages.semantics import (
            Claim, Frame, GraphSemantics, Limitation, Purpose,
        )

        semantics = GraphSemantics(
            claims=(Claim("The graph describes associations."),),
            purpose=Purpose(
                text="Target prioritisation.",
                frames=(
                    Frame(
                        text="Curated evidence only.",
                        limitations=(Limitation("No literature mining."),),
                    ),
                ),
            ),
        )
        ```
    """

    claims: Sequence[Claim] = ()
    purpose: Purpose = field(kw_only=True)

    def __post_init__(self) -> None:
        from ...service._private.validation import unit_tuple

        object.__setattr__(
            self,
            "claims",
            unit_tuple(self.claims, Claim, "graph semantics claims"),
        )
        if not isinstance(self.purpose, Purpose):
            raise TypeError("graph semantics purpose must be a Purpose")


def require_declaration_semantics(value: object, *, context: str = "semantics") -> None:
    """Reject a graph meaning root or a non-semantics attachment.

    A declaration attaches a ``Semantics`` fragment. ``GraphSemantics`` belongs
    to the graph declaration only. This helper is public so every language's
    authoring model applies the same rule without a local private helper.
    """
    if value is None:
        return
    if isinstance(value, GraphSemantics):
        raise TypeError(
            f"{context} must be a Semantics value, not GraphSemantics"
        )
    if not isinstance(value, Semantics):
        raise TypeError(f"{context} must be a Semantics value")


__all__ = [
    "Claim", "Frame", "GraphSemantics", "Limitation", "Purpose", "Semantics",
    "require_declaration_semantics",
]
