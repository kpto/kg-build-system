"""Physical sources selected for the synthetic demo build."""

from pathlib import Path

from kg_build_system import DataSourceConfig, InputFormat, bind_source

from demo.table.complex_records import ComplexRecordsTable


DATA_FILE = Path(__file__).parents[1] / "data" / "complex_records.json"

complex_records_source = bind_source(
    target=ComplexRecordsTable,
    config=DataSourceConfig(
        str(DATA_FILE),
        format=InputFormat.JSON,
        version="demo-v1",
    ),
)
