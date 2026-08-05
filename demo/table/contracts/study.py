from kg_build_system import Field, field, table

from demo.table.templates.study import StudyDetailsStruct, StudyReferenceTemplate


@table()
class StudyTable(StudyReferenceTemplate):
    """Concrete study input with the shared ID mapped to its source-specific name."""

    study_id: Field[str] = field(name="id")
    details: Field[StudyDetailsStruct] = field()
