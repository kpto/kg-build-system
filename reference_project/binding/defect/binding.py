from kg_build_system import (
    BindingOptions, Limitation, Meaning, NodeValues, Purpose, node_binding,
)

from reference_project.binding.common import provenance_stamps
from reference_project.relation.derived.defects.relation import Defects
from reference_project.graph.defect import DefectNode


# A surveyed defect with no identifier cannot be named, so those rows are
# dropped rather than given a synthetic identity: default_to here would collapse
# every unlabelled defect onto one node. The described properties keep the row
# and state the fallback, because a defect without a legible title is still the
# same defect.
defect_binding = node_binding(
    target=DefectNode,
    rows=Defects.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.defect_id.alter_rows().drop_null(),
        properties=DefectNode(
            title=row.title.default_to("Untitled defect"),
            condition_rating=row.condition_rating.default_to("Unrated"),
            summary=row.title.default_to("Untitled defect"),
            **provenance_stamps,
        ),
    ),
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil DefectNode from the Defects relation: one defect row gives the node's grain, so the binding selects the properties the node asserts.",
                limitations=(
            Limitation(
                "The node does not carry the survey timestamp or unit reference; those stay on the edge and the relation."
            ),
                ),
            ),
        ),
    ),
)
