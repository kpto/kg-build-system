from __future__ import annotations

import ast
import dataclasses
import unittest

import kg_build_system.distribution.languages.semantics as semantics_language
import kg_build_system.distribution.languages.semantics.model.internal.dto as semantics_dto_module
from kg_build_system.distribution.languages.semantics import (
    Claim,
    Frame,
    GraphSemantics,
    Limitation,
    Purpose,
    Semantics,
)
from kg_build_system.distribution.languages.semantics.model.internal import (
    ClaimDTO,
    FrameDTO,
    GraphSemanticsDTO,
    LimitationDTO,
    PurposeDTO,
    SemanticsDTO,
)
from kg_build_system.distribution.languages.semantics.model.internal.dto import (
    ClaimDTO as DirectClaimDTO,
)
from kg_build_system.distribution.languages.semantics.model.public import (
    Claim as DirectClaim,
)
from kg_build_system.distribution.languages.semantics.service.internal import (
    graph_semantics_from_document,
    graph_semantics_to_document,
    render_graph_semantics,
    render_semantics,
    render_semantics_expression,
    semantics_from_document,
    semantics_to_document,
)


def _frame() -> Frame:
    return Frame(
        "Curated evidence only.",
        limitations=(
            Limitation("No literature mining."),
            Limitation("No homology transfer."),
        ),
    )


def _purpose() -> Purpose:
    return Purpose("Target prioritisation.", frames=(_frame(),))


def _semantics() -> Semantics:
    return Semantics(
        claims=(
            Claim("The graph describes gene-disease associations."),
            Claim("Scores are per datatype."),
        ),
        frames=(_frame(), Frame("Scores only.")),
    )


def _graph_semantics() -> GraphSemantics:
    return GraphSemantics(
        claims=(Claim("The graph describes gene-disease associations."),),
        purpose=_purpose(),
    )


def _semantics_dto() -> SemanticsDTO:
    return SemanticsDTO(
        claims=(
            ClaimDTO("The graph describes gene-disease associations."),
            ClaimDTO("Scores are per datatype."),
        ),
        frames=(
            FrameDTO(
                "Curated evidence only.",
                limitations=(
                    LimitationDTO("No literature mining."),
                    LimitationDTO("No homology transfer."),
                ),
            ),
            FrameDTO("Scores only."),
        ),
    )


def _graph_semantics_dto() -> GraphSemanticsDTO:
    return GraphSemanticsDTO(
        claims=(ClaimDTO("The graph describes gene-disease associations."),),
        purpose=PurposeDTO(
            "Target prioritisation.",
            frames=(
                FrameDTO(
                    "Curated evidence only.",
                    limitations=(
                        LimitationDTO("No literature mining."),
                        LimitationDTO("No homology transfer."),
                    ),
                ),
            ),
        ),
    )


class FacadeTests(unittest.TestCase):
    def test_the_language_exports_the_authoring_units(self) -> None:
        for name in (
            "Claim", "Frame", "GraphSemantics", "Limitation", "Purpose",
            "Semantics",
        ):
            self.assertIn(name, semantics_language.__all__)

        self.assertIs(semantics_language.Claim, DirectClaim)

    def test_the_dto_is_exported_from_both_internal_paths(self) -> None:
        self.assertIs(ClaimDTO, DirectClaimDTO)
        self.assertEqual(
            set(semantics_dto_module.__all__),
            {
                "ClaimDTO", "FrameDTO", "GraphSemanticsDTO", "LimitationDTO",
                "PurposeDTO", "SemanticsDTO",
            },
        )


class UnitValidationTests(unittest.TestCase):
    def test_text_is_non_empty_for_every_unit(self) -> None:
        for factory in (Claim, Limitation, Frame, Purpose):
            with self.subTest(unit=factory.__name__):
                with self.assertRaises(ValueError):
                    factory("")
                with self.assertRaises(ValueError):
                    factory(None)  # type: ignore[arg-type]

    def test_frames_own_only_limitations_and_normalise_to_a_tuple(self) -> None:
        frame = Frame(
            "Curated evidence only.",
            limitations=[Limitation("No literature mining.")],
        )

        self.assertIsInstance(frame.limitations, tuple)
        self.assertEqual(
            frame.limitations, (Limitation("No literature mining."),),
        )
        with self.assertRaises(TypeError):
            Frame("Scope.", limitations=(Claim("Not a limitation."),))  # type: ignore[arg-type]

    def test_purposes_own_only_frames_and_normalise_to_a_tuple(self) -> None:
        purpose = Purpose("Target prioritisation.", frames=[_frame()])

        self.assertIsInstance(purpose.frames, tuple)
        self.assertEqual(purpose.frames, (_frame(),))
        with self.assertRaises(TypeError):
            Purpose("Target prioritisation.", frames=(Claim("Not a frame."),))  # type: ignore[arg-type]

    def test_units_are_frozen_and_slots(self) -> None:
        claim = Claim("A claim.")

        self.assertFalse(hasattr(claim, "__dict__"))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            claim.text = "Changed."  # type: ignore[misc]


