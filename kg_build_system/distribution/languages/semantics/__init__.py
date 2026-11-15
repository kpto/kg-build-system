"""The semantics language: purposes, claims and limitations.

A semantics value states the meaning of one declaration. A ``Purpose`` states
one expected use of the subject and owns the limitations that bound it. A
``Claim`` is a contextless assertion. The graph declaration's ``Semantics``
carries the root purpose; every other declaration may carry a local purpose that
narrows it.

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
    ```
"""
from __future__ import annotations

from .model.public import Claim, Limitation, Purpose, Semantics

__all__ = ["Claim", "Limitation", "Purpose", "Semantics"]
