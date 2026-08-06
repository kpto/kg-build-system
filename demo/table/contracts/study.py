from kg_build_system import Field, Table, field

from demo.table.templates.study import StudyDetailsStruct, StudyReferenceTemplate


class StudyTable(StudyReferenceTemplate, Table):
    """Concrete study input with the shared ID mapped to its source-specific name."""

    study_id: Field[str] = field(name="id")
    details: Field[StudyDetailsStruct] = field()
