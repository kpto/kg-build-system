"""Contract test: binding-wide semantics through DTO, document and source.

A binding carries one declaration semantics fragment. The test follows both a
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
from kg_build_system.distribution.languages.data import Field, Table, field
from kg_build_system.distribution.languages.semantics import (
    Claim,
    Limitation,
    Purpose,
    Semantics,
)
from kg_build_system.distribution.languages.semantics.model.internal.dto import (
    ClaimDTO,
    LimitationDTO,
    PurposeDTO,
    SemanticsDTO,
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
            basis="binding semantics fixture",
        ),
    )


class SiteTable(Table[BindingEstate]):
    site_id: Field[str] = field()
    unit_ref: Field[str] = field()


class SiteNode(Node):
    site_id: PropertySlot[str] = property()


class UnitNode(Node):
    unit_ref: PropertySlot[str] = property()


class HasUnitEdge(Edge[SiteNode, UnitNode]):
    pass


SEMANTICS = Semantics(
    purpose=Purpose(
        "Estate scope.",
        limitations=(Limitation("Units are not sites."),),
    ),
    claims=(Claim("Sites are monitored premises."),),
)

SEMANTICS_DTO = SemanticsDTO(
    purpose=PurposeDTO(
        "Estate scope.",
        limitations=(LimitationDTO("Units are not sites."),),
    ),
    claims=(ClaimDTO("Sites are monitored premises."),),
)

SEMANTICS_DOCUMENT = {
    "purpose": {
        "text": "Estate scope.",
        "limitations": [{"text": "Units are not sites."}],
    },
    "claims": [{"text": "Sites are monitored premises."}],
}


def _node_binding(semantics: Semantics | None = None) -> NodeBinding[SiteNode]:
    return node_binding(
        target=SiteNode,
        build_key=SiteTable.site_id.alter_rows().drop_null(),
        properties=SiteNode(site_id=SiteTable.site_id),
        semantics=semantics,
    )


def _edge_binding(
    semantics: Semantics | None = None,
) -> EdgeBinding[HasUnitEdge]:
    return edge_binding(
        target=HasUnitEdge,
        build_key=SiteTable.unit_ref.alter_rows().drop_null(),
        source_build_key=SiteTable.site_id.alter_rows().drop_null(),
        target_build_key=SiteTable.unit_ref.alter_rows().drop_null(),
        properties=HasUnitEdge(),
        semantics=semantics,
    )


class BindingSemanticsTests(unittest.TestCase):
    def test_a_node_binding_carries_semantics_into_the_dto(self) -> None:
        binding = _node_binding(SEMANTICS)
        self.assertIs(binding.semantics, SEMANTICS)

        dto = transcribe_bindings((binding,))[0]
        self.assertIsInstance(dto, NodeBindingDTO)
        self.assertEqual(dto.semantics, SEMANTICS_DTO)

        document = binding_to_document(dto)
        self.assertEqual(document["semantics"], SEMANTICS_DOCUMENT)
        self.assertEqual(binding_from_document(document), dto)

    def test_a_node_binding_renders_its_semantics(self) -> None:
        dto = transcribe_bindings((_node_binding(SEMANTICS),))[0]
        fragment = render_binding_source((dto,))

        self.assertIn("site_binding = node_binding(", fragment.body)
        self.assertIn("semantics=Semantics(", fragment.body)
        self.assertIn("Claim('Sites are monitored premises.')", fragment.body)
        self.assertIn("purpose=Purpose(", fragment.body)
        self.assertIn("Limitation('Units are not sites.')", fragment.body)
        self.assertIn(
            "from kg_build_system import Claim, Limitation, Purpose, Semantics",
            fragment.imports,
        )
        ast.parse(fragment.body)

    def test_an_edge_binding_carries_semantics_into_the_dto(self) -> None:
        binding = _edge_binding(SEMANTICS)
        self.assertIs(binding.semantics, SEMANTICS)

        dto = transcribe_bindings((binding,))[0]
        self.assertIsInstance(dto, EdgeBindingDTO)
        self.assertEqual(dto.semantics, SEMANTICS_DTO)

        document = binding_to_document(dto)
        self.assertEqual(document["semantics"], SEMANTICS_DOCUMENT)
        self.assertEqual(binding_from_document(document), dto)

    def test_an_edge_binding_renders_its_semantics(self) -> None:
        dto = transcribe_bindings((_edge_binding(SEMANTICS),))[0]
        fragment = render_binding_source((dto,))

        self.assertIn("has_unit_binding = edge_binding(", fragment.body)
        self.assertIn("semantics=Semantics(", fragment.body)
        self.assertIn("Claim('Sites are monitored premises.')", fragment.body)
        self.assertIn("Limitation('Units are not sites.')", fragment.body)
        self.assertIn(
            "from kg_build_system import Claim, Limitation, Purpose, Semantics",
            fragment.imports,
        )
        ast.parse(fragment.body)

    def test_a_binding_without_semantics_omits_the_document_member(self) -> None:
        for binding in (_node_binding(), _edge_binding()):
            with self.subTest(target=binding.target.__name__):
                self.assertIsNone(binding.semantics)
                dto = transcribe_bindings((binding,))[0]
                self.assertNotIn("semantics", binding_to_document(dto))
                self.assertIsNone(binding_from_document(
                    binding_to_document(dto),
                ).semantics)

    def test_a_binding_rejects_a_non_semantics_value(self) -> None:
        for build in (_node_binding, _edge_binding):
            with self.subTest(binding=build.__name__):
                with self.assertRaisesRegex(
                    TypeError,
                    "binding semantics must be a Semantics value",
                ):
                    build(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
