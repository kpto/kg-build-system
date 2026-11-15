"""Data-language meaning attachments: authoring, DTO, document and source."""
from __future__ import annotations

import unittest

from kg_build_system.distribution.languages.data import (
    Contract,
    Definition,
    Field,
    DerivedRelation,
    DerivedRelationOptions,
    Struct,
    StructOptions,
    SourceRelation,
    SourceRelationOptions,
    computed_field,
    field,
)
from kg_build_system.distribution.languages.data.service.internal import (
    data_from_document,
    data_to_document,
    render_data,
    transcribe_data,
)
from kg_build_system.distribution.languages.meaning.model.public import (
    Claim,
    Limitation,
    Purpose,
    Meaning,
)
from .support import TestEstate


def _meaning(label: str) -> Meaning:
    return Meaning(
        purpose=Purpose(
            text=f"{label} purpose",
            limitations=(Limitation(f"{label} is bounded."),),
        ),
        claims=(Claim(f"{label} is stated."),),
    )


class SiteAddress(Struct):
    """A nested record carrying its own meaning."""

    options = StructOptions(name="site_address", meaning=_meaning("struct"))

    city: Field[str] = field(meaning=_meaning("struct field"))


class Site(SourceRelation[TestEstate]):
    """A source relation whose options, fields and struct carry meaning."""

    options = SourceRelationOptions(
        name="site",
        contract=Contract(
            definition=Definition(grain="one row per site", identity=("site_id",)),
            meaning=_meaning("source relation"),
        ),
    )

    site_id: Field[str] = field(meaning=_meaning("field"))
    unmarked: Field[str] = field()
    address: Field[SiteAddress] = field()


class SiteDerivedRelation(DerivedRelation(Site.row_source())):
    """A derived relation whose options and output carry meaning."""

    options = DerivedRelationOptions(
        name="site_projection",
        contract=Contract(
            definition=Definition(
                grain="one row per site label", identity=("label",),
            ),
            meaning=_meaning("derived relation"),
        ),
    )

    label = computed_field(Site.site_id, meaning=_meaning("computed field"))


def _data():
    return transcribe_data((Site, SiteDerivedRelation))


def _declaration(document: dict, key: str, name: str) -> dict:
    for item in document[key]:
        if item["name"] == name:
            return item
    raise AssertionError(f"{key} does not contain {name!r}")


def _column(document: dict, name: str) -> dict:
    for item in document["columns"]:
        if item["name"] == name:
            return item
    raise AssertionError(f"columns do not contain {name!r}")


class DataMeaningTests(unittest.TestCase):
    def test_attachments_validate_the_declaration_fragment_type(self) -> None:
        with self.assertRaises(TypeError):
            SourceRelationOptions(
                contract=object(),  # pyright: ignore[reportArgumentType]
            )

        with self.assertRaises(TypeError):
            DerivedRelationOptions(
                contract=object(),  # pyright: ignore[reportArgumentType]
            )

        with self.assertRaises(TypeError):
            field(meaning=object())  # pyright: ignore[reportArgumentType]

    def test_authoring_options_and_fields_reach_the_data_dto(self) -> None:
        data = _data()

        relation = next(item for item in data.source_relations if item.name == "site")
        struct = next(
            item for item in data.structs if item.name == "site_address"
        )
        derived_relation = next(
            item for item in data.derived_relations
            if item.name == "site_projection"
        )

        assert relation.meaning is not None
        assert struct.meaning is not None
        assert derived_relation.meaning is not None
        self.assertEqual(
            relation.meaning.claims[0].text, "source relation is stated.",
        )
        self.assertEqual(
            struct.meaning.claims[0].text, "struct is stated.",
        )
        self.assertEqual(
            derived_relation.meaning.claims[0].text,
            "derived relation is stated.",
        )

        relation_columns = {item.name: item for item in relation.columns}
        site_id = relation_columns["site_id"].meaning
        struct_city = struct.columns[0].meaning
        derived_relation_label = derived_relation.columns[0].meaning
        assert site_id is not None
        assert struct_city is not None
        assert derived_relation_label is not None
        self.assertEqual(site_id.claims[0].text, "field is stated.")
        self.assertIsNone(relation_columns["unmarked"].meaning)
        self.assertEqual(
            struct_city.claims[0].text,
            "struct field is stated.",
        )
        self.assertEqual(
            derived_relation_label.claims[0].text,
            "computed field is stated.",
        )

    def test_the_document_encodes_meaning_and_omits_an_absent_attachment(
        self,
    ) -> None:
        data = _data()
        document = data_to_document(data)

        relation = _declaration(document, "source_relations", "site")
        struct = _declaration(document, "structs", "site_address")
        derived_relation = _declaration(
            document, "derived_relations", "site_projection",
        )

        self.assertEqual(
            relation["meaning"]["claims"],
            [{"text": "source relation is stated."}],
        )
        self.assertEqual(
            relation["meaning"]["purpose"],
            {
                "text": "source relation purpose",
                "limitations": [{"text": "source relation is bounded."}],
            },
        )
        self.assertIn("meaning", struct)
        self.assertIn("meaning", derived_relation)
        self.assertIn(
            "meaning", _column(relation, "site_id"),
        )
        self.assertNotIn(
            "meaning", _column(relation, "unmarked"),
        )
        self.assertIn(
            "meaning", _column(derived_relation, "label"),
        )

        self.assertEqual(data_from_document(document), data)

    def test_source_text_renders_meaning_on_every_attachment_point(self) -> None:
        fragment = render_data(_data())
        body = fragment.body

        self.assertEqual(body.count("meaning=Meaning("), 6)
        self.assertIn("options = SourceRelationOptions(", body)
        self.assertIn("meaning=Meaning(", body)
        self.assertIn("= field(", body)
        self.assertIn("computed_field(", body)

        imports = "\n".join(fragment.imports)
        for name in ("Claim", "Limitation", "Purpose", "Meaning"):
            self.assertIn(name, imports)


if __name__ == "__main__":
    unittest.main()
