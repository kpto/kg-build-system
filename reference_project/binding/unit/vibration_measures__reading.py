from kg_build_system import (
    BindingOptions, EdgeValues, Limitation, Meaning, Purpose, edge_binding,
)

from reference_project.binding.common import relation_stamps
from reference_project.graph.unit.measures__reading import MeasuresEdge
from reference_project.relation.source.estate.readings.mechanical.vibration import (
    VibrationSourceRelation,
)


vibration_measures_binding = edge_binding(
    target=MeasuresEdge,
    rows=VibrationSourceRelation.row_source(),
    bind=lambda row: EdgeValues(
        build_key=row.reading_uid.alter_rows().drop_null(),
        source_build_key=row.unit_ref.alter_rows().drop_null(),
        target_build_key=row.reading_uid.alter_rows().drop_null(),
        properties=MeasuresEdge(
            as_at=row.recorded_on,
            **relation_stamps,
        ),
    ),
    name="vibration_measure",
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil MeasuresEdge from the vibration feed: each sample names the unit and its own identifier, so one row satisfies one measures relation.",
                limitations=(
                    Limitation(
                        "Only the vibration feed is read here; a unit with no vibration sample has no edge from this binding."
                    ),
                ),
            ),
        ),
    ),
)
