"""Shared fixtures for the backend test suite.

``tests/test_document.py`` holds the whole monitored-estate project as the schema's
acceptance test, and it is also the generator's golden input. Re-exporting its
fixture here lets every layer's tests edit, extend and re-validate that one document
rather than maintaining a second copy that could drift from it.
"""

from __future__ import annotations

from test_document import document  # noqa: F401  (pytest fixture, re-exported)

__all__ = ["document"]
