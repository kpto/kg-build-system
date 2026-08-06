"""The physical evidence-release hierarchy used by this graph build."""

from kg_build_system import TableGroup, TableGroupOptions

from .contracts.association import AssociationTable
from .contracts.reference import DiseaseTable, TargetTable
from .contracts.study import StudyTable


class PharmacogenomicsTableGroup(TableGroup):
    """Evidence facts and their study provenance belong to one source product."""

    options = TableGroupOptions(members=(AssociationTable, StudyTable))


class ReferenceDataTableGroup(TableGroup):
    options = TableGroupOptions(members=(TargetTable, DiseaseTable))


class EvidenceRelease2025_06TableGroup(TableGroup):
    options = TableGroupOptions(members=(ReferenceDataTableGroup, PharmacogenomicsTableGroup))
