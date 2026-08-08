from pathlib import Path

from kg_build_system import DataSourceConfig, InputFormat, bind_source

from .evidence_release import EvidenceReleaseTableGroup

DATA_DIRECTORY = Path(__file__).parents[1] / "data"


evidence_release_source = bind_source(
    target=EvidenceReleaseTableGroup,
    config=DataSourceConfig(
        str(DATA_DIRECTORY),
        format=InputFormat.JSON,
        layout="{group_path}/{table_name}.json",
    ),
)
