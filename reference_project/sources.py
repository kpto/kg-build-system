"""Physical sources selected for the monitored-sites reference build."""

from pathlib import Path

from kg_build_system import DataSourceConfig, InputFormat, bind_source
from reference_project.table.monitored_sites import MonitoredSitesTable

DATA_FILE = Path(__file__).parent / "data" / "monitored_sites.json"

monitored_sites_source = bind_source(
    target=MonitoredSitesTable,
    config=DataSourceConfig(
        str(DATA_FILE),
        format=InputFormat.JSON,
        version="survey-2026-08",
    ),
)
