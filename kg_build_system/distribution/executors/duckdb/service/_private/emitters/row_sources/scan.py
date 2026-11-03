"""A scan is supplied by the relation its table or projection already owns."""
from __future__ import annotations

from typing import TYPE_CHECKING

from kg_build_system.distribution.languages.table.model.internal.dto import RowScanDTO

if TYPE_CHECKING:
    from ..protocols import RowSourceEmissionContext


class ScanEmitter:
    node_type = RowScanDTO

    def emit(self, plan: object, context: RowSourceEmissionContext) -> str:
        raise ValueError("a scan is supplied by its table or projection relation")


__all__ = ["ScanEmitter"]
