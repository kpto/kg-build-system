"""Hierarchical symbol keys.

A key is a tuple of string segments. A language chooses the segments; the
kernel only compares and descends them. The empty key is the root of a
language's key space.
"""
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase


@dataclass(frozen=True, slots=True)
class Key:
    """One hierarchical symbol identifier.

    ``Key(("site",))`` names a top-level symbol and
    ``Key(("site", "name"))`` names a child of it. Keys compare by their
    segments and are hashable, so they can index a symbol table.

    Example:
    ```python
    from kg_build_system.kernel import Key

    key = Key(("site",)).child("name")
    assert key.segments == ("site", "name")
    assert str(key) == "site/name"
    ```
    """

    segments: tuple[str, ...]

    def child(self, *segments: str) -> Key:
        """Return a key extended by ``segments``.

        Example:
        ```python
        key = Key(("site",)).child("name")
        assert key == Key(("site", "name"))
        ```
        """
        return Key(self.segments + tuple(segments))

    def starts_with(self, other: Key) -> bool:
        """Whether ``other`` is a prefix of this key.

        An empty key is a prefix of every key.

        Example:
        ```python
        assert Key(("site", "name")).starts_with(Key(("site",)))
        assert not Key(("site",)).starts_with(Key(("site", "name")))
        ```
        """
        return (
            len(other.segments) <= len(self.segments)
            and self.segments[: len(other.segments)] == other.segments
        )

    def matches(self, pattern: Key) -> bool:
        """Whether this key matches a pattern key.

        Each pattern segment is matched with ``fnmatchcase``; a final ``**``
        segment matches any remaining segments, including none. Without
        ``**`` the two keys must have the same length.

        Example:
        ```python
        assert Key(("site", "name")).matches(Key(("site", "*")))
        assert Key(("site", "name", "value")).matches(Key(("site", "**")))
        ```
        """
        own = self.segments
        expected = pattern.segments
        for index, segment in enumerate(expected):
            if segment == "**":
                return index == len(expected) - 1
            if index >= len(own) or not fnmatchcase(own[index], segment):
                return False
        return len(own) == len(expected)

    def to_document(self) -> list[str]:
        """Return the segments as a JSON-compatible list.

        Example:
        ```python
        assert Key(("site", "name")).to_document() == ["site", "name"]
        ```
        """
        return list(self.segments)

    def __str__(self) -> str:
        return "/".join(self.segments)


__all__ = ["Key"]
