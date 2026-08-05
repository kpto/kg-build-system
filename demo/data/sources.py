from pathlib import Path

from kg_build_system import DataSourceConfig, InputFormat, bind_source
from kg_build_system.data.models import BoundTable

from .contracts.association import Association
from .contracts.study import Study


DATA_DIRECTORY = Path(__file__).parents[1] / "data_files"


def demo_sources() -> tuple[BoundTable, BoundTable]:
    """Bind concrete local fixtures without leaking source choices into declarations."""
    return (
        bind_source(
            target=Association,
            config=DataSourceConfig(str(DATA_DIRECTORY / "association.json"), format=InputFormat.JSON),
        ),
        bind_source(
            target=Study,
            config=DataSourceConfig(str(DATA_DIRECTORY / "studies.json"), format=InputFormat.JSON),
        ),
    )
