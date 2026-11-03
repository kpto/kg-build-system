"""The ``kbs`` command surface.

The CLI is a program entry point, not a Python authoring interface. ``main`` is
the callable the console script invokes.

Example:
    ```python
    from kg_build_system.cli import main

    exit_code = main(["generate", "--help"])
    ```
"""
from __future__ import annotations


def main(argv: list[str] | None = None) -> int:
    """Run the ``kbs`` command line and return its exit code.

    Example:
        ```python
        from kg_build_system.cli import main

        main(["--help"])
        ```
    """
    from ..internal import main as implementation

    return implementation(argv)


__all__ = ["main"]
