"""Author-facing generation error."""
from __future__ import annotations


class GenerationError(ValueError):
    """A source-located, actionable generation failure.

    It extends ``ValueError``; the message names the request file and line when
    the defect comes from discovery.

    Example:
        ```python
        from kg_build_system.generation.code_generation import GenerationError

        isinstance(GenerationError("contracts/__init__.py:4: invalid request"), ValueError)
        ```
    """


__all__ = ["GenerationError"]
