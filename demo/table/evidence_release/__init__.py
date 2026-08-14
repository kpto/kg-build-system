from kg_build_system import TableGroup, TableGroupOptions
from demo.table.evidence_release.pharmacogenomics import PharmacogenomicsTableGroup
from demo.table.evidence_release.reference_data import ReferenceDataTableGroup


class EvidenceReleaseTableGroup(TableGroup):
    options = TableGroupOptions(name='evidence_release')
    pharmacogenomics = PharmacogenomicsTableGroup
    reference_data = ReferenceDataTableGroup

__all__ = ['EvidenceReleaseTableGroup']
