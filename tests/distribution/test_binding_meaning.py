"""Contract test: binding-wide meaning through DTO, document and source.

A binding carries one declaration meaning fragment. The test follows both a
node and an edge binding through the authoring factory, transcription, the
canonical document codec and source rendering.
"""
from __future__ import annotations

import ast
import unittest

from kg_build_system.distribution.languages.asset import (
    Asset,
    AssetAuthority,
    AssetOptions,
    AssetProfile,
)
from kg_build_system.distribution.languages.binding import (
    EdgeBinding,
    NodeBinding,
    edge_binding,
    node_binding,
)
from kg_build_system.distribution.languages.binding.model.internal.dto import (
    EdgeBindingDTO,
    NodeBindingDTO,
)
from kg_build_system.distribution.languages.binding.service.internal import (
    binding_from_document,
    binding_to_document,
    render_binding_source,
    transcribe_bindings,
)
from kg_build_system.distribution.languages.data import Field, SourceRelation, field
from kg_build_system.distribution.languages.meaning import (
    Claim,
    Limitation,
    Purpose,
    Meaning,
)
from kg_build_system.distribution.languages.meaning.model.internal.dto import (
    ClaimDTO,
    LimitationDTO,
    PurposeDTO,
    MeaningDTO,
)
from kg_build_system.distribution.languages.topology import (
    Edge,
    Node,
    PropertySlot,
    property,
)


class BindingEstate(Asset):
    options = AssetOptions(
        profile=AssetProfile(
            subject="estate records",
            coverage="sites and units",
            authority=AssetAuthority.PRIMARY,
            basis="binding meaning fixture",
        ),
    )


class SiteSourceRelation(SourceRelation[BindingEstate]):
    site_id: Field[str] = field()
    unit_ref: Field[str] = field()


class SiteNode(Node):
    site_id: PropertySlot[str] = property()


class UnitNode(Node):
    unit_ref: PropertySlot[str] = property()


class HasUnitEdge(Edge[SiteNode, UnitNode]):
    pass


MEANING = Meaning(
    purpose=Purpose(
        "Estate scope.",
        limitations=(Limitation("Units are not sites."),),
    ),
    claims=(Claim("Sites are monitored premises."),),
)

MEANING_DTO = MeaningDTO(
    purpose=PurposeDTO(
        "Estate scope.",
        limitations=(LimitationDTO("Units are not sites."),),
    ),
    claims=(ClaimDTO("Sites are monitored premises."),),
)

MEANING_DOCUMENT = {
    "purpose": {
        "text": "Estate scope.",
        "limitations": [{"text": "Units are not sites."}],
    },
    "claims": [{"text": "Sites are monitored premises."}],
}


def _node_binding(meaning: Meaning | None = None) -> NodeBinding[SiteNode]:
    return node_binding(
        target=SiteNode,
        build_key=SiteSourceRelation.site_id.alter_rows().drop_null(),
        properties=SiteNode(site_id=SiteSourceRelation.site_id),
        meaning=meaning,
    )


def _edge_binding(
    meaning: Meaning | None = None,
) -> EdgeBinding[HasUnitEdge]:
    return edge_binding(
        target=HasUnitEdge,
        build_key=SiteSourceRelation.unit_ref.alter_rows().drop_null(),
        source_build_key=SiteSourceRelation.site_id.alter_rows().drop_null(),
        target_build_key=SiteSourceRelation.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(),
        meaning=meaning,
    )


class BindingMeaningTests(unittest.TestCase):
    def test_a_node_binding_carries_meaning_into_the_dto(self) -> None:
        binding = _node_binding(MEANING)
        self.assertIs(binding.meaning, MEANING)

        dto = transcribe_bindings((binding,))[0]
        self.assertIsInstance(dto, NodeBindingDTO)
        self.assertEqual(dto.meaning, MEANING_DTO)

        document = binding_to_document(dto)
        self.assertEqual(document["meaning"], MEANING_DOCUMENT)
        self.assertEqual(binding_from_document(document), dto)

    def test_a_node_binding_renders_its_meaning(self) -> None:
        dto = transcribe_bindings((_node_binding(MEANING),))[0]
        fragment = render_binding_source((dto,))

        self.assertIn("site_binding = node_binding(", fragment.body)
        self.assertIn("meaning=Meaning(", fragment.body)
        self.assertIn("Claim('Sites are monitored premises.')", fragment.body)
        self.assertIn("purpose=Purpose(", fragment.body)
        self.assertIn("Limitation('Units are not sites.')", fragment.body)
        self.assertIn(
            "from kg_build_system import Claim, Limitation, Purpose, Meaning",
            fragment.imports,
        )
        ast.parse(fragment.body)

    def test_an_edge_binding_carries_meaning_into_the_dto(self) -> None:
        binding = _edge_binding(MEANING)
        self.assertIs(binding.meaning, MEANING)

        dto = transcribe_bindings((binding,))[0]
        self.assertIsInstance(dto, EdgeBindingDTO)
        self.assertEqual(dto.meaning, MEANING_DTO)

        document = binding_to_document(dto)
        self.assertEqual(document["meaning"], MEANING_DOCUMENT)
        self.assertEqual(binding_from_document(document), dto)

    def test_an_edge_binding_renders_its_meaning(self) -> None:
        dto = transcribe_bindings((_edge_binding(MEANING),))[0]
        fragment = render_binding_source((dto,))

        self.assertIn("has_unit_binding = edge_binding(", fragment.body)
        self.assertIn("meaning=Meaning(", fragment.body)
        self.assertIn("Claim('Sites are monitored premises.')", fragment.body)
        self.assertIn("Limitation('Units are not sites.')", fragment.body)
        self.assertIn(
            "from kg_build_system import Claim, Limitation, Purpose, Meaning",
            fragment.imports,
        )
        ast.parse(fragment.body)

    def test_a_binding_without_meaning_is_refused(self) -> None:
        for build in (_node_binding, _edge_binding):
            with self.subTest(binding=build.__name__):
                with self.assertRaisesRegex(
                    ValueError,
                    "a binding requires a meaning with a purpose",
                ):
                    build()

    def test_a_binding_with_claims_only_is_refused(self) -> None:
        claims_only = Meaning(claims=(Claim("A site is a premises."),))
        for build in (_node_binding, _edge_binding):
            with self.subTest(binding=build.__name__):
                with self.assertRaisesRegex(
                    ValueError,
                    "a binding requires a meaning with a purpose",
                ):
                    build(claims_only)

    def test_a_binding_rejects_a_non_meaning_value(self) -> None:
        for build in (_node_binding, _edge_binding):
            with self.subTest(binding=build.__name__):
                with self.assertRaisesRegex(
                    TypeError,
                    "binding meaning must be a Meaning value",
                ):
                    build(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
