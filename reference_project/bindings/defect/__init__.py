from kg_build_system import NodeValues, node_binding

from reference_project.bindings.common import provenance_stamps
from reference_project.table.projections.defects import DefectProjection
from reference_project.topology.defect import DefectNode


# A surveyed defect with no identifier cannot be named, so those rows are
# dropped rather than given a synthetic identity: default_to here would collapse
# every unlabelled defect onto one node. The described properties keep the row
# and state the fallback, because a defect without a legible title is still the
# same defect.
defect_binding = node_binding(
    target=DefectNode,
    rows=DefectProjection,
    bind=lambda row: NodeValues(
        build_key=row.defect_id.alter_rows().drop_null(),
        properties=DefectNode(
            title=row.title.default_to("Untitled defect"),
            condition_rating=row.condition_rating.default_to("Unrated"),
            summary=row.title.default_to("Untitled defect"),
            **provenance_stamps,
        ),
    ),
)
