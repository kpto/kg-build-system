"""The relation contract: definition, meaning, field definitions and stage privacy."""
from __future__ import annotations

import unittest

from kg_build_system import (
    Claim,
    Contract,
    Definition,
    DerivedRelation,
    DerivedRelationOptions,
    Field,
    FieldDefinition,
    Limitation,
    Meaning,
    Node,
    NodeOptions,
    NodeValues,
    Omitted,
    PropertySlot,
    Purpose,
    SourceRelation,
    SourceRelationOptions,
    Stage,
    StageOptions,
    computed_field,
    field,
    node_binding,
    property,
)
from kg_build_system.distribution.languages.data.service.internal import (
    data_from_document,
    data_to_document,
    render_data,
    transcribe_data,
)
from .support import TestEstate


class Site(SourceRelation[TestEstate]):
    """A source relation that states its contract and one field definition."""

    options = SourceRelationOptions(
        name="site",
        contract=Contract(
            definition=Definition(
                grain="one row per site in the register",
                identity=("site_id",),
            ),
            meaning=Meaning(
                claims=(Claim("The register holds one record per site."),),
            ),
        ),
    )

    site_id: Field[str] = field(
        definition=FieldDefinition(value="Site identifier in the register."),
        meaning=Omitted,
    )
    name: Field[str] = field(meaning=Omitted)


site_rows = Site.row_source()


class SiteStage(Stage(site_rows)):
    """A private stage: a definition and no contract."""

    options = StageOptions(
        name="site_stage",
        definition=Definition(
            grain="one row per site in the register",
            identity=("site_id",),
        ),
    )

    site_id = computed_field(Site.site_id, meaning=Omitted)
    name = computed_field(Site.name, meaning=Omitted)


class SiteLabel(DerivedRelation(SiteStage.row_source())):
    """A published derived relation with a purpose."""

    options = DerivedRelationOptions(
        name="site_label",
        contract=Contract(
            definition=Definition(
                grain="one row per site label",
                identity=("label",),
            ),
            meaning=Meaning(
                purpose=Purpose(
                    "Read one label per site.",
                    limitations=(Limitation("A label is not an address."),),
                ),
                claims=(Claim("One row is one site and its label."),),
            ),
        ),
    )

    label = computed_field(SiteStage.name, meaning=Omitted)


class SiteNode(Node):
    """A graph record for the binding refusal test."""

    options = NodeOptions(name="site", meaning=Omitted)

    name: PropertySlot[str] = property(meaning=Omitted)


class Bare(SourceRelation[TestEstate]):
    """A source relation without a contract."""

    options = SourceRelationOptions(name="bare", contract=Omitted)

    site_id: Field[str] = field(meaning=Omitted)


def _data():
    return transcribe_data((Site, SiteStage, SiteLabel, Bare))


