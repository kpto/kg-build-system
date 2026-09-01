from kg_build_system import edge_binding

from reference_project.bindings.common import relation_stamps
from reference_project.table.readings.mechanical.vibration import VibrationTable
from reference_project.table.readings.temperature import TemperatureTable
from reference_project.topology.unit.measures__reading import MeasuresEdge


temperature_measures_binding = edge_binding(
    target=MeasuresEdge,
    build_key=TemperatureTable.reading_uid.where_present(),
    source_build_key=TemperatureTable.unit_ref.where_present(),
    target_build_key=TemperatureTable.reading_uid.where_present(),
    properties=MeasuresEdge(
        as_at=TemperatureTable.recorded_on.default_to("Undated"),
        **relation_stamps,
    ),
    debug_name="temperature_measure",
)

vibration_measures_binding = edge_binding(
    target=MeasuresEdge,
    build_key=VibrationTable.reading_uid.where_present(),
    source_build_key=VibrationTable.unit_ref.where_present(),
    target_build_key=VibrationTable.reading_uid.where_present(),
    properties=MeasuresEdge(
        as_at=VibrationTable.recorded_on.default_to("Undated"),
        **relation_stamps,
    ),
    debug_name="vibration_measure",
)
