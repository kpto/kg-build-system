from kg_build_system import (
    BindingOptions, Limitation, Meaning, NodeValues, Purpose, node_binding,
)

from reference_project.binding.common import provenance_stamps
from reference_project.relation.derived.observations.relation import Observations
from reference_project.graph.observation import ObservationNode


# An observation with no identifier names nothing, so those rows are dropped;
# default_to on a key would merge every unlabelled observation into one node.
# Its measurements stay and state what an absent one means, since an observation
# that recorded nothing is still an observation that was taken.
observation_binding = node_binding(
    target=ObservationNode,
    rows=Observations.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.observation_uid.alter_rows().drop_null(),
        properties=ObservationNode(
            value=row.value.default_to(0.0),
            method=row.observed_by.default_to("Unrecorded method"),
            observed_on=row.observed_on.default_to("Undated"),
            summary=row.observation_uid.alter_rows().drop_null(),
            **provenance_stamps,
        ),
    ),
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil ObservationNode from the Observations relation: one observation row gives the node's grain.",
                limitations=(
            Limitation(
                "Only the value, method and date the observation asserts are copied; the survey and defect keys stay on the relation."
            ),
                ),
            ),
        ),
    ),
)
