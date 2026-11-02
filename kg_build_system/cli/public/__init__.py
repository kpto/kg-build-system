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

from ..internal import main as _main


def main(argv: list[str] | None = None) -> int:
    """Run the ``kbs`` command line and return its exit code.

    Example:
        ```python
        from kg_build_system.cli import main

        main(["--help"])
        ```
    """
    return _main(argv)


__all__ = ["main"]
