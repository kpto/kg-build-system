"""Expand nullable notes from a materialised upstream projection."""

from kg_build_system import Projection, projection_field
from reference_project.table.projections.metric_display import MetricDisplayProjection


class ExpandedNoteProjection(Projection):
    metric_key = projection_field(MetricDisplayProjection.metric_key)
    note = projection_field(MetricDisplayProjection.notes.expand())
    city = projection_field(MetricDisplayProjection.city)
