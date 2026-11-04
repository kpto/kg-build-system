"""Internal wrapper over the private graph linker."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ...model.public import GraphBlueprint


def link_blueprint(
    languages: Sequence[Any], namespace: Any,
) -> GraphBlueprint:
    """Index languages, transcribe their declarations and assemble a blueprint."""
    from .._private.link import link_blueprint as implementation

    return implementation(languages, namespace)


__all__ = ["link_blueprint"]
