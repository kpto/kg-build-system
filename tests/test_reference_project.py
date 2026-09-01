from __future__ import annotations

import unittest

from reference_project.build import create_reference_blueprint


class ReferenceDocumentationTests(unittest.TestCase):
    """The reference project is documentation for the framework, so it documents
    itself: an undocumented component or property is a gap in the example."""

    def setUp(self) -> None:
        self.components = create_reference_blueprint().components

    def test_every_component_is_described(self) -> None:
        self.assertGreater(len(self.components), 0, "no components to check")
        undocumented = [c.name for c in self.components if not c.description]
        self.assertEqual(undocumented, [], "components missing a description")

    def test_every_property_is_described(self) -> None:
        undocumented = [
            f"{component.name}.{prop.name}"
            for component in self.components
            for prop in component.properties
            if not prop.description
        ]
        total = sum(len(c.properties) for c in self.components)
        # A vacuous pass would hide a topology that stopped declaring properties.
        self.assertGreater(total, 0, "no properties to check")
        self.assertEqual(undocumented, [], "properties missing a description")


if __name__ == "__main__":
    unittest.main()
