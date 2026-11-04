"""The logical asset behind the monitored-estate reference build."""

from pathlib import Path

from kg_build_system import (
    Asset,
    AssetAuthority,
    AssetLayout,
    AssetOptions,
    AssetSemantics,
)
from kg_build_system.generation import AssetContractOptions, asset_contract
from kg_build_system.generation.code_generation.builtins import (
    DataContractInferenceConfig,
    InferDataContractProvider,
)

DATA = Path(__file__).parent / "data"


@asset_contract(
    AssetContractOptions(
        provider=InferDataContractProvider,
        configuration=DataContractInferenceConfig(
            mode="table_group",
            layout="files",
            # ``surveyed_on`` and ``recorded_on`` hold ``YYYY-MM-DDTHH:MM``
            # without seconds, which ``read_json_auto`` sniffs as VARCHAR rather
            # than TIMESTAMP. Overrides are keyed by the column's full
            # ``<relation>.<column>`` path, and a table group prefixes the
            # relation with its directory.
            override={
                "surveys.surveyed_on": {"type": "timestamp"},
                "readings.temperature.recorded_on": {"type": "timestamp"},
                "readings.mechanical.vibration.recorded_on": {"type": "timestamp"},
            },
        ),
        package="reference_project.table",
    ),
)
class Estate(Asset):
    """The monitored estate: sites, equipment, surveys and their readings."""

    options = AssetOptions(
        name="estate",
        version="2026-08",
        semantics=AssetSemantics(
            subject="monitored estate records",
            coverage="sites, equipment, surveys and logger readings",
            authority=AssetAuthority.PRIMARY,
            basis="estate registry and telemetry export",
            claims=(
                "every table is one JSON document or one partition per logger family",
            ),
            limitations=(
                "nullability is not declared by the JSON documents",
            ),
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
