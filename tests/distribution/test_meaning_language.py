from __future__ import annotations

import ast
import dataclasses
import unittest

import kg_build_system.distribution.languages.meaning as meaning_language
import kg_build_system.distribution.languages.meaning.model.internal.dto as meaning_dto_module
from kg_build_system.distribution.languages.meaning import (
    Claim,
    Limitation,
    Purpose,
    Meaning,
)
from kg_build_system.distribution.languages.meaning.model.internal import (
    ClaimDTO,
    LimitationDTO,
    PurposeDTO,
    MeaningDTO,
)
from kg_build_system.distribution.languages.meaning.model.internal.dto import (
    ClaimDTO as DirectClaimDTO,
)
from kg_build_system.distribution.languages.meaning.model.public import (
    Claim as DirectClaim,
)
from kg_build_system.distribution.languages.meaning.service.internal import (
    render_meaning,
    render_meaning_expression,
    meaning_from_document,
    meaning_to_document,
)
from kg_build_system.kernel import SourceFragment


def _purpose() -> Purpose:
    return Purpose(
        "Target prioritisation.",
        limitations=(
            Limitation("No literature mining."),
            Limitation("No homology transfer."),
        ),
    )


def _meaning() -> Meaning:
    return Meaning(
        purpose=_purpose(),
        claims=(
            Claim("The graph describes gene-disease associations."),
            Claim("Scores are per datatype."),
        ),
    )


def _meaning_dto() -> MeaningDTO:
    return MeaningDTO(
        purpose=PurposeDTO(
            "Target prioritisation.",
            limitations=(
                LimitationDTO("No literature mining."),
                LimitationDTO("No homology transfer."),
            ),
        ),
        claims=(
            ClaimDTO("The graph describes gene-disease associations."),
            ClaimDTO("Scores are per datatype."),
        ),
    )


class FacadeTests(unittest.TestCase):
    def test_the_language_exports_the_authoring_units(self) -> None:
        for name in ("Claim", "Limitation", "Purpose", "Meaning"):
            self.assertIn(name, meaning_language.__all__)

        self.assertIs(meaning_language.Claim, DirectClaim)
        self.assertFalse(hasattr(meaning_language, "Frame"))
        self.assertFalse(hasattr(meaning_language, "GraphSemantics"))

    def test_the_dto_is_exported_from_both_internal_paths(self) -> None:
        self.assertIs(ClaimDTO, DirectClaimDTO)
        self.assertEqual(
            set(meaning_dto_module.__all__),
            {
                "ClaimDTO", "LimitationDTO", "PurposeDTO", "MeaningDTO",
            },
        )


class UnitValidationTests(unittest.TestCase):
    def test_text_is_non_empty_for_every_unit(self) -> None:
        for factory in (Claim, Limitation, Purpose):
            with self.subTest(unit=factory.__name__):
                with self.assertRaises(ValueError):
                    factory("")
                with self.assertRaises(ValueError):
                    factory(None)  # type: ignore[arg-type]

    def test_purposes_own_only_limitations_and_normalise_to_a_tuple(self) -> None:
        purpose = Purpose(
            "Target prioritisation.",
            limitations=[Limitation("No literature mining.")],
        )

        self.assertIsInstance(purpose.limitations, tuple)
        self.assertEqual(
            purpose.limitations, (Limitation("No literature mining."),),
        )
        with self.assertRaises(TypeError):
            Purpose("Scope.", limitations=(Claim("Not a limitation."),))  # type: ignore[arg-type]

    def test_units_are_frozen_and_slots(self) -> None:
        claim = Claim("A claim.")

        self.assertFalse(hasattr(claim, "__dict__"))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            claim.text = "Changed."  # type: ignore[misc]


class DeclarationMeaningTests(unittest.TestCase):
    def test_meaning_requires_a_claim_or_a_purpose(self) -> None:
        with self.assertRaises(ValueError):
            Meaning()

    def test_meaning_accepts_claims_only_or_a_purpose_only(self) -> None:
        claims_only = Meaning(claims=(Claim("A claim."),))
        purpose_only = Meaning(purpose=_purpose())

        self.assertIsNone(claims_only.purpose)
        self.assertEqual(purpose_only.claims, ())

    def test_meaning_has_one_optional_purpose(self) -> None:
        field_names = [
            item.name for item in dataclasses.fields(Meaning)
        ]

        self.assertEqual(field_names, ["purpose", "claims"])

    def test_meaning_normalises_claims_and_rejects_other_units(self) -> None:
        value = Meaning(
            purpose=_purpose(), claims=[Claim("A claim.")],
        )

        self.assertIsInstance(value.claims, tuple)
        with self.assertRaises(TypeError):
            Meaning(claims=(Limitation("Not a claim."),))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            Meaning(purpose=Claim("Not a purpose."))  # type: ignore[arg-type]