class DeclarationSemanticsTests(unittest.TestCase):
    def test_semantics_requires_a_claim_or_a_frame(self) -> None:
        with self.assertRaises(ValueError):
            Semantics()

    def test_semantics_accepts_claims_only_or_frames_only(self) -> None:
        claims_only = Semantics(claims=(Claim("A claim."),))
        frames_only = Semantics(frames=(_frame(),))

        self.assertEqual(claims_only.frames, ())
        self.assertEqual(frames_only.claims, ())

    def test_semantics_has_no_purpose(self) -> None:
        field_names = {
            item.name for item in dataclasses.fields(Semantics)
        }

        self.assertNotIn("purpose", field_names)
        with self.assertRaises(TypeError):
            Semantics(  # type: ignore[call-arg]
                claims=(Claim("A claim."),), purpose=_purpose(),
            )

    def test_semantics_normalises_claims_and_frames(self) -> None:
        value = Semantics(
            claims=[Claim("A claim.")], frames=[_frame()],
        )

        self.assertIsInstance(value.claims, tuple)
        self.assertIsInstance(value.frames, tuple)
        with self.assertRaises(TypeError):
            Semantics(claims=(_frame(),))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            Semantics(frames=(Claim("Not a frame."),))  # type: ignore[arg-type]

    def test_graph_semantics_requires_a_purpose(self) -> None:
        with self.assertRaises(TypeError):
            GraphSemantics()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            GraphSemantics(claims=(Claim("A claim."),))  # type: ignore[call-arg]

    def test_graph_semantics_accepts_no_claims_when_the_purpose_is_present(
        self,
    ) -> None:
        value = GraphSemantics(purpose=_purpose())

        self.assertEqual(value.claims, ())
        self.assertEqual(value.purpose, _purpose())

    def test_graph_semantics_rejects_a_non_purpose_root(self) -> None:
        with self.assertRaises(TypeError):
            GraphSemantics(purpose=Claim("Not a purpose."))  # type: ignore[arg-type]

    def test_graph_semantics_normalises_claims(self) -> None:
        value = GraphSemantics(
            claims=[Claim("A claim.")], purpose=_purpose(),
        )

        self.assertIsInstance(value.claims, tuple)


class DTOTests(unittest.TestCase):
    def test_the_dtos_default_optional_members_to_empty_tuples(self) -> None:
        frame = FrameDTO("A frame.")
        purpose = PurposeDTO("A purpose.")
        semantics = SemanticsDTO(claims=(ClaimDTO("A claim."),))
        graph = GraphSemanticsDTO(purpose=purpose)

        self.assertEqual(frame.limitations, ())
        self.assertEqual(purpose.frames, ())
        self.assertEqual(semantics.frames, ())
        self.assertEqual(graph.claims, ())

    def test_the_dtos_carry_the_same_invariants(self) -> None:
        for factory in (ClaimDTO, LimitationDTO, FrameDTO, PurposeDTO):
            with self.subTest(dto=factory.__name__):
                with self.assertRaises(ValueError):
                    factory("")

        with self.assertRaises(TypeError):
            FrameDTO("A frame.", limitations=(ClaimDTO("wrong"),))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            PurposeDTO("A purpose.", frames=(ClaimDTO("wrong"),))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            SemanticsDTO(claims=(FrameDTO("wrong"),))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            SemanticsDTO()
        with self.assertRaises(TypeError):
            GraphSemanticsDTO()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            GraphSemanticsDTO(purpose=ClaimDTO("wrong"))  # type: ignore[arg-type]

    def test_the_dtos_normalise_and_freeze_their_tuples(self) -> None:
        frame = FrameDTO(
            "A frame.", limitations=[LimitationDTO("A limitation.")],
        )
        semantics = SemanticsDTO(
            claims=[ClaimDTO("A claim.")], frames=[frame],
        )

        self.assertIsInstance(frame.limitations, tuple)
        self.assertIsInstance(semantics.claims, tuple)
        self.assertIsInstance(semantics.frames, tuple)
        self.assertFalse(hasattr(semantics, "__dict__"))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            semantics.claims = ()  # type: ignore[misc]


