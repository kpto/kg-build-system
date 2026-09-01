from kg_build_system import edge_binding, endpoint

from reference_project.bindings.common import relation_stamps
from reference_project.table.projections.defects import DefectProjection
from reference_project.topology.defect.observed_during__survey_visit import ObservedDuringEdge
from reference_project.topology.survey import SurveyVisitNode


# The declaration's destination is concrete, so naming it here is optional. It
# is stated anyway because the endpoint token is how a binding documents which
# component a relation points at, and it becomes required the moment the
# declaration widens to the documented category.
observed_during_binding = edge_binding(
    target=ObservedDuringEdge,
    target_node=endpoint(SurveyVisitNode),
    build_key=DefectProjection.defect_id,
    source_build_key=DefectProjection.defect_id,
    target_build_key=DefectProjection.survey_id,
    properties=ObservedDuringEdge(
        as_at=DefectProjection.observed_on,
        **relation_stamps,
    ),
)
