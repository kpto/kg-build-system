"""Data-language semantics attachments: authoring, DTO, document and source."""
from __future__ import annotations

import unittest

from kg_build_system.distribution.languages.data import (
    Field,
    Projection,
    ProjectionOptions,
    Struct,
    StructOptions,
    Table,
    TableOptions,
    computed_field,
    field,
)
from kg_build_system.distribution.languages.data.service.internal import (
    data_from_document,
    data_to_document,
    render_data,
    transcribe_data,
)
from kg_build_system.distribution.languages.semantics.model.public import (
    Claim,
    Frame,
    GraphSemantics,
    Limitation,
    Purpose,
    Semantics,
)
from .support import TestEstate


def _semantics(label: str) -> Semantics:
    return Semantics(
        claims=(Claim(f"{label} is stated."),),
        frames=(
            Frame(
                text=f"{label} frame",
                limitations=(Limitation(f"{label} is bounded."),),
            ),
        ),
    )


class SiteAddress(Struct):
    """A nested record carrying its own meaning."""

    options = StructOptions(name="site_address", semantics=_semantics("struct"))

    city: Field[str] = field(semantics=_semantics("struct field"))


class Site(Table[TestEstate]):
    """A table whose options, fields and nested struct carry meaning."""

    options = TableOptions(name="site", semantics=_semantics("table"))

    site_id: Field[str] = field(semantics=_semantics("field"))
    unmarked: Field[str] = field()
    address: Field[SiteAddress] = field()


class SiteProjection(Projection(Site.row_source())):
    """A projection whose options and output carry meaning."""

    options = ProjectionOptions(
        name="site_projection",
        semantics=_semantics("projection"),
    )

    label = computed_field(Site.site_id, semantics=_semantics("computed field"))


def _data():
    return transcribe_data((Site, SiteProjection))


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


class DataSemanticsTests(unittest.TestCase):
    def test_attachments_validate_the_declaration_fragment_type(self) -> None:
        with self.assertRaises(TypeError):
            TableOptions(semantics=object())  # pyright: ignore[reportArgumentType]

        with self.assertRaises(TypeError):
            TableOptions(
                semantics=GraphSemantics(  # pyright: ignore[reportArgumentType]
                    claims=(), purpose=Purpose(text="graph purpose"),
                ),
            )

        with self.assertRaises(TypeError):
            field(semantics=object())  # pyright: ignore[reportArgumentType]

    def test_authoring_options_and_fields_reach_the_data_dto(self) -> None:
        data = _data()

        relation = next(item for item in data.relations if item.name == "site")
        struct = next(
            item for item in data.structs if item.name == "site_address"
        )
        projection = next(
            item for item in data.projections if item.name == "site_projection"
        )

        assert relation.semantics is not None
        assert struct.semantics is not None
        assert projection.semantics is not None
        self.assertEqual(relation.semantics.claims[0].text, "table is stated.")
        self.assertEqual(
            struct.semantics.claims[0].text, "struct is stated.",
        )
        self.assertEqual(
            projection.semantics.claims[0].text, "projection is stated.",
        )

        relation_columns = {item.name: item for item in relation.columns}
        site_id = relation_columns["site_id"].semantics
        struct_city = struct.columns[0].semantics
        projection_label = projection.columns[0].semantics
        assert site_id is not None
        assert struct_city is not None
        assert projection_label is not None
        self.assertEqual(site_id.claims[0].text, "field is stated.")
        self.assertIsNone(relation_columns["unmarked"].semantics)
        self.assertEqual(
            struct_city.claims[0].text,
            "struct field is stated.",
        )
        self.assertEqual(
            projection_label.claims[0].text,
            "computed field is stated.",
        )

    def test_the_document_encodes_semantics_and_omits_an_absent_attachment(
        self,
    ) -> None:
        data = _data()
        document = data_to_document(data)

        relation = _declaration(document, "relations", "site")
        struct = _declaration(document, "structs", "site_address")
        projection = _declaration(document, "projections", "site_projection")

        self.assertEqual(
            relation["semantics"]["claims"],
            [{"text": "table is stated."}],
        )
        self.assertEqual(
            relation["semantics"]["frames"],
            [
                {
                    "text": "table frame",
                    "limitations": [{"text": "table is bounded."}],
                },
            ],
        )
        self.assertIn("semantics", struct)
        self.assertIn("semantics", projection)
        self.assertIn(
            "semantics", _column(relation, "site_id"),
        )
        self.assertNotIn(
            "semantics", _column(relation, "unmarked"),
        )
        self.assertIn(
            "semantics", _column(projection, "label"),
        )

        self.assertEqual(data_from_document(document), data)

    def test_source_text_renders_semantics_on_every_attachment_point(self) -> None:
        fragment = render_data(_data())
        body = fragment.body

        self.assertEqual(body.count("semantics=Semantics("), 6)
        self.assertIn("options = TableOptions(", body)
        self.assertIn("semantics=Semantics(", body)
        self.assertIn("= field(", body)
        self.assertIn("computed_field(", body)

        imports = "\n".join(fragment.imports)
        for name in ("Claim", "Frame", "Limitation", "Semantics"):
            self.assertIn(name, imports)


if __name__ == "__main__":
    unittest.main()
