"""The contract a published relation states: its definition and its meaning.

A relation is a contract. ``Definition`` states what one row is: the grain, as
authored text, and the identity, as the output names that distinguish rows.
``Meaning`` states what the relation is for: one purpose, contextless claims and
the limitations of that purpose. A ``Stage`` states a definition and no contract.

Example:
    ```python
    from kg_build_system.distribution.languages.data import (
        Claim, Contract, Definition, Meaning,
    )

    contract = Contract(
        definition=Definition(
            grain="One row per site in the register.",
            identity=("site_id",),
        ),
        meaning=Meaning(
            claims=(Claim("The register is the authority for the sites it lists."),),
        ),
    )
    ```
"""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.distribution.languages.meaning.model.public import Meaning


@dataclass(frozen=True, slots=True)
class Definition:
    """What one row of a relation is.

    ``grain`` is authored text: one row per what. ``identity`` names the outputs
    that distinguish one row from another; the names must be outputs of the
    declaring relation and are validated there.

    Example:
        ```python
        from kg_build_system.distribution.languages.data import Definition

        definition = Definition(
            grain="One row per site in the register.",
            identity=("site_id",),
        )
        ```
    """

    grain: str
    identity: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.grain, str) or not self.grain.strip():
            raise ValueError("definition grain must be non-empty text")
        identity = tuple(self.identity)
        if not identity:
            raise ValueError("definition identity must name at least one output")
        for name in identity:
            if not isinstance(name, str) or not name.strip():
                raise ValueError(
                    "definition identity names must be non-empty text"
                )
        if len(set(identity)) != len(identity):
            raise ValueError("definition identity names must be unique")
        object.__setattr__(self, "identity", identity)


@dataclass(frozen=True, slots=True)
class Contract:
    """The two halves of a published relation's promise.

    A contract is always complete: it carries both a definition and a meaning.
    ``DerivedRelationOptions`` requires one and requires the meaning to state a
    purpose; ``SourceRelationOptions`` accepts one when the relation is read
    directly by a binding.

    Example:
        ```python
        from kg_build_system.distribution.languages.data import (
            Claim, Contract, Definition, Meaning,
        )

        contract = Contract(
            definition=Definition(
                grain="One row per site in the register.",
                identity=("site_id",),
            ),
            meaning=Meaning(
                claims=(Claim("A site has one registered name."),),
            ),
        )
        ```
    """

    definition: Definition
    meaning: Meaning

    def __post_init__(self) -> None:
        if not isinstance(self.definition, Definition):
            raise TypeError(
                "a declared contract requires a Definition and a Meaning"
            )
        if not isinstance(self.meaning, Meaning):
            raise TypeError(
                "a declared contract requires a Definition and a Meaning"
            )


__all__ = ["Contract", "Definition"]
