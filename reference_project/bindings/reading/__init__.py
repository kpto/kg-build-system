from kg_build_system import node_binding, value_expression

from reference_project.bindings.common import provenance_stamps
from reference_project.table.readings.mechanical.vibration import VibrationTable
from reference_project.table.readings.temperature import TemperatureTable
from reference_project.topology.reading import ReadingNode


# Two logger families feed one measurement entity. Each binding owns its own row
# context, and core aggregates the results, so the graph gets a single reading
# node from two producers without either knowing about the other.
temperature_reading_binding = node_binding(
    target=ReadingNode,
    build_key=TemperatureTable.reading_uid.where_present(),
    properties=ReadingNode(
        value=TemperatureTable.deg_c,
        unit_of_measure=value_expression("degC"),
        # A timestamp has no honest sentinel, so a sample the logger left
        # undated carries no date rather than the text a string property used.
        recorded_on=TemperatureTable.recorded_on,
        summary=TemperatureTable.reading_uid.default_to("Unidentified sample"),
        **provenance_stamps,
    ),
    debug_name="temperature_logger",
)

vibration_reading_binding = node_binding(
    target=ReadingNode,
    build_key=VibrationTable.reading_uid.where_present(),
    properties=ReadingNode(
        value=VibrationTable.mm_s,
        unit_of_measure=value_expression("mm/s"),
        recorded_on=VibrationTable.recorded_on,
        summary=VibrationTable.reading_uid.default_to("Unidentified sample"),
        **provenance_stamps,
    ),
    debug_name="vibration_logger",
)
