"""A second projection exercising projection-to-projection expressions."""

from kg_build_system import Projection, projection_field
from reference_project.table.projections.expanded_reading import ExpandedReadingProjection


class ReadingDisplayProjection(Projection):
    site_key = projection_field(
        ExpandedReadingProjection.site_id.expression.prepend("site::")
    )
    reading_key = projection_field(
        ExpandedReadingProjection.site_id.expression.prepend("reading::")
        .append("::")
        .append(ExpandedReadingProjection.zone_id.expression)
        .append("::")
        .append(ExpandedReadingProjection.unit_id.expression)
        .append("::")
        .append(ExpandedReadingProjection.reading_code.expression)
    )
    name = projection_field(
        ExpandedReadingProjection.zone_name.expression.append(" / ").append(
            ExpandedReadingProjection.reading_code.expression
        )
    )
    calibrated_value = projection_field(
        ExpandedReadingProjection.reading_value.expression.add(1.5).sub(0.5)
    )
    out_of_service = projection_field(
        ExpandedReadingProjection.in_service.expression.not_()
    )
    city = projection_field(ExpandedReadingProjection.city)
    remarks = projection_field(ExpandedReadingProjection.remarks)
