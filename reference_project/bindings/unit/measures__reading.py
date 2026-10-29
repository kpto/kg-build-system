from kg_build_system import EdgeValues, edge_binding

from reference_project.bindings.common import relation_stamps
from reference_project.table.readings.mechanical.vibration import VibrationTable
from reference_project.table.readings.temperature import TemperatureTable
from reference_project.topology.unit.measures__reading import MeasuresEdge


temperature_measures_binding = edge_binding(
    target=MeasuresEdge,
    rows=TemperatureTable,
    bind=lambda row: EdgeValues(
        build_key=row.reading_uid.alter_rows().drop_null(),
        source_build_key=row.unit_ref.alter_rows().drop_null(),
        target_build_key=row.reading_uid.alter_rows().drop_null(),
        properties=MeasuresEdge(
            as_at=row.recorded_on,
            **relation_stamps,
        ),
    ),
    debug_name="temperature_measure",
)

vibration_measures_binding = edge_binding(
    target=MeasuresEdge,
    rows=VibrationTable,
    bind=lambda row: EdgeValues(
        build_key=row.reading_uid.alter_rows().drop_null(),
        source_build_key=row.unit_ref.alter_rows().drop_null(),
        target_build_key=row.reading_uid.alter_rows().drop_null(),
        properties=MeasuresEdge(
            as_at=row.recorded_on,
            **relation_stamps,
        ),
    ),
    debug_name="vibration_measure",
)
