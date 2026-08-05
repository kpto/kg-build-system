from kg_build_system import Field, field, table

from demo.data.templates.study import StudyDetails, StudyReference


@table(name="study")
class Study(StudyReference):
    """Concrete study input with the shared ID mapped to its source-specific name."""

    study_id: Field[str] = field(name="id")
    details: Field[StudyDetails] = field(name="details")
