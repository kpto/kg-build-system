"""A scan is supplied by the relation its table or projection already owns."""
from __future__ import annotations

from ....table.ir import RowScanIR
from ...protocols import RowSourceContext


class ScanLowerer:
    node_type = RowScanIR

    def lower(self, plan: object, context: RowSourceContext) -> str:
        raise ValueError("a scan is supplied by its table or projection relation")


__all__ = ["ScanLowerer"]
