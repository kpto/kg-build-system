from __future__ import annotations

import unittest
from dataclasses import dataclass

import kg_build_system
from kg_build_system import (
    Asset,
    AssetAuthority,
    AssetGovernance,
    AssetLayout,
    AssetLicense,
    AssetOptions,
    AssetProfile,
    Omitted,
)
from kg_build_system.distribution.languages.annotations import Annotation
from kg_build_system.distribution.languages.asset.model.internal import (
    AssetDTO,
    AssetPartDTO,
    AssetProfileDTO,
)
from kg_build_system.distribution.languages.asset.model.public import (
    asset_name,
    asset_reference,
)
from kg_build_system.distribution.languages.asset.service.internal import (
    AssetLanguage,
    assets_from_document,
    assets_to_document,
    render_asset_source,
)
from kg_build_system.distribution.model.public.refs import (
    AssetRef,
    ref_from_document,
)
from kg_build_system.kernel import Declaration, Key, SymbolContext, SymbolRef


@dataclass(frozen=True)
class Owner(Annotation):
    namespace = "example"
    annotation_id = "owner"

    name: str


def _profile() -> AssetProfile:
    return AssetProfile(
        subject="gene-disease associations",
        coverage="all curated evidence",
        authority=AssetAuthority.PRIMARY,
        basis="Open Targets Platform release",
        title="Open Targets",
    )


def _options(name: str | None = None) -> AssetOptions:
    return AssetOptions(
        profile=_profile(),
        name=name,
        website="https://platform.opentargets.org",
        version="26.03",
        layout=AssetLayout(
            kind="parquet",
            locator="s3://open-targets/release",
            format="parquet",
            selector="{table}.parquet",
            partition_by=("release", "datatype"),
            members={
                "targets": "targets.parquet",
                "diseases": "diseases.parquet",
            },
            properties={"credentials": "open-targets-reader"},
        ),
        governance=AssetGovernance(
            license=AssetLicense(
                "CC-BY-4.0",
                url="https://creativecommons.org/licenses/by/4.0/",
                attribution="Open Targets",
            ),
            owner="genomics-team",
            metadata={"review": "quarterly", "tier": "reference"},
        ),
        annotations=(Owner("genomics-team"),),
        meaning=Omitted,
    )


def _declaration(name: str = "open_targets") -> type[Asset]:
    class OpenTargets(Asset):
        options = _options(name)

    return OpenTargets


class AssetDeclarationTests(unittest.TestCase):
    def test_the_name_defaults_to_the_snake_case_class_name(self) -> None:
        class OpenTargets(Asset):
            options = _options()

        self.assertEqual(OpenTargets._asset_name, "open_targets")
        self.assertEqual(asset_name(OpenTargets), "open_targets")
        self.assertIs(OpenTargets._asset_options, OpenTargets.options)

    def test_a_declaration_requires_asset_options(self) -> None:
        with self.assertRaises(TypeError):
            class Missing(Asset):
                pass

        with self.assertRaises(TypeError):
            class Wrong(Asset):
                options = object()

    def test_options_validate_required_text_and_mappings(self) -> None:
        with self.assertRaises(ValueError):
            AssetProfile(
                subject="",
                coverage="all",
                authority=AssetAuthority.PRIMARY,
                basis="release",
            )
        with self.assertRaises(ValueError):
            AssetLayout(members={"targets": ""})
        with self.assertRaises(ValueError):
            AssetLicense("")
        with self.assertRaises(ValueError):
            AssetProfile(
                subject="targets",
                coverage="all",
                authority=AssetAuthority.PRIMARY,
                basis="release",
                title="",
            )
        with self.assertRaises(TypeError):
            AssetOptions(profile="not a profile", meaning=Omitted)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            AssetOptions(
                profile=_profile(),
                meaning="not meaning",  # type: ignore[arg-type]
            )

    def test_layout_mappings_are_frozen_and_sorted(self) -> None:
        layout = AssetLayout(members={"b": "2", "a": "1"})

        self.assertEqual(tuple(layout.members), ("a", "b"))
        with self.assertRaises(TypeError):
            layout.members["c"] = "3"  # type: ignore[index]


