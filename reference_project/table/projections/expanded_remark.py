"""Expand each reading's remarks into one remark row of its own."""

from kg_build_system import Projection, projection_field
from reference_project.table.projections.reading_display import ReadingDisplayProjection


class ExpandedRemarkProjection(Projection):
    reading_key = projection_field(ReadingDisplayProjection.reading_key)
    remark = projection_field(ReadingDisplayProjection.remarks.expand())
    city = projection_field(ReadingDisplayProjection.city)
