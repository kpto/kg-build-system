"""Reusable study-related data shapes.

The association input refers to a study, while the study input defines that
study. Both contracts share one logical identifier despite different physical
field names in their source files.
"""

from kg_build_system import Field, field, struct, table_template


@table_template(description="A stable logical reference to a study or evidence provenance record.")
class StudyReferenceTemplate:
    study_id: Field[str] = field()


@struct(description="Descriptive fields attached to a study.")
class StudyDetailsStruct:
    name: Field[str] = field()
    description: Field[str | None] = field()
