from kg_build_system import Field, field, struct, table


@struct
class StudyDetails:
    name: Field[str] = field(name="name")


@table(name="study")
class Study:
    id: Field[str] = field(name="id")
    details: Field[StudyDetails] = field(name="details")
