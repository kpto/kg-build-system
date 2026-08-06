"""Reusable study-related data shapes.

The association input refers to a study, while the study input defines that
study. Both contracts share one logical identifier despite different physical
field names in their source files.
"""

from kg_build_system import Field, Struct, field


class StudyReferenceTemplate:
    study_id: Field[str] = field()


class StudyDetailsStruct(Struct):
    """Descriptive fields attached to a study."""
    name: Field[str] = field()
    description: Field[str | None] = field()