class AssetLanguageTests(unittest.TestCase):
    def test_discovery_selects_concrete_asset_subclasses(self) -> None:
        declaration = _declaration()

        class Namespace:
            def values(self):
                return (Asset, declaration, 1)

        declarations = tuple(AssetLanguage().discover_declarations(Namespace()))

        self.assertEqual(len(declarations), 1)
        self.assertIs(declarations[0].value, declaration)

    def test_key_kind_identity_and_transcription(self) -> None:
        declaration = _declaration()
        language = AssetLanguage()
        item = Declaration(declaration)

        self.assertEqual(language.compute_key(item), Key(("open_targets",)))
        self.assertEqual(language.get_kind(item), "asset")
        self.assertEqual(
            language.get_identity(declaration),
            SymbolRef("asset", Key(("open_targets",))),
        )

        symbol = language.transcribe(item, SymbolContext())

        self.assertEqual(symbol.key, Key(("open_targets",)))
        self.assertEqual(symbol.kind, "asset")
        self.assertEqual(symbol.value.name, "open_targets")
        self.assertEqual(symbol.references, ())
        self.assertEqual(language.get_references(declaration, None), ())


class AssetReferenceTests(unittest.TestCase):
    def test_the_asset_reference_document_round_trips(self) -> None:
        declaration = _declaration()
        reference = asset_reference(declaration)

        self.assertIsInstance(reference, AssetRef)
        self.assertEqual(reference.role, "asset")
        self.assertEqual(
            reference.to_document(), ["asset", "asset", "open_targets"],
        )
        self.assertEqual(
            ref_from_document(["asset", "asset", "open_targets"]), reference,
        )
        self.assertEqual(
            AssetRef.from_document(["asset", "asset", "open_targets"]), reference,
        )


class AssetCodecTests(unittest.TestCase):
    def test_the_asset_part_round_trips_profile_layout_and_governance(
        self,
    ) -> None:
        declaration = _declaration()
        part = AssetLanguage().transcribe(
            Declaration(declaration), SymbolContext(),
        ).value

        document = assets_to_document(AssetPartDTO((part,)))
        restored = assets_from_document(document)

        self.assertEqual(restored, AssetPartDTO((part,)))
        self.assertEqual(document[0]["name"], "open_targets")
        self.assertEqual(document[0]["profile"]["authority"], "primary")
        self.assertNotIn("meaning", document[0])
        self.assertNotIn("claims", document[0]["profile"])
        self.assertNotIn("limitations", document[0]["profile"])
        self.assertEqual(
            document[0]["layout"]["members"],
            {"diseases": "diseases.parquet", "targets": "targets.parquet"},
        )
        self.assertEqual(
            document[0]["governance"]["license"],
            {
                "identifier": "CC-BY-4.0",
                "url": "https://creativecommons.org/licenses/by/4.0/",
                "attribution": "Open Targets",
            },
        )
        self.assertEqual(
            document[0]["governance"]["metadata"],
            {"review": "quarterly", "tier": "reference"},
        )
        self.assertEqual(len(document[0]["annotations"]), 1)

    def test_a_legacy_semantics_key_decodes_as_the_profile(self) -> None:
        profile = _profile()
        part = AssetPartDTO((
            AssetDTO("open_targets", AssetProfileDTO(
                subject=profile.subject,
                coverage=profile.coverage,
                authority=profile.authority,
                basis=profile.basis,
                title=profile.title,
            )),
        ))
        document = assets_to_document(part)
        legacy = document[0].pop("profile")
        legacy["claims"] = ["a legacy claim"]
        legacy["limitations"] = ["a legacy limitation"]
        document[0]["semantics"] = legacy

        restored = assets_from_document(document)

        self.assertEqual(restored, part)

    def test_an_asset_option_carries_declaration_meaning(self) -> None:
        from kg_build_system.distribution.languages.meaning.model.public import (
            Claim,
            Meaning,
        )

        class OpenTargets(Asset):
            options = AssetOptions(
                profile=_profile(),
                meaning=Meaning(claims=(Claim("a declaration claim"),)),
            )

        part = AssetLanguage().transcribe(
            Declaration(OpenTargets), SymbolContext(),
        ).value

        self.assertEqual(part.meaning.claims[0].text, "a declaration claim")
        document = assets_to_document(AssetPartDTO((part,)))
        self.assertEqual(
            assets_from_document(document), AssetPartDTO((part,)),
        )

    def test_the_asset_part_round_trips_profile_and_meaning(self) -> None:
        from kg_build_system.distribution.languages.meaning.model.internal import (
            ClaimDTO,
            LimitationDTO,
            PurposeDTO,
            MeaningDTO,
        )

        meaning = MeaningDTO(
            purpose=PurposeDTO(
                "curation",
                limitations=(LimitationDTO("coverage varies by disease"),),
            ),
            claims=(ClaimDTO("associations are scored per datatype"),),
        )
        part = AssetPartDTO((
            AssetDTO(
                "open_targets", AssetProfileDTO(
                    subject="gene-disease associations",
                    coverage="all curated evidence",
                    authority=AssetAuthority.PRIMARY,
                    basis="Open Targets Platform release",
                ),
                meaning=meaning,
            ),
        ))

        document = assets_to_document(part)
        restored = assets_from_document(document)

        self.assertEqual(restored, part)
        self.assertIn("claims", document[0]["meaning"])
        self.assertIn("purpose", document[0]["meaning"])


