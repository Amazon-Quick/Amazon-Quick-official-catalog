"""
description: Unit tests for create_readme.py. Filesystem-free: ReadmeRenderer and DependencyParser get injected values, so the README text and dependency parsing are verified without writing any file.
last_updated: 2026-11-18

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from create_readme import (
    CONNECTOR_TYPES_PATH,
    ConnectorTypeCatalog,
    Dependency,
    DependencyParser,
    DependencyType,
    ReadmeRenderer,
    ReadmeSpec,
    Required,
)

CONNECTOR_TYPES = frozenset({"SLACK", "JIRA_CLOUD"})

SPACE = Dependency(
    name="Quick adoption insights",
    kind=DependencyType.SPACE,
    required=Required.YES,
    link="https://docs.aws.amazon.com/quick/latest/userguide/working-with-spaces.html",
)


def _spec(dependencies: tuple[Dependency, ...] = ()) -> ReadmeSpec:
    return ReadmeSpec(
        skill_name="adoption-health",
        title="Adoption health",
        summary="Reports adoption health.",
        prefix="ah",
        dependencies=dependencies,
    )


class TestReadmeRenderer(unittest.TestCase):
    def test_header_has_description_and_no_origin(self) -> None:
        text = ReadmeRenderer(_spec()).render()
        self.assertTrue(text.startswith("---\n"))
        self.assertIn('description: "What adoption-health needs', text)
        self.assertNotIn("origin:", text)

    def test_has_standard_sections(self) -> None:
        text = ReadmeRenderer(_spec()).render()
        for section in ("## Pre-requisites", "## Installation", "## Getting started"):
            self.assertIn(section, text)
        self.assertNotIn("## Overview", text)

    def test_no_dependencies_writes_none(self) -> None:
        text = ReadmeRenderer(_spec()).render()
        self.assertIn("## Pre-requisites\n\nNone.\n", text)
        self.assertNotIn("set up each dependency", text)

    def test_dependency_row_links_its_name(self) -> None:
        text = ReadmeRenderer(_spec((SPACE,))).render()
        self.assertIn("| Name | Type | Required |", text)
        self.assertIn(f"| [Quick adoption insights]({SPACE.link}) | SPACE | Y |", text)
        self.assertIn("then set up each dependency above", text)

    def test_getting_started_uses_prefix(self) -> None:
        self.assertIn("Enter `ah help`", ReadmeRenderer(_spec()).render())


class TestDependencyParser(unittest.TestCase):
    def test_parse_connector_type_accepts_it(self) -> None:
        parsed = DependencyParser(
            "Slack|SLACK|N|https://example.com/slack", CONNECTOR_TYPES
        ).parse()
        self.assertEqual(parsed.kind, "SLACK")
        self.assertIs(parsed.required, Required.NO)

    def test_parse_dependency_type_accepts_it(self) -> None:
        parsed = DependencyParser(
            "Skill|SKILL|Y|https://example.com", CONNECTOR_TYPES
        ).parse()
        self.assertEqual(parsed.kind, DependencyType.SKILL)

    def test_parse_removed_built_in_type_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DependencyParser(
                "Slack|CLOUD_CONNECTOR_BUILT_IN|Y|https://example.com", CONNECTOR_TYPES
            ).parse()

    def test_parse_unknown_type_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DependencyParser(
                "Slack|CONNECTOR|Y|https://example.com", CONNECTOR_TYPES
            ).parse()

    def test_parse_wrong_field_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DependencyParser("Slack|SKILL|Y", CONNECTOR_TYPES).parse()


class TestConnectorTypeCatalog(unittest.TestCase):
    def test_load_shipped_file_lists_slack(self) -> None:
        self.assertIn("SLACK", ConnectorTypeCatalog(CONNECTOR_TYPES_PATH).load())


if __name__ == "__main__":
    unittest.main()