class DTOTests(unittest.TestCase):
    def test_the_dtos_default_optional_members_to_empty_tuples(self) -> None:
        purpose = PurposeDTO("A purpose.")
        meaning = MeaningDTO(claims=(ClaimDTO("A claim."),))

        self.assertEqual(purpose.limitations, ())
        self.assertIsNone(meaning.purpose)
        self.assertEqual(meaning.claims[0].text, "A claim.")

    def test_the_dtos_carry_the_same_invariants(self) -> None:
        for factory in (ClaimDTO, LimitationDTO, PurposeDTO):
            with self.subTest(dto=factory.__name__):
                with self.assertRaises(ValueError):
                    factory("")

        with self.assertRaises(TypeError):
            PurposeDTO(
                "A purpose.", limitations=(ClaimDTO("wrong"),),  # type: ignore[arg-type]
            )
        with self.assertRaises(TypeError):
            MeaningDTO(claims=(PurposeDTO("wrong"),))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            MeaningDTO(purpose=ClaimDTO("wrong"))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            MeaningDTO()

    def test_the_dtos_normalise_and_freeze_their_tuples(self) -> None:
        purpose = PurposeDTO(
            "A purpose.", limitations=[LimitationDTO("A limitation.")],
        )
        meaning = MeaningDTO(
            purpose=purpose, claims=[ClaimDTO("A claim.")],
        )

        self.assertIsInstance(purpose.limitations, tuple)
        self.assertIsInstance(meaning.claims, tuple)
        self.assertFalse(hasattr(meaning, "__dict__"))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            meaning.claims = ()  # type: ignore[misc]


class CodecTests(unittest.TestCase):
    def test_a_declaration_document_has_the_canonical_shape(self) -> None:
        document = meaning_to_document(_meaning_dto())

        self.assertEqual(
            document,
            {
                "purpose": {
                    "text": "Target prioritisation.",
                    "limitations": [
                        {"text": "No literature mining."},
                        {"text": "No homology transfer."},
                    ],
                },
                "claims": [
                    {"text": "The graph describes gene-disease associations."},
                    {"text": "Scores are per datatype."},
                ],
            },
        )

    def test_the_codec_omits_absent_optional_members(self) -> None:
        claims_only = MeaningDTO(claims=(ClaimDTO("A claim."),))
        purpose_only = MeaningDTO(purpose=PurposeDTO("A purpose."))

        self.assertEqual(
            meaning_to_document(claims_only),
            {"claims": [{"text": "A claim."}]},
        )
        self.assertEqual(
            meaning_to_document(purpose_only),
            {"purpose": {"text": "A purpose."}},
        )

    def test_a_document_round_trips(self) -> None:
        meaning = _meaning_dto()

        self.assertEqual(
            meaning_from_document(meaning_to_document(meaning)),
            meaning,
        )

    def test_decoding_rejects_malformed_documents(self) -> None:
        with self.assertRaises(ValueError):
            meaning_from_document([])
        with self.assertRaises(ValueError):
            meaning_from_document({})
        with self.assertRaises(ValueError):
            meaning_from_document({"claims": "not an array"})
        with self.assertRaises(ValueError):
            meaning_from_document({"claims": [{"text": ""}]})
        with self.assertRaises(ValueError):
            meaning_from_document({"purpose": {"text": ""}})
        with self.assertRaises(ValueError):
            meaning_from_document({"purpose": {"text": "p", "limitations": [{"text": ""}]}})


class SourceRenderingTests(unittest.TestCase):
    def test_the_expression_contains_every_authored_unit(self) -> None:
        value = _meaning()
        expression = render_meaning_expression(value)

        assert value.purpose is not None
        for unit in (
            value.purpose,
            *value.purpose.limitations,
            *value.claims,
        ):
            self.assertIn(repr(unit.text), expression)

        self.assertTrue(expression.startswith("Meaning("))
        self.assertIn("purpose=Purpose(", expression)
        self.assertIn("limitations=(", expression)
        self.assertIn("claims=(", expression)
        self.assertNotIn("eval(", expression)

    def test_the_fragment_is_an_embeddable_meaning_argument(self) -> None:
        fragment = render_meaning(_meaning())

        self.assertEqual(fragment.kind, "inline")
        self.assertTrue(fragment.body.startswith("meaning=Meaning("))
        self.assertEqual(
            fragment.imports,
            (
                "from kg_build_system import Claim, Limitation, Purpose, "
                "Meaning",
            ),
        )
        ast.parse("options = Example(\n" + fragment.body + "\n)")

    def test_the_expression_is_valid_python(self) -> None:
        expression = render_meaning_expression(_meaning())

        ast.parse(expression, mode="eval")

    def test_a_claim_only_expression_omits_the_purpose(self) -> None:
        expression = render_meaning_expression(
            Meaning(claims=(Claim("A claim."),)),
        )

        self.assertNotIn("purpose=", expression)
        self.assertEqual(
            render_meaning(
                Meaning(claims=(Claim("A claim."),)),
            ).imports,
            ("from kg_build_system import Claim, Meaning",),
        )

    def test_a_dto_renders_to_the_same_source_as_its_model(self) -> None:
        self.assertEqual(
            render_meaning_expression(_meaning_dto()),
            render_meaning_expression(_meaning()),
        )
        self.assertIsInstance(render_meaning(_meaning()), SourceFragment)

    def test_the_render_is_stable_and_uses_repr_for_text(self) -> None:
        text = 'A "quoted" claim.'
        value = Meaning(claims=(Claim(text),))

        first = render_meaning_expression(value)
        second = render_meaning_expression(value)

        self.assertEqual(first, second)
        self.assertIn(repr(text), first)
        ast.parse(first, mode="eval")

    def test_a_purpose_without_limitations_renders_without_the_member(
        self,
    ) -> None:
        expression = render_meaning_expression(
            Meaning(purpose=Purpose("A purpose.")),
        )

        self.assertIn(f"purpose=Purpose({'A purpose.'!r})", expression)
        self.assertNotIn("limitations=(", expression)


if __name__ == "__main__":
    unittest.main()
