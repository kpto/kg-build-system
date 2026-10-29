from kg_build_system import NodeValues, node_binding, value_expression

from reference_project.bindings.common import provenance_stamps
from reference_project.table.readings.mechanical.vibration import VibrationTable
from reference_project.table.readings.temperature import TemperatureTable
from reference_project.topology.reading import ReadingNode


# Two logger families feed one measurement entity. Each binding owns its own row
# context, and core aggregates the results, so the graph gets a single reading
# node from two producers without either knowing about the other.
temperature_reading_binding = node_binding(
    target=ReadingNode,
    rows=TemperatureTable,
    bind=lambda row: NodeValues(
        build_key=row.reading_uid.alter_rows().drop_null(),
        properties=ReadingNode(
            value=row.deg_c,
            unit_of_measure=value_expression("degC"),
            # A timestamp has no honest sentinel, so a sample the logger left
            # undated carries no date rather than the text a string property used.
            recorded_on=row.recorded_on,
            summary=row.reading_uid.default_to("Unidentified sample"),
            **provenance_stamps,
        ),
    ),
    debug_name="temperature_logger",
)

vibration_reading_binding = node_binding(
    target=ReadingNode,
    rows=VibrationTable,
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
    debug_name="vibration_logger",
)
