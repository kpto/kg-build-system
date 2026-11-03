"""Private instruction emission mechanisms.

The emitter protocol and instruction kinds stay in ``model.internal`` and
``service.internal.instruction``; the DuckDB and Python implementations live
here.
"""
from __future__ import annotations
