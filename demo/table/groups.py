"""The physical evidence-release hierarchy used by this graph build."""

from kg_build_system import include, table_group

from .contracts.association import AssociationTable
from .contracts.reference import DiseaseTable, TargetTable
from .contracts.study import StudyTable


@table_group()
class PharmacogenomicsTableGroup:
    """Evidence facts and their study provenance belong to one source product."""

    association = include(AssociationTable)
    study = include(StudyTable)


@table_group()
class ReferenceDataTableGroup:
    target = include(TargetTable)
    disease = include(DiseaseTable)


@table_group()
class EvidenceRelease2025_06TableGroup:
    reference_data = include(ReferenceDataTableGroup)
    pharmacogenomics = include(PharmacogenomicsTableGroup)
