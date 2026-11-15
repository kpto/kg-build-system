from kg_build_system import (
    BindingOptions, EdgeValues, Limitation, Meaning, Purpose, edge_binding,
    endpoint,
)

from reference_project.binding.common import relation_stamps
from reference_project.relation.derived.defects.relation import Defects
from reference_project.graph.defect.observed_during__survey_visit import ObservedDuringEdge
from reference_project.graph.survey import SurveyVisitNode


# The declaration's destination is concrete, so naming it here is optional. It
# is stated anyway because the endpoint token is how a binding documents which
# component a relation points at, and it becomes required the moment the
# declaration widens to the documented category.
#
# A defect or a visit that the feed left unlabelled anchors no relation, so those
# rows are dropped rather than pointed at a stand-in identity.
observed_during_binding = edge_binding(
    target=ObservedDuringEdge,
    target_node=endpoint(SurveyVisitNode),
    rows=Defects.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.defect_id.alter_rows().drop_null(),
        source_build_key=row.defect_id.alter_rows().drop_null(),
        target_build_key=row.survey_id,
        properties=ObservedDuringEdge(
            as_at=row.observed_on.default_to("Undated"),
            **relation_stamps,
        ),
    ),
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil ObservedDuringEdge from the Defects relation: the defect row carries the survey that reported it, so one row satisfies one observed-during relation.",
                limitations=(
            Limitation(
                "A defect or survey whose identifier is absent is excluded."
            ),
                ),
            ),
        ),
    ),
)
