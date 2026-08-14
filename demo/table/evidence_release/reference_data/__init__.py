from kg_build_system import TableGroup, TableGroupOptions
from demo.table.evidence_release.reference_data.disease import DiseaseTable
from demo.table.evidence_release.reference_data.target import TargetTable


class ReferenceDataTableGroup(TableGroup):
    options = TableGroupOptions(name='reference_data')
    disease = DiseaseTable
    target = TargetTable

__all__ = ['ReferenceDataTableGroup']
