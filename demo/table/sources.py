from pathlib import Path

from kg_build_system import DataSourceConfig, InputFormat, bind_source
from kg_build_system.table.models import BoundSource

from .groups import EvidenceRelease2025_06TableGroup


DATA_DIRECTORY = Path(__file__).parents[1] / "data"


evidence_release_source = bind_source(
    target=EvidenceRelease2025_06TableGroup,
    config=DataSourceConfig(
        str(DATA_DIRECTORY),
        format=InputFormat.JSON,
        layout="{group_path}/{table_name}.json",
    ),
)


def demo_sources() -> tuple[BoundSource, ...]:
    """Return the discoverable evidence release source binding."""
    return (
        evidence_release_source,
    )