class CodecTests(unittest.TestCase):
    def test_a_declaration_document_has_the_canonical_shape(self) -> None:
        document = semantics_to_document(_semantics_dto())

        self.assertEqual(
            document,
            {
                "claims": [
                    {"text": "The graph describes gene-disease associations."},
                    {"text": "Scores are per datatype."},
                ],
                "frames": [
                    {
                        "text": "Curated evidence only.",
                        "limitations": [
                            {"text": "No literature mining."},
                            {"text": "No homology transfer."},
                        ],
                    },
                    {"text": "Scores only."},
                ],
            },
        )

    def test_the_codec_omits_absent_optional_members(self) -> None:
        claims_only = SemanticsDTO(claims=(ClaimDTO("A claim."),))
        frames_only = SemanticsDTO(frames=(FrameDTO("A frame."),))
        graph = GraphSemanticsDTO(purpose=PurposeDTO("A purpose."))

        self.assertEqual(
            semantics_to_document(claims_only),
            {"claims": [{"text": "A claim."}]},
        )
        self.assertEqual(
            semantics_to_document(frames_only),
            {"frames": [{"text": "A frame."}]},
        )
        self.assertEqual(
            graph_semantics_to_document(graph),
            {"purpose": {"text": "A purpose."}},
        )

    def test_a_graph_document_has_the_canonical_shape(self) -> None:
        document = graph_semantics_to_document(_graph_semantics_dto())

        self.assertEqual(
            document,
            {
                "claims": [
                    {"text": "The graph describes gene-disease associations."},
                ],
                "purpose": {
                    "text": "Target prioritisation.",
                    "frames": [
                        {
                            "text": "Curated evidence only.",
                            "limitations": [
                                {"text": "No literature mining."},
                                {"text": "No homology transfer."},
                            ],
                        },
                    ],
                },
            },
        )

    def test_both_documents_round_trip(self) -> None:
        semantics = _semantics_dto()
        graph = _graph_semantics_dto()

        self.assertEqual(
            semantics_from_document(semantics_to_document(semantics)),
            semantics,
        )
        self.assertEqual(
            graph_semantics_from_document(
                graph_semantics_to_document(graph),
            ),
            graph,
        )

    def test_decoding_rejects_malformed_documents(self) -> None:
        with self.assertRaises(ValueError):
            semantics_from_document([])
        with self.assertRaises(ValueError):
            semantics_from_document({})
        with self.assertRaises(ValueError):
            semantics_from_document({"claims": "not an array"})
        with self.assertRaises(ValueError):
            semantics_from_document({"claims": [{"text": ""}]})
        with self.assertRaises(ValueError):
            graph_semantics_from_document({})
        with self.assertRaises(ValueError):
            graph_semantics_from_document({"purpose": {"text": ""}})


class SourceRenderingTests(unittest.TestCase):
    def test_the_expression_contains_every_authored_unit(self) -> None:
        value = _semantics()
        expression = render_semantics_expression(value)

        for unit in (
            *value.claims, *value.frames,
            *(
                limitation
                for frame in value.frames
                for limitation in frame.limitations
            ),
        ):
            self.assertIn(repr(unit.text), expression)

        self.assertTrue(expression.startswith("Semantics("))
        self.assertIn("frames=(", expression)
        self.assertIn("limitations=(", expression)
        self.assertNotIn("eval(", expression)

    def test_the_fragment_is_an_embeddable_semantics_argument(self) -> None:
        fragment = render_semantics(_semantics())

        self.assertEqual(fragment.kind, "inline")
        self.assertTrue(fragment.body.startswith("semantics=Semantics("))
        self.assertEqual(
            fragment.imports,
            (
                "from kg_build_system import Claim, Frame, Limitation, Semantics",
            ),
        )
        ast.parse("options = Example(\n" + fragment.body + "\n)")

    def test_the_expression_is_valid_python(self) -> None:
        expression = render_semantics_expression(_semantics())

        ast.parse(expression, mode="eval")

    def test_the_graph_fragment_contains_the_purpose_and_every_unit(
        self,
    ) -> None:
        value = _graph_semantics()
        fragment = render_graph_semantics(value)

        self.assertTrue(fragment.body.startswith("semantics=GraphSemantics("))
        self.assertIn("purpose=Purpose(", fragment.body)
        self.assertIn(repr(value.purpose.text), fragment.body)
        for frame in value.purpose.frames:
            self.assertIn(repr(frame.text), fragment.body)
            for limitation in frame.limitations:
                self.assertIn(repr(limitation.text), fragment.body)
        self.assertEqual(
            fragment.imports,
            (
                "from kg_build_system import Claim, Frame, Limitation, "
                "Purpose, GraphSemantics",
            ),
        )
        ast.parse("options = GraphOptions(\n" + fragment.body + "\n)")

    def test_the_graph_fragment_omits_claims_when_there_are_none(self) -> None:
        fragment = render_graph_semantics(
            GraphSemantics(purpose=Purpose("A purpose.")),
        )

        self.assertNotIn("claims=(", fragment.body)
        self.assertEqual(
            fragment.imports,
            ("from kg_build_system import Purpose, GraphSemantics",),
        )

    def test_a_dto_renders_to_the_same_source_as_its_model(self) -> None:
        self.assertEqual(
            render_semantics_expression(_semantics_dto()),
            render_semantics_expression(_semantics()),
        )
        self.assertEqual(
            render_graph_semantics(_graph_semantics_dto()).body,
            render_graph_semantics(_graph_semantics()).body,
        )

    def test_the_render_is_stable_and_uses_repr_for_text(self) -> None:
        text = 'A "quoted" claim.'
        value = Semantics(claims=(Claim(text),))

        first = render_semantics_expression(value)
        second = render_semantics_expression(value)

        self.assertEqual(first, second)
        self.assertIn(repr(text), first)
        ast.parse(first, mode="eval")

    def test_an_empty_frame_renders_without_a_limitations_member(self) -> None:
        expression = render_semantics_expression(
            Semantics(frames=(Frame("A frame."),)),
        )

        self.assertIn(f"Frame({'A frame.'!r})", expression)
        self.assertNotIn("limitations=(", expression)


if __name__ == "__main__":
    unittest.main()
