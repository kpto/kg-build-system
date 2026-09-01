from kg_build_system import edge_binding
from reference_project.bindings.common import relation_stamps
from reference_project.table.projections.reading_display import ReadingDisplayProjection
from reference_project.topology.site.has_reading__reading import HasReadingEdge

has_reading_binding = edge_binding(
    target=HasReadingEdge,
    build_key=ReadingDisplayProjection.reading_key.expression.prepend("has-reading::"),
    source_build_key=ReadingDisplayProjection.site_key,
    target_build_key=ReadingDisplayProjection.reading_key,
    properties=HasReadingEdge(
        city=ReadingDisplayProjection.city,
        **relation_stamps,
    ),
    debug_name="site_has_reading",
)
