from kg_build_system import TableGroup, TableGroupOptions
from demo.table.evidence_release.pharmacogenomics.association import AssociationTable
from demo.table.evidence_release.pharmacogenomics.study import StudyTable


class PharmacogenomicsTableGroup(TableGroup):
    options = TableGroupOptions(name='pharmacogenomics')
    association = AssociationTable
    study = StudyTable

__all__ = ['PharmacogenomicsTableGroup']
