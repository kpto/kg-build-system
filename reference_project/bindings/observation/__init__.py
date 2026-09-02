from kg_build_system import node_binding

from reference_project.bindings.common import provenance_stamps
from reference_project.table.projections.observations import ObservationProjection
from reference_project.topology.observation import ObservationNode


# An observation with no identifier names nothing, so those rows are dropped;
# default_to on a key would merge every unlabelled observation into one node.
# Its measurements stay and state what an absent one means, since an observation
# that recorded nothing is still an observation that was taken.
observation_binding = node_binding(
    target=ObservationNode,
    build_key=ObservationProjection.observation_uid.where_present(),
    properties=ObservationNode(
        value=ObservationProjection.value.default_to(0.0),
        method=ObservationProjection.observed_by.default_to("Unrecorded method"),
        observed_on=ObservationProjection.observed_on.default_to("Undated"),
        summary=ObservationProjection.observation_uid.where_present(),
        **provenance_stamps,
    ),
)
