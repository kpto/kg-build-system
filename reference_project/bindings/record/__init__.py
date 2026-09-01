from kg_build_system import node_binding, value_expression

from reference_project.table.complex_records import ComplexRecordsTable
from reference_project.topology.record import RecordNode


deep_city = (
    ComplexRecordsTable.profile
    .pick(lambda value: value.contact)
    .pick(lambda value: value.location)
    .pick(lambda value: value.city)
)

title = ComplexRecordsTable.title.default_to("Untitled")

record_binding = node_binding(
    target=RecordNode,
    build_key=ComplexRecordsTable.record_id.where_present().expression.prepend("record::"),
    properties=RecordNode(
        title=title,
        city=deep_city.default_to("Unknown city"),
        summary=title,
        source_version=value_expression("demo-v1"),
    ),
    debug_name="records_without_expansion",
)
