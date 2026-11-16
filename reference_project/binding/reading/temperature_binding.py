from kg_build_system import (
    BindingOptions, Limitation, Meaning, NodeValues, Purpose, node_binding,
    value_expression,
)

from reference_project.binding.common import provenance_stamps
from reference_project.relation.source.estate.readings.temperature import (
    TemperatureSourceRelation,
)
from reference_project.graph.reading import ReadingNode


# One logger family feeds the shared measurement entity. Core aggregates the
# producers, so the graph gets one reading node without either binding knowing
# about the other.
temperature_reading_binding = node_binding(
    target=ReadingNode,
    rows=TemperatureSourceRelation.row_source(),
    bind=lambda row: NodeValues(
        build_key=row.reading_uid.alter_rows().drop_null(),
        properties=ReadingNode(
            value=row.deg_c,
            unit_of_measure=value_expression("degC"),
            # A timestamp has no honest sentinel, so an undated sample carries no
            # date rather than the text a string property used.
            recorded_on=row.recorded_on,
            summary=row.reading_uid.default_to("Unidentified sample"),
            **provenance_stamps,
        ),
    ),
    name="temperature_logger",
    options=BindingOptions(
        meaning=Meaning(
            purpose=Purpose(
                "Fulfil ReadingNode from the temperature feed: one sample gives one reading.",
                limitations=(
            Limitation(
                "The value and timestamp are carried when the logger reported them; no calibration is applied."
            ),
                ),
            ),
        ),
    ),
)
