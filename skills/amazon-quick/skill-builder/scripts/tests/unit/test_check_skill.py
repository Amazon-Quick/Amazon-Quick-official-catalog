"""
description: Unit tests for check_skill.py. Filesystem-free: each check is fed a SkillDocument built directly, so individual checks (checksum field, name format, tag balance) are verified without reading a file.
last_updated: 2026-09-13
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from check_skill import (
    CheckStatus,
    FileHeaderValidator,
    SkillDocument,
    _NameFormatCheck,
    _SkillChecksumFieldCheck,
    _TagBalanceCheck,
)

VALID_CHECKSUM = "sha256:" + "a" * 64


def _doc(frontmatter: str = "", body: str = "", dirname: str = "demo") -> SkillDocument:
    return SkillDocument(frontmatter=frontmatter, body=body, dirname=dirname)


class TestSkillChecksumFieldCheck(unittest.TestCase):
    def test_valid_checksum_passes(self) -> None:
        result = _SkillChecksumFieldCheck().run(
            _doc(frontmatter=f'checksum: "{VALID_CHECKSUM}"')
        )
        self.assertIs(result.status_code, CheckStatus.PASS)

    def test_missing_checksum_fails(self) -> None:
        result = _SkillChecksumFieldCheck().run(_doc(frontmatter="name: demo"))
        self.assertIs(result.status_code, CheckStatus.FAIL)

    def test_malformed_checksum_fails(self) -> None:
        result = _SkillChecksumFieldCheck().run(
            _doc(frontmatter='checksum: "sha256:nope"')
        )
        self.assertIs(result.status_code, CheckStatus.FAIL)


class TestNameFormatCheck(unittest.TestCase):
    def test_valid_kebab_passes(self) -> None:
        result = _NameFormatCheck().run(_doc(frontmatter='name: "my-skill"'))
        self.assertIs(result.status_code, CheckStatus.PASS)

    def test_uppercase_name_fails(self) -> None:
        result = _NameFormatCheck().run(_doc(frontmatter='name: "MySkill"'))
        self.assertIs(result.status_code, CheckStatus.FAIL)


class TestTagBalanceCheck(unittest.TestCase):
    def test_balanced_tags_pass(self) -> None:
        result = _TagBalanceCheck().run(_doc(body="<Rules>\n1. x\n</Rules>"))
        self.assertIs(result.status_code, CheckStatus.PASS)

    def test_unbalanced_tags_fail(self) -> None:
        result = _TagBalanceCheck().run(_doc(body="<Rules>\n1. x\n"))
        self.assertIs(result.status_code, CheckStatus.FAIL)


class TestFileHeaderValidator(unittest.TestCase):
    def test_compliant_python_header(self) -> None:
        text = '"""\ndescription: does x\nlast_updated: 2026-09-13\norigin: original\n"""\n'
        self.assertEqual(FileHeaderValidator(text, is_python=True).validate(), [])

    def test_compliant_markdown_header(self) -> None:
        text = (
            '---\ndescription: "x"\nlast_updated: 2026-09-13\n'
            "source_url: https://example.com\n---\n# Title\n"
        )
        self.assertEqual(FileHeaderValidator(text, is_python=False).validate(), [])

    def test_missing_provenance(self) -> None:
        text = '"""\ndescription: x\nlast_updated: 2026-09-13\n"""\n'
        self.assertEqual(
            FileHeaderValidator(text, is_python=True).validate(),
            ["source_url or origin"],
        )

    def test_missing_all_fields(self) -> None:
        missing = FileHeaderValidator(
            '"""just a docstring."""', is_python=True
        ).validate()
        self.assertEqual(
            set(missing), {"description", "last_updated", "source_url or origin"}
        )


if __name__ == "__main__":
    unittest.main()
