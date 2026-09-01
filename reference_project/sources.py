"""Physical sources selected for the monitored-estate reference build."""

from pathlib import Path

from kg_build_system import DataSourceConfig, InputFormat, bind_source

from reference_project.table.equipment import EquipmentTable
from reference_project.table.readings import ReadingsTableGroup
from reference_project.table.sites import SitesTable
from reference_project.table.surveys import SurveysTable

DATA = Path(__file__).parent / "data"

sites_source = bind_source(
    target=SitesTable,
    config=DataSourceConfig(
        str(DATA / "sites.json"),
        format=InputFormat.JSON,
        version="registry-2026-08",
    ),
)

equipment_source = bind_source(
    target=EquipmentTable,
    config=DataSourceConfig(
        str(DATA / "equipment.json"),
        format=InputFormat.JSON,
        version="register-2026-08",
    ),
)

# One layout resolves every partition of the catalogue to its own file.
readings_source = bind_source(
    target=ReadingsTableGroup,
    config=DataSourceConfig(
        str(DATA),
        format=InputFormat.JSON,
        layout="{group_path}/{table_name}.json",
        version="telemetry-2026-08",
    ),
)

surveys_source = bind_source(
    target=SurveysTable,
    config=DataSourceConfig(
        str(DATA / "surveys.json"),
        format=InputFormat.JSON,
        version="survey-2026-08",
    ),
)