class AssetSourceTests(unittest.TestCase):
    def test_the_source_render_is_a_class_option_declaration(self) -> None:
        declaration = _declaration()
        part = AssetLanguage().transcribe(
            Declaration(declaration), SymbolContext(),
        ).value

        fragment = render_asset_source(AssetPartDTO((part,)))

        self.assertIn("class OpenTargetsAsset(Asset):", fragment.body)
        self.assertIn("options = AssetOptions(", fragment.body)
        self.assertIn("profile=AssetProfile(", fragment.body)
        self.assertIn("authority=AssetAuthority.PRIMARY", fragment.body)
        self.assertIn("members={'diseases'", fragment.body)
        self.assertIn("from kg_build_system import Asset", fragment.imports)
        self.assertIn("from kg_build_system import AssetOptions", fragment.imports)
        self.assertIn("from kg_build_system import AssetLicense", fragment.imports)
        compile(fragment.body, "<asset source>", "exec")

    def test_the_source_render_includes_meaning_when_present(self) -> None:
        from kg_build_system.distribution.languages.meaning.model.internal import (
            ClaimDTO,
            MeaningDTO,
        )

        part = AssetPartDTO((
            AssetDTO(
                "open_targets", AssetProfileDTO(
                    subject="gene-disease associations",
                    coverage="all curated evidence",
                    authority=AssetAuthority.PRIMARY,
                    basis="Open Targets Platform release",
                ),
                meaning=MeaningDTO(claims=(ClaimDTO("one claim"),)),
            ),
        ))

        fragment = render_asset_source(part)

        self.assertIn("profile=AssetProfile(", fragment.body)
        self.assertIn("meaning=Meaning(", fragment.body)
        self.assertIn("one claim", fragment.body)
        compile(fragment.body, "<asset source>", "exec")


class AssetFacadeTests(unittest.TestCase):
    def test_the_top_level_facade_exports_asset(self) -> None:
        self.assertIn("Asset", kg_build_system.__all__)
        self.assertIs(kg_build_system.Asset, Asset)
        self.assertIn("AssetOptions", kg_build_system.__all__)
        self.assertIn("AssetProfile", kg_build_system.__all__)
        self.assertIs(kg_build_system.AssetProfile, AssetProfile)


if __name__ == "__main__":
    unittest.main()
