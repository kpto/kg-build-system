from pathlib import Path

from kg_build_system import DataSourceConfig, InputFormat, bind_source
from kg_build_system.data.models import BoundSource

from .groups import EvidenceRelease2025_06TableGroup


DATA_DIRECTORY = Path(__file__).parents[1] / "data_files"


def demo_sources() -> tuple[BoundSource, ...]:
    """Bind an evidence release hierarchy and resolve each final resource address."""
    return (
        bind_source(
            target=EvidenceRelease2025_06TableGroup,
            config=DataSourceConfig(
                str(DATA_DIRECTORY),
                format=InputFormat.JSON,
                layout="{group_path}/{table_name}.json",
            ),
        ),
    )
