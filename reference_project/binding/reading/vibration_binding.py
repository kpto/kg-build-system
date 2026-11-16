from kg_build_system import (
    BindingOptions, Limitation, Meaning, NodeValues, Purpose, node_binding,
    value_expression,
)

from reference_project.binding.common import provenance_stamps
from reference_project.relation.source.estate.readings.mechanical.vibration import (
    VibrationSourceRelation,
)
from reference_project.graph.reading import ReadingNode


vibration_reading_binding = node_binding(
    target=ReadingNode,
    rows=VibrationSourceRelation.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.reading_uid.alter_rows().drop_null(),
        properties=ReadingNode(
            value=row.mm_s,
            unit_of_measure=value_expression("mm/s"),
            recorded_on=row.recorded_on,
            summary=row.reading_uid.default_to("Unidentified sample"),
            **provenance_stamps,
        ),
    ),
    name="vibration_logger",
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil ReadingNode from the vibration feed: one sample gives one reading.",
                limitations=(
            Limitation(
                "The value and timestamp are carried when the logger reported them; no calibration is applied."
            ),
                ),
            ),
        ),
    ),
)
