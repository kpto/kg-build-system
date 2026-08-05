"""The physical evidence-release hierarchy used by this graph build."""

from kg_build_system import include, table_group

from .contracts.association import Association
from .contracts.reference import DiseaseReference, TargetReference
from .contracts.study import Study


@table_group(name="pharmacogenomics")
class PharmacogenomicsEvidence:
    """Evidence facts and their study provenance belong to one source product."""

    association = include(Association)
    study = include(Study)


@table_group(name="reference_data")
class ReferenceData:
    target = include(TargetReference)
    disease = include(DiseaseReference)


@table_group(name="evidence_release_2025_06")
class EvidenceRelease:
    reference_data = include(ReferenceData)
    pharmacogenomics = include(PharmacogenomicsEvidence)
