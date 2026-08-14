from kg_build_system import node_binding

from demo.table.complex_records import ComplexRecordsTable
from demo.topology.nodes.record.record import RecordNode


deep_city = (
    ComplexRecordsTable.profile
    .pick(lambda value: value.contact)
    .pick(lambda value: value.location)
    .pick(lambda value: value.city)
)

record_binding = node_binding(
    target=RecordNode,
    build_key=ComplexRecordsTable.record_id.when_present().prepend("record::"),
    properties=RecordNode(
        title=ComplexRecordsTable.title.or_else("Untitled"),
        city=deep_city.or_else("Unknown city"),
    ),
    debug_name="records_without_expansion",
)
