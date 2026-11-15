"""The logical asset behind the monitored-estate reference build."""

from pathlib import Path

from kg_build_system import (
    Asset,
    AssetAuthority,
    AssetLayout,
    AssetOptions,
    AssetProfile,
)
from kg_build_system.generation import AssetGenerationOptions, asset_generation
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)

DATA = Path(__file__).parent.parent / "data"


@asset_generation(
    AssetGenerationOptions(
        provider=InferDataContractProvider,
        configuration=DataContractInferenceConfig(
            mode="source_relation_group",
            layout="files",
            # ``surveyed_on`` and ``recorded_on`` hold ``YYYY-MM-DDTHH:MM``
            # without seconds, which ``read_json_auto`` sniffs as VARCHAR rather
            # than TIMESTAMP. Overrides are keyed by the column's full
            # ``<relation>.<column>`` path, and a source relation group prefixes
            # the relation with its directory.
            override={
                "surveys.surveyed_on": {"type": "timestamp"},
                "readings.temperature.recorded_on": {"type": "timestamp"},
                "readings.mechanical.vibration.recorded_on": {"type": "timestamp"},
            },
        ),
        package="reference_project.relation.source",
    ),
)
class Estate(Asset):
    """The monitored estate: sites, equipment, surveys and their readings."""

    options = AssetOptions(
        name="estate",
        version="2026-08",
        profile=AssetProfile(
            subject="monitored estate records",
            coverage="sites, equipment, surveys and logger readings",
            authority=AssetAuthority.PRIMARY,
            basis="estate registry and telemetry export",
        ),
        layout=AssetLayout(
            kind="json",
            locator=str(DATA),
            format="json",
            members={
                "sites": "sites.json",
                "equipment": "equipment.json",
                "surveys": "surveys.json",
                "temperature": "readings/temperature.json",
                "vibration": "readings/mechanical/vibration.json",
            },
        ),
    )