class RelationContractTests(unittest.TestCase):
    def test_a_contract_requires_a_definition_and_a_meaning(self) -> None:
        definition = Definition(grain="one row", identity=("id",))
        meaning = Meaning(claims=(Claim("One row is one record."),))

        with self.assertRaises(TypeError):
            Contract(definition=definition, meaning=None)  # pyright: ignore[reportArgumentType]

        with self.assertRaises(TypeError):
            Contract(definition=None, meaning=meaning)  # pyright: ignore[reportArgumentType]

    def test_a_definition_requires_a_grain_and_an_identity(self) -> None:
        with self.assertRaises(ValueError):
            Definition(grain="", identity=("id",))

        with self.assertRaises(ValueError):
            Definition(grain="one row", identity=())

    def test_a_derived_relation_requires_a_purpose(self) -> None:
        with self.assertRaises(ValueError):

            class ClaimOnly(DerivedRelation(SiteStage.row_source())):
                options = DerivedRelationOptions(
                    name="claim_only",
                    contract=Contract(
                        definition=Definition(
                            grain="one row per site",
                            identity=("label",),
                        ),
                        meaning=Meaning(
                            claims=(Claim("One row is one site."),),
                        ),
                    ),
                )

                label = computed_field(SiteStage.name, meaning=Omitted)

        self.assertNotIn("ClaimOnly", globals())

    def test_a_stage_has_no_meaning_member(self) -> None:
        with self.assertRaises(TypeError):
            StageOptions(
                name="bad_stage",
                definition=Definition(grain="one row", identity=("id",)),
                meaning=Meaning(  # pyright: ignore[reportCallIssue]
                    claims=(Claim("Stages carry no contract."),),
                ),
            )

    def test_identity_must_name_a_declared_output(self) -> None:
        with self.assertRaises(ValueError):

            class MissingIdentity(DerivedRelation(SiteStage.row_source())):
                options = DerivedRelationOptions(
                    name="missing_identity",
                    contract=Contract(
                        definition=Definition(
                            grain="one row per site",
                            identity=("absent",),
                        ),
                        meaning=Meaning(
                            purpose=Purpose("Read a site label."),
                        ),
                    ),
                )

                label = computed_field(SiteStage.name, meaning=Omitted)

        self.assertNotIn("MissingIdentity", globals())

    def test_a_binding_refuses_a_stage(self) -> None:
        with self.assertRaises(TypeError):
            node_binding(
                target=SiteNode,
                rows=SiteStage.row_source(),  # pyright: ignore[reportArgumentType]
                bind=lambda row: NodeValues(
                    build_key=row.site_id.alter_rows().drop_null(),
                    properties=SiteNode(name=row.name),
                ),
                meaning=Meaning(
                    purpose=Purpose("Fulfil the stage fixture from its rows."),
                ),
            )

    def test_a_source_relation_may_omit_its_contract(self) -> None:
        data = _data()
        bare = next(
            item for item in data.source_relations if item.name == "bare"
        )

        self.assertIsNone(bare.definition)
        self.assertIsNone(bare.meaning)

    def test_transcription_carries_the_contract_and_field_definitions(
        self,
    ) -> None:
        data = _data()
        site = next(
            item for item in data.source_relations if item.name == "site"
        )
        stage = next(
            item for item in data.derived_relations if item.name == "site_stage"
        )
        label = next(
            item for item in data.derived_relations if item.name == "site_label"
        )

        self.assertIsNotNone(site.definition)
        self.assertIsNotNone(site.meaning)
        assert site.definition is not None
        self.assertEqual(
            site.definition.grain, "one row per site in the register",
        )
        self.assertEqual(site.definition.identity, ("site_id",))

        columns = {item.name: item for item in site.columns}
        self.assertIsNotNone(columns["site_id"].definition)
        assert columns["site_id"].definition is not None
        self.assertEqual(
            columns["site_id"].definition.value,
            "Site identifier in the register.",
        )
        self.assertIsNone(columns["name"].definition)

        self.assertEqual(stage.visibility, "internal")
        self.assertIsNone(stage.meaning)
        self.assertEqual(label.visibility, "public")
        self.assertIsNotNone(label.meaning)

    def test_the_document_round_trips_the_contract(self) -> None:
        data = _data()
        document = data_to_document(data)

        site = next(
            item for item in document["source_relations"]
            if item["name"] == "site"
        )
        stage = next(
            item for item in document["derived_relations"]
            if item["name"] == "site_stage"
        )

        self.assertEqual(site["definition"]["grain"], "one row per site in the register")
        self.assertEqual(site["definition"]["identity"], ["site_id"])
        self.assertIn("meaning", site)
        self.assertEqual(stage["visibility"], "internal")
        self.assertNotIn("meaning", stage)
        self.assertEqual(data_from_document(document), data)

    def test_source_text_renders_the_contract_and_the_field_definition(
        self,
    ) -> None:
        body = render_data(_data()).body

        self.assertIn("Contract(", body)
        self.assertIn("Definition(", body)
        self.assertIn("FieldDefinition(", body)
        self.assertIn("identity=('site_id',)", body)
        self.assertIn("class SiteStage(Stage(", body)
        self.assertIn("class SiteLabel(DerivedRelation(", body)


if __name__ == "__main__":
    unittest.main()
