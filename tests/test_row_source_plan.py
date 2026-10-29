"""Row-source plans must not mistake a table field for the table itself."""
from __future__ import annotations

import unittest

from kg_build_system import Field, Table, TableOptions, field
from kg_build_system.compile.compiler import _row_source_plan
from kg_build_system.table.ir import RowScanIR


class SourceNamedTable(Table):
    options = TableOptions(name="source_named")
    source: Field[str | None] = field(name="source")
    identifier: Field[str | None] = field(name="identifier")


class RowSourcePlanTests(unittest.TestCase):
    def test_a_table_field_named_source_does_not_shadow_the_table(self) -> None:
        plan = _row_source_plan(SourceNamedTable.row_source())
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertIsInstance(plan, RowScanIR)
        self.assertEqual(plan.source, "source_named")


if __name__ == "__main__":
    unittest.main()
