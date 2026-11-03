"""Internal CLI composition; the implementation is private."""
from __future__ import annotations


def main(argv: list[str] | None = None) -> int:
    """Run the private CLI implementation."""
    from .._private.main import main as implementation

    return implementation(argv)


__all__ = ["main"]
